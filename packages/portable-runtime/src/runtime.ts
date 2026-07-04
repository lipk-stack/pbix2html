import type { DashboardIR, PageIR, VisualIR } from "@pbix2html/dir-schema";
import { TableStore, MeasureEvaluator, buildFilterContext, type ColumnFilter } from "@pbix2html/semantic-engine";
import { FilterState } from "./filter-state.js";
import { renderCard } from "./renderers/card.js";
import { renderBarChart } from "./renderers/bar-chart.js";
import { renderSlicer } from "./renderers/slicer.js";

export class DashboardRuntime {
  private readonly store: TableStore;
  private readonly evaluator: MeasureEvaluator;
  private readonly filterState = new FilterState();
  private currentPage: PageIR;

  constructor(
    private readonly ir: DashboardIR,
    private readonly root: HTMLElement,
  ) {
    this.store = new TableStore(ir.semanticModel, ir.data.tables);
    this.evaluator = new MeasureEvaluator(this.store);
    const firstVisiblePage = ir.pages.find((p) => p.visibility === "visible") ?? ir.pages[0];
    if (!firstVisiblePage) throw new Error("DashboardIR must contain at least one page");
    this.currentPage = firstVisiblePage;
  }

  mount(): void {
    this.render();
  }

  private render(): void {
    this.root.innerHTML = "";
    this.root.className = "pbix-page";
    this.root.style.position = "relative";
    this.root.style.width = `${this.currentPage.width}px`;
    this.root.style.height = `${this.currentPage.height}px`;

    for (const visual of this.currentPage.visuals) {
      const el = document.createElement("div");
      el.dataset["visualId"] = visual.id;
      el.style.position = "absolute";
      el.style.left = `${visual.bounds.x}px`;
      el.style.top = `${visual.bounds.y}px`;
      el.style.width = `${visual.bounds.width}px`;
      el.style.height = `${visual.bounds.height}px`;
      el.style.zIndex = String(visual.zIndex);
      this.root.appendChild(el);
      this.renderVisual(el, visual);
    }
  }

  private renderVisual(el: HTMLElement, visual: VisualIR): void {
    const filters = this.filterState.filtersFor(visual.id, this.ir.interactions);
    const ctx = buildFilterContext(this.store, filters);

    switch (visual.normalizedType) {
      case "card":
        renderCard(el, visual, this.evaluator, ctx);
        return;

      case "barChart":
      case "columnChart": {
        const selected = this.filterState.getCrossFilter(visual.id)?.values?.[0];
        renderBarChart(el, visual, this.evaluator, ctx, selected, (category) => {
          this.toggleCrossFilter(visual, category);
          this.render();
        });
        return;
      }

      case "slicer": {
        const selected = this.filterState.getSlicer(visual.id)?.values?.[0];
        renderSlicer(el, visual, this.store, selected, (value) => {
          this.setSlicer(visual, value);
          this.render();
        });
        return;
      }

      default:
        el.textContent = `Unsupported visual type: ${visual.normalizedType}`;
    }
  }

  private toggleCrossFilter(visual: VisualIR, category: unknown): void {
    const categoryRef = visual.bindings.category?.[0];
    const current = this.filterState.getCrossFilter(visual.id);
    const alreadySelected = current?.values?.[0] === category;

    if (alreadySelected || !categoryRef) {
      this.filterState.setCrossFilter(visual.id, null);
      return;
    }

    const filter: ColumnFilter = { table: categoryRef.table, column: categoryRef.column, values: [category] };
    this.filterState.setCrossFilter(visual.id, filter);
  }

  private setSlicer(visual: VisualIR, value: unknown | null): void {
    if (value === null || !visual.slicerField) {
      this.filterState.setSlicer(visual.id, null);
      return;
    }
    const filter: ColumnFilter = {
      table: visual.slicerField.table,
      column: visual.slicerField.column,
      values: [value],
    };
    this.filterState.setSlicer(visual.id, filter);
  }
}
