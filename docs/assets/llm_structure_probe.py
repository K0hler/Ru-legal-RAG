"""M1-04A experiment: an LLM labels the owner of every OCR region (stage 3 only).

Input is the retained text-extraction/1; the model sees a compact skeleton
(id, OCR category, position, head/tail of text) in windows with carried context
and must return strict JSON. Source text, tokens and locators are never sent
back or rewritten: the model only returns labels keyed by region id.

Every request/response is stored; an existing response is replayed instead of
calling the API again. Requests run one at a time with a minimum interval and
back off on 429/5xx. The API key is read from a local config file at run time
and is never written to outputs or logs.
"""

from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import re
import sys
import time
import urllib.error
import urllib.request
from collections import defaultdict
from pathlib import Path

VERSION = "llm-structure-probe/4"
OWNER = re.compile(r"^(A|S\d*)(/[^/\s]+)*$")

SYSTEM = (
    "Ты размечаешь структуру российских нормативных правовых актов. На вход подаётся "
    "последовательность областей страниц, полученных OCR из скана официального документа. "
    "Для каждой области определи владельца — структурную единицу документа, которой "
    "принадлежит её текст. Отвечай только JSON по заданной схеме."
)

RULES = """Формат строки области: `id | категория OCR | положение | текст`. Длинный текст сокращён: «начало … конец». Категория OCR и положение могут быть ошибочными, опирайся на смысл.

Как записывать владельца — путь от корня через «/»:
1. `A` — сам акт: шапка, наименование, преамбула, его собственные пункты (`A/1`, `A/4/4.1`), подписи, отметки о регистрации.
2. Документ, утверждённый актом (правила, положение, санитарные правила, форма договора и т. п., обычно с подписью «УТВЕРЖДЕН(Ы/А/О) …»), — `S`; второй утверждённый документ — `S2`, третий — `S3`. Подпись об утверждении и наименование такого документа принадлежат ему самому (`S`).
3. Приложение — `<родитель>/AN<номер>`, без номера — `<родитель>/AN`. Родитель определяется по подписи приложения: «к постановлению/приказу» — `A`; к утверждённому документу (правилам, договору и т. п.) — этот документ. Подпись и наименование приложения принадлежат приложению.
4. Внутри документа — номера структурных единиц так, как они напечатаны, без точек и скобок: раздел или глава `II` (римские цифры латиницей), пункт `3` или `3.1`, подпункт `а` или `1` (для «1)»). Путь полный: раздел → пункт → подпункт, например `S/II/3/а`.
5. Пункт с составным номером (`3.1.2`) вложен в пункт с номером-префиксом (`3.1`), если такой пункт есть; иначе — в раздел. Пункт `4.1` вложен в пункт `4`, если пункт `4` есть.
6. Нумерация пунктов бывает сквозной через разделы: пункт 289, идущий после заголовка раздела XIII, — это `…/XIII/289`.
7. Заголовок раздела принадлежит разделу (`S/II`).
8. Абзацы без номера, элементы списка с тире, таблицы, подписи к таблицам и продолжения текста принадлежат той единице, внутри которой стоят (обычно последней открытой пункт или подпункт).
9. Сноска (текст, начинающийся с надстрочной цифры) принадлежит единице, в тексте которой стоит такой же знак сноски.
10. Текст в кавычках «…» в изменяющем акте (новая редакция, дополнение) принадлежит единице изменяющего акта, которая его вводит; номера внутри цитаты в путь не включаются.
11. Колонтитулы, номера страниц, повторяющиеся служебные пометки — `owner: null`.
12. `continues_previous: true`, если текст области продолжает предложение или абзац предыдущей содержательной области (оборван переходом страницы или колонки); иначе `false`.
Не исправляй текст. Верни метку для каждой области текущего окна ровно один раз, id копируй точно."""

SCHEMA = {
    "type": "object",
    "properties": {"labels": {"type": "array", "items": {
        "type": "object",
        "properties": {"id": {"type": "string"},
                       "owner": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                       "continues_previous": {"type": "boolean"}},
        "required": ["id", "owner", "continues_previous"], "additionalProperties": False}}},
    "required": ["labels"], "additionalProperties": False,
}


def view(text: str) -> str:
    lines = [re.sub(r"^\s*#{1,6}\s+", "", line) for line in text.splitlines()]
    return re.sub(r"\s+", " ", " ".join(lines)).strip()


def skeleton(extraction: dict, max_page: int | None = None) -> list[dict]:
    raw = defaultdict(str)
    for block in extraction["blocks"]:
        raw[block["source_region_id"]] += block["original_text"]
    rows = []
    for page in extraction["pages"]:
        if max_page and page["page"] > max_page:
            break
        width = page["image_size"][0]
        for index, region in enumerate(page["regions"]):
            text = raw.get(region["region_id"], "")
            if region["category"] == "Table":
                text = "[ТАБЛИЦА] " + re.sub(r"<[^>]+>", " ", text)
            text = view(text)
            if not text:
                continue
            x0, _, x1, _ = region["bbox"]
            centre = (x0 + x1) / 2 / width
            pos = "справа" if x0 / width > 0.5 else "по центру" if abs(centre - 0.5) < 0.08 and (x1 - x0) / width < 0.7 else "слева"
            shown = text if len(text) <= 150 else text[:110] + " … " + text[-35:]
            rows.append({"id": f"{page['page']}.{index}", "page": page["page"], "category": region["category"],
                         "pos": pos, "text": shown})
    return rows


def render(rows: list[dict]) -> str:
    out, page = [], None
    for r in rows:
        if r["page"] != page:
            page = r["page"]
            out.append(f"--- страница {page} ---")
        out.append(f"{r['id']} | {r['category']} | {r['pos']} | {r['text']}")
    return "\n".join(out)


class Client:
    def __init__(self, config_path: str, min_interval: float):
        with open(config_path, encoding="utf-8") as handle:
            cfg = json.load(handle)
        self.base = cfg["openai_base_url"].rstrip("/")
        self._key = cfg["openai_api_key"]
        self.min_interval = min_interval
        self.last = 0.0

    def chat(self, body: dict, log: list) -> dict:
        delays = [20, 45, 90, 180]
        for attempt in range(len(delays) + 1):
            wait = self.min_interval - (time.time() - self.last)
            if wait > 0:
                time.sleep(wait)
            self.last = time.time()
            started = time.time()
            req = urllib.request.Request(self.base + "/chat/completions", data=json.dumps(body).encode(),
                                         headers={"Authorization": f"Bearer {self._key}",
                                                  "Content-Type": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=900) as response:
                    payload = read_stream(response) if body.get("stream") else json.loads(response.read().decode())
                log.append({"attempt": attempt, "status": 200, "seconds": round(time.time() - started, 1)})
                return payload
            except urllib.error.HTTPError as exc:
                detail = exc.read().decode(errors="replace")[:300]
                log.append({"attempt": attempt, "status": exc.code, "detail": detail,
                            "seconds": round(time.time() - started, 1)})
                if exc.code not in (408, 409, 429, 500, 502, 503, 504) or attempt == len(delays):
                    raise
                retry_after = exc.headers.get("Retry-After")
                time.sleep(max(delays[attempt], float(retry_after) if retry_after and retry_after.isdigit() else 0))
            except (urllib.error.URLError, TimeoutError, http.client.HTTPException, ConnectionError, OSError) as exc:
                log.append({"attempt": attempt, "status": "network", "detail": repr(exc)[:200]})
                if attempt == len(delays):
                    raise
                time.sleep(delays[attempt])
        raise RuntimeError("unreachable")


def read_stream(response) -> dict:
    """Assemble an OpenAI-compatible SSE stream; keeps long reasoning requests alive."""
    content, reasoning, usage, finish = [], 0, None, None
    for raw in response:
        line = raw.decode("utf-8", errors="replace").strip()
        if not line.startswith("data:"):
            continue
        data = line[5:].strip()
        if data == "[DONE]":
            break
        chunk = json.loads(data)
        if chunk.get("usage"):
            usage = chunk["usage"]
        for choice in chunk.get("choices") or []:
            delta = choice.get("delta") or {}
            if delta.get("content"):
                content.append(delta["content"])
            if delta.get("reasoning_content") or delta.get("reasoning"):
                reasoning += 1
            if choice.get("finish_reason"):
                finish = choice["finish_reason"]
    return {"choices": [{"message": {"content": "".join(content)}, "finish_reason": finish}],
            "usage": usage or {}, "stream_reasoning_chunks": reasoning}


REASONING_OVERRIDE: str | None = None


def model_params(model: str) -> dict:
    params = {"temperature": 0, "max_tokens": 24000}
    if model.startswith("qwen3.8"):
        params["reasoning_effort"] = "medium"
    if REASONING_OVERRIDE:
        params["reasoning_effort"] = REASONING_OVERRIDE
    return params


def validate(labels, ids):
    problems = []
    got = [x.get("id") for x in labels]
    missing = [i for i in ids if i not in got]
    extra = [i for i in got if i not in ids]
    dup = sorted({i for i in got if got.count(i) > 1})
    bad = [x["id"] for x in labels if x.get("owner") is not None and not OWNER.match(x["owner"])]
    if missing:
        problems.append({"missing": missing})
    if extra:
        problems.append({"extra": extra})
    if dup:
        problems.append({"duplicate": dup})
    if bad:
        problems.append({"bad_owner_syntax": bad})
    return problems


def run_document(client, model, name, rows, out_dir: Path, window: int, context_size: int, ledger, budget, prices):
    doc_dir = out_dir / model / name
    doc_dir.mkdir(parents=True, exist_ok=True)
    labels: dict[str, dict] = {}
    ordered = []
    for start in range(0, len(rows), window):
        chunk = rows[start:start + window]
        index = start // window
        path = doc_dir / f"w{index:02d}.json"
        ids = [r["id"] for r in chunk]
        context_rows = rows[max(0, start - context_size):start]
        context = "\n".join(f"{r['id']} | владелец: {labels.get(r['id'], {}).get('owner')} | {r['text'][:80]}"
                            for r in context_rows)
        scopes = sorted({str(v.get("owner")).split("/")[0] for v in labels.values() if v.get("owner")})
        user = (RULES + "\n\n"
                + (f"Уже размечено ранее (контекст, повторно не размечать):\n{context}\n"
                   f"Открытые до этого момента документы: {', '.join(scopes) or 'нет'}\n\n" if context_rows else "")
                + f"Текущее окно ({len(chunk)} областей) — размечай их:\n{render(chunk)}")
        messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]
        body = {"model": model, "messages": messages, **model_params(model),
                "response_format": {"type": "json_schema",
                                    "json_schema": {"name": "region_owners", "strict": True, "schema": SCHEMA}}}
        # transport options (streaming) do not change what is asked, so they stay out of the hash
        request_hash = hashlib.sha256(json.dumps(body, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
        body = {**body, "stream": True, "stream_options": {"include_usage": True}}
        record = None
        if path.exists():
            with open(path, encoding="utf-8") as handle:
                record = json.load(handle)
            if record.get("request_sha256") != request_hash:
                raise SystemExit(f"{path}: saved request differs from the current one; use a new output dir")
            print(f"  replay {name} w{index:02d}", flush=True)
        else:
            if ledger.get("max_calls") is not None and ledger.get("session_calls", 0) >= ledger["max_calls"]:
                raise SystemExit(f"max calls per run reached; stopping before {name} w{index:02d}")
            if ledger["rub"] >= budget:
                raise SystemExit(f"budget {budget} RUB reached ({ledger['rub']:.2f}); stopping before {name} w{index:02d}")
            log: list = []
            started = time.time()
            payload = client.chat(body, log)
            usage = payload.get("usage") or {}
            price = prices.get(model, {})
            rub = (usage.get("prompt_tokens", 0) * (price.get("in_rub_1m") or 0)
                   + usage.get("completion_tokens", 0) * (price.get("out_rub_1m") or 0)) / 1e6
            content = payload["choices"][0]["message"].get("content") or ""
            try:
                parsed = json.loads(content)["labels"]
                parse_error = None
            except (json.JSONDecodeError, KeyError, TypeError) as exc:
                parsed, parse_error = [], repr(exc)[:200]
            record = {"version": VERSION, "model": model, "document": name, "window": index,
                      "request_sha256": request_hash, "request": body, "attempts": log,
                      "seconds": round(time.time() - started, 1), "usage": usage, "rub_estimate": round(rub, 4),
                      "finish_reason": payload["choices"][0].get("finish_reason"),
                      "content": content, "parse_error": parse_error,
                      "problems": validate(parsed, ids) if not parse_error else [{"parse_error": parse_error}],
                      "labels": parsed}
            with open(path, "x", encoding="utf-8") as handle:
                json.dump(record, handle, ensure_ascii=False, indent=1)
            ledger["rub"] += rub
            ledger["calls"] += 1
            ledger["session_calls"] = ledger.get("session_calls", 0) + 1
            print(f"  {name} w{index:02d}: {record['seconds']}s tokens {usage.get('prompt_tokens')}/"
                  f"{usage.get('completion_tokens')} ~{rub:.2f} RUB problems={len(record['problems'])} "
                  f"total ~{ledger['rub']:.2f} RUB", flush=True)
        for item in record["labels"]:
            if item.get("id") in ids and item["id"] not in labels:
                labels[item["id"]] = item
        ordered.extend(ids)
    owners = {i: labels.get(i, {}).get("owner") for i in ordered}
    continuation = {i: bool(labels.get(i, {}).get("continues_previous")) for i in ordered}
    unlabeled = [i for i in ordered if i not in labels]
    summary = {"owners": owners, "continuation": continuation, "unlabeled": unlabeled}
    with open(doc_dir / "owners.json", "w", encoding="utf-8") as handle:
        json.dump(summary, handle, ensure_ascii=False, indent=1)
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--config", required=True, help="local JSON with openai_base_url/openai_api_key")
    parser.add_argument("--model", action="append", required=True)
    parser.add_argument("--doc", action="append", required=True, help="name=extraction.json[:max_page]")
    parser.add_argument("--out", required=True)
    parser.add_argument("--window", type=int, default=100)
    parser.add_argument("--context", type=int, default=15)
    parser.add_argument("--min-interval", type=float, default=6.0)
    parser.add_argument("--budget-rub", type=float, default=300.0)
    parser.add_argument("--prices", required=True, help="saved wallet-prices JSON")
    parser.add_argument("--max-calls", type=int, help="stop after this many new API calls (resume later)")
    parser.add_argument("--reasoning-effort", help="override reasoning_effort, e.g. none for a local model")
    args = parser.parse_args(argv)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    with open(args.prices, encoding="utf-8") as handle:
        price_rows = json.load(handle)
    rows = (price_rows.get("prices") or price_rows.get("data") or price_rows) if isinstance(price_rows, dict) else price_rows
    prices = {r.get("model") or r.get("id"): r for r in rows} if isinstance(rows, list) else rows
    ledger_path = out / "ledger.json"
    ledger = {"rub": 0.0, "calls": 0}
    if ledger_path.exists():
        with open(ledger_path, encoding="utf-8") as handle:
            ledger = json.load(handle)
    global REASONING_OVERRIDE
    REASONING_OVERRIDE = args.reasoning_effort
    ledger["max_calls"], ledger["session_calls"] = args.max_calls, 0
    client = Client(args.config, args.min_interval)
    try:
        for model in args.model:
            for spec in args.doc:
                name, rest = spec.split("=", 1)
                path, _, max_page = rest.partition(":")
                with open(path, encoding="utf-8") as handle:
                    extraction = json.load(handle)
                rows_ = skeleton(extraction, int(max_page) if max_page else None)
                print(f"{model} {name}: {len(rows_)} regions", flush=True)
                run_document(client, model, name, rows_, out, args.window, args.context, ledger, args.budget_rub, prices)
    finally:
        ledger.pop("max_calls", None)
        ledger.pop("session_calls", None)
        with open(ledger_path, "w", encoding="utf-8") as handle:
            json.dump(ledger, handle, indent=1)
        print(f"ledger: {ledger['calls']} calls, ~{ledger['rub']:.2f} RUB", flush=True)


if __name__ == "__main__":
    sys.exit(main())
