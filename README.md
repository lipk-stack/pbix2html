# PBIX2HTML Studio

A conversion platform that turns Power BI reports into portable, offline, interactive HTML dashboards — without a Power BI runtime, an embed token, or a network connection.

**Status: early vertical slice (Phase 0/1 of the roadmap in [ROADMAP.md](./ROADMAP.md)).** There is no `.pbix` ingestion yet. What exists today is a real, tested, end-to-end pipeline from a structured intermediate representation to a working offline dashboard — the foundation the ingestion adapters will plug into. See [COMPATIBILITY.md](./COMPATIBILITY.md) for exactly what is and isn't supported right now, and do not assume anything beyond that list works.

## What works today

```
structured DIR fixture (JSON)
  → semantic engine (relationship-aware filter propagation, measure evaluation)
  → portable runtime (DOM/SVG renderers, cross-filter interaction graph)
  → single-file offline HTML (CSP-enforced, no network, no CDN)
```

Try it:

```bash
pnpm install
pnpm --filter @pbix2html/cli run start convert-fixture fixtures/sales-report/report.json --output dashboard.html
```

Open `dashboard.html` directly from disk (`file://`), disconnect from the network, and it still works: select a year in the slicer, click a category bar to cross-filter the revenue and average-selling-price cards, click again to clear it. `tests/e2e/dashboard.spec.ts` drives exactly this flow in a real (offline) browser.

## Repository layout

```
packages/
  dir-schema/         Dashboard Intermediate Representation (DIR) — the vendor-neutral schema everything else is built on
  semantic-engine/     Relationship-aware filter-context propagation + a small structured measure-expression evaluator
  portable-runtime/    Dependency-free DOM/SVG runtime: card, bar/column chart, slicer, interaction graph
  html-exporter/       Bundles the runtime + data into a single offline HTML file (esbuild, no CDN, strict CSP)
apps/
  cli/                 `pbix2html convert-fixture <dir.json> --output <dashboard.html>`
fixtures/
  sales-report/        The DIR fixture used by the CLI demo and the e2e acceptance test
tests/e2e/             Playwright test that opens the generated HTML offline and drives real interactions
docs/adr/              Architecture decision records
```

## Documentation

- [ARCHITECTURE.md](./ARCHITECTURE.md) — how the pieces fit together today, and where PBIX/PBIP ingestion will attach
- [ROADMAP.md](./ROADMAP.md) — phased plan against the full product vision, with honest status per phase
- [COMPATIBILITY.md](./COMPATIBILITY.md) — fidelity classification for every visual type, DAX function, and ingestion path
- [DAX_SUPPORT.md](./DAX_SUPPORT.md) — exactly which measure semantics the engine evaluates (and why it is not a DAX parser yet)
- [SECURITY.md](./SECURITY.md) — threat model status, and the RLS/security limitations of the current exporter
- [docs/adr/](./docs/adr/) — ADRs for the ingestion-format research and the vertical-slice architecture choices

## Development

```bash
pnpm install
pnpm typecheck
pnpm test        # vitest — unit tests for the semantic engine, filter state, and exporter
pnpm test:e2e    # playwright — offline acceptance test against a real generated dashboard.html
```
