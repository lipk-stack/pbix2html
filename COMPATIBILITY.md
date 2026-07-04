# Compatibility

Fidelity classifications use the taxonomy: `EXACT`, `SEMANTICALLY_EQUIVALENT`, `VISUALLY_EQUIVALENT`, `APPROXIMATED`, `SNAPSHOTTED`, `CONNECTED_RUNTIME_REQUIRED`, `UNSUPPORTED`, `BLOCKED_FOR_SECURITY`, `BLOCKED_FOR_LICENSING`.

Every export also carries this table inline, computed from the input `DashboardIR`'s own `compatibility` field (see the `<details class="pbix-fidelity-report">` block in generated HTML) — this document describes the engine's *ceiling*, not a specific report's result.

## Ingestion adapters

| Adapter | Status | Classification |
|---|---|---|
| Structured DIR JSON fixture | Implemented | n/a (trusted, hand-authored test input) |
| PBIP / PBIR / TMDL reader | Not implemented | Target: `PUBLIC_DOCUMENTED_FORMAT` — planned next (Phase 2) |
| Direct `.pbix` binary parsing | Not implemented | `EXPERIMENTAL_INTEROPERABILITY` — no public read API exists; see ADR 0002 |
| Power BI Desktop bridge | Not implemented | `SUPPORTED_DESKTOP_WORKFLOW` at best, contingent on what Desktop actually exposes locally |
| Service-assisted (Fabric/Power BI REST) | Not implemented | `PUBLIC_SUPPORTED_API` for the parts that use documented REST/XMLA endpoints; opt-in only |

## Visuals

| Normalized visual type | Status | Classification |
|---|---|---|
| Card | Implemented | `EXACT` for `SUM`/`AVERAGE`/`COUNT`/`DISTINCTCOUNT`/`MIN`/`MAX`/`DIVIDE` measures |
| Bar / column chart | Implemented (single category, single measure) | `EXACT` within that scope |
| Slicer | Implemented (single-select, single field) | `SEMANTICALLY_EQUIVALENT` (Power BI slicers default to multi-select) |
| Table, matrix, pie/donut, line/area, KPI, multi-row card, buttons, images, shapes, maps, custom visuals | Not implemented | `UNSUPPORTED` |
| Bookmarks, page navigation, drill-through, tooltips | Not implemented | `UNSUPPORTED` |

## Interactions

| Interaction | Status |
|---|---|
| Slicer selection → filters every visual on the page | Implemented |
| Explicit cross-filter (`mode: "filter"` edges in the interaction graph) | Implemented |
| Highlight (`mode: "highlight"`) | Not implemented — treated as absent |
| Navigate / drill | Not implemented |
| Report-level / page-level static filters | Not implemented (only interactive state is wired into the runtime today) |

## DAX / measure semantics

See [DAX_SUPPORT.md](./DAX_SUPPORT.md) for the full function list. Summary: a fixed set of aggregations, `DIVIDE`, `CALCULATE` with `in`/`equals`/`and` filter overrides, and measure references are evaluated with real relationship-aware filter-context propagation. Everything else (iterators, time intelligence, calculation groups, `ALLSELECTED`/`ALLEXCEPT`/`REMOVEFILTERS`, virtual tables, inactive-relationship activation) is `UNSUPPORTED`.

## Security / RLS

No role-based or per-user export exists yet. See [SECURITY.md](./SECURITY.md) — **do not use this tool today to convert any model with row-level security**, since the current exporter has no concept of a security role and would embed whatever rows are in the DIR's `data.tables` verbatim.
