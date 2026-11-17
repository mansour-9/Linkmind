import {test,expect} from '@playwright/test';

const cid='11111111-1111-4111-8111-111111111111';
const connection='22222222-2222-4222-8222-222222222222';
const title='QUARTZ customer portal scope and ownership';

async function fixture(page:any,revision='7'){
 const source={id:'page-one',filename:title,text:'The portal provides account administration.',version_id:'',document_id:'live:quartz',
  locator:{},live:{connection_id:connection,native_id:'42',generation:1,revision:'7'},original_url:'https://example.atlassian.net/wiki/pages/42',source_application:'Confluence'};
 await page.route('**/api/v1/conversations/'+cid,(route:any)=>route.fulfill({json:{id:cid,title:'Citation fixture',source_policy:'auto',document_ids:[],turns:[{
  id:'turn-one',question:'What does QUARTZ do?',suppressed:false,response:{provider:'bedrock',insufficient_evidence:false,
   source_outcomes:[{name:'Confluence',code:'discovered',resources:2}],
   statements:[{text:'QUARTZ provides account administration.',evidence:[{passage_id:'page-one',quote:'account administration'},{passage_id:'page-two',quote:'The portal'}]}],
   evidence:[source,{...source,id:'page-two'}]}}]}}));
 await page.route('**/api/v1/source-answers/access',(route:any)=>route.fulfill({json:{allowed:true}}));
 await page.route('**/api/v1/connections/'+connection+'/live',(route:any)=>route.fulfill({json:{evidence:{source_revision:revision,
  original_url:source.original_url,observed_at:'2026-11-17T00:00:00Z',source_updated_at:'2026-11-16T00:00:00Z',excerpt:source.text,fields:[]}}}));
 await page.goto('/chat/'+cid);
}

test('specific page title is deduplicated and preview checks the current revision',async({page})=>{
 await fixture(page);
 await expect(page.getByRole('button',{name:'Preview source: '+title})).toHaveCount(1);
 await expect(page.getByText('This source could not be read.')).toHaveCount(0);
 await page.getByRole('button',{name:'Preview source: '+title}).click();
 await expect(page.getByRole('dialog')).toContainText(title);
 await expect(page.getByRole('dialog')).toContainText('account administration');
 await page.keyboard.press('Escape');
 await expect(page.getByRole('dialog')).toHaveCount(0);
});

test('mobile citation preview rejects a changed revision',async({page})=>{
 await page.setViewportSize({width:390,height:844});
 await fixture(page,'8');
 await page.getByRole('button',{name:'Preview source: '+title}).click();
 await expect(page.getByRole('dialog')).toContainText('Source revision changed');
 await expect(page.getByRole('dialog').getByText('The portal provides account administration.',{exact:true})).toHaveCount(0);
 expect(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth)).toBeFalsy();
 await page.screenshot({path:'results/screens/chat-repair-mobile.png',fullPage:true});
});
