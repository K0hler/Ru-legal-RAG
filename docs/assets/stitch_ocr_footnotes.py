"""Join cross-page dots.mocr footnotes in a separate, source-bound logical view.

Native JSON is never rewritten. region_order lets a consumer read continuations
beside their anchor while fragments retain their actual page and bbox.
"""

import argparse
import hashlib
import json
from pathlib import Path
import re


MARKER = re.compile(r"^\s*(?:[\d⁰¹²³⁴⁵⁶⁷⁸⁹*†‡]|[\[(]\s*[\d⁰¹²³⁴⁵⁶⁷⁸⁹*†‡]|[а-яa-z]\))", re.I)


def stitch(native):
    records, page_records = {}, []
    for pi, page in enumerate(native["pages"]):
        pointers = []
        for ri, region in enumerate(page["layout"]):
            pointer = f"/pages/{pi}/layout/{ri}/text"
            records[pointer] = {"page": page["page_number"], "bbox": region["bbox"],
                                "category": region["category"], "text": region.get("text", "")}
            pointers.append(pointer)
        page_records.append(pointers)

    roots, groups, reasons = {}, {}, {}
    previous_notes = []
    for pi, (page, pointers) in enumerate(zip(native["pages"], page_records)):
        notes = [p for p in pointers if records[p]["category"] == "Footnote" and records[p]["text"].strip()]
        if previous_notes and notes and page["page_number"] == native["pages"][pi - 1]["page_number"] + 1:
            anchor = previous_notes[-1]
            candidates = []
            for pointer in notes:
                if MARKER.match(records[pointer]["text"]):
                    break
                candidates.append(pointer)
                reasons[pointer] = "unnumbered_footnote_on_next_page"
            # shortcut: recover only one parenthetical Text after a citation's
            # unfinished number; other untagged continuations need more evidence.
            if re.search(r"№\s*\d[\w/-]*\s*$", records[anchor]["text"]):
                width, height = page["image_size"]
                following = records[notes[0]]
                index = pointers.index(notes[0]) - 1
                if index >= 0:
                    pointer = pointers[index]
                    current = records[pointer]
                    x0, y0, _, y1 = current["bbox"]
                    gap = following["bbox"][1] - y1
                    if (current["category"] == "Text" and current["text"].lstrip().startswith("(")
                            and not MARKER.match(current["text"]) and y0 >= 0.75 * height
                            and -0.005 * height <= gap <= 0.01 * height
                            and abs(x0 - following["bbox"][0]) <= 0.02 * width):
                        candidates.insert(0, pointer)
                        reasons[pointer] = "parenthetical_footer_text_after_citation_number"
            root = roots.get(anchor, anchor)
            for pointer in candidates:
                roots[pointer] = root
                groups.setdefault(root, []).append(pointer)
        previous_notes = notes

    footnotes, order = [], []
    for pointer in records:
        if pointer in roots:
            continue
        fragments = [pointer, *groups.get(pointer, [])]
        order.extend(fragments)
        if pointer not in groups:
            continue
        text, sources = "", []
        for fragment in fragments:
            source = records[fragment]
            if sources:
                text += "\n"
            start = len(text)
            text += source["text"]
            sources.append({"json_pointer": fragment, "page": source["page"], "bbox": source["bbox"],
                            "category": source["category"], "start": start, "end": len(text),
                            "reason": reasons.get(fragment, "anchor")})
        footnotes.append({"anchor": pointer, "text": text, "fragments": sources})
    return {"schema_version": "ocr-footnote-stitch/1", "region_order": order, "footnotes": footnotes,
            "inferred": True, "qualification": False}


def run(source, output):
    raw = source.read_bytes()
    result = {**stitch(json.loads(raw)), "input_path": str(source.resolve()),
              "input_sha256": hashlib.sha256(raw).hexdigest(),
              "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    with output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run(args.input, args.output)
