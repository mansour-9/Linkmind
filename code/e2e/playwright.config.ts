import { defineConfig } from "@playwright/test";
export default defineConfig({
 testDir: ".", testMatch: "*.spec.ts", timeout: 120000, workers: 1, expect: { timeout: 10000 },
 use: { baseURL: process.env.BRAIN_URL ?? "http://127.0.0.1:5175",
 browserName: "chromium", channel: "msedge", headless: true, trace: "retain-on-failure" },
 reporter: [["list"], ["json", { outputFile: "results/report.json" }]],
 outputDir: "results/artifacts",
});
