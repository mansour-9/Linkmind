import { test, expect } from "@playwright/test";

const headers = { Authorization: "Bearer demo-amal" };

test("uploads support approximate discovery, clarification and scoped follow-ups", async ({ page, request }) => {
  expect(process.env.BRAIN_E2E_DISPOSABLE).toBe("1");
  expect((await (await request.get("/api/v1/runtime", { headers })).json()).provider).toBe("mock");
  const jobs: any[] = [];
  await page.setViewportSize({ width: 1440, height: 1000 });
  const files = [
    ["Harbor_ChatPilot_PRFAQ.md", "The harbor support pilot is owned by Leena. Its rehearsal is January 12, 2027."],
    ["Harbor_ChatPilot_PRFAQ_Updated.md", "The harbor support pilot draft is owned by Omar. Its proposed rehearsal is January 19, 2027."],
    ["Harbor_Travel_Workshop.md", "The travel workshop is coordinated by Sara and takes place in Riyadh."],
  ];
  try {
    for (const [name, text] of files) {
      const result = await request.post("/api/v1/sources/upload", { headers, multipart: {
        file: { name, mimeType: "text/markdown", buffer: Buffer.from(text) }, visibility: "team",
      } });
      expect(result.status()).toBe(202);
      jobs.push(await result.json());
    }
    for (const job of jobs) {
      await expect.poll(async () => (await (await request.get("/api/v1/jobs/" + job.id, { headers })).json()).search_status).toBe("ready");
    }
    await page.goto("/");
    await expect(page.getByRole("link", { name: "Add documents", exact: true })).toHaveAttribute("href", "/admin/sources");
    const send = async (question: string) => {
      await page.getByLabel("Ask a question").fill(question);
      await page.getByRole("button", { name: "Send question", exact: true }).click();
      await expect(page.locator(".pending-turn")).toHaveCount(0);
    };
    await send("what is this caht do ?");
    await expect(page.locator(".answer-message").last()).toContainText("Add data source");
    await send("is there any file called ChatPilot PREFQA?");
    await expect(page.locator(".chat-turn").last().getByLabel("Matching sources")).toContainText("Harbor_ChatPilot_PRFAQ_Updated.md");
    await expect(page.locator(".chat-turn").last()).not.toContainText("Sonnet");
    for (const width of [1440, 1024, 390, 1920]) {
      await page.setViewportSize({ width, height: 1000 });
      expect(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)).toBe(false);
      await page.screenshot({ path: `results/screens/conversational-choices-${width}.png`, fullPage: true });
    }
    await page.setViewportSize({ width: 1440, height: 1000 });
    const updatedChoice = page.getByRole("button", { name: "Use Harbor_ChatPilot_PRFAQ_Updated.md", exact: true });
    await updatedChoice.focus();
    await updatedChoice.press("Enter");
    await expect(page.locator(".answer-statement").last()).toContainText("Omar");
    await send("who owns it?");
    await expect(page.locator(".chat-turn").last()).toContainText("Omar");
    await expect(page.locator(".chat-turn").last()).not.toContainText("Leena");
    await send("find files about the travel workshop");
    await expect(page.locator(".chat-turn").last().getByLabel("Matching sources")).toContainText("Harbor_Travel_Workshop.md");
    await expect(page.locator(".chat-turn").last()).not.toContainText("ChatPilot");
    await page.screenshot({ path: "results/screens/conversational-1440.png", fullPage: true });
    await page.setViewportSize({ width: 390, height: 900 });
    expect(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)).toBe(false);
    await page.screenshot({ path: "results/screens/conversational-390.png", fullPage: true });
  } finally {
    for (const job of jobs) await request.delete("/api/v1/documents/" + job.document_id, { headers });
  }
});
