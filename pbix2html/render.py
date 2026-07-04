"""Render a parsed :class:`~pbix2html.reader.PbixReport` as standalone HTML.

The output is a single self-contained document: a summary header, one
wireframe per report page with every visual drawn at its layout position,
and (when the archive carries a model schema) the tables of the data model.
No external assets, scripts, or network access are required to view it.
"""

from __future__ import annotations

import html
from datetime import datetime, timezone

from pbix2html.reader import Page, PbixReport, Visual

_CSS = """
:root { color-scheme: light dark; }
* { box-sizing: border-box; }
body {
  margin: 0; padding: 2rem; font: 15px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif;
  background: #f4f5f7; color: #1c1e21;
}
@media (prefers-color-scheme: dark) {
  body { background: #17191c; color: #e4e6eb; }
  .page-canvas, .card { background: #22252a; border-color: #3a3f45; }
  .visual { background: #2a2e34; border-color: #4a5058; }
  th { background: #2a2e34; }
}
h1 { font-size: 1.5rem; margin: 0 0 0.25rem; }
h2 { font-size: 1.15rem; margin: 2.5rem 0 0.75rem; }
.subtitle { opacity: 0.7; margin: 0 0 1.5rem; }
.summary { display: flex; gap: 2rem; flex-wrap: wrap; margin: 0 0 1rem; padding: 0; list-style: none; }
.summary li strong { display: block; font-size: 1.3rem; }
.card, .page-canvas {
  background: #fff; border: 1px solid #d5d9de; border-radius: 8px;
}
.card { padding: 1rem 1.25rem; overflow-x: auto; }
.page-canvas { position: relative; width: 100%; overflow: hidden; }
.page-meta { font-size: 0.85rem; opacity: 0.7; margin: 0.35rem 0 1rem; }
.visual {
  position: absolute; overflow: hidden; padding: 0.4rem 0.5rem;
  background: #fbfcfd; border: 1px solid #b9c2cc; border-radius: 4px;
  font-size: 0.72rem; line-height: 1.35;
}
.visual.hidden-visual { opacity: 0.45; border-style: dashed; }
.visual .vtype { font-weight: 600; display: block; }
.visual .vtitle { display: block; font-style: italic; }
.visual ul { margin: 0.15rem 0 0; padding-left: 1rem; }
.badge {
  display: inline-block; font-size: 0.7rem; padding: 0.1rem 0.5rem;
  border-radius: 999px; border: 1px solid currentColor; opacity: 0.75; margin-left: 0.5rem;
}
table { border-collapse: collapse; width: 100%; font-size: 0.85rem; }
th, td { text-align: left; padding: 0.35rem 0.75rem; border-bottom: 1px solid #d5d9de; vertical-align: top; }
th { background: #eef0f3; }
footer { margin-top: 3rem; font-size: 0.8rem; opacity: 0.6; }
"""


def _esc(value: str) -> str:
    return html.escape(str(value), quote=True)


def _pct(part: float, whole: float) -> str:
    if whole <= 0:
        return "0%"
    return f"{max(0.0, part / whole * 100):.3f}%"


def _render_visual(visual: Visual, page: Page) -> str:
    style = (
        f"left:{_pct(visual.x, page.width)};"
        f"top:{_pct(visual.y, page.height)};"
        f"width:{_pct(visual.width, page.width)};"
        f"height:{_pct(visual.height, page.height)};"
        f"z-index:{int(visual.z)};"
    )
    classes = "visual hidden-visual" if visual.hidden else "visual"
    parts = [f'<div class="{classes}" style="{style}" title="{_esc(visual.name)}">']
    parts.append(f'<span class="vtype">{_esc(visual.visual_type)}</span>')
    if visual.title:
        parts.append(f'<span class="vtitle">{_esc(visual.title)}</span>')
    if visual.fields:
        parts.append("<ul>" + "".join(f"<li>{_esc(f)}</li>" for f in visual.fields) + "</ul>")
    parts.append("</div>")
    return "".join(parts)


def _render_page(page: Page) -> str:
    aspect = f"padding-top:{_pct(page.height, page.width)};" if page.width > 0 else "height:20rem;"
    hidden_badge = '<span class="badge">hidden</span>' if page.hidden else ""
    visuals = "".join(_render_visual(v, page) for v in page.visuals)
    return (
        f"<h2>{_esc(page.display_name)}{hidden_badge}</h2>"
        f'<p class="page-meta">{int(page.width)} &times; {int(page.height)} px'
        f" &middot; {len(page.visuals)} visual{'s' if len(page.visuals) != 1 else ''}</p>"
        f'<div class="page-canvas"><div style="{aspect}"></div>{visuals}</div>'
    )


def _render_tables(report: PbixReport) -> str:
    if not report.tables:
        return ""
    rows = []
    for table in report.tables:
        rows.append(
            "<tr>"
            f"<td>{_esc(table.name)}</td>"
            f"<td>{_esc(', '.join(table.columns)) or '&mdash;'}</td>"
            f"<td>{_esc(', '.join(table.measures)) or '&mdash;'}</td>"
            "</tr>"
        )
    return (
        "<h2>Data model</h2>"
        '<div class="card"><table>'
        "<thead><tr><th>Table</th><th>Columns</th><th>Measures</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody>"
        "</table></div>"
    )


def _render_resources(report: PbixReport) -> str:
    if not report.static_resources:
        return ""
    items = "".join(f"<li><code>{_esc(name)}</code></li>" for name in report.static_resources)
    return f'<h2>Static resources</h2><div class="card"><ul>{items}</ul></div>'


def render_html(report: PbixReport) -> str:
    """Return a complete, self-contained HTML document for *report*."""
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    version = f" &middot; layout version {_esc(report.version)}" if report.version else ""
    summary = (
        '<ul class="summary">'
        f"<li><strong>{len(report.pages)}</strong> pages</li>"
        f"<li><strong>{report.visual_count}</strong> visuals</li>"
        f"<li><strong>{len(report.tables)}</strong> model tables</li>"
        f"<li><strong>{len(report.static_resources)}</strong> static resources</li>"
        "</ul>"
    )
    pages = "".join(_render_page(page) for page in report.pages) or "<p>No report pages found.</p>"
    return (
        "<!DOCTYPE html>\n"
        '<html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{_esc(report.source_name)} &mdash; pbix2html</title>"
        f"<style>{_CSS}</style></head><body>"
        f"<h1>{_esc(report.source_name)}</h1>"
        f'<p class="subtitle">Power BI report structure{version}</p>'
        f"{summary}{pages}{_render_tables(report)}{_render_resources(report)}"
        f"<footer>Generated by pbix2html on {generated}.</footer>"
        "</body></html>\n"
    )
