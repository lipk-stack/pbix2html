# Architecture

This document describes what exists today. For the full target architecture (multi-strategy PBIX ingestion, DAX compiler, RLS-aware export, desktop app, etc.), see the phased plan in [ROADMAP.md](./ROADMAP.md) — this vertical slice is Phase 0/1 of that plan.

## Current data flow

```
                 ┌──────────────────────────────┐
                 │  DIR fixture (JSON, trusted)  │   fixtures/sales-report/report.json
                 └──────────────┬────────────────┘
                                │  parsed against @pbix2html/dir-schema types
                 ┌──────────────▼────────────────┐
                 │        DashboardIR             │   packages/dir-schema
                 └──────────────┬────────────────┘
                                │
        ┌───────────────────────┼────────────────────────┐
        │                       │                         │
┌───────▼────────┐   ┌──────────▼──────────┐   ┌──────────▼──────────┐
│  TableStore    │   │  FilterContext        │   │  MeasureEvaluator    │
│  (row storage) │──▶│  (relationship-aware  │──▶│  (aggregation +      │
│                │   │   filter propagation) │   │   CALCULATE + DIVIDE)│
└────────────────┘   └───────────────────────┘   └──────────┬───────────┘
                     packages/semantic-engine                │
                                                              │
                 ┌────────────────────────────────────────────▼──┐
                 │            DashboardRuntime                    │   packages/portable-runtime
                 │  FilterState (slicer + cross-filter)           │
                 │  renderers: card / bar+column / slicer         │
                 │  interaction graph (explicit filter edges only)│
                 └────────────────────────┬────────────────────────┘
                                          │  bundled via esbuild (bootstrap.ts)
                 ┌────────────────────────▼────────────────────────┐
                 │           exportSingleFileHtml()                 │   packages/html-exporter
                 │  inlines: runtime JS, CSS, DIR data as JSON,     │
                 │  fidelity report; sets a CSP that blocks         │
                 │  every network origin (connect-src 'none')       │
                 └────────────────────────┬────────────────────────┘
                                          │
                                 dashboard.html (single file, offline)
```

`apps/cli` is a thin wrapper: read a DIR JSON file → `exportSingleFileHtml()` → write the result.

## Package responsibilities

- **`@pbix2html/dir-schema`** — the Dashboard Intermediate Representation (DIR) types. Everything downstream is written against this schema, not against Power BI's internal formats, so a future PBIX/PBIP adapter only has to produce a `DashboardIR` value to plug into the rest of the pipeline unchanged.
- **`@pbix2html/semantic-engine`** — `TableStore` holds row data per table; `buildFilterContext` computes, per table, which row indices are visible after direct column filters propagate through active relationships (dimension → fact always; fact → dimension only when `crossFilterDirection: "both"`); `MeasureEvaluator` walks a small structured measure-expression tree (`SUM`/`AVERAGE`/`COUNT`/`DISTINCTCOUNT`/`MIN`/`MAX`, `DIVIDE`, `CALCULATE`-style filter override, measure references) against that context. See [DAX_SUPPORT.md](./DAX_SUPPORT.md) for exactly what this does and doesn't cover.
- **`@pbix2html/portable-runtime`** — a dependency-free runtime: plain DOM manipulation and inline SVG, no chart library, no UI framework. `FilterState` distinguishes slicer selections (apply to every visual) from cross-filter clicks (apply only to visuals the `InteractionGraph` explicitly wires as `mode: "filter"` targets) — this is what stops one click from silently filtering unrelated visuals (master-prompt requirement, Section 17).
- **`@pbix2html/html-exporter`** — bundles `portable-runtime`'s `bootstrap.ts` entry point with esbuild (IIFE, minified, no external chunks), inlines the CSS, serializes the `DashboardIR` (including the row data) as JSON into a `<script type="application/json">` tag, and renders a fidelity report `<details>` block from `ir.compatibility`. The emitted page's CSP (`default-src 'none'; connect-src 'none'; script-src/style-src 'unsafe-inline'`) makes "no network dependency" a browser-enforced property of the artifact, not just a convention.

## Why these technology choices (see ADRs for detail)

- **No React / no UI framework** — the visual surface today (card, bar chart, slicer) is small enough that plain DOM/SVG is less code and zero runtime weight than shipping a framework in every exported file. Revisit if/when table/matrix virtualization needs a component model.
- **esbuild** for bundling — fast, zero-config IIFE output, already needed transitively; no reason to add webpack/rollup for this scope.
- **No DuckDB-Wasm / Arrow yet** — the semantic engine operates on plain JS arrays of row objects. This is correct for the fixture's row counts and lets the filter-propagation logic stay simple and fully unit-tested; it will not scale to large imported models and is called out as a Phase 3+ concern in the roadmap (Section 49/10 of the master brief: columnar storage, dictionary encoding, worker execution).
- **Structured measure IR instead of a DAX parser** — building a real DAX lexer/parser/binder (master brief Section 8) is a substantial compiler project on its own. Rather than fake it with string substitution, this slice defines a small **typed** expression tree that a future DAX front-end can compile *into*, and implements real (if partial) execution semantics — including relationship propagation and `CALCULATE`-style filter override — against that tree. See [DAX_SUPPORT.md](./DAX_SUPPORT.md).

## Where ingestion attaches (not yet built)

An ingestion adapter's only job is to produce a `DashboardIR`. Per the research in [docs/adr/0002-pbix-ingestion-strategy.md](./docs/adr/0002-pbix-ingestion-strategy.md):

- A **PBIP/PBIR/TMDL reader** (public, documented, git-friendly formats) is the highest-confidence next step and does not require reverse-engineering anything.
- Direct **`.pbix` parsing** is undocumented Microsoft binary/OPC-container format with no supported read API; it is scoped as an experimental, sandboxed, best-effort adapter behind the same `DashboardIR` contract, not a foundation to build on.
