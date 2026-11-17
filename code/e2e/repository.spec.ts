import { test, expect, type APIRequestContext } from '@playwright/test';

const headers = { Authorization: 'Bearer demo-amal' };
const member = { Authorization: 'Bearer demo-omar' };
async function upload(request: APIRequestContext, name: string, text: string, visibility = 'team') {
  const response = await request.post('/api/v1/sources/upload', { headers, multipart: {
    file: { name, mimeType: 'text/plain', buffer: Buffer.from(text) }, visibility,
  } });
  expect(response.status()).toBe(202);
  const job = await response.json();
  await expect.poll(async () => (await (await request.get('/api/v1/jobs/' + job.id, { headers })).json()).status).toBe('ready');
  return job;
}
test.beforeAll(async ({ request }) => {
  expect(process.env.BRAIN_E2E_DISPOSABLE).toBe('1');
  expect((await (await request.get('/api/v1/runtime', { headers })).json()).provider).toBe('mock');
});

test('organize source-only documents, filter, inspect evidence and retain revisions', async ({ page, request }) => {
  const marker = 'RepositoryBrowser' + Date.now();
  const first = await upload(request, marker + '.md', marker + ' records the release checklist.');
  const second = await upload(request, marker + '-private.txt', marker + ' is a private draft.', 'private');
  try {
    await page.goto('/content/documents');
    await page.getByLabel('Find stored knowledge').fill(marker);
    await page.getByRole('button', { name: 'Search documents', exact: true }).click();
    await expect(page.locator('.repository-row')).toHaveCount(2);
    const row = page.locator('.repository-row').filter({ hasText: marker + '.md' });
    await row.getByRole('button', { name: 'Details', exact: true }).click();
    await page.getByRole('button', { name: 'Edit details', exact: true }).click();
    await page.getByLabel('Display title').fill('Delivery handbook ' + marker);
    await page.getByLabel('Find project', { exact: true }).fill('Project ' + marker);
    await page.getByRole('button', { name: /^Create project/ }).click();
    await page.getByLabel('Find team', { exact: true }).fill('Team ' + marker);
    await page.getByRole('button', { name: /^Create team/ }).click();
    await page.getByRole('button', { name: 'Save details', exact: true }).click();
    await expect(page.getByRole('dialog')).toContainText('Project ' + marker);
    await expect(page.getByRole('dialog')).toContainText('Team ' + marker);
    await expect(page.getByRole('button', { name: 'Edit details', exact: true })).toBeVisible();
    const metadata = await (await request.get('/api/v1/documents/' + first.document_id + '/metadata', { headers })).json();
    expect(metadata.title).toBe('Delivery handbook ' + marker);
    await page.keyboard.press('Escape');
    await expect(row.getByRole('button', { name: 'Details', exact: true })).toBeFocused();
    await page.getByLabel('Project', { exact: true }).selectOption(metadata.project_id);
    await page.getByLabel('File type', { exact: true }).selectOption('md');
    await expect(page.locator('.repository-row')).toHaveCount(1);
    await expect(page.locator('.repository-row')).toContainText(metadata.title);
    await page.goto('/search?' + new URLSearchParams({ q: marker, project_id: metadata.project_id, format: 'md' }));
    await expect(page.locator('.search-result')).toHaveCount(1);
    await page.getByRole('button', { name: 'Open source passage', exact: true }).click();
    await expect(page.locator('.source-quote')).toContainText('release checklist');
    await expect(page.getByRole('dialog')).toContainText('Stored passage');
    const download = page.waitForEvent('download');
    await page.getByRole('button', { name: 'Download original', exact: true }).click();
    expect((await download).suggestedFilename()).toBe(marker + '.md');
    const revisions = await request.post('/api/v1/documents/' + first.document_id + '/revisions', { headers,
      multipart: { file: { name: marker + '-v2.txt', mimeType: 'text/plain', buffer: Buffer.from(marker + ' records a revised checklist.') } } });
    expect(revisions.status()).toBe(202);
    const next = await revisions.json();
    await expect.poll(async () => (await (await request.get('/api/v1/jobs/' + next.id, { headers })).json()).status).toBe('ready');
    const after = await (await request.get('/api/v1/documents/' + first.document_id + '/metadata', { headers })).json();
    expect(after.native_id).toBe(metadata.native_id); expect(after.project_id).toBe(metadata.project_id); expect(after.title).toBe(metadata.title);
    const job = await (await request.get('/api/v1/jobs/' + next.id, { headers })).json();
    expect(job.enrichment_status).toBe('not_requested'); expect(job.entity_count).toBe(0);
    await page.goto('/content/documents?project_id=' + metadata.project_id);
    await page.getByRole('button', { name: 'Details', exact: true }).click();
    await expect(page.locator('.repository-history li')).toHaveCount(2);
    await page.getByRole('link', { name: 'Manage source', exact: true }).click();
    await expect(page).toHaveURL(new RegExp('document_id=' + first.document_id));
    await expect(page.locator('.upload-list > li')).toHaveCount(2);
  } finally {
    await request.delete('/api/v1/documents/' + first.document_id, { headers });
    await request.delete('/api/v1/documents/' + second.document_id, { headers });
  }
});

test('resource details and project counts disappear after access revocation', async ({ page, request }) => {
  const marker = 'RepositoryAccess' + Date.now();
  const job = await upload(request, marker + '.md', marker + ' is shared initially.');
  try {
    const group = await (await request.post('/api/v1/repository/groups', { headers, data: { kind: 'project', name: marker } })).json();
    expect((await request.patch('/api/v1/documents/' + job.document_id + '/metadata', { headers, data: { expected_revision: 0, project_id: group.id } })).ok()).toBeTruthy();
    await page.goto('/content/documents?project_id=' + group.id);
    await page.getByRole('button', { name: 'Profile and workspace', exact: true }).filter({ visible: true }).first().click();
    await page.getByLabel('Demo identity').selectOption('demo-omar');
    await page.goto('/content/documents?project_id=' + group.id);
    await page.getByRole('button', { name: 'Details', exact: true }).click();
    await expect(page.getByRole('dialog')).toContainText(marker);
    expect((await (await request.get('/api/v1/repository/groups?q=' + marker, { headers: member })).json())[0].resource_count).toBe(1);
    await request.patch('/api/v1/documents/' + job.document_id + '/access', { headers, data: { visibility: 'private' } });
    await expect(page.getByRole('dialog')).toContainText('Document not found');
    await expect(page.locator('.repository-detail')).toHaveCount(0);
    expect(await (await request.get('/api/v1/repository/groups?q=' + marker, { headers: member })).json()).toEqual([]);
    await page.keyboard.press('Escape');
    await expect(page.locator('.repository-row')).toHaveCount(0);
  } finally { await request.delete('/api/v1/documents/' + job.document_id, { headers }); }
});

test('repository responsive states, keyboard evidence and honest empty/error results', async ({ page, request }) => {
  const marker = 'RepositoryLayout' + Date.now();
  const job = await upload(request, marker + '.md', marker + ' is a readable source without graph extraction.');
  const errors: string[] = []; page.on('pageerror', e => errors.push(e.message));
  try {
    for (const width of [1440, 1024, 390, 1920]) {
      await page.setViewportSize({ width, height: 1000 });
      await page.goto('/content/documents?q=' + marker);
      await expect(page.locator('.repository-row')).toHaveCount(1);
      expect(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)).toBe(false);
      await page.screenshot({ path: 'results/screens/rf2-' + width + '-repository.png', fullPage: true });
      const button = page.getByRole('button', { name: 'Details', exact: true });
      await button.focus(); await page.keyboard.press('Enter');
      await expect(page.getByRole('button', { name: 'Edit details', exact: true })).toBeVisible();
      expect(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)).toBe(false);
      await page.screenshot({ path: 'results/screens/rf2-' + width + '-details.png', fullPage: true });
      await page.getByRole('button', { name: 'Edit details', exact: true }).click();
      await expect(page.getByLabel('Display title')).toBeVisible();
      await page.screenshot({ path: 'results/screens/rf2-' + width + '-edit.png', fullPage: true });
      expect(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)).toBe(false);
      await page.keyboard.press('Escape'); await expect(button).toBeFocused();
    }
    await page.goto('/content/documents?q=no-match-' + marker);
    await expect(page.getByRole('heading', { name: 'No matching documents' })).toBeVisible();
    await page.route('**/api/v1/repository/resources?**', route => route.fulfill({ status: 503, contentType: 'application/json', body: JSON.stringify({ detail: 'Repository temporarily unavailable.' }) }));
    await page.goto('/content/documents?q=' + marker);
    await expect(page.getByRole('alert')).toContainText('Repository temporarily unavailable');
    await expect(page.locator('.repository-row')).toHaveCount(0);
    await page.unroute('**/api/v1/repository/resources?**');
    await page.getByRole('button', { name: 'Retry', exact: true }).click();
    await expect(page.locator('.repository-row')).toHaveCount(1);
    expect(errors).toEqual([]);
  } finally { await request.delete('/api/v1/documents/' + job.document_id, { headers }); }
});
