import type { VisualIR } from "@pbix2html/dir-schema";
import type { FilterContext, MeasureEvaluator } from "@pbix2html/semantic-engine";
import { formatNumber } from "../format.js";

export function renderCard(
  container: HTMLElement,
  visual: VisualIR,
  evaluator: MeasureEvaluator,
  ctx: FilterContext,
): void {
  const binding = visual.bindings.values?.[0];
  container.innerHTML = "";
  container.className = "pbix-visual pbix-card";

  if (!binding || !("measure" in binding)) {
    container.textContent = "Unsupported card binding";
    return;
  }

  const value = evaluator.evaluate(binding.measure, ctx);

  if (visual.format.showTitle !== false && visual.format.title) {
    const title = document.createElement("div");
    title.className = "pbix-card-title";
    title.textContent = visual.format.title;
    container.appendChild(title);
  }

  const valueEl = document.createElement("div");
  valueEl.className = "pbix-card-value";
  valueEl.textContent = formatNumber(value, visual.format.numberFormat);
  container.appendChild(valueEl);
}
