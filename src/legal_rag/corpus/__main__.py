import argparse
import json
from pathlib import Path
import sys

from .compiler import compile_input


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m legal_rag.corpus")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("compile", "prepare-html"):
        command = commands.add_parser(name)
        command.add_argument("--input", type=Path, required=True)
        command.add_argument("--target-date", required=True)
        command.add_argument("--output-dir", type=Path, required=True)
        if name == "compile":
            command.add_argument("--extraction-index", type=Path)
    extract = commands.add_parser("extract")
    extract.add_argument("--input", type=Path, required=True)
    extract.add_argument("--output-dir", type=Path, required=True)
    provider = extract.add_mutually_exclusive_group(required=True)
    provider.add_argument("--ocr-config", type=Path)
    provider.add_argument("--ocr-results", type=Path)
    arguments = parser.parse_args(argv)
    try:
        if arguments.command == "extract":
            from .ocr_runtime import extract_input

            result = extract_input(arguments.input, arguments.output_dir, arguments.ocr_config, arguments.ocr_results)
        elif arguments.command == "prepare-html":
            from .html_preparation import prepare_input

            result = prepare_input(arguments.input, arguments.target_date, arguments.output_dir)
        else:
            result = compile_input(arguments.input, arguments.target_date, arguments.output_dir,
                                   extraction_index=arguments.extraction_index)
    except (ValueError, OSError, KeyError, TypeError) as error:
        print(json.dumps({"result": "failed", "error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
