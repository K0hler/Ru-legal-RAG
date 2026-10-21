"""M1-04A check-pool selection: random selection by metadata only (no act bodies are read).

Cards come from the documented publication.pravo.gov.ru day feed. Candidates are
looked up in the official tree (actual.pravo attrsearch, then IPS search.json, as in
acquire_official_json_transfer.py::discover) and only their list of editions is read.

Profiles: `batch-01` (frozen; single-edition filter) and `batch-02` (official lookup is
metadata only, codes, pages 3..200, a long-document share filled first, documents
already used in development/reserved/batch 1 excluded).
"""

import argparse
import hashlib
import json
from pathlib import Path
import random
import re
import sys
import time
from datetime import date, timedelta
from urllib.parse import urlencode
from urllib.request import Request

PROJECT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT / "src"))

SCHEMA = "m1-04a-pool-selection/2"
# Batch-1 quotas (frozen selection, kept for reference) and batch-2 quotas.
DEFAULT_QUOTAS = {
    "federal_law": 2,
    "presidential_decree": 1,
    "government_resolution": 2,
    "government_order": 1,
    "ministry_order": 2,
}
BATCH2_QUOTAS = {
    "code": 1,
    "federal_law": 3,
    "presidential_decree": 1,
    "government_resolution": 2,
    "government_order": 1,
    "ministry_order": 2,
}
PAGES_MIN, PAGES_MAX = 3, 60
BATCH2_PAGES = (3, 200)
BATCH2_LONG_MIN, LONG_PAGES = 4, 20
# Titles that only change or repeal other acts (compared lowercase, after leading quotes).
AMENDING_PREFIXES = (
    "о внесении изменений",
    "о внесении изменения",
    "о внесении дополнений",
    "о признании утратившими силу",
    "о признании утратившим силу",
)
QUOTES = ' "«»“”'  # feed names of laws arrive quoted
# Rejection reasons. edition_count_unknown: the official tree answered but exposes no
# edition list, so "exactly one edition" cannot be established. lookup_error: the
# lookup itself failed (network/parse), distinct from a clean "not found".
REASONS = (
    "already_used",
    "amending_act",
    "pages_out_of_range",
    "lookup_error",
    "not_in_official_tree",
    "edition_count_unknown",
    "edition_count_not_1",
    "quota_full",
)
# Only metadata may reach a selected record.
METADATA_FIELDS = (
    "eo_number", "act_type", "date", "number", "title", "pages", "edition_count",
    "official_found", "official_source", "official_hash",
)

# The feed item carries only documentTypeId/signatoryAuthorityId (no names), so the
# type and signatory are read from the start of the feed `complexName`
# ("<Type> <issuer> от dd.mm.yyyy № N ..."). Mapping is data, not per-act logic.
GOV = "Правительства Российской Федерации"
CATEGORY_PREFIXES = (
    ("federal_law", re.compile(r"^Федеральный закон от ")),
    ("presidential_decree", re.compile(r"^Указ Президента Российской Федерации от ")),
    ("government_resolution", re.compile(rf"^Постановление {GOV} от ")),
    ("government_order", re.compile(rf"^Распоряжение {GOV} от ")),
)
ORDER_PREFIX = re.compile(r"^Приказ (.+?) от \d\d\.\d\d\.\d{4}")
FEDERAL_BODY = re.compile(
    r"^(Министерства\b.*Российской Федерации|Федеральной .*службы|Федерального (агентства|казначейства))"
)
REGIONAL_MARK = re.compile(
    r"област|кра[яе]\b|республик|автономн|округ|город|москв|санкт|севастопол|район|управлени",
    re.IGNORECASE,
)
APPROVED_TEXT_MARK = "утвержд"  # government resolutions need an approved text
# A code is a federal law titled "<...> кодекс <...> Российской Федерации" (the word
# "кодекс" in the nominative), e.g. "Градостроительный кодекс Российской Федерации".
ACT_PREFIX = re.compile(
    r"^(?:Федеральный (?:конституционный )?закон|Указ|Постановление|Распоряжение|Приказ)\b"
    r"[^\"«]*? от \d\d\.\d\d\.\d{4} № \S+\s*"
)
CODE_TITLE = re.compile(r"^(?:.*\s)?кодекс(?:\s.*)?\sРоссийской Федерации$", re.IGNORECASE)


def _norm(value):
    return " ".join(str(value).split())


def _title(value):
    """Bare title: older feed names repeat "<Type> от dd.mm.yyyy № N" before the quoted title."""
    return ACT_PREFIX.sub("", _norm(value).strip(QUOTES), count=1).strip(QUOTES)


def is_amending(title):
    return _title(title).lower().startswith(AMENDING_PREFIXES)


def categorize(complex_name, name):
    """Quota category from feed metadata, or None (ignored, not a rejection)."""
    text = _norm(complex_name)
    for category, pattern in CATEGORY_PREFIXES:
        if pattern.match(text):
            if category == "government_resolution" and APPROVED_TEXT_MARK not in _norm(name).lower():
                return None
            if category == "federal_law" and CODE_TITLE.match(_title(name)) and not is_amending(name):
                return "code"
            return category
    match = ORDER_PREFIX.match(text)
    if match and FEDERAL_BODY.match(match.group(1)) and not REGIONAL_MARK.search(match.group(1)):
        return "ministry_order"
    return None


def order_key(seed, eo_number):
    return hashlib.sha256(f"{seed}:{eo_number}".encode()).hexdigest()


def ordered(candidates, seed):
    """Deterministic seeded order, independent of input order and of other candidates."""
    return sorted(candidates, key=lambda row: order_key(seed, row["eo_number"]))


def cheap_reason(row, already_used=frozenset(), pages_range=(PAGES_MIN, PAGES_MAX)):
    """Rejections decidable from feed metadata alone."""
    if row["eo_number"] in already_used:
        return "already_used"
    if is_amending(row.get("title", "")):
        return "amending_act"
    if not pages_range[0] <= row["pages"] <= pages_range[1]:
        return "pages_out_of_range"
    return None


def official_reason(row):
    """Rejections from the official-tree lookup (used only with require_single_edition)."""
    if row.get("lookup_error"):
        return "lookup_error"
    if not row.get("in_official_tree"):
        return "not_in_official_tree"
    if row.get("edition_count") is None:
        return "edition_count_unknown"
    if row["edition_count"] != 1:
        return "edition_count_not_1"
    return None


class Counter:
    """Incremental quota/long-share counters shared by select_pool and enrich."""

    def __init__(self, quotas, long_min, long_pages):
        self.quotas, self.long_min, self.long_pages = quotas, long_min, long_pages
        self.counts = {kind: 0 for kind in quotas}
        self.long = 0

    def is_long(self, row):
        return row["pages"] >= self.long_pages

    def wants(self, row, long_phase):
        if self.counts[row["act_type"]] >= self.quotas[row["act_type"]]:
            return False
        return not long_phase or (self.is_long(row) and self.long < self.long_min)

    def take(self, row):
        self.counts[row["act_type"]] += 1
        self.long += self.is_long(row)

    def full(self):
        return all(self.counts[k] >= q for k, q in self.quotas.items()) and self.long >= self.long_min

    def phases(self):
        return (True, False) if self.long_min else (False,)


def select_pool(candidates, quotas, seed, *, require_single_edition=True, already_used=frozenset(),
                pages_range=(PAGES_MIN, PAGES_MAX), long_min=0, long_pages=LONG_PAGES):
    """Seeded selection. With long_min, a first pass fills the share of acts with at
    least long_pages pages, then a second pass fills the remaining quotas."""
    rows = [row for row in ordered(candidates, seed) if row["act_type"] in quotas]
    reasons = {}
    for row in rows:
        reason = cheap_reason(row, already_used, pages_range)
        if reason is None and require_single_edition:
            reason = official_reason(row)
        reasons[row["eo_number"]] = reason
    counter, taken, selected = Counter(quotas, long_min, long_pages), set(), []
    for long_phase in counter.phases():
        for row in rows:
            eo = row["eo_number"]
            if eo in taken or reasons[eo] is not None or not counter.wants(row, long_phase):
                continue
            counter.take(row)
            taken.add(eo)
            selected.append({key: row[key] for key in METADATA_FIELDS if key in row})
    rejected = [{"eo_number": row["eo_number"], "reason": reasons[row["eo_number"]] or "quota_full"}
                for row in rows if row["eo_number"] not in taken]
    return {"schema_version": SCHEMA, "seed": seed, "quotas": dict(quotas),
            "require_single_edition": require_single_edition,
            "pages_range": list(pages_range), "long_min": long_min, "long_pages": long_pages,
            "long_selected": counter.long, "selected": selected, "rejected": rejected}


def selected_counts(result):
    counts = {kind: 0 for kind in result["quotas"]}
    for row in result["selected"]:
        counts[row["act_type"]] += 1
    return counts


def quotas_full(result):
    counts = selected_counts(result)
    return (all(counts[kind] >= quota for kind, quota in result["quotas"].items())
            and result.get("long_selected", 0) >= result.get("long_min", 0))


def load_already_used(index_paths, selection_paths):
    """eo numbers of documents already in development/reserved/pool indexes and
    selected in earlier batches. Reads metadata files only, never document bodies."""
    used = set()
    for path in index_paths:
        for doc in json.loads(Path(path).read_text(encoding="utf-8"))["documents"]:
            used.update(re.findall(r"eoNumber=(\d{16})", doc.get("source_url", "")))
    for path in selection_paths:
        used.update(row["eo_number"] for row in json.loads(Path(path).read_text(encoding="utf-8"))["selected"])
    return used


def selection_pair_state(output):
    present = [Path(output).exists(), Path(output).with_name("selection.sha256").exists()]
    return "complete" if all(present) else "partial" if any(present) else "absent"


def write_selection_pair(output, payload):
    """Write-once selection.json + selection.sha256: both are checked before either is written."""
    output = Path(output)
    sha_path = output.with_name("selection.sha256")
    state = selection_pair_state(output)
    if state == "complete":
        return "unchanged"
    if state == "partial":
        raise FileExistsError(f"incomplete selection pair in {output.parent}; refusing to write")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("xb") as stream:
        stream.write(payload)
    with sha_path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(f"{hashlib.sha256(payload).hexdigest()}  {output.name}\n")
    return "written"


def count_actual_editions(response):
    """Complete official editions in an actual.pravo redactions response."""
    if not isinstance(response, dict) or response.get("error") or not isinstance(response.get("redactions"), list):
        return None
    flags = ("redofficial", "redcompleted", "hascontent", "contentcomplete")
    return sum(
        1 for e in response["redactions"]
        if isinstance(e, dict) and all(e.get(k) is True for k in flags)
    )


def count_ips_editions(card):
    """Completed editions in an IPS document card (the list the connector reads)."""
    if not isinstance(card, dict) or not isinstance(card.get("redactions"), list):
        return None
    return sum(1 for e in card["redactions"] if isinstance(e, dict) and e.get("completed") is True)


# ---------------------------------------------------------------- network layer

def _retry(call, attempts=3):
    for attempt in range(attempts):
        try:
            return call()
        except Exception:
            if attempt == attempts - 1:
                raise
            time.sleep(2 * (attempt + 1))


def _ips_search(ips, number, dmy):
    from legal_rag.sources.legislation_russia import urlopen

    url = ips._api_base + "/search.json"
    params = {"searchType": "attrSearch", "number_eq": number, "date": dmy, "page": 1, "limit": 10, "sort": "-date"}
    ips._meter.before_request()
    request = Request(url, data=urlencode(params).encode(),
                      headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"})
    with urlopen(request, timeout=25) as response:
        body = response.read()
    ips._meter.record_response(body)
    return json.loads(body).get("docs", [])  # no hits: the key is absent


def lookup_official(actual, ips, number, iso):
    """Find one act in the official tree by number+date and count its editions."""
    dmy = ".".join(reversed(iso.split("-")))
    compact = iso.replace("-", "")
    attrs = [{"AttrId": 6, "AttrMode": 0, "Words": [number]},
             {"AttrId": 5, "AttrMode": 0, "DateFrom": compact, "DateTo": compact}]
    # No AttrId 999 ("position") filter: it hid acts such as 22-FZ/2018 from attrsearch
    # (data/m1/m1-04a/experiments/20261021-actual-lookup-diagnosis/); the exact
    # number/date filter below keeps a single identity.
    query = urlencode({"bpa": "ebpi", "q": json.dumps(attrs, separators=(",", ":"))})
    url = actual._api_base + "/attrsearch/?" + query
    body, _ = _retry(lambda: actual._get(url))
    docs = [d for d in json.loads(body).get("docs", [])
            if str(d.get("docpass0number")).upper() == number.upper() and d.get("docpass0date") == compact]
    if len(docs) == 1:
        h = docs[0]["dochash"]
        rb, _ = _retry(lambda: actual._get(actual._url("redactions/", {"hash": h, "ttl": 4})))
        return {"in_official_tree": True, "official_source": "actual", "official_hash": h,
                "edition_count": count_actual_editions(json.loads(rb))}
    if len(docs) > 1:
        return {"in_official_tree": False, "detail": "ambiguous_official_identity"}
    docs = [d for d in _retry(lambda: _ips_search(ips, number, dmy))
            if d.get("docdate") == dmy and str(d.get("adoption", "")).upper().endswith("№ " + number.upper())]
    if len(docs) == 1:
        h = docs[0]["hash"]
        card_url = ips._api_base + "/document_card.json?" + urlencode({"hash": h})
        cb, _ = _retry(lambda: ips._get(card_url))
        return {"in_official_tree": True, "official_source": "ips", "official_hash": h,
                "edition_count": count_ips_editions(json.loads(cb))}
    return {"in_official_tree": False,
            "detail": "ambiguous_official_identity" if docs else "not_found"}


def feed_candidates(publication, day):
    """Feed-only cards for one publication day (all pages), quota-relevant types only."""
    cards, page, total = [], 1, 1
    while page <= total:
        feed = _retry(lambda: publication.fetch_feed(day, page))
        total = feed["pages_total"]
        for item in feed["events"]:
            kind = categorize(item["complexName"], item["name"])
            if kind is None:
                continue
            cards.append({
                "eo_number": item["eoNumber"], "act_type": kind,
                "date": item["documentDate"][:10], "number": item["number"].strip(),
                "title": _norm(item["name"]), "pages": item["pagesCount"],
            })
        page += 1
    return cards


def sample_days(start, end, seed, count=120):
    days = [start + timedelta(days=i) for i in range((end - start).days + 1)]
    return random.Random(seed).sample(days, count)


def lookup(actual, ips, row):
    """Official-tree metadata for one card; a failing lookup is a distinct lookup_error."""
    try:
        info = lookup_official(actual, ips, row["number"], row["date"])
    except Exception as error:  # network/parse failure, not a clean "not found"
        info = {"in_official_tree": False, "lookup_error": f"{type(error).__name__}: {error}"}
    info["official_found"] = None if info.get("lookup_error") else bool(info["in_official_tree"])
    print(row["act_type"], row["number"], row["date"], info, flush=True)
    return info


def enrich(pool, enriched, actual, ips, quotas, seed, already_used=frozenset(),
           pages_range=(PAGES_MIN, PAGES_MAX), long_min=0, long_pages=LONG_PAGES):
    """Single-edition profile: look up candidates in selection order until the quotas are
    filled. Counters are incremental (one pass per phase), mirroring select_pool."""
    rows = [row for row in ordered(pool.values(), seed) if row["act_type"] in quotas]
    counter, taken = Counter(quotas, long_min, long_pages), set()
    for long_phase in counter.phases():
        for row in rows:
            if counter.full():
                return
            eo = row["eo_number"]
            if (eo in taken or cheap_reason(row, already_used, pages_range) is not None
                    or not counter.wants(row, long_phase)):
                continue
            if eo not in enriched:
                enriched[eo] = dict(row, **lookup(actual, ips, row))
            if official_reason(enriched[eo]) is None:
                counter.take(row)
                taken.add(eo)


PROFILES = {
    "batch-01": {"quotas": DEFAULT_QUOTAS, "pages_range": (PAGES_MIN, PAGES_MAX), "long_min": 0,
                 "require_single_edition": True, "exclude_used": False},
    "batch-02": {"quotas": BATCH2_QUOTAS, "pages_range": BATCH2_PAGES, "long_min": BATCH2_LONG_MIN,
                 "require_single_edition": False, "exclude_used": True},
}
DOCUMENTS = PROJECT / "data/m1/m1-04a/documents"
USED_INDEXES = (DOCUMENTS / "index.json", DOCUMENTS / "pool/batch-01/index.json")
USED_SELECTIONS = (DOCUMENTS / "pool/batch-01/selection.json",)


def override_quotas(base, overrides):
    """Apply KIND=N overrides to a copy of the profile quotas; unknown kinds are refused."""
    quotas = dict(base)
    for item in overrides:
        kind, _, value = item.partition("=")
        if kind not in quotas or not value.isdigit():
            raise ValueError(f"bad quota override {item!r}; kinds: {sorted(quotas)}")
        quotas[kind] = int(value)
    return quotas


def load_feed_cache(path):
    if path and Path(path).exists():
        return json.loads(Path(path).read_text(encoding="utf-8"))
    return {}


def run(args):
    from legal_rag.sources.actual_pravo import ActualPravoConnector
    from legal_rag.sources.legislation_russia import LegislationRussiaConnector
    from legal_rag.sources.publication_pravo import PublicationPravoConnector

    output = Path(args.output)
    state = selection_pair_state(output)
    if state == "complete":
        print("unchanged", hashlib.sha256(output.read_bytes()).hexdigest(), flush=True)
        return 0
    if state == "partial":
        raise FileExistsError(f"incomplete selection pair in {output.parent}; refusing to run")
    profile = PROFILES[args.profile]
    quotas = override_quotas(profile["quotas"], args.quota)
    pages_range, long_min = profile["pages_range"], profile["long_min"]
    strict = profile["require_single_edition"]
    used = load_already_used(USED_INDEXES, USED_SELECTIONS) if profile["exclude_used"] else set()
    options = {"require_single_edition": strict, "already_used": used, "pages_range": pages_range,
               "long_min": long_min, "long_pages": LONG_PAGES}
    publication = PublicationPravoConnector(timeout=25, request_interval=1)
    actual = ActualPravoConnector(timeout=25, request_interval=1)
    ips = LegislationRussiaConnector(timeout=25, request_interval=1)
    all_days = sample_days(date.fromisoformat(args.date_from), date.fromisoformat(args.date_to), args.seed)
    cache = load_feed_cache(args.feed_cache)
    pool, enriched, failed_days, sampled = {}, {}, [], 0
    for limit in (60, 120):
        for day in all_days[sampled:limit]:
            key = day.isoformat()
            if key not in cache:
                try:
                    cache[key] = feed_candidates(publication, day)
                except Exception as error:  # a bad day is recorded, never silently dropped
                    cache[key] = {"error": f"{type(error).__name__}: {error}"}
            if isinstance(cache[key], dict):
                failed_days.append({"date": key, "error": cache[key]["error"]})
                continue
            for row in cache[key]:
                pool.setdefault(row["eo_number"], row)
            print("day", key, "pool", len(pool), flush=True)
        sampled = limit
        if args.feed_cache:
            Path(args.feed_cache).write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
        if strict:
            enrich(pool, enriched, actual, ips, quotas, args.seed, used, pages_range, long_min, LONG_PAGES)
            rows = list(enriched.values()) + [r for r in pool.values() if r["eo_number"] not in enriched
                                              and cheap_reason(r, used, pages_range) is not None]
        else:
            rows = list(pool.values())
        result = select_pool(rows, quotas, args.seed, **options)
        if quotas_full(result) and limit >= args.min_days:
            break
    looked_up = len(enriched)
    if not strict:  # official lookup is metadata for the selected acts only, not a filter
        for row in result["selected"]:
            info = lookup(actual, ips, row)
            enriched[row["eo_number"]] = info
            row.update({k: info[k] for k in METADATA_FIELDS if k in info})
            if info.get("lookup_error") or info.get("detail"):
                row["official_lookup_detail"] = info.get("lookup_error") or info.get("detail")
        looked_up = len(result["selected"])
    for row in result["rejected"]:
        info = enriched.get(row["eo_number"], {})
        if info.get("lookup_error") or info.get("detail"):
            row["detail"] = info.get("lookup_error") or info.get("detail")
    reasons = {}
    for row in result["rejected"]:
        reasons[row["reason"]] = reasons.get(row["reason"], 0) + 1
    if args.quota_change:
        result["quota_change"] = json.loads(Path(args.quota_change).read_text(encoding="utf-8"))
    result.update({
        "profile": args.profile,
        "date_range": [args.date_from, args.date_to],
        "days_sampled": [d.isoformat() for d in all_days[:sampled]],
        "days_failed": failed_days,
        "candidates_per_category": {k: sum(1 for r in pool.values() if r["act_type"] == k) for k in quotas},
        "selected_per_category": selected_counts(result),
        "rejection_counts": reasons,
        "already_used": sorted(used),
        "looked_up_in_official_tree": looked_up,
        "official_lookup": ("filter: exactly one complete official edition" if strict else
                            "metadata only (official_found), looked up for selected acts after selection"),
        "quotas_filled": quotas_full(result),
        "classification_source": "feed complexName prefix (feed items carry only type/authority ids); "
                                 "number and date from feed `number` and `documentDate`; "
                                 "code = federal law titled '... кодекс ... Российской Федерации'",
    })
    payload = (json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    if not result["quotas_filled"]:
        # An incomplete batch is not frozen: the selection pair stays unwritten.
        if args.partial_output:
            Path(args.partial_output).write_bytes(payload)
        print("quotas not filled", result["selected_per_category"], "long", result["long_selected"],
              "partial", args.partial_output, flush=True)
        return 3
    status = write_selection_pair(output, payload)
    print("selection.json", status, "sha256", hashlib.sha256(payload).hexdigest(), flush=True)
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from", dest="date_from", required=True)
    parser.add_argument("--to", dest="date_to", required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--profile", choices=sorted(PROFILES), default="batch-01")
    parser.add_argument("--feed-cache", help="optional JSON cache of feed cards per day (outside data/)")
    parser.add_argument("--partial-output", help="where to write an unfilled result (not frozen)")
    parser.add_argument("--quota", action="append", default=[], metavar="KIND=N",
                        help="override one profile quota (recorded decision only)")
    parser.add_argument("--min-days", type=int, default=0,
                        help="sample at least this many days (60 or 120) even if quotas fill earlier")
    parser.add_argument("--quota-change", help="JSON file whose object is recorded as `quota_change`")
    return run(parser.parse_args(argv))


if __name__ == "__main__":
    sys.exit(main())
