import { test, expect, type APIRequestContext, type Page } from "@playwright/test";
import path from "node:path";
import fs from "node:fs";

const auth = (token = "demo-amal") => ({ Authorization: "Bearer " + token });
let charter: any;
let review: any;
let savedConversation: string;
async function upload(request: APIRequestContext, name: string, visibility = "team") {
 const response = await request.post("/api/v1/sources/upload", { headers: auth(), multipart: { file: { name, mimeType: "text/markdown", buffer: fs.readFileSync(path.resolve("../fixtures/benchmark/" + name)) }, visibility } });
 expect(response.ok()).toBeTruthy(); return response.json();
}
async function ready(request: APIRequestContext, id: string) {
 await expect.poll(async () => (await (await request.get("/api/v1/jobs/" + id, { headers: auth() })).json()).status, { timeout: 90000 }).toBe("ready");
}
async function identity(page: Page, token: string) {
 await page.getByRole("button", { name: "Profile and workspace", exact: true }).filter({ visible: true }).first().click();
 await page.getByLabel("Demo identity").selectOption(token);
 await expect(page.getByRole("dialog")).toHaveCount(0);
}
async function noOverflow(page: Page) {
 expect(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)).toBe(false);
}

test.beforeAll(async ({ request }) => {
 expect(process.env.BRAIN_E2E_DISPOSABLE, "Use only a disposable mock-mode validation database; set BRAIN_E2E_DISPOSABLE=1").toBe("1");
 charter = await upload(request, "alpha-charter.md"); review = await upload(request, "alpha-review.md");
 await ready(request, charter.id); await ready(request, review.id);
 const created = await request.post("/api/v1/conversations", { headers: auth(), data: { title: "UI validation · project ownership", document_ids: [charter.document_id] } });
 savedConversation = (await created.json()).id;
 const answer = await request.post("/api/v1/conversations/" + savedConversation + "/answers", { headers: auth(), data: { question: "Who owns CB-ALPHA?" } });
 expect(answer.ok()).toBeTruthy(); expect((await answer.json()).provider).toBe("mock-extractive");
});

test("home → new chat → evidence → download → reload → identity isolation", async ({ page }) => {
 const errors: string[] = []; page.on("pageerror", e => errors.push(e.message));
 await page.setViewportSize({ width: 1440, height: 900 });
 await page.goto("/"); await expect(page.getByRole("heading", { name: "Ask Linkmind" })).toBeVisible();
 await page.getByLabel("Ask a question").fill("Who owns CB-ALPHA?");
 await page.getByRole("button", { name: "Send question" }).click();
 await expect(page).toHaveURL(/\/chat\//);
 await expect(page.locator(".answer-statement").first()).toBeVisible();
 await expect(page.getByLabel("Ask a question")).toHaveValue("");
 await page.getByText("Show work", { exact: false }).click();
 await expect(page.getByRole("heading", { name: "Cited evidence" })).toBeVisible();
 await page.screenshot({ path: "results/screens/1440-show-work.png", fullPage: true });
 await page.locator(".answer-statement").first().getByRole("button").first().click();
 await expect(page.getByRole("dialog", { name: "Source evidence" })).toBeVisible();
 await expect(page.locator(".source-quote")).not.toBeEmpty();
 await page.screenshot({ path: "results/screens/1440-source-preview.png", fullPage: true });
 const download = page.waitForEvent("download"); await page.getByRole("button", { name: "Download original" }).click(); expect((await download).suggestedFilename()).toMatch(/\.md$/);
 await page.keyboard.press("Escape"); await expect(page.locator(".answer-statement").first().getByRole("button").first()).toBeFocused();
 await page.getByLabel("Ask a question").fill("What is the launch date?"); await page.getByLabel("Ask a question").press("Enter");
 await expect(page.locator(".chat-turn")).toHaveCount(2); await expect(page.locator(".pending-turn")).toHaveCount(0);
 await page.reload(); await expect(page.locator(".answer-statement").first()).toBeVisible();
 await identity(page, "demo-nour"); await expect(page.getByRole("heading", { name: "Ask Linkmind" })).toBeVisible();
 await expect(page.locator(".answer-statement")).toHaveCount(0); await page.goto("/chat/" + savedConversation); await expect(page.getByRole("alert")).toContainText("Conversation not found");
 expect(errors).toEqual([]);
});

test("failed submission keeps its conversation and draft, with an explicit retry", async ({ page }) => {
 let attempts = 0;
 await page.route("**/api/v1/conversations/*/answers", async route => { attempts++; if (attempts === 1) await route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ detail: "Answer unavailable for transport regression." }) }); else await route.continue(); });
 await page.goto("/"); await page.getByLabel("Ask a question").fill("Who owns CB-ALPHA?"); await page.getByRole("button", { name: "Send question" }).click();
 await expect(page).toHaveURL(/\/chat\//); const url = page.url();
 await expect(page.getByRole("alert")).toContainText("Answer unavailable"); await expect(page.getByLabel("Ask a question")).toHaveValue("Who owns CB-ALPHA?");
 await page.getByRole("button", { name: "Send question" }).click(); await expect(page.locator(".answer-statement").first()).toBeVisible(); expect(page.url()).toBe(url); expect(attempts).toBe(2);
});

test("topic discovery, multi-source selection, reload and clearing scope", async ({ page, request }) => {
 await page.goto("/"); await expect(page.getByText("All sources", { exact: true })).toBeVisible();
 await page.getByRole("button", { name: "Focus sources", exact: true }).click();
 await expect(page.getByLabel("Find sources by topic")).toBeFocused();
 await page.getByLabel("Find sources by topic").fill("CB-ALPHA"); await page.getByLabel("Find sources by topic").press("Enter");
 await expect(page.locator(".source-picker-result").filter({ hasText: "alpha-charter.md" })).toContainText("Content match");
 await expect(page.locator(".picker-excerpt").first()).not.toBeEmpty();
 await page.getByLabel("Select alpha-charter.md", { exact: true }).check(); await page.getByLabel("Select alpha-review.md", { exact: true }).check();
 await page.screenshot({ path: "results/screens/focus-sources-topic-search.png", fullPage: true });
 await page.getByRole("button", { name: "Apply selection", exact: true }).click();
 await expect(page.locator(".selected-source-chip")).toHaveCount(2);
 await page.getByLabel("Ask a question").fill("Who owns CB-ALPHA?"); await page.getByRole("button", { name: "Send question" }).click(); await expect(page.locator(".answer-statement").first()).toBeVisible();
 const id=page.url().split("/chat/")[1]; const history=await (await request.get("/api/v1/conversations/"+id,{headers:auth()})).json(); expect(new Set(history.document_ids)).toEqual(new Set([charter.document_id,review.document_id]));
 await page.reload(); await expect(page.locator(".selected-source-chip")).toHaveCount(2); await expect(page.locator(".selected-source-chips")).toContainText("alpha-charter.md");
 await page.getByLabel("Ask a question").fill("Keep my question"); await page.getByRole("button", { name: "Use all sources", exact: true }).click();
 await expect(page.getByRole("heading", { name: "Ask Linkmind" })).toBeVisible(); await expect(page.getByLabel("Ask a question")).toHaveValue("Keep my question"); await expect(page.locator(".selected-source-chip")).toHaveCount(0); await expect(page.getByText("All sources", { exact: true })).toBeVisible();
});

test("source picker keeps drafts private until apply and works on mobile", async ({ page }) => {
 await page.setViewportSize({width:390,height:900}); await page.goto("/chat/"+savedConversation);
 await expect(page.locator(".selected-source-chip")).toHaveCount(1);
 await page.getByLabel("Ask a question").fill("Draft stays intact"); await page.getByRole("button", {name:"Focus sources",exact:true}).click();
 await page.getByLabel("Select alpha-review.md",{exact:true}).check(); await page.keyboard.press("Escape");
 await expect(page.getByRole("button", {name:"Focus sources",exact:true})).toBeFocused(); await expect(page.locator(".selected-source-chip")).toHaveCount(1); await expect(page.getByLabel("Ask a question")).toHaveValue("Draft stays intact");
 await page.getByRole("button", {name:"Focus sources",exact:true}).click(); await page.getByLabel("Find sources by topic").fill("no-such-topic-928374"); await page.getByLabel("Find sources by topic").press("Enter"); await expect(page.getByRole("heading",{name:"No matching sources"})).toBeVisible();
 await page.screenshot({path:"results/screens/390-focus-sources-empty.png",fullPage:true}); await noOverflow(page); await page.keyboard.press("Escape");
});

test("legacy links preserve conversation, entity and graph parameters", async ({ page, request }) => {
 await page.goto("/ask?conversation=" + savedConversation); await expect(page).toHaveURL(new RegExp("/chat/" + savedConversation));
 const entities = await (await request.get("/api/v1/wiki", { headers: auth() })).json(); const project = entities.find((e: any) => e.kind === "project");
 await page.goto("/wiki?page=" + project.id); await expect(page).toHaveURL(new RegExp("/content/" + project.id)); await expect(page.locator(".wiki-title")).toHaveText(project.name);
 await page.goto("/graph?node=" + project.id + "&kind=project"); await expect(page).toHaveURL(new RegExp("/graph\\?node=" + project.id + "&kind=project")); await expect(page.locator(".react-flow")).toBeVisible();
 for (const route of ["sources", "processing", "conflicts", "usage", "settings"]) { await page.goto("/" + route + "?keep=1"); await expect(page).toHaveURL(new RegExp("/admin/" + route + "\\?keep=1")); }
});

test("search filters, content, people and graph link to real evidence", async ({ page }) => {
 await page.goto("/search?q=CB-ALPHA"); await expect(page.locator(".search-result").first()).toBeVisible();
 await page.getByLabel("Source", { exact: true }).selectOption(charter.document_id); await expect(page).toHaveURL(/document_id=/);
 await page.locator(".search-result").first().getByRole("button", { name: "Open source passage" }).click(); await expect(page.locator(".source-quote")).not.toBeEmpty(); await page.keyboard.press("Escape");
 await page.goto("/people"); await page.getByLabel("Find a person").fill("Amal"); await page.locator(".knowledge-row").first().click(); await expect(page.locator(".wiki-title")).toContainText("Amal");
 await page.getByRole("link", { name: "Explore connections" }).click(); await expect(page.locator(".react-flow")).toBeVisible();
 await page.getByRole("button", { name: "List", exact: true }).click(); await expect(page.locator(".graph-list-view")).toBeVisible(); await page.locator(".graph-list-view > button").first().click(); await expect(page.locator(".inspector-identity")).toBeVisible();
 await page.getByRole("tab", { name: /Connections/ }).click(); await page.locator(".connection-evidence").first().click(); await expect(page.locator(".inspector-evidence .source-quote")).not.toBeEmpty();
});
test("graph demo loads, reuses uploads and connects shared people with real evidence", async ({ page, request }) => {
 await page.goto("/graph"); await page.getByRole("button", { name: "Load graph demo", exact: true }).click();
 await expect(page.locator(".graph-demo-message")).toContainText("38 entities and 105 relationships", { timeout: 90000 });
 await expect(page.locator(".graph-demo-message")).toContainText("76 cited occurrences");
 const first=await (await request.get("/api/v1/demo/graph-dataset/status",{headers:auth()})).json(); expect(first.ready).toBe(true);
 await page.getByRole("button", { name: "Load graph demo", exact: true }).click(); await expect(page.locator(".graph-demo-message")).toContainText("38 entities and 105 relationships");
 const again=await (await request.get("/api/v1/demo/graph-dataset/status",{headers:auth()})).json(); expect(again.jobs.map((j:any)=>j.id)).toEqual(first.jobs.map((j:any)=>j.id));
 await page.getByLabel("Find an entity").fill("DEMO-ATLAS"); await expect(page.locator(".entity-result").first()).toContainText("Project Atlas");
 await page.getByRole("button", { name: "Center graph on Project Atlas", exact: true }).click(); await expect(page.locator(".inspector-identity")).toContainText("Project Atlas");
 await expect.poll(()=>page.locator(".graph-node").count()).toBeGreaterThan(1);
 const immediateNodes=await page.locator(".graph-node").count();
 await page.getByLabel("Exploration depth").selectOption("3"); await expect.poll(()=>page.locator(".graph-node").count()).toBeGreaterThan(immediateNodes);
 await page.screenshot({path:"results/screens/graph-demo-atlas.png",fullPage:true});
 await page.getByLabel("Find an entity").fill("amal@demo.linkmind.local"); await expect(page.locator(".entity-result")).toHaveCount(1); await page.getByRole("button", {name:"Center graph on Amal",exact:true}).click();
 await page.getByRole("tab", {name:/Connections/}).click(); await expect(page.locator(".explorer-inspector")).toContainText("Project Atlas");
 await expect(page.locator(".explorer-inspector")).toContainText("Project Delta");
 await page.locator(".connection-evidence").first().click(); await expect(page.locator(".source-quote")).toContainText("Amal");
 await page.screenshot({path:"results/screens/graph-demo-evidence.png",fullPage:true});
 await page.goto("/search?q=DEMO-ATLAS"); await expect(page.getByRole("region", { name: "Connected knowledge" })).toContainText("Project Atlas");
 for(const job of first.jobs) await request.delete("/api/v1/documents/"+job.document_id,{headers:auth()});
});

test("canvas-only view fills the page and preserves the graph when exiting", async ({ page }) => {
 await page.goto("/graph"); await page.getByLabel("Find an entity").fill("CB-ALPHA");
 await page.getByRole("button", {name:"Center graph on Project Alpha",exact:true}).click();
 await expect.poll(()=>page.locator(".graph-node").count()).toBeGreaterThan(1);
 const url=page.url(); const count=await page.locator(".graph-node").count();
 const positions=await page.locator(".react-flow__node").evaluateAll(nodes=>nodes.map(n=>({id:n.getAttribute("data-id"),position:(n as HTMLElement).style.transform})));
 await page.getByRole("button",{name:"Enter canvas-only view",exact:true}).click();
 await expect.poll(()=>page.evaluate(()=>document.fullscreenElement?.getAttribute("aria-label"))).toBe("Knowledge graph canvas");
 await expect.poll(()=>page.locator(".explorer-canvas").evaluate(el=>Math.abs(el.getBoundingClientRect().width-innerWidth)<2 && Math.abs(el.getBoundingClientRect().height-innerHeight)<2)).toBe(true);
 await expect(page.getByRole("button",{name:"Exit canvas-only view",exact:true})).toBeVisible();
 expect(await page.locator(".graph-node").count()).toBe(count);
 expect(await page.locator(".react-flow__node").evaluateAll(nodes=>nodes.map(n=>({id:n.getAttribute("data-id"),position:(n as HTMLElement).style.transform})))).toEqual(positions);
 await page.screenshot({path:"results/screens/graph-canvas-only.png"});
 await page.keyboard.press("Escape"); await expect.poll(()=>page.evaluate(()=>document.fullscreenElement===null)).toBe(true);
 await expect(page.getByRole("button",{name:"Enter canvas-only view",exact:true})).toBeFocused();
 expect(page.url()).toBe(url); await expect(page.getByLabel("Find an entity")).toBeVisible();
 await page.setViewportSize({width:390,height:844});
 await page.getByRole("button",{name:"Enter canvas-only view",exact:true}).click();
 await expect.poll(()=>page.evaluate(()=>document.fullscreenElement!==null)).toBe(true);
 await noOverflow(page); await page.screenshot({path:"results/screens/390-graph-canvas-only.png"});
 await page.getByRole("button",{name:"Exit canvas-only view",exact:true}).click();
 await expect.poll(()=>page.evaluate(()=>document.fullscreenElement===null)).toBe(true);
 expect(await page.locator(".graph-node").count()).toBe(count);
});

test("graph demo loading failure is shown without a success claim", async ({page}) => {
 await page.route("**/api/v1/demo/graph-dataset/load",route=>route.fulfill({status:503,contentType:"application/json",body:JSON.stringify({detail:"Demo loading temporarily unavailable"})}));
 await page.goto("/graph");await page.getByRole("button",{name:"Load graph demo",exact:true}).click();await expect(page.getByRole("alert")).toContainText("Demo loading temporarily unavailable");await expect(page.locator(".graph-demo-message")).toHaveCount(0);
});

test("workspace search shows connected knowledge and graph expands a focused neighborhood", async ({ page }) => {
 await page.goto("/search?q=CB-ALPHA");
 await expect(page.getByRole("region", { name: "Connected knowledge" })).toBeVisible();
 await expect(page.locator(".search-overview-heading h2")).toHaveText("Project Alpha");
 await page.getByRole("link", { name: "View graph", exact: true }).click(); await expect(page.locator(".react-flow")).toBeVisible();
 await page.getByRole("button", { name: "Expand connections", exact: true }).click();
 await expect(page.locator(".inspector-identity")).toBeVisible();
 await page.getByLabel("Find an entity").fill("Amal"); await expect(page.locator(".entity-result").first()).toContainText("Amal");
 await page.getByRole("button", { name: "Center graph on Amal", exact: true }).first().click(); await expect(page).toHaveURL(/scope=/); await expect(page.locator(".inspector-identity")).toContainText("Amal");
 await page.getByRole("button", { name: "Close inspector" }).click(); await expect(page.locator(".explorer-inspector")).toHaveCount(0);
 await page.getByLabel("Exploration depth").selectOption("2"); await expect(page).toHaveURL(/depth=2/);
 await page.getByRole("button", { name: "List", exact: true }).click(); await expect(page.locator(".graph-list-view")).toBeVisible();
});


test("upload, revision, source management, and processing remain usable", async ({ page, request }) => {
 await page.goto("/content/documents"); await page.getByRole("button", { name: "Add data source" }).click();
 await page.getByLabel("Choose file").setInputFiles({ name: "m31-ui-disposable.txt", mimeType: "text/plain", buffer: Buffer.from("UI disposable source for upload and revision validation.") });
 await page.getByRole("combobox", { name: "Access", exact: true }).selectOption("private"); await page.getByRole("button", { name: "Upload file", exact: true }).click(); await expect(page.getByRole("dialog")).toHaveCount(0);
 const row = page.locator(".upload-list li").filter({ has: page.getByText("m31-ui-disposable.txt", { exact: true }) }); await expect(row).toBeVisible(); await row.locator("summary").filter({ hasText: "Manage source" }).click();
 await row.getByRole("button", { name: "New revision" }).click(); await page.getByLabel("New file").setInputFiles(path.resolve("../fixtures/benchmark/alpha-charter.md")); await page.getByRole("button", { name: "Upload revision", exact: true }).click(); await expect(page.getByRole("dialog")).toHaveCount(0);
 await page.goto("/admin/processing"); await expect(page.locator(".process-card").first()).toBeVisible(); await page.locator(".process-card").first().getByRole("button", { name: "Processing details" }).click(); await expect(page.getByRole("dialog", { name: "Processing details" })).toBeVisible(); await page.keyboard.press("Escape");
 const jobs = await (await request.get("/api/v1/sources", { headers: auth() })).json(); const disposable = jobs.find((j: any) => j.filename === "m31-ui-disposable.txt"); expect(disposable).toBeTruthy();
 await request.delete("/api/v1/documents/" + disposable.document_id, { headers: auth() });
});

test("revoked source suppresses a saved answer and blocks original evidence", async ({ page, request }) => {
 const created = await request.post("/api/v1/conversations", { headers: auth("demo-omar"), data: { title: "UI revocation test", document_ids: [charter.document_id] } }); const conversation = await created.json();
 const response = await request.post("/api/v1/conversations/" + conversation.id + "/answers", { headers: auth("demo-omar"), data: { question: "Who owns CB-ALPHA?" } }); expect(response.ok()).toBeTruthy(); const result = await response.json();
 try {
  await request.patch("/api/v1/documents/" + charter.document_id + "/access", { headers: auth(), data: { visibility: "private" } });
  await page.goto("/"); await identity(page, "demo-omar"); await page.goto("/chat/" + conversation.id);
  await expect(page.getByText("This answer is hidden", { exact: false })).toBeVisible(); await expect(page.locator(".answer-statement")).toHaveCount(0);
  const denied = await request.get("/api/v1/evidence/" + result.evidence[0].id, { headers: auth("demo-omar") }); expect(denied.status()).toBe(404);
 } finally { await request.patch("/api/v1/documents/" + charter.document_id + "/access", { headers: auth(), data: { visibility: "team" } }); }
});

test("conflict review preserves rationale and usage respects roles", async ({ page }) => {
 await page.goto("/admin/conflicts"); const reviewButton = page.getByRole("button", { name: "Review conflict", exact: true }).first(); await expect(reviewButton).toBeVisible(); await reviewButton.click();
 await page.getByLabel("Review rationale").fill("Both original sources remain available; this requires additional evidence."); await page.getByRole("button", { name: "Save review", exact: true }).click(); await expect(page.getByRole("dialog")).toHaveCount(0);
 await page.goto("/admin/usage"); await expect(page.getByRole("heading", { name: "AI Usage", exact: true })).toBeVisible();
 await identity(page, "demo-omar"); await page.goto("/admin/usage"); await expect(page.getByText("AI Usage is available to reviewers and administrators.")).toBeVisible(); await expect(page.locator(".usage-table")).toHaveCount(0);
});

test("safe Markdown handles tables and code without executing source HTML", async ({ page }) => {
 await page.route("**/api/v1/conversations/" + savedConversation, async route => { const response = await route.fetch(); const body = await response.json(); body.turns[0].response.statements[0].text = "## Verified heading\n\n| A | B |\n|---|---|\n| One | Two |\n\n```js\nconst value = 1;\n```\n\n<script>window.uiInjection = true</script>\n\n[unsafe](javascript:alert(1))"; await route.fulfill({ response, json: body }); });
 await page.goto("/chat/" + savedConversation); await expect(page.getByRole("heading", { name: "Verified heading" })).toBeVisible(); await expect(page.locator(".markdown table")).toBeVisible(); await expect(page.locator(".markdown pre")).toContainText("const value = 1");
 expect(await page.evaluate(() => (window as any).uiInjection)).toBeUndefined(); await expect(page.locator('.markdown a[href^="javascript:"]')).toHaveCount(0);
});

test("keyboard composition prevents duplicate submissions and new conversation resets the draft", async ({ page }) => {
 let requests = 0;
 await page.route("**/api/v1/conversations/*/answers", async route => { requests++; await new Promise(resolve => setTimeout(resolve, 300)); await route.continue(); });
 await page.goto("/"); const input = page.getByLabel("Ask a question");
 await input.fill("Who owns CB-ALPHA?"); await input.press("Shift+Enter"); await input.press("A"); expect(requests).toBe(0); await expect(input).toHaveValue("Who owns CB-ALPHA?\nA");
 await input.press("Enter"); await page.keyboard.press("Enter"); await expect(page.locator(".answer-statement").first()).toBeVisible(); expect(requests).toBe(1);
 await page.getByRole("link", { name: "New conversation", exact: true }).first().click(); await expect(page.getByRole("heading", { name: "Ask Linkmind" })).toBeVisible();
 await input.fill("Discard this draft"); await page.getByRole("link", { name: "New conversation", exact: true }).first().click(); await expect(input).toHaveValue("");
});

test("history search and desktop collapse preserve keyboard access", async ({ page }) => {
 await page.setViewportSize({ width: 1440, height: 900 }); await page.goto("/");
 const history = page.getByRole("button", { name: "See all", exact: true }); await history.click(); await page.getByLabel("Find a conversation").fill("UI validation");
 await expect(page.getByRole("dialog").getByRole("link").first()).toContainText("UI validation"); await page.keyboard.press("Escape"); await expect(history).toBeFocused();
 await page.getByRole("button", { name: "Collapse sidebar" }).click(); await expect.poll(() => page.locator(".sidebar").evaluate(el => Math.round(el.getBoundingClientRect().width))).toBe(72);
 await page.getByRole("button", { name: "Expand sidebar" }).click(); await expect.poll(() => page.locator(".sidebar").evaluate(el => Math.round(el.getBoundingClientRect().width))).toBe(280);
});

for (const width of [1440, 1024, 390, 1920]) {
 test("responsive layouts and screenshots at " + width, async ({ page }) => {
  const errors: string[] = []; page.on("pageerror", e => errors.push(e.message)); await page.setViewportSize({ width, height: 900 });
  for (const [name, route] of [["home", "/"], ["conversation", "/chat/" + savedConversation], ["search", "/search?q=CB-ALPHA"], ["people", "/people"], ["content", "/content"], ["graph", "/graph"], ["sources", "/admin/sources"], ["processing", "/admin/processing"], ["conflicts", "/admin/conflicts"], ["usage", "/admin/usage"]]) {
   await page.goto(route); if (name === "conversation") await expect(page.locator(".answer-statement").first()).toBeVisible(); else await expect(page.locator("h1")).toBeVisible(); await page.waitForTimeout(150); await noOverflow(page);
   await page.screenshot({ path: "results/screens/" + width + "-" + name + ".png", fullPage: true });
   if (name === "home" && width === 1440) await expect.poll(() => page.locator(".sidebar").evaluate(el => Math.round(el.getBoundingClientRect().width))).toBe(280);
  }
  if (width === 390) { await page.getByRole("button", { name: "Open navigation" }).click(); await expect(page.getByRole("dialog", { name: "Navigation" })).toBeVisible(); await page.keyboard.press("Escape"); await expect(page.getByRole("button", { name: "Open navigation" })).toBeFocused(); }
  else { await page.getByRole("button", { name: width === 1024 ? "Expand sidebar" : "Collapse sidebar" }).click(); await noOverflow(page); }
  expect(errors).toEqual([]);
 });
}
