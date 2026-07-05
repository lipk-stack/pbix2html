import type { TableStore } from "./table-store.js";

export interface ColumnFilter {
  table: string;
  column: string;
  values: unknown[];
}

export interface FilterContext {
  /** The column filters this context was built from — kept so CALCULATE-style overrides can replace one and recompute. */
  filters: ColumnFilter[];
  /** Row indices visible per table after direct filters + relationship propagation. `null` = unrestricted. */
  allowed: Map<string, Set<number> | null>;
}

/**
 * Relationship convention: `fromTable`/`fromColumn` is the "one" side (e.g. a
 * dimension table's key), `toTable`/`toColumn` is the "many" side (e.g. a fact
 * table's foreign key) — matching typical Power BI dimension → fact modeling.
 * Filters always propagate one → many; they propagate many → one only when
 * `crossFilterDirection` is "both".
 */
export function buildFilterContext(store: TableStore, filters: ColumnFilter[]): FilterContext {
  const allowed = new Map<string, Set<number> | null>();
  for (const name of store.tableNames()) allowed.set(name, null);

  const worklist: string[] = [];

  for (const filter of filters) {
    const rows = store.rows(filter.table);
    const valueSet = new Set(filter.values);
    const matched = new Set<number>();
    rows.forEach((row, index) => {
      if (valueSet.has(row[filter.column])) matched.add(index);
    });
    const existing = allowed.get(filter.table) ?? null;
    const combined = existing === null ? matched : intersectSets(existing, matched);
    allowed.set(filter.table, combined);
    worklist.push(filter.table);
  }

  while (worklist.length > 0) {
    const table = worklist.shift()!;
    const allowedRows = allowed.get(table);
    if (!allowedRows) continue;

    for (const rel of store.relationshipsFrom(table)) {
      const changed = propagate(store, allowed, table, rel.fromColumn, allowedRows, rel.toTable, rel.toColumn);
      if (changed) worklist.push(rel.toTable);
    }

    for (const rel of store.relationshipsTo(table)) {
      if (rel.crossFilterDirection !== "both") continue;
      const changed = propagate(store, allowed, table, rel.toColumn, allowedRows, rel.fromTable, rel.fromColumn);
      if (changed) worklist.push(rel.fromTable);
    }
  }

  return { filters, allowed };
}

/** CALCULATE-style filter override: replace filters on the same column(s), then recompute the whole context. */
export function overrideFilters(
  store: TableStore,
  ctx: FilterContext,
  overrides: ColumnFilter[],
): FilterContext {
  const merged = ctx.filters.filter(
    (existing) => !overrides.some((o) => o.table === existing.table && o.column === existing.column),
  );
  merged.push(...overrides);
  return buildFilterContext(store, merged);
}

export function allowedRowIndices(ctx: FilterContext, store: TableStore, table: string): number[] {
  const set = ctx.allowed.get(table);
  if (set === null || set === undefined) {
    return store.rows(table).map((_, i) => i);
  }
  return [...set];
}

function propagate(
  store: TableStore,
  allowed: Map<string, Set<number> | null>,
  sourceTable: string,
  sourceColumn: string,
  sourceAllowed: Set<number>,
  targetTable: string,
  targetColumn: string,
): boolean {
  const sourceRows = store.rows(sourceTable);
  const keySet = new Set<unknown>();
  for (const index of sourceAllowed) {
    keySet.add(sourceRows[index]?.[sourceColumn]);
  }

  const targetRows = store.rows(targetTable);
  const matched = new Set<number>();
  targetRows.forEach((row, index) => {
    if (keySet.has(row[targetColumn])) matched.add(index);
  });

  const existing = allowed.get(targetTable) ?? null;
  const combined = existing === null ? matched : intersectSets(existing, matched);

  if (existing !== null && setsEqual(existing, combined)) return false;
  allowed.set(targetTable, combined);
  return true;
}

function intersectSets(a: Set<number>, b: Set<number>): Set<number> {
  const [smaller, larger] = a.size <= b.size ? [a, b] : [b, a];
  const result = new Set<number>();
  for (const value of smaller) if (larger.has(value)) result.add(value);
  return result;
}

function setsEqual(a: Set<number>, b: Set<number>): boolean {
  if (a.size !== b.size) return false;
  for (const value of a) if (!b.has(value)) return false;
  return true;
}
