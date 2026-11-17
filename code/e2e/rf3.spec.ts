import { test, expect, type APIRequestContext } from '@playwright/test';

const headers = { Authorization: 'Bearer demo-amal' };

async function ready(request: APIRequestContext, job: { id: string }) {
  await expect.poll(async () => (await (await request.get('/api/v1/jobs/' + job.id, { headers })).json()).search_status).toBe('ready');
}

test.beforeAll(async ({ request }) => {
  expect(process.env.BRAIN_E2E_DISPOSABLE).toBe('1');
  expect((await (await request.get('/api/v1/runtime', { headers })).json()).provider).toBe('mock');
});

test('Arabic team question retrieves long-source roles and opens supporting evidence', async ({ page, request }) => {
  const marker = 'RF3Browser' + Date.now();
  const lines = Array.from({ length: 40 }, (_, i) => `Project ${marker} routine log section ${i}: shipment review.`);
  lines[9] = 'Maya Farouk is the Product Manager and owns scope.';
  lines[14] = 'Ethan Brooks is the Operations Lead.';
  lines[19] = 'Luis Ortega is the Integrations Engineer.';
  const response = await request.post('/api/v1/sources/upload', { headers, multipart: {
    file: { name: marker + '.md', mimeType: 'text/markdown', buffer: Buffer.from(lines.join('\n')) }, visibility: 'team',
  } });
  expect(response.status()).toBe(202);
  const job = await response.json();
  try {
    await ready(request, job);
    const conversation = await (await request.post('/api/v1/conversations', { headers, data: { document_ids: [job.document_id] } })).json();
    await page.goto('/chat/' + conversation.id);
    await page.getByLabel('Ask a question').fill('مين الأشخاص ومسؤولياتهم في المشروع؟');
    await page.getByRole('button', { name: 'Send question', exact: true }).click();
    await expect(page.locator('.answer-body')).toContainText('Maya Farouk');
    await expect(page.locator('.answer-body')).toContainText('Ethan Brooks');
    await expect(page.locator('.answer-body')).toContainText('Luis Ortega');
    await page.getByRole('button', { name: 'Preview source: '+marker+'.md',exact:true }).first().click();
    await expect(page.getByRole('dialog')).toContainText(marker+'.md');
    await expect(page.locator('.source-quote')).not.toBeEmpty();
    await page.keyboard.press('Escape');
    for (const width of [1440, 390]) {
      await page.setViewportSize({ width, height: 1000 });
      expect(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)).toBe(false);
      await page.screenshot({ path: `results/screens/rf3-${width}-roles.png`, fullPage: true });
    }
  } finally {
    await request.delete('/api/v1/documents/' + job.document_id, { headers });
  }
});

test('retained revision comparison displays both sources while current retrieval excludes superseded text', async ({ page, request }) => {
  const marker = 'RF3History' + Date.now();
  const job = await (await request.post('/api/v1/sources/upload', { headers, multipart: {
    file: { name: marker + '.md', mimeType: 'text/markdown', buffer: Buffer.from('The release coordinator is Amina.') }, visibility: 'team',
  } })).json();
  try {
    await ready(request, job);
    const revision = await (await request.post('/api/v1/documents/' + job.document_id + '/revisions', { headers, multipart: {
      file: { name: marker + '-v2.md', mimeType: 'text/markdown', buffer: Buffer.from('The release coordinator is Daniel.') },
    } })).json();
    await ready(request, revision);
    const conversation = await (await request.post('/api/v1/conversations', { headers, data: { document_ids: [job.document_id] } })).json();
    await page.goto('/chat/' + conversation.id);
    await page.getByLabel('Ask a question').fill('Who coordinates the release?');
    await page.getByRole('button', { name: 'Send question', exact: true }).click();
    await expect(page.locator('.chat-turn').last()).toContainText('Daniel');
    await expect(page.locator('.chat-turn').last()).not.toContainText('Amina');
    await page.getByLabel('Ask a question').fill('قارن النسخة السابقة بالحالية.');
    await page.getByRole('button', { name: 'Send question', exact: true }).click();
    const turn = page.locator('.chat-turn').last();
    await expect(turn).toContainText('Amina');
    await expect(turn).toContainText('Daniel');
    await expect(turn.getByRole('button', {name:/Preview source:/})).toHaveCount(2);
    const quotes=[];
    for (const preview of await turn.getByRole('button', {name:/Preview source:/}).all()) {
      await preview.click();await expect(page.locator('.source-quote')).not.toBeEmpty();
      quotes.push(await page.locator('.source-quote').innerText());await page.keyboard.press('Escape');
    }
    expect(quotes.join(' ')).toContain('Amina');expect(quotes.join(' ')).toContain('Daniel');
  } finally {
    await request.delete('/api/v1/documents/' + job.document_id, { headers });
  }
});
