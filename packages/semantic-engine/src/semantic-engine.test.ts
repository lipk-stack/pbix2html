import { describe, expect, it } from "vitest";
import type { RelationshipIR, SemanticModelIR, TableDataIR } from "@pbix2html/dir-schema";
import { TableStore } from "./table-store.js";
import { buildFilterContext, overrideFilters } from "./filter-context.js";
import { MeasureEvaluator } from "./measure-evaluator.js";

const relationships: RelationshipIR[] = [
  {
    id: "rel-date-sales",
    fromTable: "Date",
    fromColumn: "DateKey",
    toTable: "Sales",
    toColumn: "DateKey",
    crossFilterDirection: "single",
    isActive: true,
    cardinality: "oneToMany",
  },
  {
    id: "rel-product-sales",
    fromTable: "Product",
    fromColumn: "ProductKey",
    toTable: "Sales",
    toColumn: "ProductKey",
    crossFilterDirection: "both",
    isActive: true,
    cardinality: "oneToMany",
  },
];

const model: SemanticModelIR = {
  tables: [
    { name: "Date", columns: [{ name: "DateKey", dataType: "number" }, { name: "Year", dataType: "number" }] },
    { name: "Product", columns: [{ name: "ProductKey", dataType: "number" }, { name: "Category", dataType: "string" }] },
    {
      name: "Sales",
      columns: [
        { name: "SalesKey", dataType: "number" },
        { name: "DateKey", dataType: "number" },
        { name: "ProductKey", dataType: "number" },
        { name: "Amount", dataType: "number" },
        { name: "Qty", dataType: "number" },
      ],
    },
  ],
  relationships,
  measures: [
    { name: "Revenue", table: "Sales", expression: { kind: "aggregation", fn: "SUM", column: { table: "Sales", column: "Amount" } } },
    { name: "Quantity", table: "Sales", expression: { kind: "aggregation", fn: "SUM", column: { table: "Sales", column: "Qty" } } },
    {
      name: "AverageSellingPrice",
      table: "Sales",
      expression: {
        kind: "divide",
        numerator: { kind: "measureRef", measure: "Revenue" },
        denominator: { kind: "measureRef", measure: "Quantity" },
        alternateResult: 0,
      },
    },
    {
      name: "RevenueForProductA",
      table: "Sales",
      expression: {
        kind: "calculate",
        expression: { kind: "measureRef", measure: "Revenue" },
        filters: [{ operator: "equals", target: { table: "Product", column: "Category" }, values: ["A"] }],
      },
    },
  ],
};

const data: TableDataIR[] = [
  { table: "Date", rows: [{ DateKey: 1, Year: 2023 }, { DateKey: 2, Year: 2024 }] },
  { table: "Product", rows: [{ ProductKey: 1, Category: "A" }, { ProductKey: 2, Category: "B" }] },
  {
    table: "Sales",
    rows: [
      { SalesKey: 1, DateKey: 1, ProductKey: 1, Amount: 100, Qty: 2 },
      { SalesKey: 2, DateKey: 1, ProductKey: 2, Amount: 200, Qty: 1 },
      { SalesKey: 3, DateKey: 2, ProductKey: 1, Amount: 50, Qty: 5 },
      { SalesKey: 4, DateKey: 2, ProductKey: 2, Amount: 25, Qty: 1 },
    ],
  },
];

function setup() {
  const store = new TableStore(model, data);
  const evaluator = new MeasureEvaluator(store);
  return { store, evaluator };
}

describe("MeasureEvaluator", () => {
  it("computes an unfiltered SUM measure across the whole fact table", () => {
    const { store, evaluator } = setup();
    const ctx = buildFilterContext(store, []);
    expect(evaluator.evaluate("Revenue", ctx)).toBe(375);
  });

  it("propagates a one-side (Date) filter down to the many-side fact table", () => {
    const { store, evaluator } = setup();
    const ctx = buildFilterContext(store, [{ table: "Date", column: "Year", values: [2023] }]);
    expect(evaluator.evaluate("Revenue", ctx)).toBe(300);

    const ctx2024 = buildFilterContext(store, [{ table: "Date", column: "Year", values: [2024] }]);
    expect(evaluator.evaluate("Revenue", ctx2024)).toBe(75);
  });

  it("propagates two independent dimension filters simultaneously", () => {
    const { store, evaluator } = setup();
    const ctx = buildFilterContext(store, [
      { table: "Date", column: "Year", values: [2023] },
      { table: "Product", column: "Category", values: ["A"] },
    ]);
    expect(evaluator.evaluate("Revenue", ctx)).toBe(100);
  });

  it("evaluates a grouped (virtual SUMMARIZE) measure per distinct dimension value", () => {
    const { store, evaluator } = setup();
    const ctx = buildFilterContext(store, []);
    const grouped = evaluator.evaluateGroupedBy("Revenue", { table: "Product", column: "Category" }, ctx);
    const byKey = Object.fromEntries(grouped.map((g) => [g.key as string, g.value]));
    expect(byKey["A"]).toBe(150);
    expect(byKey["B"]).toBe(225);
  });

  it("DIVIDE returns the alternate result on a zero/blank denominator", () => {
    const { store, evaluator } = setup();
    const ctx = buildFilterContext(store, [{ table: "Product", column: "Category", values: ["__none__"] }]);
    expect(evaluator.evaluate("AverageSellingPrice", ctx)).toBe(0);
  });

  it("DIVIDE computes a real ratio when data is present", () => {
    const { store, evaluator } = setup();
    const ctx = buildFilterContext(store, []);
    expect(evaluator.evaluate("AverageSellingPrice", ctx)).toBeCloseTo(375 / 9);
  });

  it("CALCULATE overrides an outer filter on the same column but preserves filters on other columns", () => {
    const { store, evaluator } = setup();
    const outerCtx = buildFilterContext(store, [
      { table: "Date", column: "Year", values: [2023] },
      { table: "Product", column: "Category", values: ["B"] },
    ]);
    // RevenueForProductA overrides the Category filter to "A" but Year=2023 stays in effect.
    expect(evaluator.evaluate("RevenueForProductA", outerCtx)).toBe(100);
  });

  it("propagates a many-side filter back to the one-side only when crossFilterDirection is 'both'", () => {
    const { store, evaluator } = setup();
    // Select a single Sales row directly (SalesKey=1 -> ProductKey=1, DateKey=1).
    const ctx = buildFilterContext(store, [{ table: "Sales", column: "SalesKey", values: [1] }]);

    // Product<->Sales is bidirectional: Product should now be restricted to ProductKey=1 (Category A).
    const productRevenue = evaluator.evaluateGroupedBy("Revenue", { table: "Product", column: "Category" }, ctx);
    expect(productRevenue).toEqual([{ key: "A", value: 100 }]);

    // Date->Sales is single-direction: Date must remain unrestricted by a Sales-side filter.
    const dateGroups = evaluator.evaluateGroupedBy("Revenue", { table: "Date", column: "Year" }, ctx);
    expect(dateGroups.map((g) => g.key).sort()).toEqual([2023, 2024]);
  });

  it("overrideFilters recomputes propagation deterministically", () => {
    const { store, evaluator } = setup();
    const base = buildFilterContext(store, [{ table: "Date", column: "Year", values: [2023] }]);
    const narrowed = overrideFilters(store, base, [{ table: "Product", column: "Category", values: ["A"] }]);
    expect(evaluator.evaluate("Revenue", narrowed)).toBe(100);
  });
});
