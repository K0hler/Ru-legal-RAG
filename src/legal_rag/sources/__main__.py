import argparse
import json
from pathlib import Path
import sys

from .acquisition import acquire_fixture, acquire_publication
from .publication_pravo import PublicationPravoConnector


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m legal_rag.sources")
    commands = parser.add_subparsers(dest="command", required=True)
    fixture = commands.add_parser("acquire-fixture")
    fixture.add_argument("--fixture", type=Path, required=True)
    fixture.add_argument("--metadata", type=Path, required=True)
    fixture.add_argument("--data-dir", type=Path, required=True)
    publication = commands.add_parser("acquire-publication")
    publication.add_argument("--eo-number", required=True)
    publication.add_argument("--data-dir", type=Path, required=True)
    publication.add_argument("--timeout", type=float, default=20.0)
    arguments = parser.parse_args(argv)

    if arguments.command == "acquire-fixture":
        result = acquire_fixture(arguments.fixture, arguments.metadata, arguments.data_dir)
    else:
        result = acquire_publication(
            PublicationPravoConnector(timeout=arguments.timeout),
            arguments.eo_number,
            arguments.data_dir,
        )
    print(json.dumps(result, sort_keys=True))
    return int(result["result"] == "failed")


if __name__ == "__main__":
    sys.exit(main())
