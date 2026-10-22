"""M1-04A check-pool selection: random selection by metadata only (no act bodies are read).

Cards come from the documented publication.pravo.gov.ru day feed. Candidates are
looked up in the official tree (actual.pravo attrsearch, then IPS search.json, as in
acquire_official_json_transfer.py::discover) and only their list of editions is read.

Profiles: `batch-01` (frozen; single-edition filter) and `batch-02` (official lookup is
metadata only, codes, pages 3..200, a long-document share filled first, documents
already used in development/reserved/batch 1 excluded).

Future selection schema /3 uses the opt-in pool adapter. A positive code quota
requires a separate `freeze-codes --day ISO --output DIR/selection.json` metadata
freeze passed as `--code-candidates`. The seed orders that list along with day-feed
candidates. Scope is explicit publication days, not a portal-wide census. The
200-page profile ceiling stays unchanged unless `--pages-max` is supplied; codes alone
may run to CODE_PAGES_MAX (500, owner decision 22.10.2026) whenever the code quota is positive.
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
# Owner decision 22.10.2026: codes may run up to 500 pages (KAS RF has 480); the
# profile ceiling for every other category is unchanged.
CODE_PAGES_MAX = 500
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
# Recognize a title, not a reference to a code inside another law's title.
ACT_PREFIX = re.compile(
    r"^(?:Федеральный (?:конституционный )?закон|Указ|Постановление|Распоряжение|Приказ)\b"
    r"[^\"«]*? от \d\d\.\d\d\.\d{4} № \S+\s*"
)
CODE_TITLE = re.compile(
    r"^(?:[\w-]+\s+)*кодекс\s+(?:[\w-]+\s+)*Российской Федерации(?:\s+.*)?$", re.IGNORECASE,
)


def repo_relative(path):
    """Path recorded in a selection: relative to the repository root, forward slashes."""
    resolved = Path(path).resolve()
    try:
        return resolved.relative_to(PROJECT).as_posix()
    except ValueError:
        return resolved.as_posix()


def resolve_repo_path(path):
    """Inverse of repo_relative; absolute paths (older selections) pass through."""
    path = Path(path)
    return path if path.is_absolute() else PROJECT / path


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
    title = _title(name) or _title(complex_name)
    if (CODE_TITLE.fullmatch(title) and not title.casefold().startswith(("о ", "об "))
            and not is_amending(title)):
        return "code"
    for category, pattern in CATEGORY_PREFIXES:
        if pattern.match(text):
            if category == "government_resolution" and APPROVED_TEXT_MARK not in _norm(name).lower():
                return None
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


def cheap_reason(row, already_used=frozenset(), pages_range=(PAGES_MIN, PAGES_MAX), code_pages_max=None):
    """Rejections decidable from feed metadata alone. ``code_pages_max`` raises the page
    ceiling for codes only."""
    if row["eo_number"] in already_used:
        return "already_used"
    if is_amending(row.get("title", "")):
        return "amending_act"
    upper = code_pages_max if code_pages_max and row.get("act_type") == "code" else pages_range[1]
    if not pages_range[0] <= row["pages"] <= upper:
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


class QuotaCounter:
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
                pages_range=(PAGES_MIN, PAGES_MAX), long_min=0, long_pages=LONG_PAGES, code_pages_max=None):
    """Seeded selection. With long_min, a first pass fills the share of acts with at
    least long_pages pages, then a second pass fills the remaining quotas."""
    rows = [row for row in ordered(candidates, seed) if row["act_type"] in quotas]
    reasons = {}
    for row in rows:
        reason = cheap_reason(row, already_used, pages_range, code_pages_max)
        if reason is None and require_single_edition:
            reason = official_reason(row)
        reasons[row["eo_number"]] = reason
    counter, taken, selected = QuotaCounter(quotas, long_min, long_pages), set(), []
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
    result = {"schema_version": SCHEMA, "seed": seed, "quotas": dict(quotas),
              "require_single_edition": require_single_edition,
              "pages_range": list(pages_range), "long_min": long_min, "long_pages": long_pages,
              "long_selected": counter.long, "selected": selected, "rejected": rejected}
    if code_pages_max:
        result["code_pages_max"] = code_pages_max
    return result


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


def feed_candidates(publication, day, diagnostics=None):
    """Feed-only cards for one publication day (all pages), quota-relevant types only."""
    cards, page, total = [], 1, 1
    while page <= total:
        feed = _retry(lambda: publication.fetch_feed(day, page))
        if diagnostics is not None:
            diagnostics.append({"date": day.isoformat(), "page": page, "source_url": feed["source_url"],
                                "sha256": hashlib.sha256(feed["raw_bytes"]).hexdigest(),
                                "rejected_items": feed.get("rejected_items", [])})
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


CODE_CANDIDATES_SCHEMA = "m1-04a-code-candidates/1"


def freeze_code_candidates(publication, days, output):
    """Freeze all code candidates from explicit publication days, before any body fetch."""
    if selection_pair_state(output) != "absent":
        raise FileExistsError(f"code candidate selection already exists: {output}")
    pages, candidates = [], {}
    for day in sorted(set(days)):
        for row in feed_candidates(publication, day, pages):
            if row["act_type"] == "code":
                candidates.setdefault(row["eo_number"], row)
    result = {"schema_version": CODE_CANDIDATES_SCHEMA,
              "scope": "All non-amending code titles in the listed publication days; not a portal-wide census",
              "days": [d.isoformat() for d in sorted(set(days))], "feed_pages": pages,
              "candidates": sorted(candidates.values(), key=lambda r: r["eo_number"])}
    payload = (json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()
    write_selection_pair(output, payload)


def load_code_candidates(path):
    path = Path(path)
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != path.with_name("selection.sha256").read_text(encoding="utf-8").split()[0]:
        raise ValueError("code candidates differ from recorded sha256")
    result = json.loads(raw)
    if result["schema_version"] != CODE_CANDIDATES_SCHEMA:
        raise ValueError("unsupported code candidates schema")
    rows = result["candidates"]
    seen = set()
    for row in rows:
        eo = row["eo_number"]
        if (not isinstance(eo, str) or not re.fullmatch(r"[0-9]{16}", eo) or eo in seen
                or row["act_type"] != "code" or categorize("", row["title"]) != "code"
                or not isinstance(row["number"], str) or not row["number"].strip()
                or type(row["pages"]) is not int or row["pages"] <= 0):
            raise ValueError("invalid code candidate metadata")
        date.fromisoformat(row["date"])
        seen.add(eo)
    return rows, digest


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
           pages_range=(PAGES_MIN, PAGES_MAX), long_min=0, long_pages=LONG_PAGES, code_pages_max=None):
    """Single-edition profile: look up candidates in selection order until the quotas are
    filled. Counters are incremental (one pass per phase), mirroring select_pool."""
    rows = [row for row in ordered(pool.values(), seed) if row["act_type"] in quotas]
    counter, taken = QuotaCounter(quotas, long_min, long_pages), set()
    for long_phase in counter.phases():
        for row in rows:
            if counter.full():
                return
            eo = row["eo_number"]
            if (eo in taken or cheap_reason(row, already_used, pages_range, code_pages_max) is not None
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
MIN_DAYS_CHOICES = (0, 60, 120)  # the run checks quotas only after 60 and 120 days
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
    from legal_rag.sources.publication_pool import PublicationPoolConnector

    output = Path(args.output)
    state = selection_pair_state(output)
    if state == "complete":
        print("unchanged", hashlib.sha256(output.read_bytes()).hexdigest(), flush=True)
        return 0
    if state == "partial":
        raise FileExistsError(f"incomplete selection pair in {output.parent}; refusing to run")
    profile = PROFILES[args.profile]
    quotas = override_quotas(profile["quotas"], args.quota)
    if args.code_candidates and not quotas.get("code", 0):
        raise ValueError("--code-candidates given but the code quota is zero; "
                         "drop --code-candidates or set a positive code quota")
    pages_range, long_min = profile["pages_range"], profile["long_min"]
    if args.pages_max is not None:
        if args.pages_max < pages_range[0]:
            raise ValueError("--pages-max must be at least the profile's minimum")
        pages_range = (pages_range[0], args.pages_max)
    strict = profile["require_single_edition"]
    used = load_already_used(USED_INDEXES, USED_SELECTIONS) if profile["exclude_used"] else set()
    code_pages_max = CODE_PAGES_MAX if quotas.get("code", 0) else None
    options = {"require_single_edition": strict, "already_used": used, "pages_range": pages_range,
               "long_min": long_min, "long_pages": LONG_PAGES, "code_pages_max": code_pages_max}
    code_rows, code_reference = [], None
    if quotas.get("code", 0):
        if not args.code_candidates:
            raise ValueError("a code quota requires --code-candidates frozen by freeze-codes")
        code_rows, digest = load_code_candidates(args.code_candidates)
        code_rows = [r for r in code_rows if args.date_from <= r["date"] <= args.date_to]
        code_reference = {"path": repo_relative(args.code_candidates), "sha256": digest}
    publication = PublicationPoolConnector(timeout=25, request_interval=1)
    actual = ActualPravoConnector(timeout=25, request_interval=1)
    ips = LegislationRussiaConnector(timeout=25, request_interval=1)
    all_days = sample_days(date.fromisoformat(args.date_from), date.fromisoformat(args.date_to), args.seed)
    cache = load_feed_cache(args.feed_cache)
    pool = {row["eo_number"]: row for row in code_rows}
    enriched, failed_days, sampled, feed_pages = {}, [], 0, []
    for limit in (60, 120):
        for day in all_days[sampled:limit]:
            key = day.isoformat()
            if key not in cache:
                try:
                    diagnostics = []
                    cards = feed_candidates(publication, day, diagnostics)
                    cache[key] = {"candidates": cards, "feed_pages": diagnostics}
                except Exception as error:  # a bad day is recorded, never silently dropped
                    cache[key] = {"error": f"{type(error).__name__}: {error}"}
            if isinstance(cache[key], dict) and "error" in cache[key]:
                failed_days.append({"date": key, "error": cache[key]["error"]})
                continue
            day_result = cache[key]
            if isinstance(day_result, dict):
                feed_pages.extend(day_result["feed_pages"])
                day_result = day_result["candidates"]
            for row in day_result:
                pool.setdefault(row["eo_number"], row)
            print("day", key, "pool", len(pool), flush=True)
        sampled = limit
        if args.feed_cache:
            Path(args.feed_cache).write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
        if strict:
            enrich(pool, enriched, actual, ips, quotas, args.seed, used, pages_range, long_min, LONG_PAGES,
                   code_pages_max)
            rows = list(enriched.values()) + [r for r in pool.values() if r["eo_number"] not in enriched
                                              and cheap_reason(r, used, pages_range, code_pages_max) is not None]
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
        "schema_version": "m1-04a-pool-selection/3",
        "publication_adapter": publication.adapter_version,
        "code_candidates": code_reference,
        "feed_pages": feed_pages,
        "profile": args.profile,
        "min_days": args.min_days,
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
                                 "code = standalone code title, independent of the portal type; "
                                 "targeted code candidates frozen separately before selection",
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


# ---------------------------------------------------------------- refill of failed acquisitions

REFILL_SCHEMA = "m1-04a-pool-refill/1"
MAX_REFILL_ATTEMPTS = 3
REFILL_PROCEDURE = (
    "Each failed slot is replaced by the first candidate of the same category in the original seeded "
    "order (sha256(seed:eo_number)), after the same exclusions (already_used, amending acts, page range) "
    "and excluding every act selected or failed so far; the long-document share is kept at long_min "
    "(a long candidate is required only when the share is below it). Feed cache and seed are those of "
    "the frozen selection; nothing is looked up."
)


def pool_from_cache(cache, days):
    """Unique feed cards of the sampled days; days that failed in the cache are skipped as in the run."""
    pool = {}
    for day in days:
        cards = cache.get(day)
        if isinstance(cards, dict):
            cards = cards.get("candidates")
        if isinstance(cards, list):
            for row in cards:
                pool.setdefault(row["eo_number"], row)
    return pool


def refill(selection, pool, failures, *, taken=(), attempts=None):
    """Replace failed slots deterministically (pure, no I/O).

    `selection` carries seed, page range, long share, `already_used` and `selected` = the acts that
    currently fill slots (failed ones included). `failures` maps failed eo -> reason, `taken` are
    all acts selected so far (earlier refills too), `attempts` maps an act to its refill attempt
    number (original acts: 0)."""
    attempts = attempts or {}
    used = set(selection.get("already_used", ())) | set(taken) | set(failures)
    pages_range, seed = tuple(selection["pages_range"]), selection["seed"]
    code_pages_max = selection.get("code_pages_max")
    long_min, long_pages = selection["long_min"], selection["long_pages"]
    by_eo = {row["eo_number"]: row for row in selection["selected"]}
    kept = [row for row in selection["selected"] if row["eo_number"] not in failures]
    replaced, chosen = [], []
    for eo in sorted(failures, key=lambda e: order_key(seed, e)):
        failed = by_eo[eo]
        attempt = attempts.get(eo, 0) + 1
        if attempt > MAX_REFILL_ATTEMPTS:
            raise ValueError(f"slot of {eo} exhausted {MAX_REFILL_ATTEMPTS} refill attempts")
        need_long = sum(r["pages"] >= long_pages for r in kept + chosen) < long_min
        for row in ordered(pool.values(), seed):
            if row["act_type"] != failed["act_type"] or row["eo_number"] in used:
                continue
            if cheap_reason(row, frozenset(), pages_range, code_pages_max) is not None:
                continue
            if need_long and row["pages"] < long_pages:
                continue
            break
        else:
            raise ValueError(f"no candidate left for the slot of {eo}")
        used.add(row["eo_number"])
        new = {key: row[key] for key in METADATA_FIELDS if key in row}
        chosen.append(new)
        replaced.append({"failed_eo_number": eo, "failed_reason": failures[eo], "act_type": failed["act_type"],
                         "attempt": attempt, "replacement": new})
    result = {"schema_version": REFILL_SCHEMA, "seed": seed, "pages_range": list(pages_range),
              "long_min": long_min, "long_pages": long_pages, "procedure": REFILL_PROCEDURE,
              "replaced": replaced, "selected": chosen,
              "long_selected_after": sum(r["pages"] >= long_pages for r in kept + chosen)}
    if code_pages_max:
        result["code_pages_max"] = code_pages_max
    return result


def refill_files(batch_dir):
    """Existing refill records of a batch in round order, each verified against its `.sha256`."""
    out = []
    for path in sorted(Path(batch_dir).glob("selection-refill-??.json")):
        recorded = path.with_suffix(".sha256").read_text(encoding="utf-8").split()[0]
        if hashlib.sha256(path.read_bytes()).hexdigest() != recorded:
            raise ValueError(f"{path.name} differs from its sha256")
        out.append(json.loads(path.read_text(encoding="utf-8")))
    return out


def failure_reasons(failures_dir):
    """eo -> reason from the failure files `<eo>-<run>.json` (run report errors or recorded reason)."""
    reasons = {}
    for path in sorted(Path(failures_dir).glob("*.json")):
        eo = path.name[:16]
        record = json.loads(path.read_text(encoding="utf-8"))
        if "reason" in record and isinstance(record["reason"], str):
            reasons.setdefault(eo, record["reason"])
            continue
        try:
            errors = json.loads(Path(record["runs"][-1]["report"]).read_text(encoding="utf-8"))["errors"]
            reasons.setdefault(eo, "; ".join(f"{e['reason']}: {e['message']}" for e in errors))
        except (KeyError, OSError, IndexError):
            reasons.setdefault(eo, f"failed at {record.get('stage')}")
    return reasons


def refill_round(batch_dir, feed_cache, expected_sha=None):
    """Next refill record: acts with a failure file and no receipt that were not replaced yet."""
    batch_dir = Path(batch_dir)
    sel_path = batch_dir / "selection.json"
    digest = hashlib.sha256(sel_path.read_bytes()).hexdigest()
    recorded = (batch_dir / "selection.sha256").read_text(encoding="utf-8").split()[0]
    if digest != recorded or (expected_sha and not digest.startswith(expected_sha)):
        raise ValueError("selection.json differs from its recorded sha256")
    selection = json.loads(sel_path.read_text(encoding="utf-8"))
    prior = refill_files(batch_dir)
    pool = pool_from_cache(json.loads(Path(feed_cache).read_text(encoding="utf-8")), selection["days_sampled"])
    if selection.get("code_candidates"):
        reference = selection["code_candidates"]
        codes, code_digest = load_code_candidates(resolve_repo_path(reference["path"]))
        if code_digest != reference["sha256"]:
            raise ValueError("code candidates differ from frozen selection sha256")
        for row in codes:
            if selection["date_range"][0] <= row["date"] <= selection["date_range"][1]:
                pool.setdefault(row["eo_number"], row)
    attempts = {r["eo_number"]: 0 for r in selection["selected"]}
    acts = list(selection["selected"])
    for record in prior:
        acts += record["selected"]
        attempts.update({i["replacement"]["eo_number"]: i["attempt"] for i in record["replaced"]})
    replaced = {i["failed_eo_number"] for r in prior for i in r["replaced"]}
    reasons = failure_reasons(batch_dir / "failures")
    failed = {a["eo_number"]: reasons[a["eo_number"]] for a in acts
              if a["eo_number"] in reasons and a["eo_number"] not in replaced
              and not (batch_dir / "receipts" / f"{a['eo_number']}.json").exists()}
    if not failed:
        raise ValueError("no failed slot to refill")
    view = dict(selection, selected=[a for a in acts if a["eo_number"] not in replaced])
    result = refill(view, pool, failed, taken={a["eo_number"] for a in acts}, attempts=attempts)
    result.update({"round": len(prior) + 1, "base_selection_sha256": digest,
                   "feed_cache_sha256": hashlib.sha256(Path(feed_cache).read_bytes()).hexdigest()})
    return result


def write_refill(batch_dir, result):
    """Write-once `selection-refill-NN.json` + `.sha256`."""
    path = Path(batch_dir) / f"selection-refill-{result['round']:02d}.json"
    sha_path = path.with_suffix(".sha256")
    if path.exists() or sha_path.exists():
        raise FileExistsError(f"{path.name} already exists")
    payload = (json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    with path.open("xb") as stream:
        stream.write(payload)
    with sha_path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(f"{hashlib.sha256(payload).hexdigest()}  {path.name}\n")
    return hashlib.sha256(payload).hexdigest()


def refill_main(argv):
    parser = argparse.ArgumentParser(prog="select_m1_04a_pool.py refill")
    parser.add_argument("--batch-dir", required=True, type=Path)
    parser.add_argument("--feed-cache", required=True, type=Path)
    parser.add_argument("--selection-sha", help="expected sha256 prefix of the frozen selection.json")
    args = parser.parse_args(argv)
    result = refill_round(args.batch_dir, args.feed_cache, args.selection_sha)
    print("selection-refill", result["round"], write_refill(args.batch_dir, result), flush=True)
    return 0


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    if argv[:1] == ["refill"]:
        return refill_main(argv[1:])
    if argv[:1] == ["freeze-codes"]:
        from legal_rag.sources.publication_pool import PublicationPoolConnector

        parser = argparse.ArgumentParser(prog="select_m1_04a_pool.py freeze-codes")
        parser.add_argument("--day", action="append", required=True, type=date.fromisoformat,
                            help="target publication day; repeat to cover more days (all pages)")
        parser.add_argument("--output", required=True, type=Path,
                            help="new directory's selection.json; freezes metadata only")
        args = parser.parse_args(argv[1:])
        freeze_code_candidates(PublicationPoolConnector(timeout=25, request_interval=1), args.day, args.output)
        return 0
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
    parser.add_argument("--min-days", type=int, default=0, choices=MIN_DAYS_CHOICES,
                        help="sample at least this many days even if quotas fill earlier")
    parser.add_argument("--quota-change", help="JSON file whose object is recorded as `quota_change`")
    parser.add_argument("--code-candidates", type=Path, help="freeze-codes selection.json (required for code quota)")
    parser.add_argument("--pages-max", type=int, help="explicit page ceiling override (e.g. 500 for a 480-page code)")
    return run(parser.parse_args(argv))


if __name__ == "__main__":
    sys.exit(main())
