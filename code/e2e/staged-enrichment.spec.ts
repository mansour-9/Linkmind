import { test, expect } from "@playwright/test";

const headers = { Authorization: "Bearer demo-amal" };
test.beforeAll(async ({ request }) => {
  expect(process.env.BRAIN_E2E_DISPOSABLE).toBe("1");
  expect((await (await request.get("/api/v1/runtime", { headers })).json()).provider).toBe("mock");
});

test("refresh verifies a replacement while preserving search and original citations", async ({ page, request }) => {
  const bytes = await (await request.get("/api/v1/demo/fixtures/cloud-migration", { headers })).body();
  const uploaded = await request.post("/api/v1/sources/upload", { headers, multipart: {
    file: { name: "f13-cloud-migration.md", mimeType: "text/markdown", buffer: bytes }, visibility: "team",
  } });
  expect(uploaded.status()).toBe(202);
  const job = await uploaded.json();
  try {
    await expect.poll(async () => (await (await request.get("/api/v1/jobs/" + job.id, { headers })).json()).status).toBe("ready");
    const before = await (await request.get("/api/v1/search?q=Project%20Alpha&document_id=" + job.document_id, { headers })).json();
    const conversation = await (await request.post("/api/v1/conversations", { headers, data: { document_ids: [job.document_id] } })).json();
    expect((await request.post(`/api/v1/conversations/${conversation.id}/answers`, { headers, data: { question: "Project Alpha" } })).ok()).toBeTruthy();
    await page.goto("/admin/sources");
    const row = page.locator(`[data-source-id="${job.document_id}"]`).first();
    await row.getByText("Manage source", { exact: true }).click();
    await row.getByRole("button", { name: "Refresh knowledge", exact: true }).click();
    const dialog = page.getByRole("dialog", { name: "Refresh knowledge", exact: true });
    await expect(dialog).toContainText("Search stays available");
    const queued = page.waitForResponse(response => response.url().endsWith(`/jobs/${job.id}/reprocess`) && response.request().method() === "POST");
    await dialog.getByRole("button", { name: "Start refresh", exact: true }).click();
    const queueResponse = await queued;
    expect(queueResponse.status()).toBe(202);
    expect((await queueResponse.json()).staged_version_id).toBeTruthy();
    await expect.poll(async () => (await (await request.get("/api/v1/jobs/" + job.id, { headers })).json()).staged_activation_state).toBe("live");
    const after = await (await request.get("/api/v1/search?q=Project%20Alpha&document_id=" + job.document_id, { headers })).json();
    expect(after.map((p: any) => p.id).sort()).toEqual(before.map((p: any) => p.id).sort());
    expect((await request.get("/api/v1/evidence/" + before[0].id, { headers })).ok()).toBeTruthy();
    const history = await (await request.get(`/api/v1/conversations/${conversation.id}`, { headers })).json();
    expect(history.turns[0].suppressed).toBe(true);
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
    await expect.poll(async () => (await (await request.get("/api/v1/jobs/" + job.id, { headers })).json()).status).toBe("extraction_unavailable");
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
