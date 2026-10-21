"""M1-04A pool batch 1: random selection by metadata only (no act bodies are read).

Cards come from the documented publication.pravo.gov.ru day feed. Each candidate is
looked up in the official tree (actual.pravo attrsearch, then IPS search.json, as in
acquire_official_json_transfer.py::discover) and only its list of editions is read.
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

SCHEMA = "m1-04a-pool-selection/1"
DEFAULT_QUOTAS = {
    "federal_law": 2,
    "presidential_decree": 1,
    "government_resolution": 2,
    "government_order": 1,
    "ministry_order": 2,
}
PAGES_MIN, PAGES_MAX = 3, 60
AMENDING_PREFIX = "о внесении изменени"
QUOTES = ' "«»“”'  # feed names of laws arrive quoted
# Rejection reasons. edition_count_unknown: the official tree answered but exposes no
# edition list (or an error), so "exactly one edition" cannot be established.
REASONS = (
    "amending_act",
    "pages_out_of_range",
    "not_in_official_tree",
    "edition_count_unknown",
    "edition_count_not_1",
    "quota_full",
)
# Only metadata may reach a selected record.
METADATA_FIELDS = (
    "eo_number", "act_type", "date", "number", "title", "pages", "edition_count",
    "official_source", "official_hash",
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


def _norm(value):
    return " ".join(str(value).split())


def categorize(complex_name, name):
    """Quota category from feed metadata, or None (ignored, not a rejection)."""
    text = _norm(complex_name)
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


def cheap_reason(row):
    """Rejections decidable from feed metadata alone."""
    if _norm(row.get("title", "")).lstrip(QUOTES).lower().startswith(AMENDING_PREFIX):
        return "amending_act"
    if not PAGES_MIN <= row["pages"] <= PAGES_MAX:
        return "pages_out_of_range"
    return None


def select_pool(candidates, quotas, seed):
    selected, rejected = [], []
    counts = {kind: 0 for kind in quotas}
    for row in ordered(candidates, seed):
        kind = row["act_type"]
        if kind not in quotas:
            continue
        reason = cheap_reason(row)
        if reason is None:
            if not row["in_official_tree"]:
                reason = "not_in_official_tree"
            elif row["edition_count"] is None:
                reason = "edition_count_unknown"
            elif row["edition_count"] != 1:
                reason = "edition_count_not_1"
            elif counts[kind] >= quotas[kind]:
                reason = "quota_full"
        if reason is None:
            counts[kind] += 1
            selected.append({key: row[key] for key in METADATA_FIELDS if key in row})
        else:
            rejected.append({"eo_number": row["eo_number"], "reason": reason})
    return {"schema_version": SCHEMA, "seed": seed, "quotas": dict(quotas),
            "selected": selected, "rejected": rejected}


def selected_counts(result):
    counts = {kind: 0 for kind in result["quotas"]}
    for row in result["selected"]:
        counts[row["act_type"]] += 1
    return counts


def quotas_full(result):
    counts = selected_counts(result)
    return all(counts[kind] >= quota for kind, quota in result["quotas"].items())


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
             {"AttrId": 5, "AttrMode": 0, "DateFrom": compact, "DateTo": compact},
             {"AttrId": 999, "AttrMode": 1, "Words": [10, "position", "20220701", 0, 1]}]
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


def enrich(pool, enriched, details, actual, ips, quotas, seed):
    """Look up candidates in seeded order until every quota is filled or the pool ends."""
    for row in ordered(pool.values(), seed):
        eo = row["eo_number"]
        if eo in enriched:
            continue
        if cheap_reason(row) is not None:
            enriched[eo] = dict(row, in_official_tree=False, edition_count=None)
            continue
        current = select_pool(list(enriched.values()), quotas, seed)
        if quotas_full(current):
            return
        if selected_counts(current)[row["act_type"]] >= quotas[row["act_type"]]:
            continue
        try:
            info = lookup_official(actual, ips, row["number"], row["date"])
        except Exception as error:
            info = {"in_official_tree": False, "detail": f"lookup_error {type(error).__name__}: {error}"}
        details[eo] = info.pop("detail", None)
        enriched[eo] = dict(row, **info)
        print(row["act_type"], row["number"], row["date"], info, flush=True)


def run(args):
    from legal_rag.sources.actual_pravo import ActualPravoConnector
    from legal_rag.sources.legislation_russia import LegislationRussiaConnector
    from legal_rag.sources.publication_pravo import PublicationPravoConnector

    output = Path(args.output)
    if output.exists():
        print("unchanged", hashlib.sha256(output.read_bytes()).hexdigest(), flush=True)
        return 0
    publication = PublicationPravoConnector(timeout=25, request_interval=1)
    actual = ActualPravoConnector(timeout=25, request_interval=1)
    ips = LegislationRussiaConnector(timeout=25, request_interval=1)
    quotas = DEFAULT_QUOTAS
    all_days = sample_days(date.fromisoformat(args.date_from), date.fromisoformat(args.date_to), args.seed)
    pool, enriched, details, failed_days = {}, {}, {}, []
    used = 0
    for limit in (60, 120):
        for day in all_days[used:limit]:
            try:
                for row in feed_candidates(publication, day):
                    pool.setdefault(row["eo_number"], row)
            except Exception as error:  # a bad day is recorded, never silently dropped
                failed_days.append({"date": day.isoformat(), "error": f"{type(error).__name__}: {error}"})
            print("day", day.isoformat(), "pool", len(pool), flush=True)
        used = limit
        enrich(pool, enriched, details, actual, ips, quotas, args.seed)
        result = select_pool(list(enriched.values()), quotas, args.seed)
        if quotas_full(result):
            break
    result["rejected"] = [dict(r, detail=details[r["eo_number"]]) if details.get(r["eo_number"]) else r
                          for r in result["rejected"]]
    result.update({
        "date_range": [args.date_from, args.date_to],
        "days_sampled": [d.isoformat() for d in all_days[:used]],
        "days_failed": failed_days,
        "candidates_per_category": {k: sum(1 for r in pool.values() if r["act_type"] == k) for k in quotas},
        "looked_up_in_official_tree": len(details),
        "quotas_filled": quotas_full(result),
        "classification_source": "feed complexName prefix (feed items carry only type/authority ids); "
                                 "number and date from feed `number` and `documentDate`",
    })
    payload = (json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("xb") as stream:
        stream.write(payload)
    digest = hashlib.sha256(payload).hexdigest()
    with output.with_name("selection.sha256").open("x", encoding="utf-8") as stream:
        stream.write(f"{digest}  {output.name}\n")
    print("selection.json sha256", digest, "quotas_filled", result["quotas_filled"], flush=True)
    return 0 if result["quotas_filled"] else 3


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from", dest="date_from", required=True)
    parser.add_argument("--to", dest="date_to", required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--output", required=True)
    return run(parser.parse_args(argv))


if __name__ == "__main__":
    sys.exit(main())
