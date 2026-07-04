import { createRequire } from "node:module";
import { readFileSync } from "node:fs";
import * as esbuild from "esbuild";
import type { CompatibilityItem, DashboardIR } from "@pbix2html/dir-schema";

const require = createRequire(import.meta.url);

export interface ExportResult {
  html: string;
  warnings: string[];
}

const ACCEPTABLE_WITHOUT_WARNING = new Set(["EXACT", "SEMANTICALLY_EQUIVALENT"]);

export async function exportSingleFileHtml(ir: DashboardIR): Promise<ExportResult> {
  const entryPoint = require.resolve("@pbix2html/portable-runtime/bootstrap");
  const stylesPath = require.resolve("@pbix2html/portable-runtime/styles.css");

  const bundle = await esbuild.build({
    entryPoints: [entryPoint],
    bundle: true,
    write: false,
    format: "iife",
    target: "es2020",
    minify: true,
    logLevel: "silent",
  });

  const runtimeScript = bundle.outputFiles[0]?.text;
  if (!runtimeScript) throw new Error("Failed to bundle the portable dashboard runtime");

  const runtimeCss = readFileSync(stylesPath, "utf-8");
  const warnings = ir.compatibility.items
    .filter((item) => !ACCEPTABLE_WITHOUT_WARNING.has(item.status))
    .map((item) => describeCompatibilityItem(item));

  const html = renderTemplate({
    reportName: ir.reportName,
    css: `${runtimeCss}\n${FIDELITY_REPORT_CSS}`,
    runtimeScript,
    dataJson: JSON.stringify(ir).replace(/</g, "\\u003c"),
    compatibility: ir.compatibility,
  });

  return { html, warnings };
}

function describeCompatibilityItem(item: CompatibilityItem): string {
  const suffix = item.notes ? ` — ${item.notes}` : "";
  return `${item.objectType} "${item.objectId}": ${item.status}${suffix}`;
}

function escapeHtml(value: string): string {
  return value.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

const FIDELITY_REPORT_CSS = `
.pbix-fidelity-report { font-family: -apple-system, "Segoe UI", Roboto, sans-serif; font-size: 12px; color: #605e5c; margin: 12px; }
.pbix-fidelity-report summary { cursor: pointer; font-weight: 600; }
.pbix-fidelity-report table { border-collapse: collapse; margin-top: 8px; }
.pbix-fidelity-report td, .pbix-fidelity-report th { border: 1px solid #e1e1e1; padding: 4px 8px; text-align: left; }
`;

function renderTemplate(opts: {
  reportName: string;
  css: string;
  runtimeScript: string;
  dataJson: string;
  compatibility: DashboardIR["compatibility"];
}): string {
  const rows = opts.compatibility.items
    .map(
      (item) =>
        `<tr><td>${escapeHtml(item.objectType)}</td><td>${escapeHtml(item.objectId)}</td><td>${escapeHtml(item.status)}</td><td>${escapeHtml(item.notes ?? "")}</td></tr>`,
    )
    .join("\n");

  return `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data: blob:; font-src data:; connect-src 'none';" />
<title>${escapeHtml(opts.reportName)} — PBIX2HTML Studio export</title>
<style>${opts.css}</style>
</head>
<body>
<div id="pbix2html-root"></div>
<details class="pbix-fidelity-report">
<summary>Conversion fidelity report (overall: ${escapeHtml(opts.compatibility.overallFidelity)})</summary>
<table>
<thead><tr><th>Object type</th><th>Object</th><th>Fidelity</th><th>Notes</th></tr></thead>
<tbody>
${rows}
</tbody>
</table>
</details>
<script id="pbix2html-ir-data" type="application/json">${opts.dataJson}</script>
<script>window.__PBIX2HTML_IR__ = JSON.parse(document.getElementById("pbix2html-ir-data").textContent);</script>
<script>${opts.runtimeScript}</script>
</body>
</html>
`;
}
