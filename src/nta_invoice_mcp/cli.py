import asyncio
import json
import sys
from argparse import SUPPRESS, ArgumentParser
from collections.abc import Sequence

import httpx

from .client import (
    get_invoice_registration_history,
    lookup_invoice_registration,
    lookup_invoice_registrations,
)


def run_cli(argv: Sequence[str]) -> None:
    parser = ArgumentParser(prog="nta-invoice-mcp")
    commands = parser.add_subparsers(required=True)

    command = commands.add_parser("lookup-invoice-registration", argument_default=SUPPRESS)
    command.add_argument("--registration-number", required=True)
    command.add_argument("--day", required=True)
    command.set_defaults(handler=lookup_invoice_registration)

    command = commands.add_parser("lookup-invoice-registrations", argument_default=SUPPRESS)
    command.add_argument("--registration-numbers", nargs="+", required=True)
    command.add_argument("--day", required=True)
    command.set_defaults(handler=lookup_invoice_registrations)

    command = commands.add_parser("get-invoice-registration-history", argument_default=SUPPRESS)
    command.add_argument("--registration-number", required=True)
    command.set_defaults(handler=get_invoice_registration_history)

    arguments = vars(parser.parse_args(argv))
    handler = arguments.pop("handler")
    try:
        result = asyncio.run(handler(**arguments))
    except (ValueError, OSError, httpx.HTTPError) as exc:
        parser.exit(1, f"{parser.prog}: {exc}\n")
    sys.stdout.buffer.write((json.dumps(result, ensure_ascii=False) + "\n").encode("utf-8"))
