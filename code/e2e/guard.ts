import {request,type FullConfig} from '@playwright/test';
export default async function guard(config:FullConfig){
 const target=config.projects[0]?.use.baseURL;
 if(!target)throw new Error('An explicit isolated test URL is required.');
 const client=await request.newContext({baseURL:target,extraHTTPHeaders:{Authorization:'Bearer demo-amal'}});
 try{
  const response=await client.get('/api/v1/test-environment');
  if(!response.ok())throw new Error('Refusing to run browser tests against a non-isolated API.');
  const state=await response.json();
  if(state.isolated!==true||state.provider!=='mock'||state.connector_network!==false)throw new Error('Browser tests require isolated mock data and no external source networking.');
 }finally{await client.dispose();}
}
