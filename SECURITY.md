# Security

## Current scope

Today's input is a trusted, hand-authored structured JSON fixture (`DashboardIR`), not an untrusted `.pbix` binary. The full threat model in the master brief (Section 25: zip bombs, path traversal, parser exploits, malicious custom-visual metadata, oversized resources, memory/CPU exhaustion) applies to the **ingestion adapters that don't exist yet**. It is not yet exercised by this repository and must be built out — with sandboxing, bounded decompression, size/entry-count limits, and fuzz testing — before any adapter accepts real, untrusted `.pbix` files. Do not treat "no ingestion adapter exists" as "the security work is done"; it means the security work has not started because there is nothing yet to secure.

## What the current exporter does enforce

Every generated HTML file sets:

```
Content-Security-Policy: default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data: blob:; font-src data:; connect-src 'none';
```

`connect-src 'none'` plus no `<script src=…>`/`<link href=…>` anywhere in the emitted document (verified by `packages/html-exporter/src/index.test.ts`) means the exported dashboard cannot make an outbound network request even if something in the DIR data or a future custom-visual adapter tried to. This is a browser-enforced property of every export, not a policy the user has to trust.

DIR data is embedded as a `<script type="application/json">` block with `<` characters escaped in the JSON payload (`html-exporter/src/index.ts`), so a field value containing `</script>` cannot break out of the data tag and get interpreted as HTML/script.

## RLS: a portable HTML file is not a security boundary

**This is the master brief's Section 26 requirement, and it is not yet implemented.** The current exporter has no concept of a security role, a user, or row-level filtering at export time — it embeds every row present in the input `DashboardIR`'s `data.tables` verbatim, for anyone who opens the file to inspect (view source, `JSON.parse` the embedded script tag, etc.).

Concretely, until role-based export filtering exists:

- **Do not** feed this tool a semantic model that has row-level security (RLS) or object-level security (OLS) configured, expecting the export to respect it.
- **Do not** assume client-side JavaScript filtering (e.g., a slicer that happens to hide some rows in the UI) is an authorization control. All embedded data is inspectable by anyone with the file.
- Before this tool is used against any access-controlled model, it needs the per-role/per-user export modes described in the master brief (evaluate allowed rows *before* packaging, package only the authorized subset, record which role was applied, warn about redistribution) — tracked in [ROADMAP.md](./ROADMAP.md) Phase 4.

## Protected / encrypted source files

Not applicable yet (no binary ingestion exists), but the same commitment holds for when it does: this project will not bypass encryption, DRM, or sensitivity-label protection on a source file. An adapter that encounters a protected artifact must fail with a clear diagnostic, not attempt to work around the protection.
