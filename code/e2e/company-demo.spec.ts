import { test, expect } from "@playwright/test";

const headers = { Authorization: "Bearer demo-amal" };
test.beforeAll(async ({ request }) => {
  expect(process.env.BRAIN_E2E_DISPOSABLE).toBe("1");
  expect((await (await request.get("/api/v1/runtime", { headers })).json()).provider).toBe("mock");
});

test("fictional company questions open scoped chat and explain selected documents", async ({ page, request }) => {
  const loaded = await request.post("/api/v1/demo/company/load", { headers });
  expect(loaded.ok()).toBeTruthy();
  await expect.poll(async () => (await (await request.get("/api/v1/demo/company/status", { headers })).json()).enriched, { timeout: 90000 }).toBe(24);
  await page.goto("/admin/sources");
  await page.getByText("Try sample documents", { exact: false }).click();
  const panel = page.getByRole("region", { name: "Fictional company testing", exact: true });
  await expect(panel).toContainText("24 / 24 search ready");
  await panel.getByText("Example questions and expected results", { exact: true }).click();
  await panel.getByRole("link", { name: "What is this document about?", exact: true }).click();
  await expect(page.locator(".selected-source-chip")).toContainText("atlas-handover.md");
  await page.getByLabel("Ask a question").fill("what is that ?");
  await page.getByRole("button", { name: "Send question", exact: true }).click();
  await expect(page.locator(".answer-statement").first()).toBeVisible();
  await expect(page.locator(".answer-provider").first()).toContainText("Demo");
  await expect(page.getByText("I couldn’t find enough evidence", { exact: false })).toHaveCount(0);
  await page.getByText("Show work", { exact: false }).click();
  await expect(page.getByRole("heading", { name: "Cited evidence", exact: true })).toBeVisible();
  await page.screenshot({ path: "results/screens/company-selected-overview-1440.png", fullPage: true });
  await page.setViewportSize({ width: 390, height: 900 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)).toBe(false);
  await page.screenshot({ path: "results/screens/company-selected-overview-390.png", fullPage: true });
});

test("greetings give guidance and new information stays searchable in mock mode", async ({ page, request }) => {
  await page.goto("/");
  await page.getByLabel("Ask a question").fill("hi");
  await page.getByRole("button", { name: "Send question", exact: true }).click();
  await expect(page.locator(".answer-message")).toContainText("Linkmind");
  await expect(page.getByText("Show work", { exact: false })).toHaveCount(0);
  await page.goto("/admin/sources");
  await page.getByText("Try sample documents", { exact: false }).click();
  const panel = page.getByRole("region", { name: "Fictional company testing", exact: true });
  await panel.getByText("Add information or test a revision", { exact: true }).click();
  const download = page.waitForEvent("download");
  await panel.getByRole("button", { name: "Download an addition to upload", exact: true }).click();
  const file = await download;
  const filePath = await file.path();
  expect(filePath).toBeTruthy();
  await page.getByRole("button", { name: "Add data source", exact: true }).click();
  await page.getByLabel("Choose file").setInputFiles({ name: "company-user-addition.txt", mimeType: "text/plain", buffer: await (await import("node:fs/promises")).readFile(filePath!) });
  await page.getByRole("button", { name: "Upload file", exact: true }).click();
  const row = page.locator(".upload-list > li").filter({ hasText: "company-user-addition.txt" });
  await expect(row).toContainText("Search Ready");
  await expect(row).toContainText("Enrichment unavailable");
  const jobs = await (await request.get("/api/v1/sources", { headers })).json();
  const job = jobs.find((j: any) => j.filename === "company-user-addition.txt");
  try {
    await page.goto("/search?q=support%20drill&document_id=" + job.document_id);
    await expect(page.locator(".search-result")).toContainText("2026-12-15");
  } finally {
    await request.delete("/api/v1/documents/" + job.document_id, { headers });
  }
});
