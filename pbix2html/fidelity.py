"""Classify what a conversion actually preserved.

This module exists so the tool never silently implies more fidelity than it
delivered. Every visual and every cross-cutting report feature (filters,
theming, calculations, ...) is assigned one of a fixed set of classification
labels, each with a human-readable reason. The same data backs the on-page
fidelity report, the CLI summary, and an optional machine-readable JSON file.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from pbix2html.reader import PbixReport

EXACT = "EXACT"
SEMANTICALLY_EQUIVALENT = "SEMANTICALLY_EQUIVALENT"
VISUALLY_EQUIVALENT = "VISUALLY_EQUIVALENT"
APPROXIMATED = "APPROXIMATED"
SNAPSHOTTED = "SNAPSHOTTED"
CONNECTED_RUNTIME_REQUIRED = "CONNECTED_RUNTIME_REQUIRED"
UNSUPPORTED = "UNSUPPORTED"
BLOCKED_FOR_SECURITY = "BLOCKED_FOR_SECURITY"
BLOCKED_FOR_LICENSING = "BLOCKED_FOR_LICENSING"

# Visual families this renderer draws as a real, bounded, styled skeleton
# (title plus a shape appropriate to the family) rather than a generic box.
_FAMILY_CLASSIFICATION = {
    "textbox": (VISUALLY_EQUIVALENT, "Text content is rendered at its real position and size."),
    "shape": (VISUALLY_EQUIVALENT, "Shape bounds are rendered; fill/border styling is not extracted."),
    "visualgroup": (VISUALLY_EQUIVALENT, "Group bounds and label are rendered as a container."),
    "actionbutton": (
        VISUALLY_EQUIVALENT,
        "Button label and bounds are rendered; its action target was not extracted, so it is disabled.",
    ),
    "pagenavigator": (
        SEMANTICALLY_EQUIVALENT,
        "Replaced by real, keyboard-accessible HTML page tabs with the same destinations.",
    ),
}


def _classify_visual_type(visual_type: str) -> tuple[str, str]:
    kind = visual_type.lower()
    if kind in _FAMILY_CLASSIFICATION:
        return _FAMILY_CLASSIFICATION[kind]
    if "card" in kind:
        return (
            VISUALLY_EQUIVALENT,
            "Rendered at its real position and size; no portable row data was extracted to show a value.",
        )
    if "slicer" in kind:
        return (
            VISUALLY_EQUIVALENT,
            "The bound field name is recovered; selectable values and cross-filtering are not implemented.",
        )
    if "table" in kind or "matrix" in kind:
        return (
            VISUALLY_EQUIVALENT,
            "Rendered as a bounded skeleton grid; no portable row data was extracted.",
        )
    if "chart" in kind or kind in {"treemap", "pie", "donut", "gauge"}:
        return (
            VISUALLY_EQUIVALENT,
            "Rendered as a bounded skeleton chart; no portable row data was extracted.",
        )
    return (
        UNSUPPORTED,
        f"{visual_type!r} is not a recognized visual family; rendered as a generic labeled box.",
    )


@dataclass
class VisualFidelity:
    """Classification for one distinct (visual type, page) combination."""

    visual_type: str
    classification: str
    reason: str
    count: int

    def to_dict(self) -> dict:
        return {
            "visualType": self.visual_type,
            "classification": self.classification,
            "reason": self.reason,
            "count": self.count,
        }


@dataclass
class DimensionFidelity:
    """Classification for one cross-cutting report feature (not a single visual)."""

    key: str
    label: str
    classification: str
    reason: str

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "label": self.label,
            "classification": self.classification,
            "reason": self.reason,
        }


@dataclass
class FidelityReport:
    source_name: str
    visuals: list[VisualFidelity] = field(default_factory=list)
    dimensions: list[DimensionFidelity] = field(default_factory=list)
    hidden_visual_count: int = 0
    hidden_page_count: int = 0

    def visual_counts_by_classification(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for entry in self.visuals:
            counts[entry.classification] = counts.get(entry.classification, 0) + entry.count
        return counts

    def to_dict(self) -> dict:
        return {
            "source": self.source_name,
            "visualFamilies": [v.to_dict() for v in self.visuals],
            "reportDimensions": [d.to_dict() for d in self.dimensions],
            "hiddenVisualCount": self.hidden_visual_count,
            "hiddenPageCount": self.hidden_page_count,
            "visualCountsByClassification": self.visual_counts_by_classification(),
        }

    def to_text(self) -> str:
        lines = [f"Fidelity report for {self.source_name}", ""]
        lines.append("Report-wide features:")
        for dimension in self.dimensions:
            lines.append(f"  [{dimension.classification}] {dimension.label} — {dimension.reason}")
        lines.append("")
        lines.append("Visual families:")
        for visual in self.visuals:
            plural = "s" if visual.count != 1 else ""
            lines.append(
                f"  [{visual.classification}] {visual.visual_type} "
                f"({visual.count} instance{plural}) — {visual.reason}"
            )
        if self.hidden_visual_count or self.hidden_page_count:
            lines.append("")
            lines.append(
                f"Not rendered at all: {self.hidden_visual_count} hidden visual(s), "
                f"{self.hidden_page_count} hidden page(s)."
            )
        return "\n".join(lines)


def build_fidelity_report(report: PbixReport) -> FidelityReport:
    """Classify every visual family and cross-cutting feature found in ``report``."""
    counts: dict[tuple[str, str, str], int] = {}
    for page in report.pages:
        for visual in page.visuals:
            if visual.hidden:
                continue
            classification, reason = _classify_visual_type(visual.visual_type)
            key = (visual.visual_type, classification, reason)
            counts[key] = counts.get(key, 0) + 1
    visuals = [
        VisualFidelity(visual_type=vtype, classification=cls, reason=reason, count=count)
        for (vtype, cls, reason), count in sorted(counts.items(), key=lambda item: item[0][0].lower())
    ]

    hidden_visual_count = sum(1 for page in report.pages for visual in page.visuals if visual.hidden)
    hidden_page_count = sum(1 for page in report.pages if page.hidden)

    has_tables = bool(report.tables)
    has_resources = bool(report.static_resources)

    dimensions = [
        DimensionFidelity(
            key="page_layout",
            label="Page dimensions, visual bounds, and z-order",
            classification=EXACT,
            reason="Read directly from the report layout JSON with no approximation.",
        ),
        DimensionFidelity(
            key="page_navigation",
            label="Page navigation",
            classification=SEMANTICALLY_EQUIVALENT,
            reason="Power BI page navigator visuals are replaced by working HTML tabs to the same pages.",
        ),
        DimensionFidelity(
            key="semantic_model_metadata",
            label="Table, column, and measure names",
            classification=SEMANTICALLY_EQUIVALENT if has_tables else UNSUPPORTED,
            reason=(
                "Names are recovered from the data model schema or, failing that, from visual field "
                "bindings; this is metadata recovery only, not calculation."
                if has_tables
                else "No data model schema or recoverable visual bindings were found."
            ),
        ),
        DimensionFidelity(
            key="measure_calculations",
            label="Measures and calculated columns (DAX)",
            classification=UNSUPPORTED,
            reason="DAX expressions are not parsed or executed; no calculated values are produced.",
        ),
        DimensionFidelity(
            key="row_data",
            label="Row data and rendered values",
            classification=UNSUPPORTED,
            reason=(
                "No portable row data is extracted or embedded, so charts, cards, and tables render as "
                "bounded skeletons with no portable row data behind them."
            ),
        ),
        DimensionFidelity(
            key="filters_and_slicers",
            label="Report/page/visual filters and slicer selections",
            classification=UNSUPPORTED,
            reason="Filter definitions and slicer selection state are not extracted from the layout.",
        ),
        DimensionFidelity(
            key="cross_filtering",
            label="Cross-filtering, cross-highlighting, and drill",
            classification=UNSUPPORTED,
            reason="No interaction graph is reconstructed; visuals do not filter, highlight, or drill each other.",
        ),
        DimensionFidelity(
            key="bookmarks",
            label="Bookmarks",
            classification=UNSUPPORTED,
            reason="Bookmark state (filters, slicer values, visibility, drill state) is not extracted.",
        ),
        DimensionFidelity(
            key="themes_and_formatting",
            label="Theme colors, fonts, and conditional formatting",
            classification=UNSUPPORTED,
            reason="Report theme and per-visual formatting objects are not extracted; output uses a neutral default theme.",
        ),
        DimensionFidelity(
            key="static_resources",
            label="Images and background media",
            classification=UNSUPPORTED if has_resources else EXACT,
            reason=(
                "Resource file names are listed but the underlying bytes are not embedded, so images and "
                "backgrounds referencing them do not render."
                if has_resources
                else "No static resources were present in this report."
            ),
        ),
        DimensionFidelity(
            key="row_level_security",
            label="Row-level security enforcement",
            classification=UNSUPPORTED,
            reason=(
                "No row data is embedded, so there is no authorization boundary to enforce. This must not "
                "be read as an RLS guarantee for any future feature that embeds row data."
            ),
        ),
    ]

    return FidelityReport(
        source_name=report.source_name,
        visuals=visuals,
        dimensions=dimensions,
        hidden_visual_count=hidden_visual_count,
        hidden_page_count=hidden_page_count,
    )
