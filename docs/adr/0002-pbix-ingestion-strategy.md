# ADR 0002: PBIX ingestion strategy research

## Status

Accepted (research complete; implementation not started — tracked in ROADMAP.md Phase 2).

## Context

The master brief requires classifying every proposed ingestion mechanism as `PUBLIC_SUPPORTED_API`, `PUBLIC_DOCUMENTED_FORMAT`, `SUPPORTED_DESKTOP_WORKFLOW`, `SUPPORTED_SERVICE_WORKFLOW`, `OPEN_SOURCE_INTEROPERABILITY_LAYER`, `EXPERIMENTAL_INTEROPERABILITY`, or `UNSAFE_OR_UNSUPPORTED` before building on it. This ADR records the current (verified against Microsoft Learn documentation, July 2026) state of each candidate format.

## Findings

**`.pbix`** is Power BI Desktop's default save format: a binary container. Microsoft's own implementation-planning documentation states plainly that "this binary format... [is] not possible to open or use the file contents to track changes or improve developer productivity" — i.e., there is no supported, documented API for reading a `.pbix` file's internals directly. Any direct-PBIX parser is necessarily built by inspection/reverse engineering of an undocumented container, not against a spec. → **`EXPERIMENTAL_INTEROPERABILITY`**, quarantined behind sandboxing, versioning, and fuzzing per the brief's Section 4.4 — never the foundation of the pipeline.

**`.pbip` (Power BI Project)** is an explicitly documented, git-friendly, folder-based save format Power BI Desktop can produce, containing:
- **PBIR** (Power BI enhanced Report format) — "a publicly documented format... Each file has a public JSON schema" (Microsoft Learn, `projects-enhanced-report-format`), organizing pages/visuals/bookmarks as individual JSON files with a `definition.pbir` root pointing at the semantic model. Public schemas are published at `github.com/microsoft/json-schemas` (per-part, e.g. `visualContainer`, `page`, `pagesMetadata`).
- **TMDL** (Tabular Model Definition Language) — the semantic-model definition format, "designed from the ground up to be human-friendly," folder-per-table/perspective/role, replacing the single big `model.bim` (TMSL) file.

Both are **`PUBLIC_DOCUMENTED_FORMAT`**. Fabric's REST API also documents report definitions as either `PBIR` or `PBIR-Legacy` (`rest/api/fabric/articles/item-management/definitions/report-definition`), reinforcing PBIR as the forward-looking, spec'd target.

**Power BI Desktop as a conversion bridge (UI automation, Section 4.2)** and **service-assisted ingestion via Fabric/Power BI REST APIs (Section 4.3)** are real options — the REST/XMLA/TOM surfaces Microsoft documents are `PUBLIC_SUPPORTED_API` / `SUPPORTED_SERVICE_WORKFLOW` — but both require either a licensed Desktop install driven by fragile automation, or tenant/service credentials and explicit user consent. Both are legitimate future strategies, not something to default to.

## Decision

Build the PBIP/PBIR/TMDL reader **before** any direct-PBIX parser. It is the only ingestion path that is fully documented, requires no reverse engineering, no UI automation, and no service credentials — a user who saves their report as a `.pbip` project gets a real (not fixture) `DashboardIR` through the exact pipeline already built and tested in this iteration. This is recorded as the Phase 2 milestone in `ROADMAP.md`.

Direct `.pbix` parsing remains on the roadmap (many users will only ever have a `.pbix`, not a `.pbip`), but stays explicitly labeled `EXPERIMENTAL_INTEROPERABILITY`: sandboxed, versioned per observed format revision, with decompression/entry-count/memory limits and fuzz testing before it touches any file a user didn't author for testing purposes — per Section 4.4 of the master brief.

## Consequences

- No engineering time this iteration went into reverse-engineering the PBIX binary format — it would have been built on sand.
- The next ingestion milestone (PBIP/PBIR/TMDL reader) has a clear, documented target schema to read against and public JSON Schemas to validate input.
- `COMPATIBILITY.md` reflects `.pbix` as `UNSUPPORTED` (not "partially working" or silently approximated) until that adapter exists and is tested.
