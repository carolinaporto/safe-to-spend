"""CSV import parsers. ``parse_csv`` picks a parser and returns shared rows."""

from backend.importers import amex, chase, generic, wise
from backend.importers.base import ParsedRow, ParseError, read_rows

_PARSERS = {p.name: p for p in (chase, amex, wise, generic)}
PARSER_NAMES: list[str] = list(_PARSERS)

# Try the specific institutions before the permissive generic parser.
_DETECT_ORDER = ("wise", "amex", "chase")


def detect_parser(header: list[str]) -> str:
    for name in _DETECT_ORDER:
        if _PARSERS[name].sniff(header):
            return name
    return "generic"


def parse_csv(
    content: bytes, currency: str, parser_name: str | None = None
) -> tuple[str, list[ParsedRow]]:
    header, rows = read_rows(content)
    name = parser_name or detect_parser(header)
    parser = _PARSERS.get(name)
    if parser is None:
        raise ParseError(f"unknown parser: {name!r}")
    if name == "generic":
        return name, parser.parse(rows, currency, header)
    return name, parser.parse(rows, currency)


__all__ = [
    "ParsedRow",
    "ParseError",
    "PARSER_NAMES",
    "detect_parser",
    "parse_csv",
]
