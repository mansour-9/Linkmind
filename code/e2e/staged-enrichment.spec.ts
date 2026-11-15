import { test, expect } from "@playwright/test";

const headers = { Authorization: "Bearer demo-amal" };
test.beforeAll(async ({ request }) => {
  expect(process.env.BRAIN_E2E_DISPOSABLE).toBe("1");
  expect((await (await request.get("/api/v1/runtime", { headers })).json()).provider).toBe("mock");
});

test("optional enrichment preserves source-only answers and original citations", async ({ page, request }) => {
  const bytes = await (await request.get("/api/v1/demo/fixtures/cloud-migration", { headers })).body();
  // A distinct owner avoids reusing the already enriched legacy fixture from API tests.
  const uploaded = await request.post("/api/v1/sources/upload", { headers: { Authorization: "Bearer demo-omar" }, multipart: {
    file: { name: "f13-cloud-migration.md", mimeType: "text/markdown", buffer: bytes }, visibility: "team",
  } });
  expect(uploaded.status()).toBe(202);
  const job = await uploaded.json();
  try {
    await expect.poll(async () => (await (await request.get("/api/v1/jobs/" + job.id, { headers })).json()).status).toBe("ready");
    const before = await (await request.get("/api/v1/search?q=Project%20Alpha&document_id=" + job.document_id, { headers })).json();
    const conversation = await (await request.post("/api/v1/conversations", { headers, data: { document_ids: [job.document_id] } })).json();
    const overview = await request.post(`/api/v1/conversations/${conversation.id}/answers`, { headers, data: { question: "summarize this document" } });
    expect(overview.ok()).toBeTruthy();
    const originalPassages = (await overview.json()).evidence.map((p: any) => p.id).sort();
    await page.goto("/admin/sources");
    const row = page.locator(`[data-source-id="${job.document_id}"]`).first();
    await row.getByText("Manage source", { exact: true }).click();
    await expect(row).toContainText("Ready for search and answers");
    await row.getByRole("button", { name: "Enrich knowledge", exact: true }).click();
    const dialog = page.getByRole("dialog", { name: "Enrich knowledge", exact: true });
    await expect(dialog).toContainText("Search stays available");
    await expect(dialog).toContainText("not needed for search or answers");
    const queued = page.waitForResponse(response => response.url().endsWith(`/jobs/${job.id}/reprocess`) && response.request().method() === "POST");
    await dialog.getByRole("button", { name: "Start enrichment", exact: true }).click();
    const queueResponse = await queued;
    expect(queueResponse.status()).toBe(202);
    expect((await queueResponse.json()).staged_version_id).toBeTruthy();
    await expect.poll(async () => (await (await request.get("/api/v1/jobs/" + job.id, { headers })).json()).staged_activation_state).toBe("live");
    const after = await (await request.get("/api/v1/search?q=Project%20Alpha&document_id=" + job.document_id, { headers })).json();
    // First enrichment can add graph-assisted search candidates. Citation passages,
    // complete source overview and original bytes must remain unchanged.
    expect(before.every((p: any) => after.some((item: any) => item.id === p.id))).toBe(true);
    for (const p of before) expect((await request.get("/api/v1/evidence/" + p.id, { headers })).ok()).toBeTruthy();
    expect(await (await request.get(`/api/v1/documents/${job.version_id}/download`, { headers })).body()).toEqual(bytes);
    const nextOverview = await request.post(`/api/v1/conversations/${conversation.id}/answers`, { headers, data: { question: "summarize this document" } });
    expect(nextOverview.ok()).toBeTruthy();
    expect((await nextOverview.json()).evidence.map((p: any) => p.id).sort()).toEqual(originalPassages);
    const history = await (await request.get(`/api/v1/conversations/${conversation.id}`, { headers })).json();
    expect(history.turns[0].suppressed).toBe(false);
    await page.goto("/admin/processing");
    const card = page.locator(".process-card").filter({ hasText: job.filename }).first();
    await expect(card).toContainText("Search Ready");
    await expect(card).toContainText("Knowledge Enriched");
  } finally {
    await request.delete("/api/v1/documents/" + job.document_id, { headers });
  }
});

test("a failed refresh remains search ready and reports the actual failure", async ({ page, request }) => {
  const name = "f13-arbitrary-" + Date.now() + ".txt";
  const uploaded = await request.post("/api/v1/sources/upload", { headers, multipart: {
    file: { name, mimeType: "text/plain", buffer: Buffer.from("StagedUnknownZebra remains available even without a configured extraction model.") }, visibility: "team",
  } });
  const job = await uploaded.json();
  try {
    await expect.poll(async () => (await (await request.get("/api/v1/jobs/" + job.id, { headers })).json()).status).toBe("ready");
    expect((await request.post(`/api/v1/jobs/${job.id}/reprocess`, { headers })).status()).toBe(202);
    await expect.poll(async () => (await (await request.get("/api/v1/jobs/" + job.id, { headers })).json()).status).toBe("enrichment_staged_failed");
    await page.goto("/admin/processing");
    const card = page.locator(".process-card").filter({ hasText: name });
    await expect(card).toContainText("Knowledge refresh failed");
    await expect(card).toContainText("Refresh rolled back");
    await expect(card).toContainText("Search Ready");
    await expect(card).not.toContainText("Previous verified knowledge is still available");
    await expect(card.getByRole("button", { name: "Retry enrichment", exact: true })).toBeVisible();
    await expect.poll(async () => (await (await request.get(`/api/v1/search?q=StagedUnknownZebra&document_id=${job.document_id}`, { headers })).json()).length).toBeGreaterThan(0);
    for (const width of [1440, 1024, 390, 1920]) {
      await page.setViewportSize({ width, height: 1000 });
      await card.scrollIntoViewIfNeeded();
      expect(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)).toBe(false);
      await page.screenshot({ path: `results/screens/f13-processing-${width}.png`, fullPage: true });
    }
  } finally {
    await request.delete("/api/v1/documents/" + job.document_id, { headers });
  }
});
