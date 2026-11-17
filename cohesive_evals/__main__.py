"""One CLI for MV1 orchestration; historical probes retain their existing public commands."""

import argparse
from pathlib import Path


def main():
    """Parse explicit paths, dispatch a scenario operation and preserve nonzero failures."""
    parser = argparse.ArgumentParser(description=__doc__)
    operations = parser.add_subparsers(dest="operation", required=True)
    build = operations.add_parser(
        "mv1-run", help="Build, generate, independently check and freeze"
    )
    build.add_argument("--output", required=True, type=Path)
    build.add_argument("--prepare-locks", action="store_true")
    qualify = operations.add_parser(
        "mv1-qualify", help="Qualify the frozen suite against named defects"
    )
    qualify.add_argument("--frozen", required=True, type=Path)
    qualify.add_argument("--output", required=True, type=Path)
    integration = operations.add_parser(
        "mv1-integration", help="Verify HTTP/replay and physical state"
    )
    integration.add_argument("--fixtures", required=True, type=Path)
    integration.add_argument("--output", required=True, type=Path)
    record = operations.add_parser("mv1-record", help="Bundle successful JSON evidence")
    record.add_argument("--run", action="append", required=True, metavar="NAME=PATH")
    record.add_argument("--http-fixtures", required=True, type=Path)
    record.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    for name in ("output", "fixtures", "http_fixtures", "frozen"):
        if hasattr(args, name):
            setattr(args, name, getattr(args, name).resolve())
    if args.operation == "mv1-run":
        from .mv1.run import run

        run(args.output, args.prepare_locks)
    elif args.operation == "mv1-qualify":
        from .mv1.qualify import run

        run(args.frozen, args.output)
    elif args.operation == "mv1-integration":
        from .mv1.integration import run

        run(args.fixtures, args.output)
    else:
        from .mv1.record import record

        record(args)


if __name__ == "__main__":
    main()
