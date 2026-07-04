import type { VisualIR } from "@pbix2html/dir-schema";
import type { FilterContext, MeasureEvaluator } from "@pbix2html/semantic-engine";
import { formatNumber } from "../format.js";

const SVG_NS = "http://www.w3.org/2000/svg";

export function renderBarChart(
  container: HTMLElement,
  visual: VisualIR,
  evaluator: MeasureEvaluator,
  ctx: FilterContext,
  selectedCategory: unknown,
  onCategoryClick: (category: unknown) => void,
): void {
  const categoryRef = visual.bindings.category?.[0];
  const valueBinding = visual.bindings.values?.[0];
  container.innerHTML = "";
  container.className = "pbix-visual pbix-bar-chart";

  if (!categoryRef || !valueBinding || !("measure" in valueBinding)) {
    container.textContent = "Unsupported bar chart binding";
    return;
  }

  if (visual.format.showTitle !== false && visual.format.title) {
    const title = document.createElement("div");
    title.className = "pbix-visual-title";
    title.textContent = visual.format.title;
    container.appendChild(title);
  }

  const groups = evaluator
    .evaluateGroupedBy(valueBinding.measure, categoryRef, ctx)
    .map((g) => ({ key: g.key, value: g.value ?? 0 }))
    .sort((a, b) => String(a.key).localeCompare(String(b.key)));

  const maxValue = Math.max(1, ...groups.map((g) => g.value));
  const chartHeight = 160;
  const barWidth = 48;
  const gap = 16;
  const width = groups.length * (barWidth + gap) + gap;

  const svg = document.createElementNS(SVG_NS, "svg");
  svg.setAttribute("viewBox", `0 0 ${width} ${chartHeight + 24}`);
  svg.setAttribute("width", String(width));
  svg.setAttribute("height", String(chartHeight + 24));
  svg.setAttribute("role", "img");
  svg.setAttribute("aria-label", visual.format.title ?? "Bar chart");
  svg.setAttribute("class", "pbix-bar-svg");

  groups.forEach((group, index) => {
    const barHeight = (group.value / maxValue) * chartHeight;
    const x = gap + index * (barWidth + gap);
    const y = chartHeight - barHeight;
    const isSelected = selectedCategory !== undefined && selectedCategory === group.key;

    const rect = document.createElementNS(SVG_NS, "rect");
    rect.setAttribute("x", String(x));
    rect.setAttribute("y", String(y));
    rect.setAttribute("width", String(barWidth));
    rect.setAttribute("height", String(Math.max(barHeight, 1)));
    rect.setAttribute("class", isSelected ? "pbix-bar pbix-bar-selected" : "pbix-bar");
    rect.setAttribute("data-category", String(group.key));
    rect.setAttribute("tabindex", "0");
    rect.setAttribute("role", "button");
    rect.setAttribute("aria-label", `${group.key}: ${formatNumber(group.value, visual.format.numberFormat)}`);
    rect.addEventListener("click", () => onCategoryClick(group.key));
    rect.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        onCategoryClick(group.key);
      }
    });
    svg.appendChild(rect);

    const label = document.createElementNS(SVG_NS, "text");
    label.setAttribute("x", String(x + barWidth / 2));
    label.setAttribute("y", String(chartHeight + 16));
    label.setAttribute("text-anchor", "middle");
    label.setAttribute("class", "pbix-bar-label");
    label.textContent = String(group.key);
    svg.appendChild(label);
  });

  container.appendChild(svg);
}
