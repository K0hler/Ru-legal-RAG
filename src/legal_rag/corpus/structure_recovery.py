"""Conservative recovery of explicitly superscripted siblings omitted by a sidecar."""

import copy
import re


RULE = "explicit-superscript-sibling/1"


def recover_siblings(candidates, units, owners, blocks, protected, soup):
    """Adjust normalized scopes only; retain original sidecar rows and evidence."""
    paragraphs = {}
    for b in blocks:
        paragraphs.setdefault(b["paragraph"], []).append(b)
    starts = {u["np"]: u for u in units}
    markers = {c["html_id"]: c for c in candidates if c["line"] == 0}
    recovered = []
    for c in candidates:
        exponent = c["number_components"]["superscript"]
        if (c["kind_hint"] != "numbered" or c["delimiter"] != "." or c["quoted"]
                or c["in_table"] or c["line"] or not exponent or not exponent.isdigit()
                or not c["html_id"] or c["html_id"] in starts):
            continue
        bs = paragraphs.get(c["paragraph"], [])
        if not bs or any(b["block_id"] in protected for b in bs):
            continue
        start, end = bs[0]["html_start"], bs[-1]["html_end"]
        owner = owners.by_id.get(owners.find(start, end))
        if not owner or owner["kind"] != "point" or owner.get("structure_origin") or owners.in_form(owner["source_id"]):
            continue
        parent = owners.by_id.get(owner["parent_source_id"])
        if parent and (parent["kind"] not in {"section", "annex", "approved_text"}
                       or "(форма)" in parent["caption"].casefold()):
            continue
        previous = markers.get(owner["np"])
        if (not previous or previous["delimiter"] != "." or previous["quoted"]
                or previous["number_components"]["base"] != c["number_components"]["base"]
                or not (previous["number_components"]["superscript"] or "").isdigit()
                or int(exponent) != int(previous["number_components"]["superscript"]) + 1):
            continue
        # A different paragraph style or a nested unit makes siblinghood uncertain.
        if set(soup.find(id=owner["np"]).get("class", [])) != set(soup.find(id=c["html_id"]).get("class", [])):
            continue
        if any(u["source_id"] != owner["source_id"] and owner["html_start"] <= u["html_start"]
               < owner["html_end"] and u["html_end"] > start for u in units):
            continue
        if any(u["parent_source_id"] == owner["parent_source_id"] and u["kind"] == "point"
               and u["number_canonical"] == c["number_canonical"] for u in units):
            continue
        if not owner["html_start"] < start < end <= owner["html_end"]:
            continue
        original_start, original_end = owner["html_start"], owner["html_end"]
        new = copy.deepcopy(owner)
        new.update(source_id="html:" + c["html_id"], np=c["html_id"], html_start=start,
                   number_canonical=c["number_canonical"], number_display=c["number_display"],
                   caption=c["excerpt"], source_state=None, structure_origin="html_recovery",
                   recovery_evidence={"rule": RULE, "html_id": c["html_id"], "paragraph": c["paragraph"],
                       "previous_source_id": owner["source_id"], "previous_address": owner["address"],
                       "source_declared_start": original_start, "source_declared_end": original_end,
                       "marker": copy.deepcopy(c)},
                   address=owner["address"].rsplit("/", 1)[0] + "/" + c["number_canonical"])
        owner.setdefault("source_declared_range", (original_start, original_end))
        owner["html_end"] = start
        recovered.append(new)
    units.extend(recovered)
    units.sort(key=lambda u: (u["html_start"], u["level"]))
    recovered.extend(recover_letter_lists(candidates, units, owners, blocks, protected))
    units.sort(key=lambda u: (u["html_start"], u["level"]))
    return recovered


def recover_letter_lists(candidates, units, owners, blocks, protected):
    """Recover only a complete adjacent alphabetic list introduced by a colon."""
    alphabet = "абвгдежзиклмнопрстуфхцчшщэюя"
    paragraphs = {}
    for b in blocks:
        if b["paragraph"] is not None and b["text"] and not b["note"] and not b["exclusion_reason"]:
            paragraphs.setdefault(b["paragraph"], []).append(b)
    ordered = sorted(paragraphs)
    markers = {c["paragraph"]: c for c in candidates if c["kind_hint"] == "letter"
               and not c["quoted"] and not c["in_table"] and not c["line"] and c["html_id"]}
    starts = {n["np"] for n in units}
    recovered = []
    for i, para in enumerate(ordered):
        intro = paragraphs[para]
        if not " ".join(b["numbering_text"] for b in intro).rstrip().endswith(":"):
            continue
        owner = owners.by_id.get(owners.find(intro[0]["html_start"], intro[-1]["html_end"]))
        if not owner or owner["kind"] not in {"part", "point"} or owners.in_form(owner["source_id"]):
            continue
        run = []
        for ordinal in ordered[i + 1:]:
            c, bs = markers.get(ordinal), paragraphs[ordinal]
            if (not c or len(run) >= len(alphabet) or c["number_canonical"] != alphabet[len(run)]
                    or c["html_id"] in starts or any(b["block_id"] in protected for b in bs)
                    or owners.find(bs[0]["html_start"], bs[-1]["html_end"]) != owner["source_id"]):
                break
            run.append((c, bs))
        if len(run) < 2:
            continue
        # A following letter with a gap is an incomplete list, not a partial success.
        next_index = i + 1 + len(run)
        if next_index < len(ordered) and ordered[next_index] in markers:
            continue
        for index, (c, bs) in enumerate(run):
            if index + 1 < len(run):
                end = run[index + 1][1][0]["html_start"]
            elif re.search(r",\s*[-–—]\s*$", " ".join(b["numbering_text"] for b in bs)):
                end = bs[-1]["html_end"]
            else:
                following = [n["html_start"] for n in units if bs[0]["html_start"] < n["html_start"] < owner["html_end"]
                             and n["level"] <= owner["level"] + 1]
                end = min(following, default=owner["html_end"])
            new = {**owner, "source_id": "html:" + c["html_id"], "np": c["html_id"],
                   "npe": c["html_id"], "html_start": bs[0]["html_start"], "html_end": end,
                   "kind": "item", "source_unit": "html_letter", "parent_source_id": owner["source_id"],
                   "level": owner["level"] + 1, "number_canonical": c["number_canonical"],
                   "number_display": c["number_display"], "number_is_explicit": True,
                   "caption": c["excerpt"], "source_state": None, "structure_origin": "html_recovery",
                   "address": owner["address"] + "/item/" + c["number_canonical"],
                   "recovery_evidence": {"rule": "explicit-letter-list/1", "html_id": c["html_id"],
                       "intro_html_id": intro[0]["html_id"], "parent_source_id": owner["source_id"],
                       "sequence": [m["number_canonical"] for m, _ in run],
                       "end_basis": "printed_list_closure" if end == bs[-1]["html_end"] else "next_peer_or_parent_end"}}
            for key in ("source_declared_range", "source_declared_anchors", "normalization_evidence", "number_origin"):
                new.pop(key, None)
            recovered.append(new)
    units.extend(recovered)
    return recovered
