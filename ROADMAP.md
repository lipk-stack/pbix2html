# Roadmap

Phased against the full product vision. Status reflects what is actually implemented and tested in this repository today — not intent.

## Phase 0 — Research and spike ✅ done (this iteration)

- [x] Researched current PBIX/PBIP/PBIR/TMDL format status (see [docs/adr/0002-pbix-ingestion-strategy.md](./docs/adr/0002-pbix-ingestion-strategy.md))
- [x] Defined the DIR (Dashboard Intermediate Representation) schema
- [x] One structured-input → HTML conversion proof of concept
- [x] Standalone single-file HTML experiment, verified offline in a real browser

## Phase 1 — Vertical slice ✅ done for the scope below, ⬜ not yet for the rest

Done:
- [x] One report, one page, `structured-fixture` source only
- [x] Card, bar/column chart, slicer
- [x] Basic measures: `SUM`, `AVERAGE`, `COUNT`, `COUNTROWS`, `DISTINCTCOUNT`, `MIN`, `MAX`, `DIVIDE`, `CALCULATE`-style filter override
- [x] Cross-filtering via an explicit interaction graph (not a blind "filter everything" click handler)
- [x] Standalone single-file HTML, CSP-enforced offline, verified with Playwright against a real generated file

Not yet:
- [ ] Multiple pages / page navigation / bookmarks
- [ ] Table, matrix, pie/donut, line/area, KPI, and remaining native visual families
- [ ] Report-level and page-level static filters (only interactive slicer + cross-filter state is wired today)
- [ ] Multi-select slicers (current slicer is single-select-or-clear)
- [ ] Themes/formatting beyond title + numberFormat + currency/percent detection

## Phase 2 — Core MVP (not started)

- [ ] PBIP/PBIR/TMDL reader → DIR adapter (highest-confidence next milestone; public documented formats)
- [ ] Multiple pages, relationships beyond two dimension tables, measure dependency graph
- [ ] Offline package export (multi-file `dashboard-package/` + zip), not just single-file HTML
- [ ] Machine-readable compatibility/fidelity report as a standalone JSON artifact (today it's inline HTML only)

## Phase 3 — Semantic depth (not started)

- [ ] Real DAX lexer/parser/AST/binder (see [DAX_SUPPORT.md](./DAX_SUPPORT.md) for why the current structured-IR evaluator is not this)
- [ ] Inactive relationships, `USERELATIONSHIP`, iterators (`SUMX`/`RANKX`/etc.), time intelligence, calculation groups

## Phase 4 — Enterprise conversion (not started)

- [ ] RLS-safe per-role export (see [SECURITY.md](./SECURITY.md) — this is a hard requirement before this tool touches any row-level-secured model)
- [ ] Service-assisted (Fabric/Power BI REST) adapter, opt-in, audited
- [ ] Batch conversion, richer CLI, policy controls

## Phase 5 — Advanced visuals (not started)

Maps, matrix depth, custom visual adapters, drill-through, report-page tooltips.

## Phase 6 — Scale and hardening (not started)

Columnar/worker-based data engine for large models, fuzzing the (future) binary PBIX parser, browser matrix, signed releases, SBOM.

## First genuine PBIX ingestion pathway — not yet started

`.pbix` itself has no public read API (see the ADR). The plan is: PBIP/PBIR/TMDL reader first (Phase 2), since it reaches the same DIR output for anyone who saves their report as a `.pbip` project, and gives the whole downstream pipeline (already built and tested) a real, non-fixture input before attempting the harder, less-supported direct-PBIX or Desktop-bridge strategies from the master brief's ingestion matrix.
