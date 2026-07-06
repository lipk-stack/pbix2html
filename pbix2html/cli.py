"""Command-line interface: ``pbix2html report.pbix [-o report.html]``."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pbix2html import __version__
from pbix2html.reader import PbixError, read_pbix
from pbix2html.render import render_html


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pbix2html",
        description="Convert a Power BI .pbix/.pbit file to a standalone HTML document.",
    )
    parser.add_argument("input", help="path to the .pbix or .pbit file")
    parser.add_argument(
        "-o",
        "--output",
        help="output HTML path (default: input path with a .html suffix)",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    input_path = Path(args.input)
    output_path = Path(args.output) if args.output else input_path.with_suffix(".html")

    try:
        report = read_pbix(input_path)
    except FileNotFoundError:
        print(f"pbix2html: file not found: {input_path}", file=sys.stderr)
        return 2
    except PbixError as exc:
        print(f"pbix2html: {exc}", file=sys.stderr)
        return 1

    output_path.write_text(render_html(report), encoding="utf-8")
    print(
        f"Wrote {output_path} ({len(report.pages)} pages, {report.visual_count} visuals)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
