#!/usr/bin/env node
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import type { DashboardIR } from "@pbix2html/dir-schema";
import { exportSingleFileHtml } from "@pbix2html/html-exporter";

interface ParsedArgs {
  command?: string;
  input?: string;
  output?: string;
}

function parseArgs(argv: string[]): ParsedArgs {
  const [command, input, ...rest] = argv;
  let output: string | undefined;
  for (let i = 0; i < rest.length; i++) {
    if (rest[i] === "--output" || rest[i] === "-o") {
      output = rest[i + 1];
      i++;
    }
  }
  return { command, input, output };
}

function printUsage(): void {
  console.error("Usage: pbix2html convert-fixture <dir-fixture.json> --output <dashboard.html>");
  console.error("");
  console.error(
    "Converts a structured Dashboard IR (DIR) fixture — JSON conforming to @pbix2html/dir-schema — into a",
  );
  console.error("portable, offline, single-file interactive HTML dashboard.");
  console.error("");
  console.error("Direct .pbix ingestion is not implemented yet; see ROADMAP.md for the ingestion strategy roadmap.");
}

async function main(): Promise<void> {
  const { command, input, output } = parseArgs(process.argv.slice(2));

  if (command !== "convert-fixture" || !input) {
    printUsage();
    process.exitCode = 1;
    return;
  }

  const outputPath = resolve(output ?? "dashboard.html");
  const irJson = await readFile(resolve(input), "utf-8");
  const ir = JSON.parse(irJson) as DashboardIR;

  const { html, warnings } = await exportSingleFileHtml(ir);

  await mkdir(dirname(outputPath), { recursive: true });
  await writeFile(outputPath, html, "utf-8");

  console.log(`Wrote ${outputPath} (${(html.length / 1024).toFixed(1)} KB)`);
  console.log(`Overall fidelity: ${ir.compatibility.overallFidelity}`);
  if (warnings.length > 0) {
    console.log("Fidelity warnings:");
    for (const warning of warnings) console.log(`  - ${warning}`);
  }
}

main().catch((error) => {
  console.error(error instanceof Error ? (error.stack ?? error.message) : error);
  process.exitCode = 1;
});
