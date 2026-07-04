import { describe, expect, it } from "vitest";
import type { InteractionGraph } from "@pbix2html/dir-schema";
import { FilterState } from "./filter-state.js";

const interactions: InteractionGraph = {
  edges: [
    { sourceVisualId: "bar1", targetVisualId: "card1", mode: "filter" },
    { sourceVisualId: "bar1", targetVisualId: "table1", mode: "none" },
  ],
};

describe("FilterState", () => {
  it("applies slicer selections to every visual", () => {
    const state = new FilterState();
    state.setSlicer("slicer1", { table: "Date", column: "Year", values: [2023] });

    expect(state.filtersFor("card1", interactions)).toEqual([
      { table: "Date", column: "Year", values: [2023] },
    ]);
    expect(state.filtersFor("unrelated-visual", interactions)).toEqual([
      { table: "Date", column: "Year", values: [2023] },
    ]);
  });

  it("applies a cross-filter only to visuals wired as 'filter' targets", () => {
    const state = new FilterState();
    state.setCrossFilter("bar1", { table: "Product", column: "Category", values: ["A"] });

    expect(state.filtersFor("card1", interactions)).toEqual([
      { table: "Product", column: "Category", values: ["A"] },
    ]);
    // table1 is wired with mode "none" -> must NOT receive the cross-filter.
    expect(state.filtersFor("table1", interactions)).toEqual([]);
    // a visual with no edge from bar1 at all must also be unaffected.
    expect(state.filtersFor("some-other-visual", interactions)).toEqual([]);
  });

  it("clearing a cross-filter removes it from downstream targets", () => {
    const state = new FilterState();
    state.setCrossFilter("bar1", { table: "Product", column: "Category", values: ["A"] });
    state.setCrossFilter("bar1", null);
    expect(state.filtersFor("card1", interactions)).toEqual([]);
  });
});
