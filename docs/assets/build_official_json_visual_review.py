"""Build an offline source/JSON/failure comparison from retained evidence only."""

from collections import Counter
import hashlib
from html import escape
import json
from pathlib import Path
import sys

from bs4 import BeautifulSoup, Comment, NavigableString

PROJECT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT / "src"))
from acquire_official_json_transfer import sha  # noqa: E402
from validate_official_json_transfer import source_input  # noqa: E402
from legal_rag.corpus.official_structure import Anchors  # noqa: E402

INPUTS = PROJECT / "data/m1/pilot_runs/official-json-qualification-20261016-v1"
VALIDATION = PROJECT / "data/m1/pilot_runs/official-json-qualification-20261016-validation-v1"
OUT = Path(__file__).with_name("official-json-visual-review-20261016")
CASES = {
    "building-safety": {"name": "384-ФЗ — цитируемая статья", "target": "h7_a43", "kind": "reader",
        "verdict": "Ошибка контрольной проверки, а не вложенности JSON",
        "reason": "В статье 43 закона №384-ФЗ приведён текст новой статьи 5¹ другого закона — №184-ФЗ. Адаптер правильно поместил её внутрь цитаты. Проверяющий взял ближайшую статью 5¹ и сравнил её с основной статьёй 43, хотя статья 43 также присутствует выше в цепочке родителей.",
        "detail": "Официальный JSON оставляет весь этот текст в статье 43. В нём нет отдельного узла для цитируемой статьи 5¹. Такое дерево проще и в показанном месте сохраняет правильную принадлежность текста.",
        "takeaway": "Можно оставить цитату цельным текстом статьи 43. Дополнительное поддерево статьи 5¹ для этого фрагмента необязательно."},
    "civil-procedure": {"name": "ГПК РФ — последний отказ адаптера", "target": "sii_di", "kind": "adapter",
        "verdict": "Адаптер не поддерживает тип «подраздел»",
        "reason": "JSON прямо указывает unit=подраздел и lvl=1. В таблице типов нашего адаптера подраздела нет. Код останавливается до построения дерева этого документа. Сообщение про отсутствие номера здесь не объясняет настоящую причину: номер I напечатан в заголовке.",
        "detail": "Официальное дерево показывает: раздел II → подраздел I → глава 11 → статья 121. В показанном месте нет обнаруженного конфликта родителей или границ.",
        "takeaway": "Для сохранения этого дерева достаточно оставить тип «подраздел» таким, каким его выдал источник."},
    "budget": {"name": "Бюджетный кодекс — заголовок части", "target": "b1", "kind": "adapter",
        "verdict": "Слишком узкое правило распознавания заголовка",
        "reason": "Наше правило принимает строку «ЧАСТЬ ПЕРВАЯ» целиком. Источник выдаёт «ЧАСТЬ ПЕРВАЯ. ОБЩИЕ ПОЛОЖЕНИЯ». Из-за названия после номера совпадение не находится. Это ограничение нашего правила; в JSON уже стоят unit=часть и lvl=0.",
        "detail": "Дочерние глава, статья и пункты уже перечислены в JSON с согласованными уровнями и диапазонами. Для их сохранения распознавать этот заголовок регулярным выражением не требуется.",
        "takeaway": "Можно хранить исходный заголовок целиком, сохранив тип и вложенность из JSON."},
    "disability": {"name": "181-ФЗ — ненумерованный абзац", "target": "hiv_a15:1~_q1", "kind": "adapter",
        "verdict": "Адаптер не поддерживает тип «абзац»",
        "reason": "Источник выделил вводный абзац статьи 15¹: unit=абзац, caption=*абзац 1. Типа «абзац» в таблице адаптера нет, поэтому документ получает отказ. Сам текст начинается со слова «Соблюдение»; печатного номера 1 у этого абзаца нет.",
        "detail": "Звёздочка и номер находятся в служебной подписи JSON. Следующие пункты 1), 2), 3) находятся на том же уровне под статьёй. JSON не превращает вводный абзац в родителя этих пунктов.",
        "takeaway": "Можно сохранить служебный узел абзаца и его исходную подпись, не придумывая печатный номер."},
    "resource-contracts": {"name": "ПП РФ №124 — прошёл", "target": "j1", "kind": "pass",
        "verdict": "Отказа не было: документ прошёл полный контроль",
        "reason": "Официальный JSON, адаптер и независимые проверки согласованы. Включён для сравнения с отказавшими документами того же набора.",
        "detail": "Ниже показаны первые пункты постановления. Все 128 узлов исходного JSON имеют существующие ссылки и формально согласованные диапазоны.",
        "takeaway": "Здесь нет причины отказа, которую нужно исправлять."},
    "heat-metering": {"name": "ПП РФ №1034 — последний по порядку, прошёл", "target": "zf1", "kind": "pass",
        "verdict": "Последний скачанный документ прошёл полный контроль",
        "reason": "Если под «последним документом» имеется в виду последний в списке загрузки, это №1034. Он не был отклонён. Последним отказом именно адаптера в той серии был ГПК; №384-ФЗ отклонил отдельный проверяющий.",
        "detail": "Ниже показаны утверждённые Правила и начало их вложенной структуры. Все 271 узел JSON имеют существующие ссылки и формально согласованные диапазоны.",
        "takeaway": "Адаптер не сообщил ошибки в этом документе."},
}


def markup(tag):
    """Display source formatting without executing source HTML or attributes."""
    if isinstance(tag, Comment):
        return ""
    if isinstance(tag, NavigableString):
        return escape(str(tag))
    if tag.name in {"script", "style", "label", "img"}:
        return ""
    body = "".join(markup(child) for child in tag.children)
    if tag.name == "br":
        return "<br>"
    if tag.name in {"sup", "sub", "b", "strong", "i", "em"}:
        return f"<{tag.name}>{body}</{tag.name}>"
    if set(tag.get("class", [])) & {"W9", "WB"}:
        return "<sup>" + body + "</sup>"
    if set(tag.get("class", [])) & {"mark", "markx"}:
        return '<span class="editorial">' + body + "</span>"
    return body


def formal_checks(rows, anchors):
    issues, stack, seen, previous, parents = [], [], set(), {}, {}
    for i, row in enumerate(rows):
        if row["id"] in seen:
            issues.append({"check": "duplicate_id", "index": i})
        seen.add(row["id"])
        while stack and stack[-1]["lvl"] >= row["lvl"]:
            stack.pop()
        parent = stack[-1] if stack else None
        pid = parent["id"] if parent else None
        parents[row["id"]] = pid
        if row["lvl"] != (parent["lvl"] + 1 if parent else 0):
            issues.append({"check": "level_jump", "index": i})
        if parent and not row["id"].startswith(pid + "_"):
            issues.append({"check": "parent_prefix", "index": i})
        if any(row[k] not in anchors for k in ("np", "npe")):
            issues.append({"check": "missing_anchor", "index": i})
        else:
            start, end = anchors[row["np"]]["start"], anchors[row["npe"]]["end"]
            if start >= end:
                issues.append({"check": "reversed_range", "index": i})
            if parent and all(parent[k] in anchors for k in ("np", "npe")):
                if not anchors[parent["np"]]["start"] <= start < end <= anchors[parent["npe"]]["end"]:
                    issues.append({"check": "outside_parent", "index": i})
            if start < previous.get(pid, -1):
                issues.append({"check": "overlapping_siblings", "index": i})
            previous[pid] = end
        stack.append(row)
    return {"nodes": len(rows), "issues": issues, "checks": ["Уникальные ID", "Уровни и ID родителей",
        "Существование np/npe", "Конец после начала", "Вложенность диапазонов", "Отсутствие пересечений соседей"]}, parents


def build():
    protected = {str(p): sha(p) for p in INPUTS.rglob("*") if p.is_file()}
    documents = []
    for key, spec in CASES.items():
        path, manifest, raw, asset, html = source_input(INPUTS, key)
        bundle = manifest["structure_bundle"]
        rows = json.loads(raw[bundle["structure_sha256"]])["data"]
        anchors = Anchors(html).ids
        audit, parents = formal_checks(rows, anchors)
        assert not audit["issues"], (key, audit["issues"])
        by_id = {r["id"]: (i, r) for i, r in enumerate(rows)}
        index, focus = by_id[spec["target"]]
        ancestor_ids, pid = [], parents[focus["id"]]
        while pid:
            ancestor_ids.insert(0, pid)
            pid = parents[pid]
        visible = [by_id[pid] for pid in ancestor_ids]
        for i in range(index, min(len(rows), index + 6)):
            if i > index and rows[i]["lvl"] < focus["lvl"]:
                break
            visible.append((i, rows[i]))
        # For the quoted-article example, the next source article makes the
        # actual end of article 43 visible without adding unrelated descendants.
        if key == "building-safety":
            visible = [*[(by_id[pid]) for pid in ancestor_ids], (index, focus), (index + 1, rows[index + 1])]
        soup = BeautifulSoup(html, "html.parser")
        ps = soup.find_all("p")
        positions = {p.get("id"): n for n, p in enumerate(ps) if p.get("id")}
        start = positions[focus["np"]]
        if key in {"civil-procedure", "disability"}:
            start = positions[by_id[parents[focus["id"]]][1]["np"]]
        excerpt = []
        for n in range(start, len(ps)):
            p = ps[n]
            if not p.get_text(strip=True):
                continue
            excerpt.append({"paragraph": n + 1, "id": p.get("id"), "html": markup(p),
                            "heading": bool(set(p.get("class", [])) & {"H", "T"}),
                            "focus": p.get("id") in {"p380", "p370"} if key == "building-safety" else p.get("id") == focus["np"],
                            "boundary": key == "building-safety" and p.get("id") == "p371"})
            if len(excerpt) >= (5 if key == "building-safety" else 6):
                break
        result = json.loads((VALIDATION / key / "result.json").read_bytes())
        ast, evidence = [], []
        if key == "building-safety":
            tree = json.loads(Path(result["draft"]).read_bytes())["content"]["trees"][0]
            outer = next(n for n in tree["nodes"] if n.get("source_id") == focus["id"])
            for n in tree["nodes"]:
                if n["address"] == outer["address"] or (n["address"].startswith(outer["address"] + "/")
                        and (n.get("block_id") is None or n.get("block_id") in {517, 519})):
                    ast.append({k: n.get(k) for k in ("address", "parent_address", "kind", "caption", "text", "block_id", "source_id")})
            assert {e["block_id"] for e in result["checks"]["errors"]} == {517, 519}
            assert not result["basic"]["errors"] and result["basic"]["audit"]["critical_count"] == 0
            evidence = result["checks"]["errors"]
        else:
            evidence = result.get("error", {})
        documents.append({**spec, "key": key, "audit": audit, "excerpt": excerpt, "focus": focus,
            "json_rows": [{"pointer": f"/data/{i}", "row": row, "parent": parents[row["id"]]} for i, row in visible],
            "ast": ast, "error": evidence, "result": result["status"],
            "technical": bool(result.get("repeat_identical") and not result["basic"]["errors"]),
            "source_url": asset["source_url"], "source_sha256": asset["sha256"],
            "structure_sha256": bundle["structure_sha256"], "input": str(path.relative_to(PROJECT)),
            "types": dict(Counter(r["unit"] for r in rows))})
    assert sum(d["audit"]["nodes"] for d in documents) == 6514
    assert Counter(d["kind"] for d in documents) == {"adapter": 3, "reader": 1, "pass": 2}
    assert {str(p): sha(p) for p in INPUTS.rglob("*") if p.is_file()} == protected
    data = {"documents": documents, "protected_files_unchanged": len(protected),
            "schema_version": "official-json-visual-review/1", "source_snapshot": "2026-10-16",
            "limits": "Formal source-tree checks only; displayed failures are first recorded blockers, not full legal verification."}
    template = Path(__file__).with_name("official_json_visual_review.template.html").read_text(encoding="utf-8")
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    page = template.replace("__EVIDENCE__", payload)
    assert page.count('id="evidence"') == 1 and "__EVIDENCE__" not in page
    OUT.mkdir(exist_ok=True)
    (OUT / "index.html").write_text(page, encoding="utf-8", newline="\n")
    receipt = {"schema_version": data["schema_version"], "html_sha256": hashlib.sha256(page.encode()).hexdigest(),
        "generator_sha256": sha(__file__), "template_sha256": sha(Path(__file__).with_name("official_json_visual_review.template.html")),
        "documents": [{"key": d["key"], "audit": d["audit"], "source_sha256": d["source_sha256"],
                       "structure_sha256": d["structure_sha256"]} for d in documents],
        "protected_files_unchanged": len(protected), "production_changed": False, "frozen_decisions_changed": False}
    (OUT / "checks.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(OUT / "index.html"))
    print("6 documents; 6514 source units; 0 formal issues;", len(protected), "input files unchanged")


if __name__ == "__main__":
    build()
