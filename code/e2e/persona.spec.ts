import { test, expect } from "@playwright/test";

test("Linkmind introduces itself naturally and gives only the help requested", async ({ page, request }) => {
  expect(process.env.BRAIN_E2E_DISPOSABLE).toBe("1");
  expect((await (await request.get("/api/v1/runtime", { headers: { Authorization: "Bearer demo-amal" } })).json()).provider).toBe("mock");
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto("/");
  const send = async (question: string) => {
    await page.getByLabel("Ask a question").fill(question);
    await page.getByRole("button", { name: "Send question", exact: true }).click();
    await expect(page.locator(".pending-turn")).toHaveCount(0);
    return page.locator(".chat-turn").last();
  };
  const greeting = await send("hi");
  await expect(greeting).toContainText("I'm Linkmind");
  await expect(greeting).toContainText("👋");
  await expect(greeting).not.toContainText("Supported files");
  const capabilities = await send("what is u can do form me ?");
  await expect(capabilities).toContainText("find answers");
  await expect(capabilities).not.toContainText("Admin Console");
  expect((await capabilities.locator(".answer-message").innerText()).length).toBeLessThan(250);
  const thanks = await send("thanks");
  await expect(thanks.locator(".answer-message")).toHaveText("You're welcome 🙂");
  const identity = await send("مين انت؟");
  await expect(identity).toContainText("أنا Linkmind");
  await expect(identity.locator(".answer-provider")).toHaveCount(0);
  for (const width of [1440, 390]) {
    await page.setViewportSize({ width, height: 1000 });
    expect(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)).toBe(false);
    await page.screenshot({ path: `results/screens/linkmind-persona-${width}.png`, fullPage: true });
  }
  const upload = await send("how do I upload a file?");
  await expect(upload).toContainText("Open Documents and choose Add document");
});
