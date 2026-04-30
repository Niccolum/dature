import argparse
import sys

from dature.cli.inspect_cmd import cmd_inspect
from dature.cli.parsing import add_common_args
from dature.cli.validate_cmd import cmd_validate


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dature",
        description="dature CLI: inspect and validate dataclass-based configuration.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    inspect = subparsers.add_parser(
        "inspect",
        help="Print the load report (sources, field origins, merged data).",
    )
    add_common_args(inspect)
    inspect.add_argument(
        "--field",
        default=None,
        metavar="DOTTED.PATH",
        help="Filter origins and merged data by a dotted field path.",
    )
    inspect.add_argument(
        "--format",
        choices=["json", "text"],
        default="json",
        help="Output format (default: json).",
    )
    inspect.set_defaults(func=cmd_inspect)

    validate = subparsers.add_parser(
        "validate",
        help="Try loading the schema; exit 0 on success, 1 on validation failure, 2 on usage error.",
    )
    add_common_args(validate)
    validate.set_defaults(func=cmd_validate)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
