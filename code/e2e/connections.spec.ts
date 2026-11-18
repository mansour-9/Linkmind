import { test, expect } from '@playwright/test';
const headers={Authorization:'Bearer demo-amal'};
test.beforeAll(async({request})=>{expect(process.env.BRAIN_E2E_DISPOSABLE).toBe('1');expect((await(await request.get('/api/v1/runtime',{headers})).json()).provider).toBe('mock');});

test('Notion uses explicit handbook pages and offers only live access',async({page,request})=>{
 const name='Notion handbook '+Date.now();
 await page.goto('/admin/connections');
 await page.getByRole('button',{name:'Add Source',exact:true}).click();
 await page.getByLabel('Source type',{exact:true}).selectOption('notion');
 await page.getByLabel('Connection name',{exact:true}).fill(name);
 await page.getByLabel('Notion handbook pages').fill('Annual leave | https://app.notion.com/p/82103dfedad64d708d0006374a0d21ff');
 await page.getByRole('button',{name:'Save configuration',exact:true}).click();
 await expect(page.getByRole('dialog')).toHaveCount(0);
 const items=await (await request.get('/api/v1/connections',{headers})).json();
 const connection=items.find((item:{name:string})=>item.name===name);
 try{
  expect(connection.config.auth_method).toBe('oauth');
  expect(connection.config.notion_pages).toHaveLength(1);
  const card=page.locator('.connection-card').filter({hasText:name});
  await expect(card.getByRole('button',{name:'Sign in securely'})).toBeVisible();
  await expect(card.getByRole('option',{name:'Live Only'})).toHaveCount(1);
  await expect(card.getByRole('option',{name:'Live + Sync'})).toHaveCount(0);
 }finally{
  await request.delete('/api/v1/connections/'+connection.id+'?expected_generation='+connection.generation,{headers});
 }
});

test('five source types complete admin configuration, demo authentication, test and mode lifecycle',async({page,request})=>{
 const marker='SourceManagement'+Date.now();await page.goto('/admin/settings');
 await page.getByRole('link',{name:'Manage sources and connections'}).click();
 await expect(page.getByRole('heading',{name:'Sources & MCP Connections',exact:true})).toBeVisible();
 const created:string[]=[];
 try{
 for(const kind of ['jira','confluence','onedrive','sharepoint','custom_mcp']){
  await page.getByRole('button',{name:'Add Source',exact:true}).click();
  await page.getByLabel('Source type',{exact:true}).selectOption(kind);
  await page.getByLabel('Connection name',{exact:true}).fill(marker+' '+kind);
  await expect(page.getByLabel('Integration environment')).toHaveValue('mock');
  await page.getByRole('button',{name:'Save configuration',exact:true}).click();
  await expect(page.getByRole('dialog')).toHaveCount(0);
  const card=page.locator('.connection-card').filter({hasText:marker+' '+kind});
  await expect(card).toContainText('Demo connector');
  const connections=await(await request.get('/api/v1/connections',{headers})).json();const c=connections.find((x:any)=>x.name===marker+' '+kind);created.push(c.id);
  const premature=await request.patch(`/api/v1/connections/${c.id}/mode`,{headers,data:{mode:'live',expected_generation:c.generation}});expect(premature.status()).toBe(409);
  await card.getByRole('button',{name:'Authenticate demo',exact:true}).click();
  await expect(card).toContainText('Demo authenticated');
  await card.getByRole('button',{name:'Test connection',exact:true}).click();
  await expect(card).toContainText('tested');
  await page.getByLabel('Connection mode for '+marker+' '+kind).selectOption('live');
  await expect(card.getByRole('button',{name:'Read live resource',exact:true})).toBeEnabled();
  await card.getByRole('button',{name:'Read live resource',exact:true}).click();
  await page.getByRole('button',{name:'Read authorized evidence',exact:true}).click();
  await expect(page.locator('.live-observation')).toContainText('Synthetic demonstration fixture');
  await expect(page.locator('.live-observation')).toContainText('not added to the repository');
  await page.keyboard.press('Escape');
  expect((await(await request.get(`/api/v1/repository/resources?source_instance_id=${c.id}`,{headers})).json()).total).toBe(0);
 }
 const first=page.locator('.connection-card').filter({hasText:marker+' jira'});
 await page.getByLabel('Connection mode for '+marker+' jira').selectOption('sync');
 await expect.poll(async()=>(await(await request.get(`/api/v1/repository/resources?source_instance_id=${created[0]}`,{headers})).json()).total,{timeout:20000}).toBe(1);
 const resources=await(await request.get(`/api/v1/repository/resources?source_instance_id=${created[0]}`,{headers})).json();const documentId=resources.items[0].document_id;
 await first.getByRole('button',{name:'Edit',exact:true}).click();
 await page.getByLabel('Connection name',{exact:true}).fill(marker+' renamed');await page.getByRole('button',{name:'Save configuration',exact:true}).click();
 await expect(page.getByRole('dialog')).toHaveCount(0);
 const renamed=page.locator('.connection-card').filter({hasText:marker+' renamed'});await expect(renamed).toContainText('Not configured');
 expect((await request.get('/api/v1/documents/'+documentId+'/metadata',{headers})).status()).toBe(404);
 for(const width of [1440,390]){await page.setViewportSize({width,height:1000});expect(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth)).toBe(false);await page.screenshot({path:`results/screens/rf4-${width}-management.png`,fullPage:true});}
 await renamed.getByRole('button',{name:'Remove',exact:true}).click();await page.getByRole('button',{name:'Remove connection',exact:true}).click();await expect(renamed).toHaveCount(0);
 }finally{
 const connections=await(await request.get('/api/v1/connections',{headers})).json();for(const c of connections.filter((x:any)=>created.includes(x.id)))await request.delete(`/api/v1/connections/${c.id}?expected_generation=${c.generation}`,{headers});
 }
});

test('real configuration persists without pretending provider authentication is available',async({page,request})=>{
 const name='PendingRealSource'+Date.now();await page.goto('/admin/connections');await page.getByRole('button',{name:'Add Source',exact:true}).click();
 await page.getByLabel('Connection name',{exact:true}).fill(name);await page.getByLabel('Integration environment').selectOption('real');
 await page.getByLabel('Authentication method',{exact:true}).selectOption('server');await page.getByLabel('Atlassian site URL').fill('https://pending-real.atlassian.net');await page.getByLabel('Allowed Jira project key').fill('RF');
 await page.getByRole('button',{name:'Save configuration',exact:true}).click();await expect(page.getByRole('dialog')).toHaveCount(0);
 const card=page.locator('.connection-card').filter({hasText:name});await expect(card).toContainText('Real source');await card.getByRole('button',{name:'Set up authentication'}).click();
 await expect(page.getByRole('alert')).toContainText('Provider sign-in is not configured');await expect(card).toContainText('Not configured');
 await card.getByRole('button',{name:'Remove',exact:true}).click();await page.getByRole('button',{name:'Remove connection',exact:true}).click();await expect(card).toHaveCount(0);
});

test('members cannot read source configuration or manage connections',async({page,request})=>{
 const member={Authorization:'Bearer demo-omar'};
 expect((await request.get('/api/v1/connections',{headers:member})).status()).toBe(403);
 expect((await request.post('/api/v1/connections',{headers:member,data:{kind:'jira',execution:'mock',name:'Forbidden',scope_id:'demo-scope'}})).status()).toBe(403);
 await page.goto('/admin/connections');await page.getByRole('button',{name:'Profile and workspace',exact:true}).filter({visible:true}).first().click();await page.getByLabel('Demo identity').selectOption('demo-omar');await expect(page.getByRole('dialog')).toHaveCount(0);
 await page.goto('/admin/connections');await expect(page.getByText('Source administration is restricted to authorized administrators.')).toBeVisible();await expect(page.getByRole('button',{name:'Add Source',exact:true})).toHaveCount(0);
});


test('scope selection keeps demo authentication and requires a new connection test',async({page,request})=>{
 const name='Scope picker '+Date.now();
 const result=await request.post('/api/v1/connections',{headers,data:{kind:'confluence',execution:'mock',name,scope_id:'demo-scope'}});expect(result.status()).toBe(201);
 const source=await result.json();await request.post(`/api/v1/connections/${source.id}/authenticate`,{headers});
 await page.goto('/admin/connections');const card=page.locator('.connection-card').filter({hasText:name});
 await card.getByRole('button',{name:'Choose accessible scope',exact:true}).click();
 await expect(page.getByRole('dialog')).toContainText('Demo scopes are synthetic');
 await page.getByRole('button',{name:'Select scope',exact:true}).click();
 await expect(page.getByRole('dialog')).toHaveCount(0);await expect(card).toContainText('Demo authenticated');
 const current=(await(await request.get('/api/v1/connections',{headers})).json()).find((c:any)=>c.id===source.id);
 expect(current.tested_generation).toBeNull();expect(current.mode).toBe('disconnected');
 await card.getByRole('button',{name:'Test connection',exact:true}).click();await expect(card).toContainText('tested');
 await page.getByLabel('Connection mode for '+name).selectOption('live');
 await page.setViewportSize({width:390,height:844});await expect(card.getByRole('button',{name:'Choose accessible scope'})).toBeVisible();
 expect(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth)).toBeFalsy();
 const final=(await(await request.get('/api/v1/connections',{headers})).json()).find((c:any)=>c.id===source.id);
 await request.delete(`/api/v1/connections/${source.id}?expected_generation=${final.generation}`,{headers});
});

test('real OAuth setup is saved without pretending to connect an account',async({page,request})=>{
 const name='OAuth pending '+Date.now();await page.goto('/admin/connections');await page.getByRole('button',{name:'Add Source',exact:true}).click();
 await page.getByLabel('Connection name',{exact:true}).fill(name);await page.getByLabel('Integration environment',{exact:true}).selectOption('real');
 await expect(page.getByLabel('Authentication method',{exact:true})).toHaveValue('oauth');
 await page.getByLabel('Atlassian site URL').fill('https://oauth-pending.atlassian.net');
 await expect(page.getByRole('dialog')).toContainText('After saving, sign in and choose');
 await page.getByRole('button',{name:'Save configuration',exact:true}).click();await expect(page.getByRole('dialog')).toHaveCount(0);
 const card=page.locator('.connection-card').filter({hasText:name});await expect(card).toContainText('Provider registration is pending');
 await expect(card.getByRole('button',{name:'Choose accessible scope'})).toBeDisabled();await expect(card.getByRole('button',{name:'Test connection',exact:true})).toBeDisabled();
 await card.getByRole('button',{name:'Sign in securely',exact:true}).click();await expect(page.getByRole('alert')).toContainText('Provider sign-in is not configured');
 const source=(await(await request.get('/api/v1/connections',{headers})).json()).find((c:any)=>c.name===name);expect(source.scope).toBe('pending-scope');expect(source.mode).toBe('disconnected');
 await request.delete(`/api/v1/connections/${source.id}?expected_generation=${source.generation}`,{headers});
 const denied=await request.get('/api/v1/connections/oauth/callback?state=invalid&code=fictional',{maxRedirects:0});expect(denied.status()).toBe(303);expect(denied.headers().location).toContain('auth=failed');
});
