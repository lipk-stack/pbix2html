"""Render a parsed PBIX/PBIT report as a self-contained interactive HTML shell.

The renderer never pretends that layout metadata is equivalent to embedded report
data. It provides page navigation and faithful geometry for the metadata that was
actually extracted, while clearly marking layout-only output.
"""

from __future__ import annotations

import html
from datetime import datetime, timezone

from pbix2html.fidelity import FidelityReport, build_fidelity_report
from pbix2html.reader import Page, PbixReport, Visual

_CSS = r"""
:root {
  color-scheme: light dark;
  --bg: #f3f5f8;
  --panel: #ffffff;
  --panel-2: #f8fafc;
  --text: #172033;
  --muted: #667085;
  --line: #d7dde7;
  --accent: #2563eb;
  --warn-bg: #fff7ed;
  --warn-line: #fdba74;
  --warn-text: #9a3412;
  --shadow: 0 10px 30px rgba(15, 23, 42, .10);
}
* { box-sizing: border-box; }
html, body { min-height: 100%; }
body { margin: 0; font: 14px/1.45 system-ui, -apple-system, "Segoe UI", sans-serif; background: var(--bg); color: var(--text); }
button { font: inherit; }
.app-header { position: sticky; top: 0; z-index: 100000; background: var(--panel); border-bottom: 1px solid var(--line); }
.header-inner { max-width: 1600px; margin: 0 auto; padding: .9rem 1rem .65rem; }
.title-row { display: flex; gap: 1rem; align-items: flex-start; justify-content: space-between; }
h1 { font-size: 1.05rem; margin: 0; overflow-wrap: anywhere; }
.subtitle { color: var(--muted); margin: .2rem 0 0; font-size: .78rem; }
.summary { display: flex; gap: .55rem; flex-wrap: wrap; margin: .7rem 0 0; padding: 0; list-style: none; }
.summary li { border: 1px solid var(--line); background: var(--panel-2); border-radius: 999px; padding: .2rem .55rem; color: var(--muted); font-size: .74rem; }
.summary strong { color: var(--text); }
.page-tabs { display: flex; gap: .35rem; overflow-x: auto; padding: .65rem 0 .2rem; scrollbar-width: thin; }
.page-tab { flex: 0 0 auto; border: 1px solid var(--line); background: var(--panel); color: var(--text); border-radius: 7px; padding: .4rem .65rem; cursor: pointer; }
.page-tab:hover { border-color: var(--accent); }
.page-tab[aria-selected="true"] { color: #fff; background: var(--accent); border-color: var(--accent); }
.hidden-tab { display: none; }
.show-hidden .hidden-tab { display: inline-flex; }
.hidden-toggle { flex: 0 0 auto; border: 0; background: transparent; color: var(--accent); cursor: pointer; padding: .4rem .5rem; }
main { max-width: 1600px; margin: 0 auto; padding: 1rem; }
.fidelity-banner { margin: 0 0 1rem; padding: .8rem 1rem; border: 1px solid var(--warn-line); background: var(--warn-bg); color: var(--warn-text); border-radius: 9px; }
.fidelity-banner strong { display: block; margin-bottom: .15rem; }
.report-page { display: none; }
.report-page.active { display: block; }
.page-toolbar { display: flex; gap: .75rem; align-items: baseline; justify-content: space-between; margin: 0 0 .55rem; }
.page-toolbar h2 { font-size: 1rem; margin: 0; }
.page-meta { color: var(--muted); font-size: .76rem; white-space: nowrap; }
.badge { display: inline-block; font-size: .65rem; padding: .08rem .38rem; border-radius: 999px; border: 1px solid currentColor; opacity: .75; margin-left: .4rem; }
.page-frame { width: 100%; overflow: auto; border: 1px solid var(--line); border-radius: 10px; background: #dfe5ee; box-shadow: var(--shadow); }
.page-canvas { position: relative; width: 100%; min-width: 720px; overflow: hidden; background: var(--panel); isolation: isolate; }
.page-spacer { width: 100%; pointer-events: none; }
.visual { position: absolute; overflow: hidden; background: var(--panel); border: 1px solid #cbd5e1; border-radius: 4px; font-size: clamp(8px, .72vw, 12px); line-height: 1.25; color: var(--text); }
.visual-inner { width: 100%; height: 100%; min-width: 0; min-height: 0; padding: .3em .4em; }
.visual.hidden-visual { display: none !important; }
.visual-title { display: block; font-weight: 650; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; margin-bottom: .25em; }
.visual-type { color: var(--muted); font-size: .82em; }
.visual-shape { background: transparent; border-color: #d5dbe5; pointer-events: none; }
.visual-visualGroup { background: transparent; border: 1px dashed #94a3b8; pointer-events: none; }
.visual-textbox { background: transparent; border-color: transparent; }
.visual-textbox .visual-inner { display: flex; align-items: center; }
.visual-pageNavigator { display: none; }
.visual-actionButton .visual-inner { display: flex; align-items: center; justify-content: center; background: var(--panel-2); }
.visual-actionButton button { max-width: 100%; border: 1px solid var(--line); border-radius: 5px; padding: .3em .55em; background: var(--panel); color: var(--muted); }
.card-value { font-size: clamp(12px, 1.5vw, 24px); font-weight: 700; letter-spacing: -.02em; color: var(--muted); margin-top: .12em; }
.slicer-shell { display: flex; align-items: center; justify-content: space-between; gap: .4em; border: 1px solid var(--line); border-radius: 4px; padding: .32em .45em; background: var(--panel-2); color: var(--muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.chart-skeleton { height: calc(100% - 1.4em); min-height: 18px; display: flex; align-items: end; gap: 4%; padding: 5% 4% 4%; border-left: 1px solid var(--line); border-bottom: 1px solid var(--line); }
.chart-skeleton i { display: block; flex: 1; min-width: 2px; border-radius: 2px 2px 0 0; background: #93b4f6; }
.chart-skeleton i:nth-child(1) { height: 42%; }
.chart-skeleton i:nth-child(2) { height: 72%; }
.chart-skeleton i:nth-child(3) { height: 55%; }
.chart-skeleton i:nth-child(4) { height: 84%; }
.chart-skeleton i:nth-child(5) { height: 63%; }
.table-skeleton { width: 100%; border-collapse: collapse; font-size: .8em; }
.table-skeleton td { height: 1.35em; border-bottom: 1px solid var(--line); }
.table-skeleton td:first-child { width: 30%; }
.binding-details { position: absolute; right: .25em; bottom: .2em; max-width: calc(100% - .5em); color: var(--muted); font-size: .75em; }
.binding-details summary { cursor: pointer; list-style: none; text-align: right; white-space: nowrap; }
.binding-details summary::-webkit-details-marker { display: none; }
.binding-details[open] { left: .25em; background: var(--panel); border: 1px solid var(--line); border-radius: 4px; padding: .3em; z-index: 5; max-height: 85%; overflow: auto; }
.binding-details ul { margin: .25em 0 0; padding-left: 1.15em; }
.card-section { margin-top: 1rem; }
.card { background: var(--panel); border: 1px solid var(--line); border-radius: 9px; padding: .9rem 1rem; overflow-x: auto; }
.card-section h2 { font-size: .95rem; }
table { border-collapse: collapse; width: 100%; font-size: .82rem; }
th, td { text-align: left; padding: .4rem .6rem; border-bottom: 1px solid var(--line); vertical-align: top; }
th { background: var(--panel-2); }
.fidelity-pill { display: inline-block; font-size: .72rem; font-weight: 600; padding: .1rem .5rem; border-radius: 999px; white-space: nowrap; }
.fidelity-EXACT, .fidelity-SEMANTICALLY_EQUIVALENT { background: #dcfce7; color: #14532d; }
.fidelity-VISUALLY_EQUIVALENT, .fidelity-APPROXIMATED, .fidelity-SNAPSHOTTED { background: #fef9c3; color: #713f12; }
.fidelity-UNSUPPORTED, .fidelity-CONNECTED_RUNTIME_REQUIRED { background: #fee2e2; color: #7f1d1d; }
.fidelity-BLOCKED_FOR_SECURITY, .fidelity-BLOCKED_FOR_LICENSING { background: #e0e7ff; color: #312e81; }
@media (prefers-color-scheme: dark) {
  .fidelity-EXACT, .fidelity-SEMANTICALLY_EQUIVALENT { background: #14532d; color: #dcfce7; }
  .fidelity-VISUALLY_EQUIVALENT, .fidelity-APPROXIMATED, .fidelity-SNAPSHOTTED { background: #713f12; color: #fef9c3; }
  .fidelity-UNSUPPORTED, .fidelity-CONNECTED_RUNTIME_REQUIRED { background: #7f1d1d; color: #fee2e2; }
  .fidelity-BLOCKED_FOR_SECURITY, .fidelity-BLOCKED_FOR_LICENSING { background: #312e81; color: #e0e7ff; }
}
footer { max-width: 1600px; margin: 0 auto; padding: 1rem; color: var(--muted); font-size: .74rem; }
@media (prefers-color-scheme: dark) {
  :root { --bg: #111827; --panel: #1f2937; --panel-2: #273449; --text: #f3f4f6; --muted: #a7b0c0; --line: #3b475a; --accent: #3b82f6; --warn-bg: #3b2415; --warn-line: #9a5b28; --warn-text: #fed7aa; --shadow: 0 10px 30px rgba(0, 0, 0, .28); }
  .page-frame { background: #0f172a; }
}
@media (max-width: 760px) {
  .header-inner, main { padding-left: .65rem; padding-right: .65rem; }
  .title-row { display: block; }
  .summary { gap: .35rem; }
  .page-toolbar { align-items: flex-start; }
}
"""

_JS = r"""
(() => {
  const tabs = Array.from(document.querySelectorAll('.page-tab'));
  const pages = Array.from(document.querySelectorAll('.report-page'));
  const nav = document.querySelector('.page-tabs');
  const toggle = document.querySelector('.hidden-toggle');
  function visibleTabs() { return tabs.filter(t => getComputedStyle(t).display !== 'none'); }
  function activate(id, focus = false) {
    const target = document.getElementById(id);
    if (!target) return;
    pages.forEach(p => { const active = p === target; p.classList.toggle('active', active); p.hidden = !active; });
    tabs.forEach(t => { const active = t.dataset.page === id; t.setAttribute('aria-selected', String(active)); t.tabIndex = active ? 0 : -1; if (active && focus) t.focus(); });
    try { history.replaceState(null, '', '#' + encodeURIComponent(id)); } catch (_) {}
    window.scrollTo({top: 0, behavior: 'auto'});
  }
  tabs.forEach(tab => {
    tab.addEventListener('click', () => activate(tab.dataset.page));
    tab.addEventListener('keydown', event => {
      const list = visibleTabs(); const at = list.indexOf(tab); let next = null;
      if (event.key === 'ArrowRight') next = list[(at + 1) % list.length];
      if (event.key === 'ArrowLeft') next = list[(at - 1 + list.length) % list.length];
      if (event.key === 'Home') next = list[0];
      if (event.key === 'End') next = list[list.length - 1];
      if (next) { event.preventDefault(); activate(next.dataset.page, true); }
    });
  });
  if (toggle) {
    toggle.addEventListener('click', () => {
      const showing = nav.classList.toggle('show-hidden');
      toggle.setAttribute('aria-pressed', String(showing));
      toggle.textContent = showing ? 'Hide hidden pages' : 'Show hidden pages';
      if (!showing) {
        const active = tabs.find(t => t.getAttribute('aria-selected') === 'true');
        if (active && active.classList.contains('hidden-tab')) { const first = visibleTabs()[0]; if (first) activate(first.dataset.page); }
      }
    });
  }
  const hash = decodeURIComponent(location.hash.replace(/^#/, ''));
  const hashTab = tabs.find(t => t.dataset.page === hash && !t.classList.contains('hidden-tab'));
  const initial = hashTab || tabs.find(t => !t.classList.contains('hidden-tab')) || tabs[0];
  if (initial) activate(initial.dataset.page);
})();
"""


def _esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def _pct(part: float, whole: float) -> str:
    if whole <= 0:
        return "0%"
    return f"{max(0.0, part / whole * 100):.3f}%"


def _slug(value: str, index: int) -> str:
    safe = "".join(ch.lower() if ch.isalnum() else "-" for ch in value).strip("-")
    safe = "-".join(part for part in safe.split("-") if part)
    return f"page-{index + 1}-{safe[:48] or 'report-page'}"


def _visual_class(visual_type: str) -> str:
    safe = "".join(ch if ch.isalnum() else "-" for ch in visual_type)
    return f"visual-{safe or 'unknown'}"


def _binding_label(field: str) -> str:
    return field.split(": ", 1)[-1] if ": " in field else field


def _render_bindings(visual: Visual) -> str:
    if not visual.fields:
        return ""
    items = "".join(f"<li>{_esc(field)}</li>" for field in visual.fields)
    return (
        '<details class="binding-details">'
        f'<summary aria-label="Show field bindings">{len(visual.fields)} field'
        f"{'s' if len(visual.fields) != 1 else ''}</summary>"
        f"<ul>{items}</ul></details>"
    )


def _render_visual_body(visual: Visual) -> str:
    kind = visual.visual_type.lower()
    title = visual.title or visual.visual_type
    title_html = f'<span class="visual-title">{_esc(title)}</span>' if title else ""
    if kind == "textbox":
        return title_html
    if kind == "pagenavigator":
        return ""
    if kind == "shape":
        return title_html
    if kind == "visualgroup":
        return title_html or '<span class="visual-type">group</span>'
    if "card" in kind:
        return f'{title_html}<div class="card-value" title="No portable row data was extracted">—</div>'
    if "slicer" in kind:
        field = _binding_label(visual.fields[0]) if visual.fields else "Filter"
        return f'{title_html}<div class="slicer-shell"><span>{_esc(field)}</span><span>▾</span></div>'
    if "table" in kind or "matrix" in kind:
        rows = "".join("<tr><td></td><td></td><td></td></tr>" for _ in range(4))
        return f'{title_html}<table class="table-skeleton" aria-hidden="true"><tbody>{rows}</tbody></table>'
    if "chart" in kind or kind in {"treemap", "pie", "donut", "gauge"}:
        bars = "".join("<i></i>" for _ in range(5))
        return f'{title_html}<div class="chart-skeleton" aria-hidden="true">{bars}</div>'
    if kind == "actionbutton":
        label = visual.title or "Action"
        return f'<button type="button" disabled title="Action target was not extracted">{_esc(label)}</button>'
    return f'{title_html}<span class="visual-type">{_esc(visual.visual_type)}</span>'


def _render_visual(visual: Visual, page: Page) -> str:
    if visual.hidden:
        return ""
    style = (
        f"left:{_pct(visual.x, page.width)};"
        f"top:{_pct(visual.y, page.height)};"
        f"width:{_pct(visual.width, page.width)};"
        f"height:{_pct(visual.height, page.height)};"
        f"z-index:{max(-32768, min(32767, int(visual.z)))};"
    )
    classes = f"visual {_visual_class(visual.visual_type)}"
    body = _render_visual_body(visual)
    bindings = _render_bindings(visual)
    return (
        f'<div class="{classes}" style="{style}" data-visual-type="{_esc(visual.visual_type)}"'
        f' title="{_esc(visual.name)}"><div class="visual-inner">{body}{bindings}</div></div>'
    )


def _render_page(page: Page, page_id: str, active: bool) -> str:
    aspect = _pct(page.height, page.width) if page.width > 0 else "56.25%"
    visuals = "".join(_render_visual(v, page) for v in page.visuals)
    hidden_count = sum(1 for v in page.visuals if v.hidden)
    visible_count = len(page.visuals) - hidden_count
    badge = '<span class="badge">hidden page</span>' if page.hidden else ""
    hidden_attr = "" if active else " hidden"
    return (
        f'<section class="report-page{" active" if active else ""}" id="{_esc(page_id)}"'
        f' role="tabpanel" data-hidden-page="{str(page.hidden).lower()}"{hidden_attr}>'
        '<div class="page-toolbar">'
        f"<h2>{_esc(page.display_name)}{badge}</h2>"
        f'<span class="page-meta">{int(page.width)} × {int(page.height)} px · '
        f"{visible_count} visible visual{'s' if visible_count != 1 else ''}"
        f"{f' · {hidden_count} hidden' if hidden_count else ''}</span>"
        "</div>"
        '<div class="page-frame"><div class="page-canvas">'
        f'<div class="page-spacer" style="padding-top:{aspect};"></div>{visuals}'
        "</div></div></section>"
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
        '<section class="card-section"><h2>Semantic metadata</h2><div class="card"><table>'
        "<thead><tr><th>Table</th><th>Columns</th><th>Measures</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table></div></section>"
    )


def _pill(classification: str) -> str:
    return f'<span class="fidelity-pill fidelity-{_esc(classification)}">{_esc(classification)}</span>'


def _render_fidelity_report(fidelity: FidelityReport) -> str:
    dimension_rows = "".join(
        f"<tr><td>{_esc(d.label)}</td><td>{_pill(d.classification)}</td><td>{_esc(d.reason)}</td></tr>"
        for d in fidelity.dimensions
    )
    if fidelity.visuals:
        visual_rows = "".join(
            f"<tr><td>{_esc(v.visual_type)}</td><td>{_pill(v.classification)}</td>"
            f"<td>{v.count}</td><td>{_esc(v.reason)}</td></tr>"
            for v in fidelity.visuals
        )
        visual_table = (
            "<table><thead><tr><th>Visual type</th><th>Classification</th><th>Count</th>"
            f"<th>Reason</th></tr></thead><tbody>{visual_rows}</tbody></table>"
        )
    else:
        visual_table = "<p>No rendered visuals to classify.</p>"
    not_rendered = ""
    if fidelity.hidden_visual_count or fidelity.hidden_page_count:
        not_rendered = (
            f"<p>Not rendered at all: <strong>{fidelity.hidden_visual_count}</strong> hidden visual(s), "
            f"<strong>{fidelity.hidden_page_count}</strong> hidden page(s).</p>"
        )
    return (
        '<section class="card-section"><h2>Conversion fidelity report</h2><div class="card">'
        "<h3>Report-wide features</h3>"
        f"<table><thead><tr><th>Feature</th><th>Classification</th><th>Reason</th></tr></thead>"
        f"<tbody>{dimension_rows}</tbody></table>"
        "<h3>Visual families</h3>"
        f"{visual_table}{not_rendered}"
        "</div></section>"
    )


def _render_resources(report: PbixReport) -> str:
    if not report.static_resources:
        return ""
    items = "".join(f"<li><code>{_esc(name)}</code></li>" for name in report.static_resources)
    return '<section class="card-section"><h2>Static resources</h2>' f'<div class="card"><ul>{items}</ul></div></section>'


def render_html(report: PbixReport, fidelity: FidelityReport | None = None) -> str:
    """Return a complete, self-contained interactive HTML document."""
    if fidelity is None:
        fidelity = build_fidelity_report(report)
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    version = f" · layout version {_esc(report.version)}" if report.version else ""
    page_ids = [_slug(page.display_name, i) for i, page in enumerate(report.pages)]
    first_visible = next((i for i, page in enumerate(report.pages) if not page.hidden), 0)
    tabs = []
    for i, (page, page_id) in enumerate(zip(report.pages, page_ids)):
        hidden_class = " hidden-tab" if page.hidden else ""
        selected = i == first_visible
        tabs.append(
            f'<button class="page-tab{hidden_class}" type="button" role="tab" data-page="{_esc(page_id)}"'
            f' aria-controls="{_esc(page_id)}" aria-selected="{str(selected).lower()}" tabindex="{0 if selected else -1}">'
            f"{_esc(page.display_name)}</button>"
        )
    hidden_pages = sum(1 for page in report.pages if page.hidden)
    hidden_toggle = (
        '<button class="hidden-toggle" type="button" aria-pressed="false">Show hidden pages</button>'
        if hidden_pages else ""
    )
    summary = (
        '<ul class="summary">'
        f"<li><strong>{len(report.pages)}</strong> pages</li>"
        f"<li><strong>{report.visual_count}</strong> visuals</li>"
        f"<li><strong>{len(report.tables)}</strong> semantic tables</li>"
        f"<li><strong>{len(report.static_resources)}</strong> resources</li></ul>"
    )
    if report.pages:
        pages = "".join(_render_page(page, page_ids[i], i == first_visible) for i, page in enumerate(report.pages))
    else:
        pages = '<div class="card">No report pages found.</div>'
    fidelity_banner = (
        '<aside class="fidelity-banner" role="status"><strong>Layout-only compatibility mode</strong>'
        "This PBIX exposed report layout metadata but no portable row data. Page switching works offline, "
        "but chart values, slicer choices, cross-filtering, and measure results cannot be reconstructed from layout metadata alone."
        "</aside>"
    )
    return (
        "<!DOCTYPE html>\n"
        '<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{_esc(report.source_name)} — pbix2html</title><style>{_CSS}</style></head><body>"
        '<header class="app-header"><div class="header-inner"><div class="title-row"><div>'
        f"<h1>{_esc(report.source_name)}</h1><p class=\"subtitle\">Portable Power BI layout{version}</p>"
        f'</div>{summary}</div><nav class="page-tabs" role="tablist" aria-label="Report pages">{"".join(tabs)}{hidden_toggle}</nav>'
        "</div></header>"
        f"<main>{fidelity_banner}{pages}{_render_tables(report)}{_render_resources(report)}"
        f"{_render_fidelity_report(fidelity)}</main>"
        f"<footer>Generated by pbix2html on {generated}. No external runtime dependencies.</footer><script>{_JS}</script>"
        "</body></html>\n"
    )
