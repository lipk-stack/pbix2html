import type {
  AggregationFunction,
  ColumnRef,
  FilterExpressionIR,
  MeasureExpressionIR,
  MeasureIR,
} from "@pbix2html/dir-schema";
import type { TableStore } from "./table-store.js";
import { allowedRowIndices, type ColumnFilter, type FilterContext, overrideFilters } from "./filter-context.js";

export class MeasureEvaluator {
  private readonly measuresByName = new Map<string, MeasureIR>();

  constructor(private readonly store: TableStore) {
    for (const measure of store.model.measures) {
      this.measuresByName.set(measure.name, measure);
    }
  }

  evaluate(measureName: string, ctx: FilterContext): number | null {
    const measure = this.measuresByName.get(measureName);
    if (!measure) throw new Error(`Unknown measure: ${measureName}`);
    return this.evaluateExpression(measure.expression, ctx, new Set([measureName]));
  }

  /** Virtual GROUPBY: evaluates `measureName` once per distinct value of `groupBy`, each under a CALCULATE-style override. */
  evaluateGroupedBy(
    measureName: string,
    groupBy: ColumnRef,
    ctx: FilterContext,
  ): { key: unknown; value: number | null }[] {
    const indices = allowedRowIndices(ctx, this.store, groupBy.table);
    const rows = this.store.rows(groupBy.table);
    const keys = [...new Set(indices.map((i) => rows[i]?.[groupBy.column]))];

    return keys.map((key) => {
      const groupCtx = overrideFilters(this.store, ctx, [
        { table: groupBy.table, column: groupBy.column, values: [key] },
      ]);
      return { key, value: this.evaluate(measureName, groupCtx) };
    });
  }

  private evaluateExpression(
    expr: MeasureExpressionIR,
    ctx: FilterContext,
    visiting: Set<string>,
  ): number | null {
    switch (expr.kind) {
      case "aggregation":
        return this.evaluateAggregation(expr.fn, expr.column, ctx);

      case "divide": {
        const numerator = this.evaluateExpression(expr.numerator, ctx, visiting);
        const denominator = this.evaluateExpression(expr.denominator, ctx, visiting);
        if (denominator === null || denominator === 0) return expr.alternateResult ?? null;
        if (numerator === null) return null;
        return numerator / denominator;
      }

      case "measureRef": {
        if (visiting.has(expr.measure)) {
          throw new Error(`Circular measure reference detected at "${expr.measure}"`);
        }
        const referenced = this.measuresByName.get(expr.measure);
        if (!referenced) throw new Error(`Unknown measure reference: ${expr.measure}`);
        return this.evaluateExpression(referenced.expression, ctx, new Set([...visiting, expr.measure]));
      }

      case "calculate": {
        const overrides: ColumnFilter[] = expr.filters.flatMap(filterExpressionToColumnFilters);
        const newCtx = overrideFilters(this.store, ctx, overrides);
        return this.evaluateExpression(expr.expression, newCtx, visiting);
      }

      case "binaryOp": {
        const left = this.evaluateExpression(expr.left, ctx, visiting);
        const right = this.evaluateExpression(expr.right, ctx, visiting);
        if (left === null || right === null) return null;
        switch (expr.op) {
          case "+":
            return left + right;
          case "-":
            return left - right;
          case "*":
            return left * right;
          case "/":
            return right === 0 ? null : left / right;
        }
      }
    }
  }

  private evaluateAggregation(
    fn: AggregationFunction,
    column: ColumnRef | undefined,
    ctx: FilterContext,
  ): number | null {
    if (!column) {
      throw new Error(`Aggregation ${fn} requires a column reference (COUNTROWS uses column.table only)`);
    }
    const indices = allowedRowIndices(ctx, this.store, column.table);
    if (fn === "COUNTROWS") return indices.length;

    const rows = this.store.rows(column.table);
    const values = indices
      .map((i) => rows[i]?.[column.column])
      .filter((v): v is number => typeof v === "number");

    switch (fn) {
      case "SUM":
        return values.length === 0 ? 0 : values.reduce((a, b) => a + b, 0);
      case "AVERAGE":
        return values.length === 0 ? null : values.reduce((a, b) => a + b, 0) / values.length;
      case "MIN":
        return values.length === 0 ? null : Math.min(...values);
      case "MAX":
        return values.length === 0 ? null : Math.max(...values);
      case "COUNT":
        return values.length;
      case "DISTINCTCOUNT":
        return new Set(indices.map((i) => rows[i]?.[column.column])).size;
      default:
        throw new Error(`Unsupported aggregation function: ${fn satisfies never}`);
    }
  }
}

export function filterExpressionToColumnFilters(expr: FilterExpressionIR): ColumnFilter[] {
  switch (expr.operator) {
    case "in":
    case "equals":
      if (!expr.target) throw new Error("Filter expression missing target column");
      return [{ table: expr.target.table, column: expr.target.column, values: expr.values ?? [] }];
    case "and":
      return (expr.operands ?? []).flatMap(filterExpressionToColumnFilters);
    default:
      throw new Error(
        `Filter operator "${expr.operator}" is not yet supported by the portable semantic engine`,
      );
  }
}
