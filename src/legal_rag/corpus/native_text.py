"""Saved actual.pravo HTML scalars; offsets address the evidence-bound field."""

from html import unescape
from html.parser import HTMLParser
import json
import re

from .compiler import content_hash
from .structure import build_structure


EXTRACTOR_VERSION = "actual-native-html/3"
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
    locator = asset["evidence"]["locator"]
    if locator not in {"$.redtext", "/redtext", "$.doctext", "/doctext"}:
        raise ValueError("native profile requires /redtext or /doctext evidence")
    field = locator.removeprefix("$.").removeprefix("/")
    response = json.loads(payload.decode("utf-8"))
    if not isinstance(response, dict) or response.get("error") is not None:
        raise ValueError("invalid native source response")
    html = response.get(field)
    if not isinstance(html, str) or not html.strip():
        raise ValueError(f"native response needs non-empty {field} HTML")
    from .housing_html import extract_html

    raw = extract_html(html.encode("utf-8"))
    entries = [*raw["text_nodes"], *raw["blocks"], *raw["unsupported_regions"]]
    for region in raw["unsupported_regions"]:
        for row in region.get("rows", []):
            entries.extend([row, *row["cells"]])
    for entry in entries:
        span = entry["source_span"]
        span.update(source_asset_sha256=asset["sha256"], json_pointer="/" + field,
                    offset_unit="unicode_codepoints_in_decoded_json_scalar")
        span["html_locator"] = "/" + field + span["html_locator"]
        span["locator"] = f"{span['html_locator']}:chars:{span['char_start']}:{span['char_end']}"
        if "block_id" in entry:
            entry["locator"] = span["locator"]
    extraction = {"schema_version": "text-extraction/1", "source_asset_sha256": asset["sha256"],
                  "extractor_version": EXTRACTOR_VERSION,
                  "config": {"profile": "actual.pravo." + field, "json_pointer": "/" + field,
                             "cleanup": "entity-decode-collapse-whitespace/1", "superscript_classes": ["W9", "WB"]},
                  "models": [], "text_nodes": raw["text_nodes"], "unsupported_regions": raw["unsupported_regions"],
                  "pages": [{"page": None, "mode": "native_text", "confidence": None, "blocks": raw["blocks"]}]}
    extraction["extraction_id"] = content_hash(extraction)
    return extraction


def native_tree(asset: dict, extraction: dict) -> dict:
    return build_structure(extraction, asset["declared_identity"], asset["role"])
