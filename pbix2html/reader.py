"""Read report layout and metadata from a .pbix/.pbit archive.

The reader intentionally handles only documented/structural ZIP parts that can be
parsed without executing report content or proprietary model binaries.
"""

from __future__ import annotations

import json
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, BinaryIO, Union

LAYOUT_PART = "Report/Layout"
VERSION_PART = "Version"
SCHEMA_PART = "DataModelSchema"
STATIC_RESOURCE_PREFIX = "Report/StaticResources/"

# PBIX/PBIT input is untrusted. Keep decompression bounded before materialising
# members in memory. These limits are intentionally generous for report metadata
# while still preventing trivial ZIP-bomb exhaustion.
MAX_ARCHIVE_MEMBERS = 50_000
MAX_VERSION_BYTES = 1 * 1024 * 1024
MAX_LAYOUT_BYTES = 64 * 1024 * 1024
MAX_SCHEMA_BYTES = 64 * 1024 * 1024


class PbixError(Exception):
    """Raised when a file cannot be safely read as a PBIX/PBIT report."""


@dataclass
class Visual:
    """One visual container on a report page."""

    name: str = ""
    visual_type: str = "unknown"
    title: str = ""
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    width: float = 0.0
    height: float = 0.0
    fields: list[str] = field(default_factory=list)
    hidden: bool = False


@dataclass
class Page:
    """One report page (a section in the layout JSON)."""

    name: str
    display_name: str
    ordinal: int
    width: float
    height: float
    visuals: list[Visual] = field(default_factory=list)
    hidden: bool = False


@dataclass
class Table:
    """A table from the data model schema, when available."""

    name: str
    columns: list[str] = field(default_factory=list)
    measures: list[str] = field(default_factory=list)


@dataclass
class PbixReport:
    """Everything extracted from one archive."""

    source_name: str
    version: str = ""
    pages: list[Page] = field(default_factory=list)
    tables: list[Table] = field(default_factory=list)
    static_resources: list[str] = field(default_factory=list)

    @property
    def visual_count(self) -> int:
        return sum(len(page.visuals) for page in self.pages)


def _read_part(archive: zipfile.ZipFile, name: str, limit: int) -> bytes:
    """Read one member with both declared-size and streamed-size limits."""
    try:
        info = archive.getinfo(name)
    except KeyError as exc:
        raise PbixError(f"Archive member is missing: {name}") from exc

    if info.file_size > limit:
        raise PbixError(
            f"Archive member {name!r} is too large: {info.file_size} bytes "
            f"(limit {limit} bytes)"
        )

    try:
        with archive.open(info, "r") as member:
            data = member.read(limit + 1)
    except (OSError, RuntimeError, zipfile.BadZipFile, NotImplementedError) as exc:
        raise PbixError(f"Could not safely read archive member {name!r}: {exc}") from exc

    if len(data) > limit:
        raise PbixError(f"Archive member {name!r} exceeds the {limit}-byte limit")
    return data


def _decode_text(data: bytes) -> str:
    """Decode a PBIX text part (UTF-16 with or without BOM, or UTF-8)."""
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        return data.decode("utf-16")
    if len(data) >= 2 and data[1] == 0:
        try:
            return data.decode("utf-16-le")
        except UnicodeDecodeError:
            pass
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise PbixError(f"Could not decode text part as UTF-16 or UTF-8: {exc}") from exc


def _load_json_string(value: Any) -> Any:
    """Layout parts store nested JSON as strings; decode them defensively."""
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (ValueError, TypeError):
            return None
    return value if isinstance(value, (dict, list)) else None


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _literal_text(expr: Any) -> str:
    """Extract text from a layout literal expression."""
    if not isinstance(expr, dict):
        return ""
    expr_value = expr.get("expr")
    literal = expr_value.get("Literal", {}) if isinstance(expr_value, dict) else {}
    value = literal.get("Value", "") if isinstance(literal, dict) else ""
    if isinstance(value, str) and len(value) >= 2 and value[0] == value[-1] == "'":
        return value[1:-1]
    return str(value) if value else ""


def _visual_title(single_visual: dict, vc_objects: dict) -> str:
    for source in (vc_objects, single_visual.get("objects") or {}):
        titles = source.get("title") if isinstance(source, dict) else None
        if isinstance(titles, list) and titles:
            properties = titles[0].get("properties", {}) if isinstance(titles[0], dict) else {}
            text = _literal_text(properties.get("text", {}))
            if text:
                return text
    return ""


def _visual_fields(single_visual: dict) -> list[str]:
    fields: list[str] = []
    projections = single_visual.get("projections")
    if isinstance(projections, dict):
        for role, entries in projections.items():
            if not isinstance(entries, list):
                continue
            for entry in entries:
                ref = entry.get("queryRef") if isinstance(entry, dict) else None
                if isinstance(ref, str) and ref:
                    fields.append(f"{role}: {ref}")
    return fields


def _parse_visual(container: dict) -> Visual:
    visual = Visual(
        x=_as_float(container.get("x")),
        y=_as_float(container.get("y")),
        z=_as_float(container.get("z")),
        width=_as_float(container.get("width")),
        height=_as_float(container.get("height")),
    )
    config = _load_json_string(container.get("config"))
    if not isinstance(config, dict):
        return visual

    visual.name = str(config.get("name", ""))
    layouts = config.get("layouts")
    if isinstance(layouts, list) and layouts:
        position = layouts[0].get("position", {}) if isinstance(layouts[0], dict) else {}
        if isinstance(position, dict):
            visual.x = _as_float(position.get("x"), visual.x)
            visual.y = _as_float(position.get("y"), visual.y)
            visual.z = _as_float(position.get("z"), visual.z)
            visual.width = _as_float(position.get("width"), visual.width)
            visual.height = _as_float(position.get("height"), visual.height)

    single_visual = config.get("singleVisual")
    if isinstance(single_visual, dict):
        visual.visual_type = str(single_visual.get("visualType") or "unknown")
        display = single_visual.get("display")
        visual.hidden = isinstance(display, dict) and display.get("mode") == "hidden"
        visual.fields = _visual_fields(single_visual)
        vc_objects = single_visual.get("vcObjects")
        visual.title = _visual_title(
            single_visual, vc_objects if isinstance(vc_objects, dict) else {}
        )
    elif isinstance(config.get("singleVisualGroup"), dict):
        visual.visual_type = "visualGroup"
        visual.title = str(config["singleVisualGroup"].get("displayName", ""))
    return visual


def _parse_page(section: dict, index: int) -> Page:
    page = Page(
        name=str(section.get("name", f"section{index}")),
        display_name=str(section.get("displayName", f"Page {index + 1}")),
        ordinal=int(_as_float(section.get("ordinal"), index)),
        width=_as_float(section.get("width"), 1280.0),
        height=_as_float(section.get("height"), 720.0),
    )
    section_config = _load_json_string(section.get("config"))
    if isinstance(section_config, dict):
        visibility = section_config.get("visibility")
        page.hidden = visibility == 1 or visibility == "HiddenInViewMode"

    containers = section.get("visualContainers")
    if isinstance(containers, list):
        page.visuals = [_parse_visual(c) for c in containers if isinstance(c, dict)]
        page.visuals.sort(key=lambda v: (v.z, v.y, v.x))
    return page


def _parse_tables(schema_text: str) -> list[Table]:
    try:
        schema = json.loads(schema_text)
    except ValueError:
        return []
    model = schema.get("model", {}) if isinstance(schema, dict) else {}
    tables: list[Table] = []
    for entry in model.get("tables", []) if isinstance(model, dict) else []:
        if not isinstance(entry, dict):
            continue
        name = str(entry.get("name", ""))
        if name.startswith("DateTableTemplate_") or name.startswith("LocalDateTable_"):
            continue
        table = Table(name=name)
        for column in entry.get("columns", []) or []:
            if isinstance(column, dict) and column.get("name"):
                table.columns.append(str(column["name"]))
        for measure in entry.get("measures", []) or []:
            if isinstance(measure, dict) and measure.get("name"):
                table.measures.append(str(measure["name"]))
        tables.append(table)
    return tables


def read_pbix(source: Union[str, Path, BinaryIO]) -> PbixReport:
    """Read a .pbix or .pbit file and return its parsed report structure."""
    source_name = Path(str(source)).name if isinstance(source, (str, Path)) else "report.pbix"
    try:
        archive = zipfile.ZipFile(source)
    except FileNotFoundError:
        raise
    except (zipfile.BadZipFile, OSError, ValueError) as exc:
        raise PbixError(f"{source_name} is not a readable PBIX archive: {exc}") from exc

    with archive:
        infos = archive.infolist()
        if len(infos) > MAX_ARCHIVE_MEMBERS:
            raise PbixError(
                f"{source_name} contains too many archive members: {len(infos)} "
                f"(limit {MAX_ARCHIVE_MEMBERS})"
            )
        names = {info.filename for info in infos}
        if LAYOUT_PART not in names:
            raise PbixError(
                f"{source_name} has no {LAYOUT_PART} part; it does not look like a PBIX/PBIT report"
            )

        report = PbixReport(source_name=source_name)
        if VERSION_PART in names:
            report.version = _decode_text(
                _read_part(archive, VERSION_PART, MAX_VERSION_BYTES)
            ).strip()

        layout_text = _decode_text(_read_part(archive, LAYOUT_PART, MAX_LAYOUT_BYTES))
        try:
            layout = json.loads(layout_text)
        except ValueError as exc:
            raise PbixError(f"{source_name}: {LAYOUT_PART} is not valid JSON: {exc}") from exc

        sections = layout.get("sections") if isinstance(layout, dict) else None
        if isinstance(sections, list):
            report.pages = [
                _parse_page(section, i)
                for i, section in enumerate(sections)
                if isinstance(section, dict)
            ]
            report.pages.sort(key=lambda p: p.ordinal)

        if SCHEMA_PART in names:
            report.tables = _parse_tables(
                _decode_text(_read_part(archive, SCHEMA_PART, MAX_SCHEMA_BYTES))
            )

        report.static_resources = sorted(
            name[len(STATIC_RESOURCE_PREFIX) :]
            for name in names
            if name.startswith(STATIC_RESOURCE_PREFIX) and not name.endswith("/")
        )
    return report
