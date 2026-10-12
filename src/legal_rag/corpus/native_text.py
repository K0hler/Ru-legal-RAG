"""Bounded actual.pravo redtext/HTML profile; all offsets address the JSON scalar."""

from html import unescape
from html.parser import HTMLParser
import json
import re

from .compiler import content_hash


EXTRACTOR_VERSION = "actual-redtext-html/1"
PARSER_VERSION = "native-59-structure/1"
VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}


def _cleanup(text: str) -> tuple[str, list[dict]]:
    mapping, offset = [], 0
    matches = list(re.finditer(r"\s+|\S+", text))
    for index, match in enumerate(matches):
        before = match[0]
        after = ("" if index in {0, len(matches) - 1} else " ") if before.isspace() else before
        mapping.append({"decoded_start": match.start(), "decoded_end": match.end(),
                        "text_start": offset, "text_end": offset + len(after),
                        "before": before, "after": after,
                        "operation": "copy" if before == after else "whitespace"})
        offset += len(after)
    return "".join(entry["after"] for entry in mapping), mapping


class _NativeHTML(HTMLParser):
    def __init__(self, html: str, digest: str):
        super().__init__(convert_charrefs=False)
        self.html, self.digest = html, digest
        self.line_starts = [0]
        for match in re.finditer("\n", html):
            self.line_starts.append(match.end())
        self.stack, self.text_nodes, self.groups = [], [], []
        self.paragraph_count = 0
        self.saw_body = False

    def scalar_offset(self):
        line, column = self.getpos()
        return self.line_starts[line - 1] + column

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "body":
            self.saw_body = True
        if tag == "p":
            if any(entry["tag"] == "p" for entry in self.stack):
                raise ValueError("nested/unclosed native paragraph")
            self.paragraph_count += 1
        if tag == "br":
            self.token(self.get_starttag_text(), "\n", kind="line_break")
        if tag not in VOID_TAGS:
            self.stack.append({"tag": tag, "attrs": attrs, "paragraph": self.paragraph_count})

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID_TAGS:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if tag in VOID_TAGS:
            return
        if not self.stack or self.stack[-1]["tag"] != tag:
            raise ValueError("unbalanced native HTML")
        self.stack.pop()

    def handle_data(self, data):
        self.token(data, data)

    def handle_entityref(self, name):
        self.entity(name)

    def handle_charref(self, name):
        self.entity("#" + name)

    def entity(self, name):
        raw = "&" + name
        if self.html[self.scalar_offset() + len(raw):].startswith(";"):
            raw += ";"
        self.token(raw, unescape(raw))

    def token(self, raw, decoded, kind="text"):
        start = self.scalar_offset()
        if self.html[start:start + len(raw)] != raw:
            raise ValueError("native text locator mismatch")
        tags = [entry["tag"] for entry in self.stack]
        paragraph = next((entry for entry in reversed(self.stack) if entry["tag"] == "p"), None)
        note = any(set(entry["attrs"].get("class", "").split()) & {"mark", "markx"} for entry in self.stack)
        superscript = any(entry["tag"] == "sup" or "W9" in entry["attrs"].get("class", "").split()
                          for entry in self.stack)
        reason = "non_document_text" if "body" not in tags or set(tags) & {"script", "style"} else "portal_control" if "label" in tags else None
        unsupported = bool(set(tags) & {"table", "ul", "ol"})
        locator = f"/redtext/html/p[{paragraph['paragraph']}]" if paragraph else "/redtext/html/" + "/".join(tags)
        key = (paragraph["paragraph"] if paragraph else None, note, reason, locator, unsupported)
        # Outside-paragraph nodes remain separate; no unlocated or hidden service text.
        if not self.groups or self.groups[-1]["key"] != key or paragraph is None:
            self.groups.append({"key": key, "tokens": [], "note": note, "reason": reason,
                                "unsupported": unsupported,
                                "paragraph": paragraph["paragraph"] if paragraph else None,
                                "html_id": paragraph["attrs"].get("id") if paragraph else None})
        span = {"source_asset_sha256": self.digest, "json_pointer": "/redtext", "html_locator": locator,
                "char_start": start, "char_end": start + len(raw),
                "offset_unit": "unicode_codepoints_in_decoded_json_scalar",
                "locator": f"{locator}:chars:{start}:{start + len(raw)}"}
        token = {"text_node_id": len(self.text_nodes), "kind": kind, "raw_text": raw,
                 "decoded_text": decoded, "superscript": superscript, "source_span": span}
        self.text_nodes.append(token)
        self.groups[-1]["tokens"].append(token)


def extract_native(asset: dict, payload: bytes) -> dict:
    if asset["evidence"]["locator"] not in {"$.redtext", "/redtext"}:
        raise ValueError("native profile requires /redtext evidence")
    response = json.loads(payload.decode("utf-8"))
    if not isinstance(response, dict) or response.get("error") is not None:
        raise ValueError("invalid native source response")
    html = response.get("redtext")
    if not isinstance(html, str) or not html.strip():
        raise ValueError("native response needs non-empty redtext HTML")
    parser = _NativeHTML(html, asset["sha256"])
    parser.feed(html)
    parser.close()
    if parser.stack or not parser.saw_body:
        raise ValueError("incomplete native HTML document")
    blocks = []
    for group in parser.groups:
        tokens = group["tokens"]
        original = "".join(token["decoded_text"] for token in tokens)
        text, mapping = _cleanup(original)
        span = {**tokens[0]["source_span"], "char_end": tokens[-1]["source_span"]["char_end"]}
        span["locator"] = f"{span['html_locator']}:chars:{span['char_start']}:{span['char_end']}"
        decoding, offset = [], 0
        for token in tokens:
            decoding.append({"text_node_id": token["text_node_id"], "decoded_start": offset,
                             "decoded_end": offset + len(token["decoded_text"]),
                             "operation": "copy" if token["raw_text"] == token["decoded_text"] else "entity_or_break"})
            offset += len(token["decoded_text"])
        # Preserve visible spelling; the address separately records a source-marked exponent.
        prefix = "".join(("^" if token["superscript"] and (index == 0 or not tokens[index - 1]["superscript"]) else "")
                         + token["decoded_text"] for index, token in enumerate(tokens))
        blocks.append({"block_id": len(blocks), "text": text, "original_text": original,
                       "original_html": html[span["char_start"]:span["char_end"]],
                       "source_span": span, "locator": span["locator"], "text_node_ids": [t["text_node_id"] for t in tokens],
                       "decoding_mapping": decoding, "cleanup_mapping": mapping,
                       "numbering_text": _cleanup(prefix)[0], "note": group["note"],
                       "unsupported_structure": group["unsupported"],
                       "ambiguous_boundary": bool(re.search(
                           r"[\r\n]\s*(?:Статья [0-9]+\.|[0-9]+(?:[.^][0-9]+)*[.)]|[а-яa-z]\))\s", original)),
                       "exclusion_reason": group["reason"], "paragraph": group["paragraph"],
                       "html_id": group["html_id"], "bbox": None, "table_cells": [], "unresolved_regions": []})
    extraction = {"schema_version": "text-extraction/1", "source_asset_sha256": asset["sha256"],
                  "extractor_version": EXTRACTOR_VERSION,
                  "config": {"profile": "actual.pravo.redtext", "json_pointer": "/redtext",
                             "cleanup": "entity-decode-collapse-whitespace/1", "superscript_class": "W9"},
                  "models": [], "text_nodes": parser.text_nodes,
                  "pages": [{"page": None, "mode": "native_text", "confidence": None, "blocks": blocks}]}
    extraction["extraction_id"] = content_hash(extraction)
    return extraction


def native_tree(asset: dict, extraction: dict) -> dict:
    blocks = extraction["pages"][0]["blocks"]
    visible = [block for block in blocks if not block["exclusion_reason"] and not block["note"]]
    article_indices = [index for index, block in enumerate(visible) if re.match(r"Статья [0-9]", block["text"])]
    preamble_blocks = visible[:article_indices[0]] if article_indices else []
    preamble = [block["text"] for block in preamble_blocks]
    signing_indices = [index for index, block in enumerate(visible)
                       if article_indices and index > article_indices[-1]
                       and block["text"].startswith("Президент Российской Федерации")]
    signature = visible[signing_indices[0]:] if len(signing_indices) == 1 else []
    numbers = [block["text"] for block in signature if re.match(r"№\s*[0-9]", block["text"])]
    dates = [block["text"] for block in signature if re.fullmatch(r"[0-9]+ [а-я]+ [0-9]{4} года", block["text"])]
    claim = _cleanup(asset["declared_identity"])[0]
    claimed = re.fullmatch(r'Федеральный закон от 02\.05\.2006 № 59-ФЗ "([^"]+)"', claim)
    identity_matches = bool(claimed and "ФЕДЕРАЛЬНЫЙ ЗАКОН" in preamble and claimed[1] in preamble
                            and numbers == ["№ 59-ФЗ"] and dates == ["2 мая 2006 года"])
    identity = {"act_id": content_hash({"declared_identity": asset["declared_identity"]}),
                "declared_identity": asset["declared_identity"],
                "status": "claim_matches_header" if identity_matches else "unresolved",
                "evidence_block_ids": [b["block_id"] for b in [*preamble_blocks, *signature] if b["text"] in {
                    "ФЕДЕРАЛЬНЫЙ ЗАКОН", "№ 59-ФЗ", "2 мая 2006 года", claimed[1] if claimed else ""}]}
    namespace = "act" if asset["role"] != "amendment" else "amendment/" + asset["sha256"]
    nodes, unresolved, excluded, addresses = [], [], [], set()
    article = part = item = last = last_paragraph = None
    counters = {}

    def numbered(parent, kind):
        key = (parent, kind)
        counters[key] = counters.get(key, 0) + 1
        return f"{parent}/{kind}/{counters[key]}"

    for block in blocks:
        entry = {key: block[key] for key in ("text", "source_span", "text_node_ids", "original_text", "original_html", "block_id")}
        if block["exclusion_reason"] or not block["text"]:
            excluded.append({**entry, "reason": block["exclusion_reason"] or "whitespace"})
            continue
        text = block["text"]
        kind = address = None
        reason = "unsupported_or_ambiguous_native_structure"
        heading = re.fullmatch(r"Статья ([1-9][0-9]*(?:\.[1-9][0-9]*)?)\. .+", text)
        part_match = re.match(r"^([1-9][0-9]*(?:[.^][1-9][0-9]*)?)\.\s", block["numbering_text"])
        item_match = re.match(r"^([1-9][0-9]*)\)\s", text)
        subitem = re.match(r"^([а-яa-z])\)\s", text)
        if not identity_matches:
            reason = "identity_unresolved"
        elif block["paragraph"] is None:
            reason = "unaddressed_document_text"
        elif block["unsupported_structure"]:
            reason = "unsupported_native_table_or_list"
        elif block["ambiguous_boundary"]:
            reason = "multiple_native_provision_boundaries"
        elif block["note"] or text.startswith(("Примечание", "(В редакции", "(Особенности", "(С учетом")):
            parent = last if last and last_paragraph == block["paragraph"] else namespace
            kind, address = "note", numbered(parent, "note")
        elif heading:
            kind, address = "article", namespace + "/article/" + heading[1]
            article, part, item = address, None, None
        elif text.startswith(("Статья", "Приложение", "Глава", "Раздел", "Таблица")):
            article = part = item = last = None
        elif text in {"РОССИЙСКАЯ ФЕДЕРАЦИЯ", "ФЕДЕРАЛЬНЫЙ ЗАКОН", claimed[1], "№ 59-ФЗ", "2 мая 2006 года", "Москва, Кремль"} or text.startswith(("Принят Государственной Думой", "Одобрен Советом Федерации", "Президент Российской Федерации")):
            kind, address = "header", numbered(namespace, "header")
            article = part = item = None
        elif article and part_match:
            kind, address = "part", article + "/part/" + part_match[1].replace("^", ".")
            part, item = address, None
        elif article and item_match:
            kind, address = "item", (part or article) + "/item/" + item_match[1]
            item = address
        elif article and subitem and (item or part):
            kind, address = "subitem", (item or part) + "/subitem/" + subitem[1]
        elif article and not re.match(r"^(?:\d+(?:[.^]\d+)*[.)]|[а-яa-zA-ZА-Я][.)]\s)", text):
            kind, address = "paragraph", numbered(item or part or article, "paragraph")
        if address in addresses:
            reason, kind, address = "duplicate_address", None, None
            article = part = item = last = None
        if kind:
            addresses.add(address)
            parent = address.rsplit("/", 2)[0] if kind != "article" else namespace
            nodes.append({**entry, "kind": kind, "address": address, "parent_address": parent,
                          "provision_id": content_hash({"extraction_id": extraction["extraction_id"], "address": address})})
            if kind != "note":
                last = address
                last_paragraph = block["paragraph"]
        else:
            unresolved.append({**entry, "kind": "unresolved_block", "reason": reason})
            article = part = item = last = None
    token_sizes = {t["text_node_id"]: len(t["raw_text"]) for t in extraction["text_nodes"]}
    accounting = {"total_source_chars": sum(token_sizes.values()), "total_text_nodes": len(token_sizes),
                  "total_chars": sum(len(b["text"]) for b in blocks)}
    for name, entries in (("parsed", nodes), ("unresolved", unresolved), ("excluded", excluded)):
        accounting[name + "_source_chars"] = sum(token_sizes[i] for b in entries for i in b["text_node_ids"])
        accounting[name + "_text_nodes"] = sum(len(b["text_node_ids"]) for b in entries)
        accounting[name + "_chars"] = sum(len(b["text"]) for b in entries)
    return {"schema_version": "legal-ast/1", "parser_version": PARSER_VERSION,
            "extraction_id": extraction["extraction_id"], "source_asset_sha256": asset["sha256"],
            "role": asset["role"], "identity_decision": identity, "namespace": namespace,
            "nodes": nodes, "unresolved_blocks": unresolved, "excluded_blocks": excluded,
            "cleanup_mapping": [{"block_id": b["block_id"], "mapping": b["cleanup_mapping"]} for b in blocks],
            "accounting": accounting}
