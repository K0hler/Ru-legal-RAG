"""Conservative recovery of explicitly superscripted siblings omitted by a sidecar."""

import copy


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
        owner["source_declared_range"] = (original_start, original_end)
        owner["html_end"] = start
        recovered.append(new)
    units.extend(recovered)
    units.sort(key=lambda u: (u["html_start"], u["level"]))
    return recovered
