"""Conservative, parser-independent HTML preparation; no legal hierarchy inference."""

import hashlib
from html.parser import HTMLParser
from pathlib import Path
import platform
import re
import json

import bs4
from bs4 import BeautifulSoup, Comment, Declaration, Doctype, ProcessingInstruction
import tinycss2

from .compiler import _write_once, content_hash, json_bytes, load_input


PREPARER_VERSION = "html-preparation/1"
DROP_TAGS = {"head", "script", "style"}
HEAD_TAGS = {"title", "base", "link", "meta", "style", "script", "noscript", "template"}
PRESENTATION_ATTRIBUTES = {
    "class", "style", "align", "valign", "color", "bgcolor", "face", "size",
    "border", "cellpadding", "cellspacing", "width", "height", "hidden", "aria-hidden",
}
NON_TEXT = (Comment, Declaration, Doctype, ProcessingInstruction)


class _OpeningTags(HTMLParser):
    """Exact opening-tag anchors; do not mistake them for complete element spans."""

    def __init__(self, html):
        super().__init__()
        self.line_starts = [0, *(match.end() for match in re.finditer("\n", html))]
        self.spans = {}
        self.feed(html)
        self.close()

    def handle_starttag(self, tag, attrs):
        line, column = self.getpos()
        start = self.line_starts[line - 1] + column
        self.spans[start] = start + len(self.get_starttag_text())

    handle_startendtag = handle_starttag


def _text(root):
    return "".join(str(node) for node in root.find_all(string=True) if not isinstance(node, NON_TEXT))


def _vertical_align(style):
    declarations = [node for node in tinycss2.parse_blocks_contents(style)
                    if node.type == "declaration" and node.lower_name == "vertical-align"]
    important = [node for node in declarations if node.important]
    values = important or declarations
    return (tinycss2.serialize(values[-1].value).strip().lower(), values[-1].important) if values else None


def prepare_html(html: str) -> dict:
    """Preserve DOM content and source anchors; strip explicit technical formatting."""
    if not isinstance(html, str) or not html.strip():
        raise ValueError("HTML must be a non-empty string")
    soup = BeautifulSoup(html, "html.parser")
    for head in soup.find_all("head"):
        if head.find("body") or any(child.name not in HEAD_TAGS for child in head.find_all(recursive=False)):
            raise ValueError("document content inside head requires HTML repair before preparation")
        if any(not isinstance(child, (bs4.Tag, *NON_TEXT)) and str(child).strip() for child in head.contents):
            raise ValueError("unexpected text inside head requires HTML repair before preparation")
    openings = _OpeningTags(html)
    source_text_chars = len(_text(soup))
    # Only standalone .class / tag.class selectors qualify. Complex CSS stays in source.
    alignment = {}
    for style in soup.find_all("style"):
        css = "".join(str(node) for node in style.find_all(string=True))
        for rule in tinycss2.parse_stylesheet(css, skip_comments=True, skip_whitespace=True):
            if rule.type != "qualified-rule":
                continue
            value = _vertical_align(rule.content)
            if value is not None:
                for selector in tinycss2.serialize(rule.prelude).split(","):
                    match = re.fullmatch(r"([A-Za-z][\w-]*)?\.([\w-]+)", selector.strip())
                    if match:
                        alignment.setdefault((match[1].lower() if match[1] else None, match[2]), set()).add(value)
    source_map = []
    for index, tag in enumerate(soup.find_all(True)):
        start = openings.line_starts[tag.sourceline - 1] + tag.sourcepos
        excluded = next((parent.name for parent in [tag, *tag.parents] if parent.name in DROP_TAGS), None)
        row = {"key": f"e{index}", "tag": tag.name, "attributes": dict(tag.attrs),
               "source_start": start, "source_end": openings.spans[start],
               "output_start": None, "output_end": None, "exclusion_reason": excluded}
        source_map.append(row)
        if excluded:
            continue
        classes = tag.get("class", [])
        values = {value for cls in classes for key in ((None, cls), (tag.name, cls)) for value in alignment.get(key, ())}
        inline = _vertical_align(tag.get("style", ""))
        important_values = {value for value, important in values if important}
        if inline is not None and (inline[1] or not important_values):
            value = inline[0]
        else:
            candidates = important_values or {value for value, _ in values}
            value = next(iter(candidates)) if len(candidates) == 1 else None
        if tag.name in {"span", "font"} and value in {"super", "sub"}:
            tag.name = "sup" if value == "super" else "sub"
        elif tag.name == "font":
            tag.name = "span"
        tag.attrs = {key: value for key, value in tag.attrs.items()
                     if key not in PRESENTATION_ATTRIBUTES and not key.startswith("on")}
        if set(classes) & {"mark", "markx"}:
            tag["data-lr-note"] = "true"
    excluded = []
    # Empty comments keep neighbouring whitespace nodes separate on the next parse.
    for node in list(soup.find_all(string=lambda value: isinstance(value, NON_TEXT))):
        excluded.append({"reason": type(node).__name__, "text": "", "markup": str(node)})
        node.replace_with(Comment(""))
    for tag in list(soup.find_all(DROP_TAGS)):
        if not any(parent.name in DROP_TAGS for parent in tag.parents):
            excluded.append({"reason": tag.name, "text": _text(tag),
                             "source_start": openings.line_starts[tag.sourceline - 1] + tag.sourcepos})
            tag.replace_with(Comment(""))
    retained = _text(soup)
    prepared = soup.decode(formatter="minimal")
    output = BeautifulSoup(prepared, "html.parser")
    output_openings = _OpeningTags(prepared)
    retained_rows = (row for row in source_map if row["exclusion_reason"] is None)
    for row, tag in zip(retained_rows, output.find_all(True), strict=True):
        start = output_openings.line_starts[tag.sourceline - 1] + tag.sourcepos
        row.update(output_start=start, output_end=output_openings.spans[start])
    excluded_chars = sum(len(row["text"]) for row in excluded)
    if _text(output) != retained or source_text_chars != len(retained) + excluded_chars:
        raise ValueError("HTML preparation changed or lost decoded text")
    return {"schema_version": PREPARER_VERSION,
            "runtime": {"beautifulsoup4": bs4.__version__, "tinycss2": tinycss2.__version__,
                        "python": platform.python_version(), "parser": "html.parser"},
            "source_html_sha256": hashlib.sha256(html.encode("utf-8")).hexdigest(),
            "prepared_html_sha256": hashlib.sha256(prepared.encode("utf-8")).hexdigest(),
            "offset_unit": "unicode_codepoints_in_html", "span_kind": "opening_tag",
            "source_map": source_map, "excluded": excluded,
            "accounting": {"source_text_chars": source_text_chars, "retained_text_chars": len(retained),
                           "excluded_text_chars": excluded_chars}, "html": prepared}


def prepare_input(input_path: Path, target_date: str, output_dir: Path) -> dict:
    """Validate the retained portal wrapper and permission before derived writes."""
    manifest, raw, archive = load_input(input_path, target_date)
    if len(manifest["assets"]) != 1:
        raise ValueError("HTML preparation requires one source asset")
    asset = manifest["assets"][0]
    fields = {"$.redtext": "redtext", "/redtext": "redtext", "$.doctext": "doctext", "/doctext": "doctext"}
    locator = asset["evidence"]["locator"]
    if asset["metadata"]["media_type"].split(";")[0] != "application/json" or locator not in fields:
        raise ValueError("HTML preparation requires explicit /redtext or /doctext JSON evidence")
    response = json.loads(raw[asset["sha256"]].decode("utf-8"))
    if not isinstance(response, dict) or response.get("error") is not None:
        raise ValueError("invalid source response")
    source = response.get(fields[locator])
    preparation = prepare_html(source)
    prepared = preparation.pop("html")
    record = {**preparation, "input_hash": manifest["manifest_hash"], "validated_input_hash": content_hash(manifest),
              "source_asset_sha256": asset["sha256"], "source_url": asset["source_url"],
              "json_pointer": "/" + fields[locator], "target_date_claim": target_date,
              "admission_status": manifest["admission_status"], "admission_blockers": manifest["admission_blockers"],
              "source_statuses": manifest["source_statuses"], "legal_admission": "not_requested"}
    record["preparation_id"] = content_hash(record)
    output_dir = Path(output_dir).resolve()
    directory = output_dir / record["preparation_id"]
    files = {directory / "source.html": source.encode("utf-8"), directory / "prepared.html": prepared.encode("utf-8"),
             directory / "manifest.json": json_bytes(record), directory / "input.json": json_bytes(manifest)}
    protected = [(archive / name).resolve() for name in ("raw", "assets", "items", "relations", "candidates", "approved")]
    for path, payload in files.items():
        resolved = path.resolve()
        if not resolved.is_relative_to(output_dir) or any(resolved.is_relative_to(root) for root in protected):
            raise ValueError("HTML output overlaps protected source/approved state or escapes output")
        if path.exists() and path.read_bytes() != payload:
            raise ValueError(f"immutable artifact conflict: {path}")
    result = "unchanged" if all(path.exists() for path in files) else "new"
    for path, payload in files.items():
        if not path.exists():
            _write_once(path, payload)
    return {"result": result, "preparation_id": record["preparation_id"],
            "html": str(directory / "prepared.html"), "source_html": str(directory / "source.html"),
            "manifest": str(directory / "manifest.json")}
