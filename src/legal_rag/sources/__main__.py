import argparse
import json
from pathlib import Path
import sys

from .acquisition import (
    acquire_actual,
    acquire_fixture,
    acquire_legislation,
    acquire_publication,
)
from .actual_pravo import ActualPravoConnector
from .handoff import build_edition_candidate
from .legislation_russia import LegislationRussiaConnector
from .publication_pravo import PublicationPravoConnector
from .pilot import run_pilot
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
    legislation = commands.add_parser("acquire-legislation")
    legislation.add_argument("--document-hash", required=True)
    legislation.add_argument("--data-dir", type=Path, required=True)
    legislation.add_argument("--timeout", type=float, default=20.0)
    relations = commands.add_parser("reconcile-relations")
    relations.add_argument("--claims", type=Path, required=True)
    relations.add_argument("--data-dir", type=Path, required=True)
    candidate = commands.add_parser("build-candidate")
    candidate.add_argument("--reconciliation", type=Path, required=True)
    candidate.add_argument("--data-dir", type=Path, required=True)
    candidate.add_argument("--review-decision", type=Path)
    pilot = commands.add_parser("run-pilot")
    pilot.add_argument("--data-dir", type=Path, required=True)
    pilot.add_argument("--timeout", type=float, default=20.0)
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
    elif arguments.command == "acquire-legislation":
        result = acquire_legislation(
            LegislationRussiaConnector(timeout=arguments.timeout),
            arguments.document_hash,
            arguments.data_dir,
        )
    elif arguments.command == "reconcile-relations":
        result = reconcile_publication_relations(arguments.claims, arguments.data_dir)
    elif arguments.command == "build-candidate":
        result = build_edition_candidate(
            arguments.reconciliation,
            arguments.data_dir,
            arguments.review_decision,
        )
    else:
        result = run_pilot(arguments.data_dir, arguments.timeout)
    print(json.dumps(result, sort_keys=True))
    return int(result["result"] == "failed")


if __name__ == "__main__":
    sys.exit(main())
