import type { VisualIR } from "@pbix2html/dir-schema";
import type { TableStore } from "@pbix2html/semantic-engine";

export function renderSlicer(
  container: HTMLElement,
  visual: VisualIR,
  store: TableStore,
  selectedValue: unknown,
  onSelect: (value: unknown | null) => void,
): void {
  const field = visual.slicerField;
  container.innerHTML = "";
  container.className = "pbix-visual pbix-slicer";

  if (!field) {
    container.textContent = "Unsupported slicer binding";
    return;
  }

  if (visual.format.showTitle !== false && visual.format.title) {
    const title = document.createElement("div");
    title.className = "pbix-visual-title";
    title.textContent = visual.format.title;
    container.appendChild(title);
  }

  const list = document.createElement("ul");
  list.className = "pbix-slicer-list";

  const values = store
    .distinctValues(field.table, field.column)
    .sort((a, b) => String(a).localeCompare(String(b)));

  for (const value of values) {
    const item = document.createElement("li");
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = String(value);
    const isSelected = value === selectedValue;
    button.className = isSelected ? "pbix-slicer-item pbix-slicer-item-selected" : "pbix-slicer-item";
    button.setAttribute("aria-pressed", String(isSelected));
    button.addEventListener("click", () => {
      onSelect(isSelected ? null : value);
    });
    item.appendChild(button);
    list.appendChild(item);
  }

  container.appendChild(list);
}
