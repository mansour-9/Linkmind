import { test, expect } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

const auth = (token = "demo-amal") => ({ Authorization: "Bearer " + token });

test.beforeAll(() => {
  expect(process.env.BRAIN_E2E_DISPOSABLE, "Readiness checks require a disposable mock database").toBe("1");
});

test("ordinary source text is ready without enrichment and optional failures do not hide it", async ({ page, request }) => {
  const marker = "ReadinessBrowser" + Date.now();
  const name = marker + ".md";
  const text = marker + " confirms the release review is on Thursday.\n";
  let documentId: string | undefined;
  try {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto("/admin/sources");
    await page.getByRole("button", { name: "Add data source", exact: true }).click();
    await page.getByLabel("Choose file").setInputFiles({ name, mimeType: "text/markdown", buffer: Buffer.from(text) });
    await page.getByRole("button", { name: "Upload file", exact: true }).click();
    await expect(page.getByRole("dialog")).toHaveCount(0);
    const source = page.locator(".upload-list > li").filter({ hasText: name });
    await expect(source).toContainText("Search Ready");
    await expect(source).toContainText("Ready for search and answers");
    const sources = await (await request.get("/api/v1/sources", { headers: auth() })).json();
    const job = sources.find((j: any) => j.filename === name);
    documentId = job.document_id;
    expect(job.status).toBe("ready");
    expect(job.enrichment_status).toBe("not_requested");
    expect(job.enrichment_requested).toBe(false);
    expect(job.search_status).toBe("ready");
    expect(job.entity_count).toBe(0);
    const shared=await (await request.get("/api/v1/search?q=" + marker, { headers: auth("demo-omar") })).json();
    expect(shared.some((p:any)=>p.document_id===documentId)).toBe(true);
    expect(await (await request.get("/api/v1/search?q=" + marker, { headers: auth("demo-nour") })).json()).toEqual([]);
    await page.goto("/search?q=" + marker);
    await expect(page.locator(".search-result")).toContainText(text.trim());
    await page.getByRole("button", { name: "Open source passage", exact: true }).click();
    await expect(page.locator(".source-quote")).toContainText(text.trim());
    const download = page.waitForEvent("download");
    await page.getByRole("button", { name: "Download original", exact: true }).click();
    expect((await download).suggestedFilename()).toBe(name);
    await page.keyboard.press("Escape");
    // Enrichment is an explicit action, with an honest unsupported-mock failure.
    expect((await request.post(`/api/v1/jobs/${job.id}/reprocess`, { headers: auth() })).status()).toBe(202);
    await expect.poll(async () => (await (await request.get(`/api/v1/jobs/${job.id}`, { headers: auth() })).json()).status).toBe("enrichment_staged_failed");
    await page.goto("/admin/processing");
    const card = page.locator(".process-card").filter({ hasText: name });
    await expect(card).toContainText("Search Ready");
    await card.getByRole("button", { name: "Retry enrichment", exact: true }).click();
    await expect.poll(async () => (await (await request.get("/api/v1/jobs/" + job.id, { headers: auth() })).json()).attempt_history.length).toBe(3);
    await expect(card).toContainText("Knowledge refresh failed");
    await card.scrollIntoViewIfNeeded();
    await page.screenshot({ path: "results/screens/f11-1440-processing.png", fullPage: true });
    await card.getByRole("button", { name: "Processing details", exact: true }).click();
    await expect(page.getByRole("dialog")).toContainText("Search: ready");
    await expect(page.getByRole("dialog").locator(".knowledge-card")).toHaveCount(3);
    await page.keyboard.press("Escape");
    await expect(card.getByRole("button", { name: "Processing details", exact: true })).toBeFocused();
    await page.setViewportSize({ width: 390, height: 900 });
    await card.scrollIntoViewIfNeeded();
    expect(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)).toBe(false);
    await page.screenshot({ path: "results/screens/f11-390-processing.png", fullPage: true });
    await page.goto("/");
    await page.getByLabel("Ask a question").fill(marker);
    await page.getByRole("button", { name: "Send question", exact: true }).click();
    await expect(page.locator(".answer-statement")).toContainText(text.trim());
    await expect(page.locator('.answer-provider')).toContainText('Demo');
  } finally {
    if (documentId) await request.delete("/api/v1/documents/" + documentId, { headers: auth() });
  }
});

test("a search-ready replacement hides old graph facts and suppresses saved answers", async ({ page, request }) => {
  const uploaded = await request.post("/api/v1/sources/upload", { headers: auth(), multipart: {
    file: { name: "readiness-original.md", mimeType: "text/markdown", buffer: fs.readFileSync(path.resolve("../fixtures/benchmark/alpha-architecture.md")) }, visibility: "team",
  } });
  expect(uploaded.ok()).toBeTruthy();
  const old = await uploaded.json();
  try {
    await expect.poll(async () => (await (await request.get("/api/v1/jobs/" + old.id, { headers: auth() })).json()).status).toBe("ready");
    expect((await request.post(`/api/v1/jobs/${old.id}/reprocess`, { headers: auth() })).status()).toBe(202);
    await expect.poll(async () => (await (await request.get("/api/v1/jobs/" + old.id, { headers: auth() })).json()).enrichment_status).toBe("ready");
    const prior = await (await request.get("/api/v1/search?q=CB-ALPHA&document_id=" + old.document_id, { headers: auth() })).json();
    expect(prior.length).toBeGreaterThan(0);
    const conversation = await (await request.post("/api/v1/conversations", { headers: auth(), data: { document_ids: [old.document_id] } })).json();
    expect((await request.post("/api/v1/conversations/" + conversation.id + "/answers", { headers: auth(), data: { question: "CB-ALPHA" } })).ok()).toBeTruthy();
    const marker = "ReplacementBrowser" + Date.now();
    const revised = await (await request.post("/api/v1/documents/" + old.document_id + "/revisions", { headers: auth(), multipart: {
      file: { name: marker + ".md", mimeType: "text/markdown", buffer: Buffer.from(marker + " is the current source text.") },
    } })).json();
    await expect.poll(async () => (await (await request.get("/api/v1/jobs/" + revised.id, { headers: auth() })).json()).search_status).toBe("ready");
    const graph = await (await request.get("/api/v1/graph", { headers: auth() })).json();
    expect(graph.nodes.every((n: any) => n.version_id !== old.version_id)).toBe(true);
    expect(graph.edges.every((e: any) => !prior.some((p: any) => p.id === e.chunk_id))).toBe(true);
    const history = await (await request.get("/api/v1/conversations/" + conversation.id, { headers: auth() })).json();
    expect(history.turns[0].suppressed).toBe(true);
    expect(history.turns[0].response).toBeNull();
    expect((await request.get("/api/v1/evidence/" + prior[0].id, { headers: auth() })).ok()).toBeTruthy();
    await page.goto("/search?q=" + marker);
    await expect(page.locator(".search-result")).toContainText(marker);
    const forbidden = await request.get("/api/v1/search?q=" + marker, { headers: auth("demo-nour") });
    expect(await forbidden.json()).toEqual([]);
  } finally {
    await request.delete("/api/v1/documents/" + old.document_id, { headers: auth() });
  }
});

test("semantic outage is disclosed even when text search finds no matches", async ({ page }) => {
  await page.route("**/api/v1/search?**", route => route.fulfill({ status: 200,
    headers: { "Content-Type": "application/json", "X-Linkmind-Semantic-Status": "failed" }, body: "[]" }));
  await page.goto("/search?q=no-matches-during-semantic-outage");
  await expect(page.getByText("Semantic search is temporarily unavailable. Showing text matches.")).toBeVisible();
  await expect(page.getByText("No matching evidence. Try an exact project identifier or a different phrase.")).toBeVisible();
});
