import type { InteractionGraph } from "@pbix2html/dir-schema";
import type { ColumnFilter } from "@pbix2html/semantic-engine";

/**
 * Interactive filter state for one page. Slicer selections apply to every
 * visual on the page (matching default Power BI slicer behavior). Cross-filter
 * clicks (bar/column/pie categories) apply ONLY to visuals the interaction
 * graph explicitly names as "filter" targets of the clicking visual — this is
 * what keeps a single click from silently filtering every unrelated visual.
 */
export class FilterState {
  private readonly slicerFilters = new Map<string, ColumnFilter>();
  private readonly crossFilters = new Map<string, ColumnFilter>();

  setSlicer(visualId: string, filter: ColumnFilter | null): void {
    if (filter === null) this.slicerFilters.delete(visualId);
    else this.slicerFilters.set(visualId, filter);
  }

  getSlicer(visualId: string): ColumnFilter | undefined {
    return this.slicerFilters.get(visualId);
  }

  setCrossFilter(sourceVisualId: string, filter: ColumnFilter | null): void {
    if (filter === null) this.crossFilters.delete(sourceVisualId);
    else this.crossFilters.set(sourceVisualId, filter);
  }

  getCrossFilter(sourceVisualId: string): ColumnFilter | undefined {
    return this.crossFilters.get(sourceVisualId);
  }

  /** Column filters that apply to `targetVisualId` given the current interactive selections. */
  filtersFor(targetVisualId: string, interactions: InteractionGraph): ColumnFilter[] {
    const filters = [...this.slicerFilters.values()];
    for (const edge of interactions.edges) {
      if (edge.mode !== "filter" || edge.targetVisualId !== targetVisualId) continue;
      const crossFilter = this.crossFilters.get(edge.sourceVisualId);
      if (crossFilter) filters.push(crossFilter);
    }
    return filters;
  }
}
