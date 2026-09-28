import argparse
import json
from pathlib import Path
import sys

from .acquisition import acquire_actual, acquire_fixture, acquire_publication
from .actual_pravo import ActualPravoConnector
from .publication_pravo import PublicationPravoConnector
from .relations import reconcile_publication_relations


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
    actual = commands.add_parser("acquire-actual")
    actual.add_argument("--document-hash", required=True)
    actual.add_argument("--data-dir", type=Path, required=True)
    actual.add_argument("--timeout", type=float, default=20.0)
    relations = commands.add_parser("reconcile-relations")
    relations.add_argument("--claims", type=Path, required=True)
    relations.add_argument("--data-dir", type=Path, required=True)
    arguments = parser.parse_args(argv)

    if arguments.command == "acquire-fixture":
        result = acquire_fixture(arguments.fixture, arguments.metadata, arguments.data_dir)
    elif arguments.command == "acquire-publication":
        result = acquire_publication(
            PublicationPravoConnector(timeout=arguments.timeout),
            arguments.eo_number,
            arguments.data_dir,
        )
    elif arguments.command == "acquire-actual":
        result = acquire_actual(
            ActualPravoConnector(timeout=arguments.timeout),
            arguments.document_hash,
            arguments.data_dir,
        )
    else:
        result = reconcile_publication_relations(arguments.claims, arguments.data_dir)
    print(json.dumps(result, sort_keys=True))
    return int(result["result"] == "failed")


if __name__ == "__main__":
    sys.exit(main())
