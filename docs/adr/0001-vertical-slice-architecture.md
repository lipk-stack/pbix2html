# ADR 0001: Vertical-slice architecture for the first iteration

## Status

Accepted.

## Context

The full product brief (see conversation/PR history) specifies an enormous surface: multi-strategy PBIX ingestion, a full DAX compiler, a plugin visual-translator registry, RLS-aware export, a Tauri/Rust/.NET desktop app, and more. Building any single piece of that in isolation without an end-to-end working path risks producing exactly what the brief explicitly forbids: architecture diagrams and empty interfaces with no working code.

## Decision

Build one real, narrow, fully-tested vertical slice first (master brief Section 56, Phase 0/1; Section 67, first coding milestone):

```
structured DIR fixture → DIR schema → semantic engine → portable runtime → single-file HTML
```

Specific choices:

1. **pnpm workspaces monorepo**, packages split by responsibility (`dir-schema`, `semantic-engine`, `portable-runtime`, `html-exporter`, `apps/cli`) so a future PBIX/PBIP adapter is an additional package that produces `DashboardIR`, not a rewrite.
2. **No UI framework (no React) for the exported runtime.** The visual surface (card, bar chart, slicer) is small; plain DOM + inline SVG is less code, no bundle weight, and no framework version to keep offline-safe. Revisit once table/matrix virtualization is in scope.
3. **esbuild** to bundle the runtime into a single inline `<script>` — fast, zero-config IIFE output, no reason to add webpack/rollup at this scale.
4. **Plain in-memory row arrays**, not Arrow/DuckDB-Wasm, for the semantic engine. Correct and fully unit-testable at fixture scale; explicitly flagged in `ARCHITECTURE.md`/`ROADMAP.md` as a Phase 3+ concern once real imported-model row counts are in play.
5. **A typed measure-expression IR instead of a DAX text parser.** A real DAX lexer/parser/binder is a compiler project in its own right (Section 8). Faking it with regex/string substitution — which the brief explicitly forbids — would be worse than not having it. This slice defines the target IR a DAX front-end will compile into, and implements genuine execution semantics (relationship-aware filter propagation, `CALCULATE`-style override) against it now, so the runtime and exporter don't need to change when the DAX front-end lands.
6. **CSP as an enforcement mechanism, not just a claim.** The exporter sets `connect-src 'none'` and inlines everything, so "no network dependency" is verifiable by a browser, not just documentation.
7. **Explicit interaction graph for cross-filtering**, not "filter every visual on every click" — required by Section 17, and by far the easiest requirement to accidentally violate with a naive implementation.

## Consequences

- Every claim in `README.md`/`COMPATIBILITY.md` is backed by a passing test (`vitest` for engine/exporter logic, Playwright for the real offline browser acceptance flow) — no aspirational feature descriptions.
- The slice deliberately does not attempt multi-page navigation, bookmarks, most visual types, or any DAX beyond a handful of aggregations — those are Phase 2+ per `ROADMAP.md`, not missing pieces of Phase 1.
- Ingestion (PBIX/PBIP) is completely out of scope for this iteration; see ADR 0002 for the research that will inform which adapter gets built first.
