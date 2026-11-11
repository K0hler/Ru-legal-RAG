"""Preconditions and decisions for a retained amendment-ledger/1 proposal."""

from datetime import datetime

from .compiler import _date, _object, _strings, _text, content_hash


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _subtree(nodes, address):
    node = nodes[address]
    result = [node]
    for child in node["children"]:
        result.extend(_subtree(nodes, child))
    return result


def bind_operations(original, proposals):
    """Check preconditions in proposed order without generating a dated edition."""
    nodes = {node["address"]: node for node in original["nodes"]}
    _require(len(nodes) == len(original["nodes"]), "duplicate original address")
    resolved = {}
    changed_by = {}
    for proposal in proposals:
        op = dict(proposal)
        op_id = _text(op["id"])
        try:
            _require(op_id not in resolved, "duplicate operation ID")
            _require(bool(op["evidence"]), "missing operation evidence")
            kind = op["kind"]
            address = op["target"]
            node = nodes[address]
            owner = op["owner"]
            dependencies = _strings(op["requires"])
            _require(set(dependencies) <= resolved.keys(), "unknown or forward dependency")
            _require(node["parent_address"] == "act/owner/" + owner, "target owner mismatch")
            affected = _subtree(nodes, address) if kind == "delete_unit" else [node]
            previous = {changed_by[n["address"]] for n in affected if n["address"] in changed_by}
            _require(previous <= set(dependencies), "missing dependency for modified target")
            op["expected_before"] = {"sha256": content_hash(affected), "nodes": affected}
            if kind in {"replace_text", "insert_text"}:
                before, after = op["payload"]["before"], _text(op["payload"]["after"])
                old = node["text"]
                _require(node["kind"] == "text", "text operation requires a text node")
                if op.get("paragraph") is not None:
                    siblings = [a for a in nodes[node["parent_address"]]["children"] if nodes[a]["kind"] == "text"]
                    _require(type(op["paragraph"]) is int and siblings.index(address) + 1 == op["paragraph"],
                             "paragraph number differs from target")
                if kind == "replace_text":
                    _require(old.count(_text(before)) == 1 and before != after, "missing or ambiguous text precondition")
                    start = old.index(before)
                else:
                    _require(before == "" and old.endswith(_text(op["punctuation"])), "insertion boundary mismatch")
                    _require(op["position"] in {"end", "before_final_punctuation"}, "unknown insertion boundary")
                    start = len(old) - (len(op["punctuation"]) if op["position"] == "before_final_punctuation" else 0)
                end = start + len(before)
                op["range"] = [start, end]
                nodes[address] = {**node, "text": old[:start] + after + old[end:]}
                changed_by[address] = op_id
            elif kind == "insert_after":
                payload = op["payload"]
                destination, number = _text(payload["address"]), payload["number"]
                body = _text(payload["text"])
                parent = nodes[node["parent_address"]]
                siblings = list(parent["children"])
                index = siblings.index(address) + 1
                suffix = number if number is not None else f"paragraph/{index + 1}"
                _require(destination == parent["address"] + "/" + suffix and destination not in nodes,
                         "invalid or occupied insertion address")
                _require(number is None or body.startswith(number + ". "), "inserted point number mismatch")
                op["expected_before"]["next_sibling"] = siblings[index] if index < len(siblings) else None
                op["expected_before"]["absent_address"] = destination
                siblings.insert(index, destination)
                nodes[parent["address"]] = {**parent, "children": siblings}
                if number is not None:
                    text_address = destination + "/text"
                    _require(text_address not in nodes, "occupied insertion text address")
                    op["expected_before"]["absent_text_address"] = text_address
                    nodes[destination] = {"address": destination, "children": [text_address], "text": "",
                                          "parent_address": parent["address"], "kind": "point", "number": number}
                    changed_by[destination] = op_id
                else:
                    text_address = destination
                nodes[text_address] = {"address": text_address, "children": [], "text": body, "kind": "text",
                                       "parent_address": destination if number is not None else parent["address"]}
                changed_by[text_address] = op_id
            elif kind == "delete_unit":
                _require(node["kind"] == "point" and op["payload"] is None, "invalid unit deletion")
                parent = nodes[node["parent_address"]]
                nodes[parent["address"]] = {**parent, "children": [a for a in parent["children"] if a != address]}
                for item in affected:
                    del nodes[item["address"]]
            else:
                raise ValueError(f"unsupported operation {kind}")
        except (ValueError, KeyError, TypeError) as error:
            raise ValueError(f"{op_id}: {error}") from error
        resolved[op_id] = op
    return list(resolved.values())


def check_review(ledger, review=None, independent=None):
    """Report readiness by target date from supplied human records."""
    operations = {op["id"]: op for op in ledger["operations"]}
    order = {op_id: index for index, op_id in enumerate(operations)}
    dates = ledger["target_dates"]
    if review is None:
        _require(independent is None, "independent review requires a first review")
        return dict.fromkeys(dates, "awaiting_legal_review")
    records = (review,) if independent is None else (review, independent)
    for record in records:
        _object(record, {"schema_version", "ledger_sha256", "reviewer", "role", "reviewed_at",
                         "rationale", "operations", "dates"}, optional={"first_review_sha256"})
        _require(record["schema_version"] == "amendment-ledger-review/1"
                 and record["ledger_sha256"] == content_hash(ledger), "review binds a different ledger")
        _require(record["role"] == "Legal Reviewer", "Legal Reviewer role required")
        _text(record["reviewer"])
        _text(record["rationale"])
        _require(datetime.fromisoformat(_text(record["reviewed_at"])).utcoffset() is not None,
                 "review time requires a UTC offset")
        _object(record["operations"], set(operations))
        _require(all(value in {"confirmed", "rejected", "disputed", "unresolved"}
                     for value in record["operations"].values()), "invalid operation decision")
        _object(record["dates"], set(dates))
        for target_date, decision in record["dates"].items():
            _object(decision, {"complete", "rationale", "dispositions"})
            _require(decision["complete"] in {"confirmed", "disputed", "unresolved"}, "invalid completeness decision")
            _text(decision["rationale"])
            _object(decision["dispositions"], set(operations))
            for op_id, row in decision["dispositions"].items():
                _object(row, {"status", "rationale"}, optional={"basis"})
                status = row["status"]
                _require(status in {"include", "not_yet_effective", "outside_scope", "superseded", "unresolved"},
                         "invalid dated disposition")
                _text(row["rationale"])
                if status in {"include", "not_yet_effective"}:
                    start = _date(operations[op_id]["effect"]["start"])
                    _require((start <= target_date) == (status == "include"), "disposition conflicts with ledger date")
                if status == "include":
                    _require(all(decision["dispositions"][dep]["status"] == "include"
                                 for dep in operations[op_id]["requires"]), "included operation lacks its predecessor")
                if status in {"outside_scope", "superseded"}:
                    basis = _object(row.get("basis"), {"operation_id", "address"})
                    source_id = basis["operation_id"]
                    _require(source_id in operations and any(e["address"] == basis["address"]
                             for e in operations[source_id]["evidence"]), "exclusion has no bound official evidence")
                    if status == "outside_scope":
                        _require(source_id == op_id, "scope exclusion must cite the affected operation")
                    else:
                        affected = {n["address"] for n in operations[source_id]["expected_before"]["nodes"]}
                        _require(order[source_id] > order[op_id]
                                 and decision["dispositions"][source_id]["status"] == "include"
                                 and operations[op_id]["target"] in affected,
                                 "supersession requires a later included operation")
                else:
                    _require("basis" not in row, "unexpected exclusion evidence")
    _require(review["reviewer"] == ledger["primary_legal_reviewer"] and "first_review_sha256" not in review,
             "first decision requires the assigned Legal Reviewer")
    if independent is not None:
        _require(independent["first_review_sha256"] == content_hash(review)
                 and independent["reviewer"].strip().casefold() != review["reviewer"].strip().casefold(),
                 "second decision must be independent and bind the first")
    result = {}
    for date in dates:
        first = review["dates"][date]
        if independent is not None and (
            independent["operations"] != review["operations"]
            or independent["dates"][date]["complete"] != first["complete"]
            or any({k: v for k, v in row.items() if k != "rationale"} !=
                   {k: v for k, v in independent["dates"][date]["dispositions"][op].items() if k != "rationale"}
                   for op, row in first["dispositions"].items())
        ):
            result[date] = "disputed"
        elif first["complete"] == "disputed" or "disputed" in review["operations"].values():
            result[date] = "disputed" if independent else "independent_legal_review_required"
        elif (first["complete"] != "confirmed" or any(value != "confirmed" for value in review["operations"].values())
              or any(row["status"] == "unresolved" for row in first["dispositions"].values())):
            result[date] = "unresolved"
        else:
            result[date] = "reviewed_for_reconstruction"
    return result
