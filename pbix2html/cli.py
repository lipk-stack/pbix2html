"""Command-line interface: ``pbix2html report.pbix [-o report.html]``."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pbix2html import __version__
from pbix2html.fidelity import build_fidelity_report
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
    parser.add_argument(
        "--fidelity-report",
        help=(
            "also write a machine-readable JSON fidelity report to this path, classifying "
            "every visual family and report-wide feature as EXACT/SEMANTICALLY_EQUIVALENT/"
            "VISUALLY_EQUIVALENT/UNSUPPORTED/etc."
        ),
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

    fidelity = build_fidelity_report(report)
    output_path.write_text(render_html(report, fidelity), encoding="utf-8")
    if args.fidelity_report:
        Path(args.fidelity_report).write_text(
            json.dumps(fidelity.to_dict(), indent=2) + "\n", encoding="utf-8"
        )

    counts = fidelity.visual_counts_by_classification()
    unsupported = counts.get("UNSUPPORTED", 0)
    print(
        f"Wrote {output_path} ({len(report.pages)} pages, {report.visual_count} visuals). "
        f"Fidelity: {unsupported} unsupported visual instance(s) out of {report.visual_count}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
