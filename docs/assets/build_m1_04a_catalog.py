"""Build the M1-04A working tree: hash-verified copies of original documents.

Originals stay in their content-addressed `sources` archives; this script only
copies `raw/<sha256>` bytes into a readable per-document layout and never
rewrites an existing file with different bytes. Earlier experiment outputs are
not moved: their paths are pinned by reports and freeze hashes.
"""

import argparse
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[2]
M1 = ROOT / "data" / "m1"
TWO_PDF = M1 / "experiments" / "m1-04a-20261017-two-pdf-v1" / "inputs"
M1_04A = M1 / "inputs" / "m1-04a"

# (group, manifest, slug-for-single-asset). Groups follow the evaluation
# protocol: development may be inspected, reserved stays closed until Task 3.
SINGLE = [
    ("development", TWO_PDF / "resolution-416" / "input.json", "resolution-416"),
    ("development", TWO_PDF / "sp-3.1.3597-20" / "input.json", "sp-3.1.3597-20"),
    ("development", M1_04A / "resolution-1156" / "input.json", "resolution-1156"),
    ("development", M1_04A / "sp-2.1.3678-20" / "input.json", "sp-2.1.3678-20"),
    ("reserved", M1_04A / "sanpin-2.3-2.4.3590-20" / "input.json", "sanpin-2.3-2.4.3590-20"),
    ("reserved", M1_04A / "sp-2.4.3648-20" / "input.json", "sp-2.4.3648-20"),
    ("reserved", M1_04A / "resolution-2314" / "input.json", "resolution-2314"),
    ("reserved", M1_04A / "resolution-564" / "input.json", "resolution-564"),
]
SANPIN = M1 / "inputs" / "m1-04" / "sanpin-original-amendments.json"
# Check-pool batches: `<batch>/<slug>/input.json` written by acquire_m1_04a_pool.py. Their
# rows go to the batch's own index so the frozen `documents/index.json` stays unchanged.
POOL_BATCHES = ("batch-01", "batch-02", "batch-03", "batch-04", "batch-05", "batch-06", "batch-07")
# Protocol life cycle of a pool batch: measured once on frozen code, then it joins
# development. Recorded in `<batch>/status.json` (write-once) because the indexes are frozen.
POOL_STATUS = {
    "batch-01": [
        {"status": "measured", "date": "2026-10-21", "evidence": "experiments/20261021-batch-01-first-pass"},
        {"status": "development", "date": "2026-10-21",
         "report": "docs/milestones/m1/04a/M1_04A_POOL_BATCH_1_2026-10-21.md"},
    ],
    "batch-02": [
        {"status": "measured", "date": "2026-10-22", "evidence": "experiments/20261022-batch-02-first-pass"},
        {"status": "development", "date": "2026-10-22",
         "report": "docs/milestones/m1/04a/M1_04A_POOL_BATCH_2_2026-10-22.md"},
    ],
    "batch-03": [
        {"status": "measured", "date": "2026-10-22", "evidence": "experiments/20261022-batch-03-first-pass"},
        {"status": "development", "date": "2026-10-22",
         "report": "docs/milestones/m1/04a/M1_04A_POOL_BATCH_3_2026-10-22.md"},
    ],
    "batch-04": [
        {"status": "measured", "date": "2026-10-23", "evidence": "experiments/20261023-batch-04-first-pass"},
        {"status": "development", "date": "2026-10-23",
         "report": "docs/milestones/m1/04a/M1_04A_POOL_BATCH_4_2026-10-23.md"},
    ],
    "batch-05": [
        {"status": "measured", "date": "2026-10-23", "evidence": "experiments/20261023-batch-05-first-pass"},
        {"status": "development", "date": "2026-10-23",
         "report": "docs/milestones/m1/04a/M1_04A_POOL_BATCH_5_2026-10-23.md"},
    ],
    "batch-06": [
        {"status": "measured", "date": "2026-10-24", "evidence": "experiments/20261024-batch-06-first-pass"},
        {"status": "development", "date": "2026-10-24",
         "report": "docs/milestones/m1/04a/M1_04A_POOL_BATCH_6_2026-10-24.md"},
    ],
}
# SanPiN 2.1.3684-21 bundle: original resolution No. 3 plus nine amending resolutions.
SANPIN_SLUGS = {
    "66210869f6617b4eb5b38b27fe76fceab46f845fd14c6ecfebe9ae67c8f01a12": "sanpin-2.1.3684-21",
    "5a6c0fc08092e297115815ed14db87cf38edc8f7f97a91a77bfb416f4395ff39": "sanpin-2.1.3684-21_amend-2021-06-26-no16",
    "09d1df316132aef8dfc1710066d95f300cc4a62ab4086058cd8eba99990148f8": "sanpin-2.1.3684-21_amend-2021-12-14-no37",
    "17ef26d65e0171999ddf58db068327bf09172a555425119bd3fcad40a30f0a5d": "sanpin-2.1.3684-21_amend-2022-02-14-no6",
    "d6b6b0e15886b3714566285dacb056feb69a20934222cf5e7b2dbe6c1b2a13cc": "sanpin-2.1.3684-21_amend-2024-11-15-no11",
    "d1368055901455abdb8754da5ec4a996cd0c0562c76097552c02e23a575328de": "sanpin-2.1.3684-21_amend-2025-06-17-no10",
    "14e725ed77a72eb6ec2b8bbdf06b9aadeba01a0cdc33930756792b4f886eab63": "sanpin-2.1.3684-21_amend-2025-06-25-no13",
    "a0ee4eb3704e516d4c23f629f105fc70973427f0b0ea74b8f8d54a0c5fb3073e": "sanpin-2.1.3684-21_amend-2025-12-29-no21",
    "2bc8a80b1bf86bff17e3c544f3b53c85456ce48ee507d07167c634e3ad1bc680": "sanpin-2.1.3684-21_amend-2026-02-12-no2",
    "4cdf224aba025b5edaeea4f249eed2864471e73a1037f8386a3ceaa5c39216ff": "sanpin-2.1.3684-21_amend-2026-09-10-no25",
}

README = """# M1-04А: рабочая папка задачи

Создана 21.10.2026. Здесь всё новое по задаче М1-04А лежит по одной схеме.

| Папка | Что внутри | Можно менять? |
|---|---|---|
| `documents/development/<документ>/` | Оригиналы документов разработки: `document.pdf` + `source.json` (URL, SHA-256, откуда скопирован) | Нет |
| `documents/reserved/<документ>/` | Квалификационный резерв Task 3. **Не открывать до Task 3.** | Нет |
| `documents/pool/<партия>/<документ>/` | Новые документы проверочного пула | Нет |
| `ocr/<документ>/<прогон>/` | Результаты OCR dots.mocr: native-ответы и `text-extraction/1` | Нет, новый прогон — новая папка |
| `gold/<документ>/` | Эталоны (`manual-*`, `auto-*`) и хеши заморозки | Нет после заморозки |
| `experiments/<ГГГГММДД>-<имя>/` | Прогоны кода, оценки, сравнения | Нет, новый прогон — новая папка |

Оригиналы — проверенные по SHA-256 копии из архивов `sources`; сами архивы
не тронуты. Материалы до 21.10.2026 не перемещались (на их пути ссылаются
отчёты и хеши) — карта в `LEGACY.md`. Каталог документов — `documents/index.json`,
пересоздаётся `docs/assets/build_m1_04a_catalog.py`.
"""

LEGACY = """# Где лежат материалы М1-04А до 21.10.2026

Не перемещались. Пути закреплены в отчётах `docs/milestones/m1/04a/` и хешах.

## Оригиналы (архивы `sources`, по SHA-256)

- `data/m1-02-sources/` — СанПиН 2.1.3684-21 и девять изменяющих постановлений.
- `data/m1/experiments/m1-04a-20261017-v1/acquisition/archive/` — шесть
  дополнительных актов (2 разработки, 4 резерва).
- `data/m1/experiments/m1-04a-20261017-two-pdf-v1/archive/` — ПП №416, СП 3.1.3597-20.

Копии всех 18 лежат в `documents/`.

## Результаты OCR

- `data/m1/pilot_runs/m1-04-seal-recovery-20261016-v1/` — финальный OCR 10 PDF СанПиН (103 стр.).
- `data/m1/experiments/m1-04a-20261017-v1/development-ocr/` — СП 2.1.3678-20 и ПП №1156.
- `data/m1/experiments/m1-04a-20261017-two-pdf-v1/` — ПП №416 и СП 3.1.3597-20 (26 стр.).
- `data/m1/experiments/m1-04a-20261017-json-v1/` — замороженный native JSON всех 12 документов разработки.

## Эталоны

- `data/m1/experiments/m1-04a-20261017-logical-v1/gold/` — ручной эталон 8 документов (849 областей).
- `data/m1/experiments/m1-04a-20261018-llm-v1/blind/gold/` — слепой эталон 6 изменяющих актов (76 областей).

## Эксперименты

| Папка в `data/m1/experiments/` | Что это |
|---|---|
| `m1-04a-20261017-v1/` | Исходный разбор, пробы Dedoc, загрузка шести актов, shared-v1…v6 |
| `m1-04a-20261017-scope-v1/` | Инвентаризация областей 12 документов |
| `m1-04a-20261017-footnotes-v1/`, `-v2/` | Склейка сносок через страницы |
| `m1-04a-20261017-json-v1/` | Прямой JSON → Dedoc / Docling |
| `m1-04a-20261017-two-pdf-v1/` | Два новых PDF через весь конвейер |
| `m1-04a-20261017-logical-v1/` | Прототип логических абзацев: эталон, прогоны, сравнения |
| `m1-04a-20261018-llm-v1/` | LLM-гибрид этапа 3, слепой набор |
| `m1-04a-20261020-logical-text-v1/`, `20261021-...-v2/` | Сверка `logical-text/1` с прототипом |
| `isanlp-rst-resolution416-20261020-v1/`, `rumodernbert-rulaw-resolution416-20261020-v1/` | Пробы других моделей на ПП №416 |
"""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_once(path: Path, data: bytes) -> str:
    if path.exists():
        if path.read_bytes() != data:
            raise ValueError(f"refusing to overwrite different content: {path}")
        return "unchanged"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return "new"


def place(out: Path, group: str, slug: str, manifest_path: Path, manifest: dict, asset: dict) -> dict:
    archive = Path(manifest["archive_root"])
    if not archive.is_absolute():
        archive = (manifest_path.parent / archive).resolve()
    digest = asset["sha256"]
    record = json.loads((archive / "assets" / f"{digest}.json").read_text(encoding="utf-8"))
    raw = archive / record["archive_key"]
    if record.get("sha256") != digest or sha256(raw) != digest:
        raise ValueError(f"archive asset hash mismatch: {digest}")
    target = out / "documents" / group / slug / "document.pdf"
    if target.exists():
        if sha256(target) != digest:
            raise ValueError(f"existing copy differs: {target}")
        status = "unchanged"
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(raw, target)
        if sha256(target) != digest:
            target.unlink()
            raise ValueError(f"copy hash mismatch: {target}")
        status = "new"
    source = {
        "slug": slug, "group": group, "role": asset["role"],
        "declared_identity": asset.get("declared_identity"),
        "sha256": digest, "byte_length": record.get("byte_length"),
        "source_url": record.get("source_url"), "captured_at": record.get("captured_at"),
        "media_type": record.get("media_type"),
        "copied_from": str(raw.relative_to(ROOT)).replace("\\", "/"),
        "input_manifest": str(manifest_path.relative_to(ROOT)).replace("\\", "/"),
    }
    write_once(target.parent / "source.json",
               (json.dumps(source, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    return {**source, "copy": status}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=M1 / "m1-04a")
    out = parser.parse_args(argv).output
    rows = []
    for group, manifest_path, slug in SINGLE:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        (asset,) = [a for a in manifest["assets"] if a["role"] == "original"]
        rows.append(place(out, group, slug, manifest_path, manifest, asset))
    manifest = json.loads(SANPIN.read_text(encoding="utf-8"))
    for asset in manifest["assets"]:
        rows.append(place(out, "development", SANPIN_SLUGS[asset["sha256"]], SANPIN, manifest, asset))
    pool_rows = {}
    for batch in POOL_BATCHES:
        group = f"pool/{batch}"
        for manifest_path in sorted((out / "documents" / group).glob("*/input.json")):
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            (asset,) = [a for a in manifest["assets"] if a["role"] == "original"]
            row = place(out, group, manifest_path.parent.name, manifest_path, manifest, asset)
            pool_rows.setdefault(group, []).append(row)
    for name in ("experiments", "gold", "ocr", "documents/pool"):
        (out / name).mkdir(parents=True, exist_ok=True)
    index = {"schema_version": "m1-04a-document-index/1",
             "documents": sorted(({k: r[k] for k in r if k != "copy"} for r in rows),
                                 key=lambda r: (r["group"], r["slug"]))}
    write_once(out / "documents" / "index.json",
               (json.dumps(index, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    for group, group_rows in pool_rows.items():
        pool_index = {"schema_version": "m1-04a-document-index/1", "group": group,
                      "documents": sorted(({k: r[k] for k in r if k != "copy"} for r in group_rows),
                                          key=lambda r: r["slug"])}
        write_once(out / "documents" / group / "index.json",
                   (json.dumps(pool_index, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8"))
        rows += group_rows
    for batch, history in POOL_STATUS.items():
        status = {"schema_version": "m1-04a-pool-status/1", "group": f"pool/{batch}",
                  "status": history[-1]["status"], "history": history}
        write_once(out / "documents" / "pool" / batch / "status.json",
                   (json.dumps(status, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    for name, text in (("README.md", README), ("LEGACY.md", LEGACY)):
        write_once(out / name, text.encode("utf-8"))
    summary = {}
    for r in rows:
        summary.setdefault(r["group"], []).append(f'{r["slug"]} ({r["copy"]})')
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
