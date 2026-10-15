"""Verify retained experiment evidence and make a self-contained Russian viewer."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
ROOT = PROJECT / "data/m1/experiments/official-structure-20261015-v1"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_once(path, payload):
    if path.exists():
        assert path.read_bytes() == payload, f"immutable result conflict: {path}"
    else:
        path.write_bytes(payload)


def verify(attempt):
    summary = json.loads((attempt / "results.json").read_bytes())
    preflight = json.loads((ROOT / "preflight.json").read_bytes())
    assert summary["scope_sha256"] == sha(ROOT / "preflight.json")
    assert summary["adapter_sha256"] == sha(attempt / "adapter.py")
    assert summary["adapter_sha256"] == sha(PROJECT / "docs/assets/experiment_official_structure.py")
    trees = {}
    for result in summary["documents"]:
        key = result["document"]
        path = attempt / key
        assert sha(path / "run-a/tree.json") == sha(path / "run-b/tree.json") == result["tree_sha256"]
        assert sha(path / "run-a/controls.json") == sha(path / "run-b/controls.json") == result["controls_sha256"]
        t = json.loads((path / "run-a/tree.json").read_bytes())
        assert t["summary"]["technical_accounting_pass"] and not t["summary"]["number_mismatches"]
        assert t["summary"]["whole_body_text_matches_dom"]
        assert len(t["text_nodes"]) == sum(len(b["text_node_ids"]) for b in t["blocks"])
        record = next(r for r in preflight["records"] if r["document"] == key)
        assert sha(PROJECT / record["source_file"]) == t["source_asset_sha256"]
        assert sha(PROJECT / record["response_file"]) == t["structure_asset_sha256"]
        by_id = {n["source_id"]: n for n in t["nodes"]}
        all_owned = []
        for n in t["nodes"]:
            all_owned.extend(n["own_block_ids"])
            parent = by_id.get(n["parent_source_id"])
            if parent:
                assert parent["html_start"] <= n["html_start"] < n["html_end"] <= parent["html_end"]
        expected = [b["block_id"] for b in t["blocks"] if b["owner_source_id"]]
        assert sorted(all_owned) == sorted(expected) and len(all_owned) == len(set(all_owned))
        trees[key] = t
    assert len(trees) == 7 and sum(len(t["nodes"]) for t in trees.values()) == 3906
    for p, expected in preflight["protected_files_sha256"].items():
        assert sha(PROJECT / p) == expected, p
    checks = []

    def check(name, condition, detail):
        assert condition, name
        checks.append({"name": name, "verified": True, "detail": detail})

    housing = trees["housing-code"]
    children = [n for n in housing["nodes"] if n["parent_source_id"] == "si_h1_a12_j2:1~"]
    check("ЖК РФ: семь буквенных подпунктов пункта 2¹ статьи 12",
          [n["number_canonical"] for n in children] == list("абвгдеж"),
          [{"id": n["source_id"], "number": n["number_canonical"], "np": n["np"]} for n in children])
    check("ЖК РФ: сложный индекс 1.1-1 сохранён",
          any(n["number_canonical"] == "1.1-1" for n in housing["nodes"]),
          "Индекс остаётся строкой; надстрочная часть не склеена с основным номером.")
    r354 = trees["government-decree-354"]
    kinds = Counter(n["kind"] for n in r354["nodes"] if n["source_unit"] == "вложение")
    check("№354: вложения разделены на утверждённые тексты и примечания",
          kinds == Counter(approved_text=2, notes_section=1, normative_note=2), dict(kinds))
    for name, count in [("government-decree-354", 93), ("government-decree-491", 6)]:
        check(name + ": изображения сохранены", sum(r["tag"] == "img" for r in trees[name]["regions"]) == count,
              "Сохранены оригинальная разметка и координаты; формулы на изображениях не распознаны.")
    gas = trees["gas"]
    annex = next(n for n in gas["nodes"] if n["source_id"] == "zf1_uf2")
    check("№410: приложение принадлежит утверждённым Правилам",
          annex["kind"] == "annex" and annex["parent_source_id"] == "zf1" and
          next(n for n in gas["nodes"] if n["source_id"] == "zf1")["kind"] == "approved_text",
          {"np": annex["np"], "npe": annex["npe"], "number": annex["number_canonical"],
           "note": "Ненумерованному приложению не придуман номер; заголовок и оговорки сохраняются в исходном HTML."})
    forms = trees["housing-status"]
    check("№47: три приложения и шесть таблиц сохранены",
          sum(n["kind"] == "annex" for n in forms["nodes"]) == 3 and
          forms["summary"]["regions"]["table"] == 6 and forms["summary"]["table_cells"] == 42,
          {"table_rows": forms["summary"]["table_rows"], "table_cells": forms["summary"]["table_cells"]})
    start_ids = {n["np"] for n in forms["nodes"]}
    form_list = [b for b in forms["blocks"] if b["html_id"] in ["p350", "p351", "p352", "p353", "p354"]]
    check("Подтверждённый пробел №47: список а–д внутри формы без отдельных узлов",
          len(form_list) == 5 and all(b["html_id"] not in start_ids and b["owner_source_id"] == "zf1_u2" for b in form_list),
          [{"html_id": b["html_id"], "text": b["text"], "owner": b["owner_source_id"]} for b in form_list])
    law = trees["energy-saving"]
    start_ids = {n["np"] for n in law["nodes"]}
    quote_heads = [b for b in law["blocks"] if b["html_id"] in ["p408", "p759"]]
    check("Подтверждённый пробел №261-ФЗ: две цитируемые статьи без собственного поддерева",
          len(quote_heads) == 2 and all(b["html_id"] not in start_ids and b["owner_source_id"].startswith("h10_a37_") for b in quote_heads),
          [{"html_id": b["html_id"], "text": b["text"], "owner": b["owner_source_id"]} for b in quote_heads])
    check("Редакционные примечания не потеряны",
          sum(t["summary"]["block_roles"].get("editorial_note", 0) for t in trees.values()) == 2122,
          "2 122 блока. Их юридическая область действия отдельно не квалифицирована; у 17 нет владельца по диапазонам JSON.")
    return {"source_run_recorded_at": summary["recorded_at"], "documents": 7, "source_nodes": 3906,
            "protected_files_unchanged": len(preflight["protected_files_sha256"]), "checks": checks,
            "checker_sha256": sha(Path(__file__)), "full_legal_ast_qualified": False}, summary


def viewer(data):
    template = r'''<!doctype html><html lang="ru"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>М1-03А · официальная разметка</title>
<style>body{margin:0;font:15px system-ui;color:#25314a;background:#f7f8fc}header{padding:20px 28px;background:white;border-bottom:1px solid #dce2ee}h1{font-size:23px;margin:0 0 8px}p{margin:8px 0;line-height:1.5}select,input,button{font:inherit;padding:8px;border:1px solid #d7deeb;border-radius:6px;background:white}select{max-width:100%}#stats{padding:14px 28px;color:#514320;background:#fff5dc}main{display:grid;grid-template-columns:350px 1fr;height:76vh}aside{padding:16px;overflow:auto;border-right:1px solid #dce2ee}#search{width:92%;margin:0 0 12px}#nodes button{display:block;width:100%;text-align:left;margin:3px 0;white-space:normal;font-size:13px}section{padding:16px;overflow:auto}iframe{width:100%;height:53vh;border:1px solid #dce2ee;background:white}#issues{margin-top:12px}#issues button{display:block;margin:4px 0;text-align:left;font-size:13px}pre{white-space:pre-wrap;overflow-wrap:anywhere}small{color:#5d6980}.selected{outline:2px solid #df830c}@media(max-width:800px){main{grid-template-columns:1fr;height:auto}aside{max-height:35vh}iframe{height:60vh}}</style>
<header><h1>М1-03А: эксперимент с официальной структурой</h1><p>Исходные узлы и текст сохранены. Цитаты, внутренние списки и область действия примечаний требуют дополнительной обработки. Юридического допуска нет.</p><label>Документ <select id="document"></select></label></header>
<div id="stats"></div><main><aside><input id="search" placeholder="Найти статью, пункт или идентификатор" aria-label="Поиск узла"><div id="nodes"></div></aside><section><h2 id="caption">Выберите узел</h2><p id="path"></p><small id="evidence"></small><iframe id="source" sandbox="" title="Фрагмент исходного документа"></iframe><div id="issues"></div></section></main>
<script id="data" type="application/json">__DATA__</script><script>
const dataset=JSON.parse(document.getElementById('data').textContent);
const names={'federal-law-59':'Федеральный закон №59-ФЗ','housing-code':'Жилищный кодекс РФ','government-decree-354':'Постановление №354','government-decree-491':'Постановление №491','energy-saving':'Федеральный закон №261-ФЗ','gas':'Постановление №410','housing-status':'Постановление №47'};
const select=document.getElementById('document'), list=document.getElementById('nodes'), query=document.getElementById('search');
let doc,characters,styles;
dataset.forEach((d,i)=>{const o=document.createElement('option');o.value=i;o.textContent=names[d.document]||d.document;select.append(o)});
function plain(s){const t=new DOMParser().parseFromString(s,'text/html');const digits={'0':'⁰','1':'¹','2':'²','3':'³','4':'⁴','5':'⁵','6':'⁶','7':'⁷','8':'⁸','9':'⁹','-':'⁻'};t.querySelectorAll('sup').forEach(e=>{e.textContent=Array.from(e.textContent).map(c=>digits[c]||c).join('')});return t.body.textContent.replace(/^\$/,'')}
function show(node,target){const kinds={section:'раздел',chapter:'глава',article:'статья',part:'часть',point:'пункт',item:'пункт',subitem:'подпункт',annex:'приложение',approved_text:'утверждённый текст',notes_section:'примечания',normative_note:'примечание'};document.getElementById('caption').textContent=plain(node.caption);document.getElementById('path').textContent=node.provision_path.map(n=>(kinds[n.kind]||n.kind)+(n.number?' '+n.number:'')).join(' → ');document.getElementById('evidence').textContent=node.source_id+' · '+node.np+' — '+node.npe+' · '+node.html_start+' — '+node.html_end;const text=characters.slice(node.html_start,node.html_end).join('');const highlight=target?'[id="'+target.replaceAll('"','')+'"]{background:#ffe3a2!important}':'';document.getElementById('source').srcdoc='<meta charset="utf-8"><meta http-equiv="Content-Security-Policy" content="default-src \'none\'; img-src data:; style-src \'unsafe-inline\'">'+styles+'<style>body{padding:16px;font:16px Georgia;line-height:1.55}'+highlight+'</style>'+text;window.lastSelectedSourceId=node.source_id}
function showIssue(id,owner){const node=doc.nodes.find(n=>n.source_id===owner)||doc.nodes.find(n=>n.np===id);if(node)show(node,id)}
function render(){list.replaceChildren();const s=query.value.toLocaleLowerCase('ru');doc.nodes.filter(n=>(plain(n.caption)+' '+n.source_id).toLocaleLowerCase('ru').includes(s)).forEach(n=>{const b=document.createElement('button');b.textContent=plain(n.caption);b.style.paddingLeft=(8+n.level*9)+'px';b.onclick=()=>show(n);list.append(b)})}
function change(){doc=dataset[Number(select.value)];characters=Array.from(doc.html);const parsed=new DOMParser().parseFromString(doc.html,'text/html');styles=Array.from(parsed.querySelectorAll('head style')).map(s=>s.outerHTML).join('');query.value='';render();const s=doc.summary;document.getElementById('stats').textContent=s.source_nodes+' узлов · '+s.number_mismatches+' расхождений номеров · '+s.marker_gap_candidates+' кандидатов на пропущенную структуру · '+s.quote_candidates+' кандидатов на цитаты. Полный учёт текста: '+(s.technical_accounting_pass?'подтверждён':'ошибка')+'.';const issues=document.getElementById('issues');issues.replaceChildren();const h=document.createElement('h3');h.textContent='Места для дополнительного разбора';issues.append(h);doc.controls.unrepresented_marker_candidates.forEach(c=>{const b=document.createElement('button');b.textContent=c.html_id+' · '+c.prefix.slice(0,150);b.onclick=()=>showIssue(c.html_id,c.owner_source_id);issues.append(b)});doc.controls.amendment_quote_candidates.forEach(c=>{const b=document.createElement('button');b.textContent='Цитата · '+c.start_html_id+' · '+c.prefix.slice(0,130);b.onclick=()=>showIssue(c.start_html_id,c.owner_source_id);issues.append(b)});show(doc.nodes[0])}
select.onchange=change;query.oninput=render;change();window.reviewStats={documents:dataset.length,nodes:dataset.reduce((s,d)=>s+d.nodes.length,0)};
</script></html>'''
    return template.replace("__DATA__", json.dumps(data, ensure_ascii=False).replace("<", "\\u003c")).encode()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--attempt", type=Path, default=ROOT / "attempt-05")
    args = parser.parse_args()
    result, summary = verify(args.attempt)
    data = json.loads((args.attempt / "viewer-data.json").read_bytes())
    write_once(args.attempt / "index-v2.html", viewer(data))
    write_once(args.attempt / f"witness-checks-{result['checker_sha256'][:12]}.json",
               (json.dumps(result, ensure_ascii=False, indent=2) + "\n").encode())
    print(json.dumps({"documents": result["documents"], "source_nodes": result["source_nodes"],
                      "witness_checks": len(result["checks"]), "protected_files": result["protected_files_unchanged"],
                      "viewer": str(args.attempt / "index-v2.html"),
                      "technical_pass": summary["technical_pass_count"],
                      "full_legal_ast_qualified": False}, ensure_ascii=False))


if __name__ == "__main__":
    main()
