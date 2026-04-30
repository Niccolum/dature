import sys
from argparse import Namespace

from dature import get_load_report, load
from dature.cli.format import format_dature_error, format_json, format_text
from dature.cli.parsing import build_load_kwargs, build_sources, import_attr
from dature.errors import DatureConfigError, DatureError


def cmd_inspect(args: Namespace) -> int:
    try:
        schema = import_attr(args.schema)
        sources = build_sources(args.source)
        load_kwargs = build_load_kwargs(args)
    except (ValueError, TypeError, ImportError, AttributeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    try:
        result = load(*sources, schema=schema, debug=True, **load_kwargs)
    except (DatureError, DatureConfigError) as exc:
        print(format_dature_error(exc), file=sys.stderr)
        return 1
    except (FileNotFoundError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    report = get_load_report(result)
    if report is None:
        print("error: failed to obtain load report", file=sys.stderr)
        return 1

    try:
        if args.format == "json":
            output = format_json(report, field=args.field)
        else:
            output = format_text(report, field=args.field)
    except KeyError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(output)
    return 0
