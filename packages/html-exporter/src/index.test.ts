import { describe, expect, it } from "vitest";
import type { DashboardIR } from "@pbix2html/dir-schema";
import { exportSingleFileHtml } from "./index.js";

const fixture: DashboardIR = {
  irVersion: "0.1.0",
  source: { originalFormat: "structured-fixture", adapterId: "test-fixture", storageMode: "import" },
  reportName: "Test Report",
  semanticModel: {
    tables: [{ name: "Sales", columns: [{ name: "Amount", dataType: "number" }] }],
    relationships: [],
    measures: [
      {
        name: "Revenue",
        table: "Sales",
        expression: { kind: "aggregation", fn: "SUM", column: { table: "Sales", column: "Amount" } },
      },
    ],
  },
  data: { snapshotTimestamp: "2026-01-01T00:00:00.000Z", tables: [{ table: "Sales", rows: [{ Amount: 10 }] }] },
  pages: [
    {
      id: "page1",
      name: "Page1",
      displayName: "Page 1",
      width: 1280,
      height: 720,
      visibility: "visible",
      filters: [],
      visuals: [
        {
          id: "card1",
          sourceType: "card",
          normalizedType: "card",
          bounds: { x: 0, y: 0, width: 200, height: 100 },
          zIndex: 0,
          bindings: { values: [{ measure: "Revenue" }] },
          format: { title: "Revenue", showTitle: true },
          filters: [],
          interactions: [],
          fidelity: "EXACT",
        },
      ],
    },
  ],
  interactions: { edges: [] },
  compatibility: {
    overallFidelity: "EXACT",
    items: [{ objectId: "card1", objectType: "visual", status: "EXACT" }],
  },
  provenance: [],
};

describe("exportSingleFileHtml", () => {
  it("produces a self-contained HTML document with no external network references", async () => {
    const { html, warnings } = await exportSingleFileHtml(fixture);

    expect(html).toContain("<!doctype html>");
    expect(html).toContain("Test Report");
    expect(html).toContain('id="pbix2html-root"');
    expect(html).toContain("Content-Security-Policy");
    expect(html).toContain("connect-src 'none'");
    expect(warnings).toEqual([]);

    // No CDN/remote script or stylesheet references anywhere in the document.
    // (The SVG XML namespace URI is a fixed identifier, not a network fetch, so it's exempted.)
    const withoutSvgNamespace = html.replaceAll("http://www.w3.org/2000/svg", "");
    expect(withoutSvgNamespace).not.toMatch(/https?:\/\//);
    expect(html).not.toMatch(/<script[^>]+src=/);
    expect(html).not.toMatch(/<link[^>]+href=/);
  });

  it("embeds the DIR data so the runtime can mount without a network request", async () => {
    const { html } = await exportSingleFileHtml(fixture);
    expect(html).toContain('"reportName":"Test Report"');
    expect(html).toContain("__PBIX2HTML_IR__");
  });

  it("surfaces non-exact fidelity classifications as human-readable warnings", async () => {
    const withWarning: DashboardIR = {
      ...fixture,
      compatibility: {
        overallFidelity: "APPROXIMATED",
        items: [{ objectId: "card1", objectType: "visual", status: "APPROXIMATED", notes: "custom visual fallback" }],
      },
    };
    const { warnings, html } = await exportSingleFileHtml(withWarning);
    expect(warnings).toEqual(['visual "card1": APPROXIMATED — custom visual fallback']);
    expect(html).toContain("custom visual fallback");
  });
});
