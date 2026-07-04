"""Build synthetic PBIX archives for tests, matching the real part layout."""

from __future__ import annotations

import io
import json
import zipfile


def visual_container(
    visual_type: str = "barChart",
    name: str = "visual1",
    x: float = 10,
    y: float = 20,
    width: float = 300,
    height: float = 200,
    z: float = 0,
    title: str = "",
    projections: dict | None = None,
) -> dict:
    config: dict = {
        "name": name,
        "layouts": [{"id": 0, "position": {"x": x, "y": y, "z": z, "width": width, "height": height}}],
        "singleVisual": {"visualType": visual_type},
    }
    if projections:
        config["singleVisual"]["projections"] = projections
    if title:
        config["singleVisual"]["vcObjects"] = {
            "title": [{"properties": {"text": {"expr": {"Literal": {"Value": f"'{title}'"}}}}}]
        }
    return {
        "x": x,
        "y": y,
        "z": z,
        "width": width,
        "height": height,
        "config": json.dumps(config),
    }


def section(
    display_name: str = "Page 1",
    name: str = "ReportSection1",
    ordinal: int = 0,
    visuals: list[dict] | None = None,
    hidden: bool = False,
) -> dict:
    return {
        "name": name,
        "displayName": display_name,
        "ordinal": ordinal,
        "width": 1280,
        "height": 720,
        "visualContainers": visuals or [],
        "config": json.dumps({"visibility": 1} if hidden else {}),
    }


def build_pbix(
    sections: list[dict] | None = None,
    version: str = "1.28",
    schema: dict | None = None,
    static_resources: dict[str, bytes] | None = None,
    layout_encoding: str = "utf-16-le",
) -> io.BytesIO:
    layout = {"id": 0, "sections": sections if sections is not None else [section()]}
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("Version", version.encode("utf-16"))  # with BOM, like real files
        archive.writestr("Report/Layout", json.dumps(layout).encode(layout_encoding))
        archive.writestr("[Content_Types].xml", b"<Types/>")
        if schema is not None:
            archive.writestr("DataModelSchema", json.dumps(schema).encode("utf-16-le"))
        for name, data in (static_resources or {}).items():
            archive.writestr(f"Report/StaticResources/{name}", data)
    buffer.seek(0)
    return buffer
