"""M1-04A second-layer corpus: official IPS structure JSON + HTML for ~100 diverse federal acts.

Phases (run in order from the repository root; every phase writes its files once):

  candidates  random pages of IPS attribute search per group -> candidates.json
  screen      card + document_content for a seeded sample of candidates -> screen/<nd>/, screen.json
  screen2     continue the same seeded order until 2x quota structured documents -> screen-round-2.json
  select      greedy pick by structure features within group quotas -> selection.json (frozen)
  fetch       documenttext for the picks, nesting check, refill from the ranked reserve -> docs/<slug>/
  split       seeded 70/30 dev/holdout split stratified by group -> split.json (frozen before development)

Only the federal IPS base (c000000000) is used: it holds acts of the President, Government, Federal
Assembly, Constitutional Court and earlier bodies. Ministry orders and SanPiN are not in it.
Requests are sequential with a pause of at least REQUEST_PAUSE seconds.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import re
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode

from bs4 import BeautifulSoup

API = "http://ips.pravo.gov.ru/api/ips/legislation"
BASE_ID = "c000000000"
REQUEST_PAUSE = 1.1
SEED = 20261025
SCREEN_FACTOR = 2.5
HOLDOUT_SHARE = 0.3

# group -> (quota, search filters). Filters use the IPS front-end names (type, organ).
# Quotas after screening round 1 (25.10.2026): intl, ks and osnovy had no candidate with structure
# nodes (IPS does not mark them up; KS/osnovy/most pre-1993 laws have no text either, and
# actual.pravo has no content editions for them), so their 14 places went to pp +5, fz +4,
# ukaz +3, rp +2. The original quotas are kept in QUOTAS_ROUND_1.
QUOTAS_ROUND_1 = {"pp": 24, "fz": 18, "ukaz": 16, "rp": 10, "intl": 8, "code": 6, "fkz": 4,
                  "law-pre1993": 4, "duma-sf": 4, "ks": 4, "osnovy": 2}
GROUPS = {
    "pp": (29, [{"type": "Постановление", "organ": "Правительство"}]),
    "fz": (22, [{"type": "Федеральный закон"}]),
    "ukaz": (19, [{"type": "Указ"}]),
    "rp": (12, [{"type": "Распоряжение", "organ": "Правительство"}]),
    "intl": (0, [{"type": t} for t in ("Соглашение", "Договор", "Конвенция", "Протокол")]),
    "code": (6, [{"type": "Кодекс"}]),
    "fkz": (4, [{"type": "Федеральный конституционный закон"}]),
    "law-pre1993": (4, [{"type": "Закон"}]),
    "duma-sf": (4, [{"type": "Постановление", "organ": o}
                    for o in ("Государственная Дума Федерального Собрания", "Совет Федерации Федерального Собрания")]),
    "ks": (0, [{"type": "Постановление", "organ": "Конституционный Суд"}, {"type": "Определение"}]),
    "osnovy": (0, [{"type": "Основы законодательства"}]),
}
CORPORA = Path(__file__).resolve().parents[2] / "data/m1/m1-04a/json-corpus"
# Acquisition profiles. v1 is the frozen 25.10.2026 corpus (default; reproduces as before). v2 (owner request
# 26.10.2026): 150 new acts biased to decrees and government resolutions, none of them in v1.
PROFILES = {
    "v1": {"seed": SEED, "quotas": {g: q for g, (q, _) in GROUPS.items()}, "round_1": QUOTAS_ROUND_1,
           "exclude_corpora": ()},
    "v2": {"seed": 20261026,
           "quotas": {"pp": 45, "fz": 25, "ukaz": 45, "rp": 15, "intl": 0, "code": 8, "fkz": 4, "law-pre1993": 4,
                      "duma-sf": 4, "ks": 0, "osnovy": 0},
           "round_1": {"pp": 45, "fz": 25, "ukaz": 45, "rp": 15, "code": 8, "fkz": 4, "law-pre1993": 4,
                       "duma-sf": 4},
           "exclude_corpora": (CORPORA / "20261025-v1",)},
}


def excluded_nds(profile) -> set:
    """IPS document ids already in an earlier corpus (its fetched documents)."""
    out = set()
    for corpus in profile["exclude_corpora"]:
        out |= {d["nd"] for d in json.loads((Path(corpus) / "fetch.json").read_text(encoding="utf-8"))["documents"]}
    return out


# Screening round 2 continues each group's seeded candidate order until it has this many
# documents with structure nodes (or the candidates run out).
ROUND2_TARGET_FACTOR = 2
PAGES_PER_FILTER = 3
PAGE_LIMIT = 200


def now():
    return datetime.now(timezone.utc).isoformat()


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class Client:
    def __init__(self, log_path: Path):
        self.log_path = log_path
        self.last = 0.0

    def request(self, endpoint, params, post=False):
        wait = self.last + REQUEST_PAUSE - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        url = f"{API}/{endpoint}"
        data = None
        if post:
            data = urlencode(params).encode()
        else:
            url += "?" + urlencode(params)
        headers = {"Accept": "application/json", "User-Agent": "legal-rag-m1-04a-json-corpus"}
        if post:
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        for attempt in range(3):
            try:
                with urllib.request.urlopen(urllib.request.Request(url, data=data, headers=headers), timeout=90) as r:
                    body, status, final = r.read(), r.status, r.geturl()
                break
            except Exception as error:  # retry transient failures, then propagate
                if attempt == 2:
                    self._log({"url": url, "params": params if post else None, "error": str(error), "at": now()})
                    raise
                time.sleep(3 * (attempt + 1))
        self.last = time.monotonic()
        record = {"url": url, "params": params if post else None, "status": status, "response_url": final,
                  "sha256": sha(body), "bytes": len(body), "at": now()}
        self._log(record)
        return body, record

    def _log(self, record):
        with self.log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def write_once(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = value if isinstance(value, bytes) else (
        json.dumps(value, ensure_ascii=False, indent=1) + "\n").encode("utf-8")
    with path.open("xb") as handle:
        handle.write(data)


def search(client, filters, page):
    params = {"searchType": "attrSearch", "bpas": BASE_ID, "page": str(page), "limit": str(PAGE_LIMIT), **filters}
    body, record = client.request("search.json", params, post=True)
    return json.loads(body.decode("utf-8")).get("docs", []), record


def count(client, filters):
    params = {"searchType": "attrSearch", "bpas": BASE_ID, **filters}
    body, record = client.request("search_counter.json", params, post=True)
    return json.loads(body.decode("utf-8")).get("totalCount", 0), record


# ------------------------------------------------------------------ phases


def phase_candidates(root: Path, profile=PROFILES["v1"]):
    client = Client(root / "requests.jsonl")
    rng = random.Random(profile["seed"])
    out = {"schema_version": "m1-04a-json-corpus-candidates/1", "seed": profile["seed"], "base": BASE_ID,
           "created_at": now(), "groups": {}}
    for group, (_, filter_list) in GROUPS.items():
        if not profile["quotas"].get(group) and profile is not PROFILES["v1"]:
            continue  # v1 also searched its zero-quota groups; later profiles skip them
        entries = []
        for filters in filter_list:
            total, _ = count(client, filters)
            pages = max(1, math.ceil(total / PAGE_LIMIT))
            chosen = sorted(rng.sample(range(1, pages + 1), min(PAGES_PER_FILTER, pages)))
            docs = []
            for page in chosen:
                found, record = search(client, filters, page)
                docs += [{"hash": d["hash"], "nd": d["nd"], "docdate": d["docdate"], "adoption": d["adoption"],
                          "name": d["name"], "state": d["state"], "search_sha256": record["sha256"]}
                         for d in found if d.get("baseid") == BASE_ID]
            entries.append({"filters": filters, "total": total, "pages": chosen, "docs": docs})
            print(group, filters, "total", total, "pages", chosen, "docs", len(docs), flush=True)
        out["groups"][group] = entries
    write_once(root / "candidates.json", out)


def unit_tree(nodes):
    """Pre-order IPS nodes -> list of (node, parent unit or None)."""
    stack, rows = [], []
    for n in nodes:
        del stack[n["lvl"]:]
        rows.append((n, stack[-1]["unit"] if stack else None))
        stack.append(n)
    return rows


def features(nodes, docdate, name):
    rows = unit_tree(nodes)
    feats = set()
    for n, parent in rows:
        feats.add("unit:" + n["unit"])
        feats.add(f"edge:{parent or 'ROOT'}>{n['unit']}")
        if "<sup>" in n["caption"]:
            feats.add("flag:superscript")
        if re.search(r"\b\d+\.\d+", n["caption"]):
            feats.add("flag:dotted-number")
    attached = sum(1 for n in nodes if n["lvl"] == 0 and n["unit"] in ("вложение", "приложение"))
    if attached >= 2:
        feats.add("flag:several-attached")
    depth = max((n["lvl"] for n in nodes), default=-1) + 1
    feats.add(f"depth:{min(depth, 6)}")
    size = len(nodes)
    feats.add("size:" + ("0" if size == 0 else "1-5" if size <= 5 else "6-30" if size <= 30 else
                         "31-200" if size <= 200 else "201-1000" if size <= 1000 else "1000+"))
    year = int(docdate[-4:])
    feats.add(f"decade:{year // 10 * 10}")
    if re.match(r"О внесении изменени|О внесении дополнени|Об изменени", name):
        feats.add("flag:amending")
    return sorted(feats)


def candidate_orders(root: Path, profile=PROFILES["v1"]):
    """Each group's deduplicated candidates in the seeded screening order (shared by both rounds); documents of an
    excluded earlier corpus are left out."""
    candidates = json.loads((root / "candidates.json").read_text(encoding="utf-8"))
    rng = random.Random(profile["seed"] + 1)
    orders = {}
    excluded = excluded_nds(profile)
    for group in GROUPS:
        pool, seen = [], set(excluded)
        for entry in candidates["groups"].get(group, []):
            for d in entry["docs"]:
                if d["nd"] not in seen:
                    seen.add(d["nd"])
                    pool.append(d)
        rng.shuffle(pool)
        orders[group] = pool
    return orders


def screen_one(client, root: Path, d):
    folder = root / "screen" / d["nd"]
    try:
        card_raw, card_rec = client.request("document_card.json", {"hash": d["hash"]})
        card = json.loads(card_raw.decode("utf-8"))
        rdk = card["actualrdk"]
        content_raw, content_rec = client.request(
            "document_content", {"nd": card["nd"], "rdk": rdk, "bpa": card["baseid"]})
        content = json.loads(content_raw.decode("utf-8"))
        write_once(folder / "card.json", card_raw)
        write_once(folder / "document_content.json", content_raw)
        nodes = content.get("data") if isinstance(content.get("data"), list) else []
        if any("unit" not in n for n in nodes):
            # Observed in round 1: nodes without `unit` (e.g. 'Статья 1' with no unit field).
            raise ValueError("structure node without unit")
        return {**d, "rdk": rdk, "status": content.get("status"), "nodes": len(nodes),
                "card_sha256": card_rec["sha256"], "content_sha256": content_rec["sha256"],
                "features": features(nodes, d["docdate"], d["name"]) if nodes else []}
    except Exception as error:
        return {**d, "error": f"{type(error).__name__}: {error}"}


def phase_screen(root: Path, profile=PROFILES["v1"]):
    orders = candidate_orders(root, profile)
    client = Client(root / "requests.jsonl")
    screened = {"schema_version": "m1-04a-json-corpus-screen/1", "created_at": now(), "groups": {}}
    for group in GROUPS:
        quota = profile["round_1"].get(group, 0)
        rows = []
        for d in orders[group][: max(quota, math.ceil(quota * SCREEN_FACTOR))]:
            rows.append(screen_one(client, root, d))
            print(group, d["nd"], rows[-1].get("nodes", rows[-1].get("error")), flush=True)
        screened["groups"][group] = rows
    write_once(root / "screen.json", screened)


def phase_screen2(root: Path, profile=PROFILES["v1"]):
    """Continue each group's seeded order until ROUND2_TARGET_FACTOR * quota structured documents."""
    first = json.loads((root / "screen.json").read_text(encoding="utf-8"))
    orders = candidate_orders(root, profile)
    client = Client(root / "requests.jsonl")
    screened = {"schema_version": "m1-04a-json-corpus-screen/1", "round": 2, "created_at": now(),
                "target_factor": ROUND2_TARGET_FACTOR, "groups": {}}
    for group in GROUPS:
        quota = profile["quotas"][group]
        done = {r["nd"] for r in first["groups"].get(group, [])}
        have = sum(1 for r in first["groups"].get(group, []) if r.get("nodes"))
        rows = []
        for d in orders[group]:
            if have >= ROUND2_TARGET_FACTOR * quota:
                break
            if d["nd"] in done:
                continue
            rows.append(screen_one(client, root, d))
            have += bool(rows[-1].get("nodes"))
            print(group, d["nd"], rows[-1].get("nodes", rows[-1].get("error")), "have", have, flush=True)
        screened["groups"][group] = rows
    write_once(root / "screen-round-2.json", screened)


def rank_group(rows, covered, rng):
    """Greedy order: next pick adds most features not yet covered (corpus-wide); seeded ties."""
    rest = [r for r in rows if r.get("nodes")]
    rng.shuffle(rest)
    order, covered = [], set(covered)
    while rest:
        best = max(rest, key=lambda r: len(set(r["features"]) - covered))
        rest.remove(best)
        order.append(best)
        covered |= set(best["features"])
    return order


def screened_rows(root: Path):
    """Group -> screened rows of both rounds, in screening order."""
    rows = {}
    for name in ("screen.json", "screen-round-2.json"):
        path = root / name
        if path.exists():
            for group, items in json.loads(path.read_text(encoding="utf-8"))["groups"].items():
                rows.setdefault(group, []).extend(items)
    return rows


def phase_select(root: Path, profile=PROFILES["v1"]):
    screened = {"groups": screened_rows(root)}
    rng = random.Random(profile["seed"] + 2)
    covered, groups = set(), {}
    for group in GROUPS:
        quota = profile["quotas"][group]
        order = rank_group(screened["groups"].get(group, []), covered, rng) if quota else []
        picks, reserve = order[:quota], order[quota:]
        for r in picks:
            covered |= set(r["features"])
        groups[group] = {"quota": quota, "picks": [r["nd"] for r in picks], "reserve": [r["nd"] for r in reserve],
                         "shortfall": max(0, quota - len(picks))}
        print(group, "picks", len(picks), "reserve", len(reserve), flush=True)
    selection = {"schema_version": "m1-04a-json-corpus-selection/1", "seed": profile["seed"], "created_at": now(),
                 "screen_sha256": {n: sha((root / n).read_bytes())
                                   for n in ("screen.json", "screen-round-2.json") if (root / n).exists()},
                 "quotas_round_1": profile["round_1"],
                 **({"excluded_corpora": [Path(c).name for c in profile["exclude_corpora"]]}
                    if profile["exclude_corpora"] else {}),
                 "rule": "greedy by new structure features (corpus-wide coverage), seeded tie order; "
                         "documents without structure nodes are not eligible",
                 "groups": groups, "covered_features": sorted(covered)}
    write_once(root / "selection.json", selection)


def nesting_check(html_text: str, nodes):
    """Every node range lies inside its parent's range in HTML paragraph order; ids exist.

    Range ends are paragraph ids `p<N>` or table-row ids `r<N>` (on <tr>). Fetch attempts 01 (only <p>)
    and 02 (only `p<N>`) falsely rejected 11 acts; every element with such an id counts, in document order.
    """
    ids = [e["id"] for e in BeautifulSoup(html_text, "html.parser").find_all(id=re.compile(r"^[pr]\d+$"))]
    pos = {pid: i for i, pid in enumerate(ids)}
    stack, problems = [], []
    for n in nodes:
        del stack[n["lvl"]:]
        if n["np"] not in pos or n["npe"] not in pos:
            problems.append({"node": n["id"], "problem": "paragraph id not in HTML"})
        else:
            span = (pos[n["np"]], pos[n["npe"]])
            if span[0] > span[1]:
                problems.append({"node": n["id"], "problem": "inverted range"})
            if stack and "span" in stack[-1] and not (stack[-1]["span"][0] <= span[0] and span[1] <= stack[-1]["span"][1]):
                problems.append({"node": n["id"], "problem": "outside parent", "parent": stack[-1]["id"]})
            n = {**n, "span": span}
        stack.append(n)
    return len(ids), problems


def phase_fetch(root: Path, profile=PROFILES["v1"]):
    selection = json.loads((root / "selection.json").read_text(encoding="utf-8"))
    rows = {r["nd"]: (g, r) for g, items in screened_rows(root).items() for r in items}
    client = Client(root / "requests.jsonl")
    result = {"schema_version": "m1-04a-json-corpus-fetch/1", "created_at": now(), "documents": [], "rejected": []}
    for group, plan in selection["groups"].items():
        queue, taken = list(plan["picks"]) + list(plan["reserve"]), 0
        while queue and taken < plan["quota"]:
            nd = queue.pop(0)
            _, row = rows[nd]
            slug = f"{group}-{nd}"
            card = json.loads((root / "screen" / nd / "card.json").read_text(encoding="utf-8"))
            try:
                text_raw, text_rec = client.request("documenttext", {"nd": nd, "rdk": row["rdk"], "bpa": card["baseid"]})
                text = json.loads(text_raw.decode("utf-8"))
                content = json.loads((root / "screen" / nd / "document_content.json").read_text(encoding="utf-8"))
                paragraphs, problems = nesting_check(text["doctext"], content["data"])
            except Exception as error:
                result["rejected"].append({"group": group, "nd": nd, "reason": f"{type(error).__name__}: {error}"})
                print(group, nd, "REJECTED", error, flush=True)
                continue
            if problems or str(text.get("rdk")) != str(row["rdk"]):
                result["rejected"].append({"group": group, "nd": nd, "reason": "nesting/edition check failed",
                                           "problems": problems[:20], "problem_count": len(problems)})
                write_once(root / "rejected" / nd / "documenttext.json", text_raw)
                print(group, nd, "REJECTED", len(problems), "problems", flush=True)
                continue
            folder = root / "docs" / slug
            write_once(folder / "card.json", (root / "screen" / nd / "card.json").read_bytes())
            write_once(folder / "document_content.json", (root / "screen" / nd / "document_content.json").read_bytes())
            write_once(folder / "documenttext.json", text_raw)
            write_once(folder / "document.html", text["doctext"].encode("utf-8"))
            meta = {"slug": slug, "group": group, "nd": nd, "rdk": row["rdk"], "hash": row["hash"],
                    "adoption": row["adoption"], "docdate": row["docdate"], "state": row["state"],
                    "public_url": f"http://ips.pravo.gov.ru/search/{row['hash']}", "nodes": row["nodes"],
                    "html_paragraphs": paragraphs, "features": row["features"],
                    "card_sha256": row["card_sha256"], "content_sha256": row["content_sha256"],
                    "text_sha256": text_rec["sha256"], "from_reserve": nd not in plan["picks"]}
            write_once(folder / "source.json", meta)
            result["documents"].append(meta)
            taken += 1
            print(group, nd, "ok", row["nodes"], "nodes", flush=True)
        if taken < plan["quota"]:
            result.setdefault("shortfall", {})[group] = plan["quota"] - taken
    write_once(root / "fetch.json", result)


def phase_split(root: Path, profile=PROFILES["v1"]):
    fetched = json.loads((root / "fetch.json").read_text(encoding="utf-8"))
    rng = random.Random(profile["seed"] + 3)
    split = {"schema_version": "m1-04a-json-corpus-split/1", "seed": profile["seed"] + 3, "created_at": now(),
             "fetch_sha256": sha((root / "fetch.json").read_bytes()), "holdout_share": HOLDOUT_SHARE,
             "rule": "per group: shuffle slugs with the seed, round(share * n) go to holdout",
             "dev": [], "holdout": []}
    by_group = {}
    for d in fetched["documents"]:
        by_group.setdefault(d["group"], []).append(d["slug"])
    for group in sorted(by_group):
        slugs = sorted(by_group[group])
        rng.shuffle(slugs)
        k = round(HOLDOUT_SHARE * len(slugs))
        split["holdout"] += sorted(slugs[:k])
        split["dev"] += sorted(slugs[k:])
    write_once(root / "split.json", split)
    print("dev", len(split["dev"]), "holdout", len(split["holdout"]))


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("candidates", "screen", "screen2", "select", "fetch", "split"))
    parser.add_argument("--root", required=True)
    parser.add_argument("--profile", choices=sorted(PROFILES), default="v1",
                        help="v1: the frozen 25.10.2026 corpus; v2: 150 new acts biased to decrees and resolutions")
    args = parser.parse_args(argv)
    root = Path(args.root)
    root.mkdir(parents=True, exist_ok=True)
    {"candidates": phase_candidates, "screen": phase_screen, "screen2": phase_screen2, "select": phase_select,
     "fetch": phase_fetch, "split": phase_split}[args.phase](root, PROFILES[args.profile])


if __name__ == "__main__":
    sys.exit(main())
