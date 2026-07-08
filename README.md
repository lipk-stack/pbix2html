# pbix2html

Convert Power BI `.pbix` / `.pbit` files into standalone HTML documents that
show the report's structure: every page rendered as a positioned wireframe of
its visuals (type, title, bound fields), plus the data model tables (for
`.pbit` templates), registered static resources, and an explicit fidelity
report classifying what was and wasn't preserved.

Uses only the Python standard library — no dependencies to install.

## Usage

```bash
# Convert a report (writes report.html next to the input)
python -m pbix2html report.pbix

# Choose the output path
python -m pbix2html report.pbix -o out/report.html

# Also write a machine-readable fidelity report
python -m pbix2html report.pbix --fidelity-report report.fidelity.json
```

Or install it as a command:

```bash
pip install .
pbix2html report.pbix
```

## Fidelity report

pbix2html never claims a feature was converted when it wasn't. Every output
includes a "Conversion fidelity report" section (and, with
`--fidelity-report`, a JSON file — see `pbix2html/fidelity.py`) classifying
each visual family and each report-wide feature (layout, navigation, semantic
model metadata, DAX, filters, cross-filtering, bookmarks, theming, static
resources, row-level security) as one of: `EXACT`, `SEMANTICALLY_EQUIVALENT`,
`VISUALLY_EQUIVALENT`, `APPROXIMATED`, `SNAPSHOTTED`,
`CONNECTED_RUNTIME_REQUIRED`, `UNSUPPORTED`, `BLOCKED_FOR_SECURITY`, or
`BLOCKED_FOR_LICENSING`, with a plain-language reason for each.

## What gets extracted

A PBIX file is a ZIP archive. pbix2html reads:

| Part | Contents |
| --- | --- |
| `Report/Layout` | Pages, visual positions, visual types, titles, field bindings |
| `Version` | Layout format version |
| `DataModelSchema` | Tables, columns, measures (present in `.pbit` templates) |
| `Report/StaticResources/` | Names of registered images/themes |

The binary `DataModel` blob inside `.pbix` files uses a proprietary
compression (XPress9) and is intentionally not parsed; save your report as a
`.pbit` template if you want the data model section populated.

## Development

```bash
python -m unittest discover -v
```

Tests build synthetic PBIX archives in memory (see `tests/helpers.py`), so
the suite runs offline with no fixtures. A real-world sample corpus can be
downloaded on demand with `scripts/build_pbix_corpus.py` or the
"Build Public PBIX Corpus" workflow (manual dispatch).
