# DAX support

## This is not a DAX parser

`packages/dir-schema`'s `MeasureExpressionIR` is a small, **typed, non-textual** expression tree:

```ts
type MeasureExpressionIR =
  | { kind: "aggregation"; fn: AggregationFunction; column?: ColumnRef }
  | { kind: "divide"; numerator: ...; denominator: ...; alternateResult?: number }
  | { kind: "measureRef"; measure: string }
  | { kind: "calculate"; expression: ...; filters: FilterExpressionIR[] }
  | { kind: "binaryOp"; op: "+" | "-" | "*" | "/"; left: ...; right: ... };
```

A future DAX front-end (lexer → parser → AST → name binder → type analyzer → dependency resolver → this IR) is real, separately-scoped compiler work — see the master brief's Section 8 pipeline. Nothing in this repository converts DAX text today; the fixture in `fixtures/sales-report/report.json` authors this IR by hand, exactly as a compiler backend would emit it.

This is deliberately **not** "replace DAX function names with SQL/JS via regex" — the evaluator in `packages/semantic-engine/src/measure-evaluator.ts` implements actual row/filter-context semantics: relationship propagation (`packages/semantic-engine/src/filter-context.ts`), `CALCULATE`-style filter override (replace-then-recompute, not blind AND), and measure-reference resolution with cycle detection.

## What's evaluated today

| Function / construct | Status | Notes |
|---|---|---|
| `SUM` | `EXACT` | over the currently visible (filtered) rows |
| `AVERAGE` | `EXACT` | |
| `COUNT` | `EXACT` | counts non-null numeric values in the column |
| `COUNTROWS` | `EXACT` | via `column.table`, ignores `column.column` |
| `DISTINCTCOUNT` | `EXACT` | |
| `MIN` / `MAX` | `EXACT` | |
| `DIVIDE` | `EXACT` | returns `alternateResult` (or `null`) on a zero/blank denominator, matching DAX `DIVIDE` semantics rather than throwing |
| `CALCULATE` (filter override) | `SEMANTICALLY_EQUIVALENT` | supports `in`/`equals`/`and` filter expressions; overrides only the columns named, recomputes full propagation — not full `CALCULATE` (no `ALL`/`ALLEXCEPT`/`REMOVEFILTERS`/`KEEPFILTERS` modifiers) |
| Measure references | `EXACT` | with circular-reference detection |
| Relationship propagation | `EXACT` for the modeled subset | one-side → many-side always; many-side → one-side only when `crossFilterDirection: "both"` — see `ARCHITECTURE.md` |

## Explicitly unsupported (not silently approximated)

`FILTER`, `ALL`, `ALLEXCEPT`, `ALLSELECTED`, `REMOVEFILTERS`, `KEEPFILTERS`, `VALUES`, `DISTINCT`, `SELECTEDVALUE`, `HASONEVALUE`, `ISFILTERED`, `ISCROSSFILTERED`, `SUMX`/`AVERAGEX`/`MINX`/`MAXX`/`RANKX` and other iterators, `TOPN`, `SUMMARIZE`/`SUMMARIZECOLUMNS`/`ADDCOLUMNS`/`SELECTCOLUMNS`, `TREATAS`, `USERELATIONSHIP`, `CROSSFILTER`, `RELATED`/`RELATEDTABLE`, time intelligence, calculation groups, dynamic format strings.

Calling `MeasureEvaluator` with an expression tree that uses an unsupported `FilterExpressionIR.operator` throws immediately (`measure-evaluator.ts`'s `filterExpressionToColumnFilters`) rather than silently producing a wrong number — consistent with the "never fake fidelity" principle.

## Virtual `SUMMARIZE`/grouping

`MeasureEvaluator.evaluateGroupedBy` is a minimal, hand-written substitute for `SUMMARIZECOLUMNS`: it enumerates the distinct values of one grouping column under the current filter context and re-evaluates the measure once per value via a `CALCULATE`-style override. It does not support multi-column grouping, and is `SEMANTICALLY_EQUIVALENT` rather than `EXACT` against real `SUMMARIZECOLUMNS` (no shared-subexpression optimization, no multi-level totals/subtotals).
