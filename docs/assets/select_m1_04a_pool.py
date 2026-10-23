"""M1-04A check-pool selection: random selection by metadata only (no act bodies are read).

Cards come from the documented publication.pravo.gov.ru day feed. Candidates are
looked up in the official tree (actual.pravo attrsearch, then IPS search.json, as in
acquire_official_json_transfer.py::discover) and only their list of editions is read.

Profiles: `batch-01` (frozen; single-edition filter) and `batch-02` (official lookup is
metadata only, codes, pages 3..200, a long-document share filled first, documents
already used in development/reserved/batch 1 excluded). `batch-03` takes every census
code up to 2 (code quota = min(2, frozen code candidates)), excludes batches 1-2 with
their refill picks and every failed acquisition, and samples 120 days that no earlier
batch sampled. `batch-04` has no code quota (11 acts, at least 4 long) and excludes
batches 1-3 the same way. `batch-05` keeps the batch-04 quotas, excludes batches 1-4 and adds
soft preferences (acts of 5+ pages; one act per type, issuer and publication day): every pass
runs with them first, then without them for open quotas (long share first), and `soft_fallbacks` records each
pick that misses one. A newly frozen selection gets a write-once `selection-provenance.json`
(exact command, `min_days`, feed-cache hash, code commit).

Future selection schema /3 uses the opt-in pool adapter. A positive code quota
requires a separate `freeze-codes --day ISO --output DIR/selection.json` metadata
freeze passed as `--code-candidates`. The seed orders that list along with day-feed
candidates. Scope is explicit publication days, not a portal-wide census. The
200-page profile ceiling stays unchanged unless `--pages-max` is supplied; codes alone
may run to CODE_PAGES_MAX (500, owner decision 22.10.2026) whenever the code quota is positive.

`census-codes --output DIR/selection.json` is the code census: every CODE_REFERENCE code is
verified in actual.pravo (number+date), its portal publication is confirmed in the day feed,
`freeze-codes` runs on the eligible days and `census.json` records each code's reason.
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
BATCH3_QUOTAS = {
    "code": 2,  # upper bound: the effective quota is min(2, frozen census codes)
    "federal_law": 2,
    "presidential_decree": 1,
    "government_resolution": 2,
    "government_order": 1,
    "ministry_order": 2,
}
# Batch 4: no code quota (the census has only KAS, already in development).
BATCH4_QUOTAS = {
    "federal_law": 3,
    "presidential_decree": 1,
    "government_resolution": 2,
    "government_order": 2,
    "ministry_order": 3,
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


SOFT_MISSES = ("issuer_day_repeat", "pages_below_preferred")
ISSUER_FIELDS = ("issuer", "publication_date")


class SoftPreferences:
    """Batch-05 soft preferences (owner wish 23.10.2026, plan Review Focus 1-2).

    Every pass runs first with the preferences, then once more without them for the
    quotas still open; a pick that misses a preference is recorded as a soft fallback.
    ``preferred_pages_min``: prefer acts with at least that many pages.
    ``one_per_issuer_day``: prefer at most one act per (type, issuer, publication day);
    a card without issuer or publication day is never treated as a repeat."""

    def __init__(self, preferred_pages_min=None, one_per_issuer_day=False):
        self.pages_min, self.per_issuer_day = preferred_pages_min, one_per_issuer_day
        self.active = bool(preferred_pages_min or one_per_issuer_day)
        self.keys = set()

    def key(self, row):
        if not self.per_issuer_day or not row.get("issuer") or not row.get("publication_date"):
            return None
        return row["act_type"], row["issuer"], row["publication_date"]

    def misses(self, row):
        out = []
        key = self.key(row)
        if key is not None and key in self.keys:
            out.append("issuer_day_repeat")
        if self.pages_min and row["pages"] < self.pages_min:
            out.append("pages_below_preferred")
        return out

    def take(self, row):
        key = self.key(row)
        if key is not None:
            self.keys.add(key)

    def passes(self, phases):
        """(soft, long_phase) passes: each phase runs with the preferences, then without them.
        The long share stays a hard requirement: its relaxed pass runs before the short-phase
        passes, which could otherwise fill the quotas with short acts."""
        return [(soft, phase) for phase in phases for soft in ((True, False) if self.active else (False,))]


def select_pool(candidates, quotas, seed, *, require_single_edition=True, already_used=frozenset(),
                pages_range=(PAGES_MIN, PAGES_MAX), long_min=0, long_pages=LONG_PAGES, code_pages_max=None,
                preferred_pages_min=None, one_per_issuer_day=False):
    """Seeded selection. With long_min, a first pass fills the share of acts with at
    least long_pages pages, then a second pass fills the remaining quotas. Soft
    preferences (off by default) run those passes first with, then without them."""
    rows = [row for row in ordered(candidates, seed) if row["act_type"] in quotas]
    reasons = {}
    for row in rows:
        reason = cheap_reason(row, already_used, pages_range, code_pages_max)
        if reason is None and require_single_edition:
            reason = official_reason(row)
        reasons[row["eo_number"]] = reason
    counter, taken, selected = QuotaCounter(quotas, long_min, long_pages), set(), []
    soft, fallbacks = SoftPreferences(preferred_pages_min, one_per_issuer_day), []
    fields = METADATA_FIELDS + ISSUER_FIELDS if soft.active else METADATA_FIELDS
    for soft_pass, long_phase in soft.passes(counter.phases()):
        for row in rows:
            eo = row["eo_number"]
            if eo in taken or reasons[eo] is not None or not counter.wants(row, long_phase):
                continue
            misses = soft.misses(row)
            if soft_pass and misses:
                continue
            counter.take(row)
            soft.take(row)
            taken.add(eo)
            selected.append({key: row[key] for key in fields if key in row})
            if misses:
                fallbacks.append({"eo_number": eo, "act_type": row["act_type"], "pages": row["pages"],
                                  "misses": misses})
    rejected = [{"eo_number": row["eo_number"], "reason": reasons[row["eo_number"]] or "quota_full"}
                for row in rows if row["eo_number"] not in taken]
    result = {"schema_version": SCHEMA, "seed": seed, "quotas": dict(quotas),
              "require_single_edition": require_single_edition,
              "pages_range": list(pages_range), "long_min": long_min, "long_pages": long_pages,
              "long_selected": counter.long, "selected": selected, "rejected": rejected}
    if code_pages_max:
        result["code_pages_max"] = code_pages_max
    if soft.active:
        result.update({
            "preferred_pages_min": preferred_pages_min, "one_per_issuer_day": one_per_issuer_day,
            "soft_fallbacks": fallbacks,
            "soft_fallback_counts": {m: sum(m in f["misses"] for f in fallbacks) for m in SOFT_MISSES},
        })
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


def actual_exact_docs(actual, number, iso):
    """actual.pravo attrsearch by number+date; only exact number/date matches are kept."""
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
    return docs, url, hashlib.sha256(body).hexdigest()


def lookup_official(actual, ips, number, iso):
    """Find one act in the official tree by number+date and count its editions."""
    dmy = ".".join(reversed(iso.split("-")))
    docs, _, _ = actual_exact_docs(actual, number, iso)
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


def feed_issuer(item):
    """Issuing body of a feed item: its `signatoryAuthorityId` (portal GUID); when absent,
    `name:` + the complexName text before « от dd.mm.yyyy» (type and issuer)."""
    authority = item.get("signatoryAuthorityId")
    if isinstance(authority, str) and authority.strip():
        return authority.strip()
    return "name:" + re.split(r" от \d\d\.\d\d\.\d{4}", _norm(item.get("complexName", "")), maxsplit=1)[0]


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
                "issuer": feed_issuer(item),
                "publication_date": str(item.get("publishDateShort") or day.isoformat())[:10],
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


CODE_CENSUS_SCHEMA = "m1-04a-code-census/1"
# Authored reference list of codes of the Russian Federation adopted by federal law
# (adoption acts only, never amending/introducing laws), including codes that lost
# force. Every entry is verified in actual.pravo by exact number+date; the census
# never trusts this list for titles, publication dates or EO numbers.
CODE_REFERENCE = (
    ("Гражданский кодекс Российской Федерации (часть первая)", "51-ФЗ", "1994-11-30"),
    ("Гражданский кодекс Российской Федерации (часть вторая)", "14-ФЗ", "1996-01-26"),
    ("Гражданский кодекс Российской Федерации (часть третья)", "146-ФЗ", "2001-11-26"),
    ("Гражданский кодекс Российской Федерации (часть четвертая)", "230-ФЗ", "2006-12-18"),
    ("Налоговый кодекс Российской Федерации (часть первая)", "146-ФЗ", "1998-07-31"),
    ("Налоговый кодекс Российской Федерации (часть вторая)", "117-ФЗ", "2000-08-05"),
    ("Бюджетный кодекс Российской Федерации", "145-ФЗ", "1998-07-31"),
    ("Уголовный кодекс Российской Федерации", "63-ФЗ", "1996-06-13"),
    ("Уголовно-процессуальный кодекс Российской Федерации", "174-ФЗ", "2001-12-18"),
    ("Уголовно-исполнительный кодекс Российской Федерации", "1-ФЗ", "1997-01-08"),
    ("Кодекс Российской Федерации об административных правонарушениях", "195-ФЗ", "2001-12-30"),
    ("Гражданский процессуальный кодекс Российской Федерации", "138-ФЗ", "2002-11-14"),
    ("Арбитражный процессуальный кодекс Российской Федерации", "95-ФЗ", "2002-07-24"),
    ("Кодекс административного судопроизводства Российской Федерации", "21-ФЗ", "2015-03-08"),
    ("Трудовой кодекс Российской Федерации", "197-ФЗ", "2001-12-30"),
    ("Семейный кодекс Российской Федерации", "223-ФЗ", "1995-12-29"),
    ("Жилищный кодекс Российской Федерации", "188-ФЗ", "2004-12-29"),
    ("Земельный кодекс Российской Федерации", "136-ФЗ", "2001-10-25"),
    ("Градостроительный кодекс Российской Федерации", "190-ФЗ", "2004-12-29"),
    ("Лесной кодекс Российской Федерации", "200-ФЗ", "2006-12-04"),
    ("Водный кодекс Российской Федерации", "74-ФЗ", "2006-06-03"),
    ("Воздушный кодекс Российской Федерации", "60-ФЗ", "1997-03-19"),
    ("Кодекс торгового мореплавания Российской Федерации", "81-ФЗ", "1999-04-30"),
    ("Кодекс внутреннего водного транспорта Российской Федерации", "24-ФЗ", "2001-03-07"),
    ("Таможенный кодекс Российской Федерации", "61-ФЗ", "2003-05-28"),
    ("Арбитражный процессуальный кодекс Российской Федерации (1995)", "70-ФЗ", "1995-05-05"),
    ("Водный кодекс Российской Федерации (1995)", "167-ФЗ", "1995-11-16"),
    ("Лесной кодекс Российской Федерации (1997)", "22-ФЗ", "1997-01-29"),
    ("Градостроительный кодекс Российской Федерации (1998)", "73-ФЗ", "1998-05-07"),
)
CENSUS_REASONS = (
    "lookup_error",
    "not_in_official_tree",
    "ambiguous_official_identity",
    "not_a_code_title",
    "no_portal_publication",
    "not_in_day_feed",
    "eo_mismatch",
    "pages_out_of_range",
)
PORTAL_PUBLICATION = re.compile(r"pravo\.gov\.ru\)\D*?(\d\d)\.(\d\d)\.(\d{4})\D*?(\d{16})")
DMY = re.compile(r"\b(\d\d)\.(\d\d)\.(\d{4})\b")
# actual.pravo names code parts "<Code>. Часть первая"; the feed form is "(часть первая)".
CODE_PART_SUFFIX = re.compile(r"\.\s+Часть\s+\S+$")


def portal_publication(publications):
    """(ISO date, EO number) of the portal entry in an actual.pravo publications list."""
    for entry in publications or ():
        match = PORTAL_PUBLICATION.search(_norm(entry))
        if match:
            d, m, y, eo = match.groups()
            return f"{y}-{m}-{d}", eo
    return None


def first_publication_day(publications, adoption_iso):
    """Earliest dated publication on/after adoption; the adoption day when none is dated."""
    days = sorted(f"{y}-{m}-{d}" for entry in publications or () for d, m, y in DMY.findall(_norm(entry))
                  if f"{y}-{m}-{d}" >= adoption_iso)
    return days[0] if days else adoption_iso


def scan_feed_day(publication, day):
    """All pages of one day feed: item count, code rows (feed metadata only) and page diagnostics."""
    rows, pages, items, page, total = [], [], 0, 1, 1
    while page <= total:
        feed = _retry(lambda: publication.fetch_feed(day, page))
        total = feed["pages_total"]
        items += len(feed["events"])
        pages.append({"page": page, "source_url": feed["source_url"],
                      "sha256": hashlib.sha256(feed["raw_bytes"]).hexdigest(),
                      "rejected_items": feed.get("rejected_items", [])})
        for item in feed["events"]:
            if categorize(item["complexName"], item["name"]) == "code":
                rows.append({"eo_number": item["eoNumber"], "date": item["documentDate"][:10],
                             "number": item["number"].strip(), "title": _norm(item["name"]),
                             "pages": item["pagesCount"]})
        page += 1
    return {"day": day.isoformat(), "pages_total": total, "items": items, "code_rows": rows, "feed_pages": pages}


def census_entry(actual, publication, title, number, adoption, feed_cache, code_pages_max, previous=None):
    entry = {"reference_title": title, "number": number, "adoption_date": adoption,
             "status": "excluded", "reason": None}

    def excluded(reason, **extra):
        entry.update(extra, reason=reason)
        return entry

    if previous is not None:  # one recorded exact actual.pravo match from an earlier unfrozen run
        record = previous["actual"]
        docs = [{"dochash": record["hash"], "docnames": record["title"], "docstate": record["state"],
                 "publications": record["publications"], "docimagepath": record["image_path"]}]
        url, sha = record["request_url"], record["response_sha256"]
    else:
        try:
            docs, url, sha = actual_exact_docs(actual, number, adoption)
        except Exception as error:
            return excluded("lookup_error", detail=f"{type(error).__name__}: {error}")
    entry["actual"] = {"request_url": url, "response_sha256": sha, "exact_matches": len(docs)}
    if previous is not None:
        entry["actual"]["reused_from"] = previous["source"]
    if not docs:
        return excluded("not_in_official_tree")
    if len(docs) > 1:
        return excluded("ambiguous_official_identity")
    doc = docs[0]
    publications = doc.get("publications") if isinstance(doc.get("publications"), list) else []
    entry["actual"].update(hash=doc.get("dochash"), title=_norm(doc.get("docnames") or ""),
                           state=doc.get("docstate"), publications=[_norm(p) for p in publications],
                           image_path=doc.get("docimagepath"))
    if categorize("", CODE_PART_SUFFIX.sub("", entry["actual"]["title"])) != "code":
        return excluded("not_a_code_title")
    portal = portal_publication(publications)
    entry["portal_publication"] = {"date": portal[0], "eo_number": portal[1]} if portal else None
    day = date.fromisoformat(portal[0] if portal else first_publication_day(publications, adoption))
    if day not in feed_cache:
        try:
            feed_cache[day] = scan_feed_day(publication, day)
        except Exception as error:
            feed_cache[day] = {"day": day.isoformat(), "error": f"{type(error).__name__}: {error}"}
    scan = feed_cache[day]
    entry["feed_check"] = {k: scan[k] for k in ("day", "pages_total", "items", "error", "reused_from") if k in scan}
    matches = [r for r in scan.get("code_rows", [])
               if r["number"].upper() == number.upper() and r["date"] == adoption]
    if len(matches) != 1:
        # A failed or empty feed on a non-portal act still leaves no portal publication.
        return excluded("not_in_day_feed" if portal else "no_portal_publication")
    row = matches[0]
    entry.update(eo_number=row["eo_number"], pages=row["pages"], feed_title=row["title"])
    if portal and portal[1] != row["eo_number"]:
        return excluded("eo_mismatch")
    if not 0 < row["pages"] <= code_pages_max:
        return excluded("pages_out_of_range")
    entry.update(status="eligible")
    return entry


def reusable_census(path):
    """Recorded exact actual.pravo matches and empty feed days from an earlier unfrozen census.

    A day with feed items is never reused: its code rows were not recorded.
    """
    previous = json.loads(Path(path).read_text(encoding="utf-8"))
    if previous.get("schema_version") != CODE_CENSUS_SCHEMA:
        raise ValueError("unsupported previous census schema")
    source = repo_relative(path)
    matches, days = {}, {}
    for e in previous["codes"]:
        if e.get("actual", {}).get("exact_matches") == 1 and "publications" in e["actual"]:
            matches[(e["number"], e["adoption_date"])] = {"actual": e["actual"], "source": source}
        check = e.get("feed_check")
        if check and check.get("items") == 0 and check.get("pages_total") == 0 and not check.get("error"):
            day = date.fromisoformat(check["day"])
            days[day] = {"day": check["day"], "pages_total": 0, "items": 0, "code_rows": [], "reused_from": source}
    return matches, days


def census_codes(actual, publication, reference=CODE_REFERENCE, code_pages_max=CODE_PAGES_MAX, previous=None):
    """Every reference code with its status; eligible codes carry the portal EO number and pages."""
    matches, feed_cache = reusable_census(previous) if previous else ({}, {})
    entries = []
    for title, number, adoption in reference:
        entry = census_entry(actual, publication, title, number, adoption, feed_cache, code_pages_max,
                             matches.get((number, adoption)))
        print(number, adoption, entry["status"], entry["reason"], flush=True)
        entries.append(entry)
    coverage = sorted(({"day": s["day"], "items": s.get("items"), "error": s.get("error"),
                        "reused_from": s.get("reused_from")}
                       for s in feed_cache.values()), key=lambda r: r["day"])
    return entries, coverage


def write_code_census(actual, publication, output, counter=None, reference=CODE_REFERENCE, previous=None):
    """Census, then freeze-codes on the eligible days into ``output``; census.json is write-once."""
    output = Path(output)
    census_path = output.with_name("census.json")
    if selection_pair_state(output) != "absent" or census_path.exists():
        raise FileExistsError(f"code census already exists in {output.parent}")
    entries, coverage = census_codes(actual, publication, reference, previous=previous)
    days = sorted({date.fromisoformat(e["feed_check"]["day"]) for e in entries if e["status"] == "eligible"})
    freeze_code_candidates(publication, days, output)
    reasons = {}
    for e in entries:
        if e["reason"]:
            reasons[e["reason"]] = reasons.get(e["reason"], 0) + 1
    result = {
        "schema_version": CODE_CENSUS_SCHEMA,
        "scope": ("Codes of the Russian Federation from an authored reference list, each verified in "
                  "actual.pravo by exact number+date; portal publication from the actual.pravo "
                  "publications list, EO number and pages from the publication day feed. Metadata only."),
        "code_pages_max": CODE_PAGES_MAX,
        "codes": entries,
        "eligible": [{k: e[k] for k in ("eo_number", "number", "adoption_date", "pages", "feed_title")}
                     for e in entries if e["status"] == "eligible"],
        "excluded_by_reason": dict(sorted(reasons.items())),
        "portal_feed_checks": coverage,
        "selection": repo_relative(output),
        "selection_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "requests": dict(counter) if counter is not None else None,
        "previous_census": repo_relative(previous) if previous else None,
    }
    payload = (json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()
    with census_path.open("xb") as stream:
        stream.write(payload)
    return result


def count_requests(connector, counter, name):
    """Count every transport call (retries included) without changing the connector."""
    original = connector._get

    def counted(*args, **kwargs):
        counter[name] = counter.get(name, 0) + 1
        return original(*args, **kwargs)

    connector._get = counted
    return connector


def sample_days(start, end, seed, count=120, exclude=()):
    """`exclude` (ISO days sampled by earlier batches) is removed before sampling."""
    skip = set(exclude)
    days = [start + timedelta(days=i) for i in range((end - start).days + 1)]
    days = [day for day in days if day.isoformat() not in skip]
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
           pages_range=(PAGES_MIN, PAGES_MAX), long_min=0, long_pages=LONG_PAGES, code_pages_max=None,
           preferred_pages_min=None, one_per_issuer_day=False):
    """Single-edition profile: look up candidates in selection order until the quotas are
    filled. Counters are incremental (one pass per phase), mirroring select_pool."""
    rows = [row for row in ordered(pool.values(), seed) if row["act_type"] in quotas]
    counter, taken = QuotaCounter(quotas, long_min, long_pages), set()
    soft = SoftPreferences(preferred_pages_min, one_per_issuer_day)
    for soft_pass, long_phase in soft.passes(counter.phases()):
        for row in rows:
            if counter.full():
                return
            eo = row["eo_number"]
            if (eo in taken or cheap_reason(row, already_used, pages_range, code_pages_max) is not None
                    or not counter.wants(row, long_phase) or (soft_pass and soft.misses(row))):
                continue
            if eo not in enriched:
                enriched[eo] = dict(row, **lookup(actual, ips, row))
            if official_reason(enriched[eo]) is None:
                counter.take(row)
                soft.take(row)
                taken.add(eo)


PROFILES = {
    "batch-01": {"quotas": DEFAULT_QUOTAS, "pages_range": (PAGES_MIN, PAGES_MAX), "long_min": 0,
                 "require_single_edition": True, "exclude_used": False},
    "batch-02": {"quotas": BATCH2_QUOTAS, "pages_range": BATCH2_PAGES, "long_min": BATCH2_LONG_MIN,
                 "require_single_edition": False, "exclude_used": True},
    "batch-03": {"quotas": BATCH3_QUOTAS, "pages_range": BATCH2_PAGES, "long_min": BATCH2_LONG_MIN,
                 "require_single_edition": False, "exclude_used": True, "codes_from_census": True,
                 "prior_batches": ("batch-01", "batch-02")},
    "batch-04": {"quotas": BATCH4_QUOTAS, "pages_range": BATCH2_PAGES, "long_min": BATCH2_LONG_MIN,
                 "require_single_edition": False, "exclude_used": True,
                 "prior_batches": ("batch-01", "batch-02", "batch-03")},
    # Batch 5: batch-04 quotas plus soft preferences (acts of 5+ pages; one act per type,
    # issuer and publication day), each relaxed only when a quota cannot be filled otherwise.
    "batch-05": {"quotas": BATCH4_QUOTAS, "pages_range": BATCH2_PAGES, "long_min": BATCH2_LONG_MIN,
                 "require_single_edition": False, "exclude_used": True,
                 "prior_batches": ("batch-01", "batch-02", "batch-03", "batch-04"),
                 "preferred_pages_min": 5, "one_per_issuer_day": True},
}
MIN_DAYS_CHOICES = (0, 60, 120)  # the run checks quotas only after 60 and 120 days
DOCUMENTS = PROJECT / "data/m1/m1-04a/documents"
USED_INDEXES = (DOCUMENTS / "index.json", DOCUMENTS / "pool/batch-01/index.json")
USED_SELECTIONS = (DOCUMENTS / "pool/batch-01/selection.json",)
PROVENANCE_SCHEMA = "m1-04a-pool-selection-provenance/2"


def prior_batch_exclusions(prior_batches, documents=None):
    """(used eo numbers, sampled days) of earlier pool batches, from metadata files only:
    development/reserved and batch indexes, frozen selections and refill picks, and every
    act with a failure record (`failures/<eo>-*.json`), whether or not it was refilled."""
    documents = Path(documents or DOCUMENTS)
    batches = [documents / "pool" / name for name in prior_batches]
    indexes = [documents / "index.json"] + [b / "index.json" for b in batches]
    selections = []
    for batch in batches:
        selections.append(batch / "selection.json")
        selections.extend(sorted(batch.glob("selection-refill-??.json")))
    used = load_already_used(indexes, selections)
    days = set()
    for batch in batches:
        used.update(path.name[:16] for path in (batch / "failures").glob("*.json")
                    if re.fullmatch(r"\d{16}", path.name[:16]))
        days.update(json.loads((batch / "selection.json").read_text(encoding="utf-8")).get("days_sampled", ()))
    return used, days


def write_provenance(output, args, feed_cache, selection_sha):
    """Write-once `selection-provenance.json` beside a newly frozen selection."""
    import subprocess

    path = Path(output).with_name("selection-provenance.json")
    cache = None
    if feed_cache and Path(feed_cache).exists():
        cache = {"path": repo_relative(feed_cache),
                 "sha256": hashlib.sha256(Path(feed_cache).read_bytes()).hexdigest()}
    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=PROJECT, capture_output=True,
                                text=True, check=True).stdout.strip()
        dirty = bool(subprocess.run(["git", "status", "--porcelain", "--", "docs/assets", "src/legal_rag/sources"], cwd=PROJECT,
                                    capture_output=True, text=True, check=True).stdout.strip())
    except (OSError, subprocess.CalledProcessError):
        commit, dirty = None, None
    payload = {
        "schema_version": PROVENANCE_SCHEMA,
        "selection": Path(output).name,
        "selection_sha256": selection_sha,
        "command": getattr(args, "command", None),
        "min_days": args.min_days,
        "feed_cache": cache,
        "code_commit": commit,
        "scripts_dirty": dirty,
    }
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    return path


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
    prior_days = set()
    if profile.get("prior_batches"):
        used, prior_days = prior_batch_exclusions(profile["prior_batches"])
    elif profile["exclude_used"]:
        used = load_already_used(USED_INDEXES, USED_SELECTIONS)
    else:
        used = set()
    code_pages_max = CODE_PAGES_MAX if quotas.get("code", 0) else None
    options = {"require_single_edition": strict, "already_used": used, "pages_range": pages_range,
               "long_min": long_min, "long_pages": LONG_PAGES, "code_pages_max": code_pages_max}
    soft_options = {key: profile[key] for key in ("preferred_pages_min", "one_per_issuer_day") if key in profile}
    options.update(soft_options)
    code_rows, code_reference = [], None
    if quotas.get("code", 0):
        if not args.code_candidates:
            raise ValueError("a code quota requires --code-candidates frozen by freeze-codes")
        code_rows, digest = load_code_candidates(args.code_candidates)
        code_rows = [r for r in code_rows if args.date_from <= r["date"] <= args.date_to]
        code_reference = {"path": repo_relative(args.code_candidates), "sha256": digest}
        if profile.get("codes_from_census"):  # every census code, at most the profile bound
            quotas["code"] = min(quotas["code"], len(code_rows))
    publication = PublicationPoolConnector(timeout=25, request_interval=1)
    actual = ActualPravoConnector(timeout=25, request_interval=1)
    ips = LegislationRussiaConnector(timeout=25, request_interval=1)
    all_days = sample_days(date.fromisoformat(args.date_from), date.fromisoformat(args.date_to), args.seed,
                           120, sorted(prior_days))
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
                   code_pages_max, **soft_options)
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
        "days_excluded_from_sampling": sorted(prior_days),
        "looked_up_in_official_tree": looked_up,
        "official_lookup": ("filter: exactly one complete official edition" if strict else
                            "metadata only (official_found), looked up for selected acts after selection"),
        "quotas_filled": quotas_full(result),
        "classification_source": "feed complexName prefix (feed items carry only type/authority ids); "
                                 "number and date from feed `number` and `documentDate`; "
                                 "code = standalone code title, independent of the portal type; "
                                 "targeted code candidates frozen separately before selection",
    })
    if soft_options.get("one_per_issuer_day"):
        result["issuer_source"] = ("feed item signatoryAuthorityId (portal GUID); when absent, 'name:' + "
                                   "complexName text before the date; publication day = feed publishDateShort")
    payload = (json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    if not result["quotas_filled"]:
        # An incomplete batch is not frozen: the selection pair stays unwritten.
        if args.partial_output:
            Path(args.partial_output).write_bytes(payload)
        print("quotas not filled", result["selected_per_category"], "long", result["long_selected"],
              "partial", args.partial_output, flush=True)
        return 3
    status = write_selection_pair(output, payload)
    if status != "unchanged":
        write_provenance(output, args, args.feed_cache, hashlib.sha256(payload).hexdigest())
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


def failure_reasons(failures_dir, stage=None):
    """eo -> reason from the failure files `<eo>-<run>.json` (run report errors or recorded reason);
    with `stage`, only records of that stage (e.g. `ocr`: `<eo>-ocr-<run>.json`)."""
    reasons = {}
    for path in sorted(Path(failures_dir).glob("*.json")):
        eo = path.name[:16]
        record = json.loads(path.read_text(encoding="utf-8"))
        if stage is not None and record.get("stage") != stage:
            continue
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
    """Next refill record: acts not replaced yet with a failure file and no receipt, or with an OCR
    failure record (`stage: ocr`) despite a receipt."""
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
    # A slot fails when its act has a failure record and no receipt (acquisition), or when the
    # acquired act has an OCR failure record (stage `ocr`, written by hand after the OCR run).
    reasons = failure_reasons(batch_dir / "failures")
    ocr_reasons = failure_reasons(batch_dir / "failures", stage="ocr")
    failed = {}
    for act in acts:
        eo = act["eo_number"]
        if eo in replaced:
            continue
        if (batch_dir / "receipts" / f"{eo}.json").exists():
            if eo in ocr_reasons:
                failed[eo] = ocr_reasons[eo]
        elif eo in reasons:
            failed[eo] = reasons[eo]
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
    if argv[:1] == ["census-codes"]:
        from legal_rag.sources.actual_pravo import ActualPravoConnector
        from legal_rag.sources.publication_pool import PublicationPoolConnector

        parser = argparse.ArgumentParser(prog="select_m1_04a_pool.py census-codes")
        parser.add_argument("--output", required=True, type=Path,
                            help="new directory's selection.json; census.json is written beside it")
        parser.add_argument("--previous", type=Path,
                            help="earlier unfrozen census.json: reuse its exact actual.pravo matches and empty feed days")
        args = parser.parse_args(argv[1:])
        counter = {}
        actual = count_requests(ActualPravoConnector(timeout=25, request_interval=1), counter, "actual.pravo")
        publication = count_requests(PublicationPoolConnector(timeout=25, request_interval=1), counter,
                                     "publication.pravo")
        result = write_code_census(actual, publication, args.output, counter, previous=args.previous)
        print("census-codes", result["eligible"], result["excluded_by_reason"], result["requests"], flush=True)
        return 0
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from", dest="date_from", required=True)
    parser.add_argument("--to", dest="date_to", required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--profile", choices=sorted(PROFILES), default="batch-01")
    parser.add_argument("--feed-cache", help="optional JSON cache of feed cards per day (batch-03: inside the batch dir)")
    parser.add_argument("--partial-output", help="where to write an unfilled result (not frozen)")
    parser.add_argument("--quota", action="append", default=[], metavar="KIND=N",
                        help="override one profile quota (recorded decision only)")
    parser.add_argument("--min-days", type=int, default=0, choices=MIN_DAYS_CHOICES,
                        help="sample at least this many days even if quotas fill earlier")
    parser.add_argument("--quota-change", help="JSON file whose object is recorded as `quota_change`")
    parser.add_argument("--code-candidates", type=Path, help="freeze-codes selection.json (required for code quota)")
    parser.add_argument("--pages-max", type=int, help="explicit page ceiling override (e.g. 500 for a 480-page code)")
    args = parser.parse_args(argv)
    import subprocess

    args.command = "PYTHONPATH=src " + subprocess.list2cmdline(
        [sys.executable, "docs/assets/select_m1_04a_pool.py", *argv])
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
