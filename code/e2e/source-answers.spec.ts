import { test,expect } from '@playwright/test';
const headers={Authorization:'Bearer demo-amal'};
test.beforeAll(async({request})=>{expect(process.env.BRAIN_E2E_DISPOSABLE).toBe('1');expect((await(await request.get('/api/v1/runtime',{headers})).json()).provider).toBe('mock');});

async function connection(request:any){
 const created=await request.post('/api/v1/connections',{headers,data:{kind:'jira',execution:'mock',name:'RF5 synthetic '+Date.now(),scope_id:'rf5-'+Date.now()}});expect(created.status()).toBe(201);
 const {id}=await created.json();await request.post(`/api/v1/connections/${id}/authenticate`,{headers});await request.post(`/api/v1/connections/${id}/test`,{headers});
 const current=(await(await request.get('/api/v1/connections',{headers})).json()).find((c:any)=>c.id===id);
 expect((await request.patch(`/api/v1/connections/${id}/mode`,{headers,data:{mode:'live',expected_generation:current.generation}})).ok()).toBeTruthy();return id;
}
async function remove(request:any,id:string){const c=(await(await request.get('/api/v1/connections',{headers})).json()).find((c:any)=>c.id===id);if(c)await request.delete(`/api/v1/connections/${id}?expected_generation=${c.generation}`,{headers});}

test('selected stored reasons and live fields share a transient answer with reauthorized evidence',async({page,request})=>{
 const id=await connection(request),name='RF5-decision-'+Date.now()+'.md';
 const uploaded=await request.post('/api/v1/sources/upload',{headers,multipart:{file:{name,mimeType:'text/markdown',buffer:Buffer.from('SYNTHETIC RF5 DECISION '+name+'\nThe fictional review moved from Wednesday to Thursday because integration tests were incomplete.')},visibility:'team'}});
 expect(uploaded.ok()).toBeTruthy();const job=await uploaded.json();await expect.poll(async()=>(await(await request.get('/api/v1/jobs/'+job.id,{headers})).json()).search_status).toBe('ready');
 const conversations=(await(await request.get('/api/v1/conversations',{headers})).json()).length;
 await page.goto('/ask/sources');await expect(page.getByRole('heading',{name:'Ask across sources',exact:true})).toBeVisible();
 await expect(page.getByText('No stored documents selected',{exact:true})).toBeVisible();await page.getByRole('button',{name:'Focus sources',exact:true}).click();await expect(page.getByRole('dialog')).toContainText('Only explicitly selected documents are used');
 await page.getByLabel('Find sources by topic').fill(name);await page.getByRole('dialog').getByRole('button',{name:'Search',exact:true}).click();
 await page.getByRole('checkbox',{name:'Select '+name,exact:true}).check();await page.getByRole('button',{name:'Apply selection',exact:true}).click();
 await page.getByRole('button',{name:'Add connected resource',exact:true}).click();await page.getByLabel('Connection 1',{exact:true}).selectOption(id);
 await page.getByLabel('Cross-source question').fill('Why did the review move, and what does the selected Jira resource currently report?');
 const response=page.waitForResponse(r=>r.url().endsWith('/api/v1/source-answers')&&r.request().method()==='POST');await page.getByRole('button',{name:'Ask selected sources',exact:true}).click();const result=await(await response).json();
 await expect(page.getByRole('region',{name:'Cross-source result'})).toContainText('integration tests were incomplete');await expect(page.getByRole('region',{name:'Cross-source result'})).toContainText('status: "Synthetic demo"');
 expect(result.saved).toBe(false);expect(result.retained).toBe(false);expect(result.sources.map((s:any)=>s.origin)).toContain('live');
 expect((await(await request.get('/api/v1/conversations',{headers})).json()).length).toBe(conversations);
 expect((await(await request.get('/api/v1/repository/resources?source_instance_id='+id,{headers})).json()).total).toBe(0);
 const liveIndex=result.sources.findIndex((s:any)=>s.origin==='live')+1;await page.getByRole('button',{name:'Open source '+liveIndex,exact:true}).click();await expect(page.getByRole('dialog')).toContainText('Synthetic demo');await expect(page.getByRole('dialog').locator('blockquote')).toHaveCount(0);await page.keyboard.press('Escape');
 const c=(await(await request.get('/api/v1/connections',{headers})).json()).find((c:any)=>c.id===id);await request.patch(`/api/v1/connections/${id}/mode`,{headers,data:{mode:'disconnected',expected_generation:c.generation}});
 await page.getByRole('button',{name:'Open source '+liveIndex,exact:true}).click();await expect(page.getByRole('alert')).toContainText('This result is hidden');await expect(page.getByRole('region',{name:'Cross-source result'})).toHaveCount(0);
 await remove(request,id);
});

test('historical request does not substitute a live reading and works on mobile',async({page,request})=>{
 const id=await connection(request);await page.setViewportSize({width:390,height:844});await page.goto('/ask/sources');await page.getByRole('button',{name:'Add connected resource',exact:true}).click();await page.getByLabel('Connection 1',{exact:true}).selectOption(id);
 await page.getByLabel('Cross-source question').fill('What was this issue status yesterday?');await page.getByRole('button',{name:'Ask selected sources',exact:true}).click();await expect(page.getByRole('region',{name:'Cross-source result'})).toContainText('Live current state was not used as evidence of a past state');
 expect(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth)).toBeFalsy();await page.screenshot({path:'results/screens/rf5-mobile.png',fullPage:true});
 await page.reload();await expect(page.getByRole('region',{name:'Cross-source result'})).toHaveCount(0);await remove(request,id);
});

test('source request is explicit and member cannot use another owner connection',async({request})=>{
 const id=await connection(request);expect((await request.post('/api/v1/source-answers',{headers,data:{question:'Question without selected sources'}})).status()).toBe(422);
 const member={Authorization:'Bearer demo-omar'};expect(await(await request.get('/api/v1/retrieval/connections',{headers:member})).json()).toEqual([]);
 expect((await request.post('/api/v1/source-answers',{headers:member,data:{question:'What is the current status?',live_resources:[{connection_id:id,native_id:'demo-1'}]}})).status()).toBe(404);await remove(request,id);
});
