# pbix2html

Convert Power BI `.pbix` / `.pbit` files into standalone HTML documents that
show the report's structure: every page rendered as a positioned wireframe of
its visuals (type, title, bound fields), plus the data model tables (for
`.pbit` templates) and registered static resources.

Uses only the Python standard library — no dependencies to install.

## Usage

```bash
# Convert a report (writes report.html next to the input)
python -m pbix2html report.pbix

# Choose the output path
python -m pbix2html report.pbix -o out/report.html
```

Or install it as a command:

```bash
pip install .
pbix2html report.pbix
```

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
