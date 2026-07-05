import type { DashboardIR } from "@pbix2html/dir-schema";
import { DashboardRuntime } from "./runtime.js";

declare global {
  interface Window {
    __PBIX2HTML_IR__?: DashboardIR;
  }
}

function boot(): void {
  const ir = window.__PBIX2HTML_IR__;
  const root = document.getElementById("pbix2html-root");
  if (!ir || !root) {
    console.error("PBIX2HTML: missing embedded dashboard data or #pbix2html-root mount point.");
    return;
  }
  new DashboardRuntime(ir, root).mount();
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", boot);
} else {
  boot();
}
