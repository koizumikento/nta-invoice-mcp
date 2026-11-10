import asyncio
import json
import sys
from argparse import SUPPRESS, ArgumentParser
from collections.abc import Sequence

import httpx

from .client import lookup_invoice_registration


def run_cli(argv: Sequence[str]) -> None:
    parser = ArgumentParser(prog="nta-invoice-mcp")
    commands = parser.add_subparsers(required=True)

    command = commands.add_parser("lookup-invoice-registration", argument_default=SUPPRESS)
    command.add_argument("--registration-number", required=True)
    command.add_argument("--day", required=True)
    command.set_defaults(handler=lookup_invoice_registration)

    arguments = vars(parser.parse_args(argv))
    handler = arguments.pop("handler")
    try:
        result = asyncio.run(handler(**arguments))
    except (ValueError, OSError, httpx.HTTPError) as exc:
        parser.exit(1, f"{parser.prog}: {exc}\n")
    sys.stdout.buffer.write((json.dumps(result, ensure_ascii=False) + "\n").encode("utf-8"))
