"""Explicit, one-attempt AWS evaluation adapters; production providers are untouched."""
import json
import time
from urllib.request import urlopen
from decimal import Decimal
import boto3
from botocore.config import Config
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from botocore.httpsession import URLLib3Session
from app.contracts import Extraction, AnswerVerdict
from app.providers import EXTRACT, UNTRUSTED
from diagnostics.m32_core import BudgetStopped

REGION='us-east-1'
SONNET='us.anthropic.claude-sonnet-4-6'
GEMMA='google.gemma-4-31b'
HOST='https://bedrock-mantle.us-east-1.api.aws'
VERIFY=UNTRUSTED+(
    'For each assertion, return one boolean in order: is the complete assertion supported by its quoted evidence? '
    'Interpret claims according to the supplied effective_from/effective_to dates and source tense. '
    'Historical relationships describe the period in their source; do not assume they are current. '
    'An explicit month permits normalizing its first and last day. Do not use outside knowledge.')


def simplify(value):
    if isinstance(value,dict):return {k:simplify(v) for k,v in value.items() if k not in {'format','default'}}
    if isinstance(value,list):return [simplify(v) for v in value]
    return value


def prices():
    results={}
    for offer,model,select in [
        ('AmazonBedrockFoundationModels',SONNET,lambda a:a.get('model')=='Claude Sonnet 4.6' and a.get('feature')=='On-demand Inference' and a.get('usagetype') in ['USE1-MP:USE1_InputTokenCount-Units','USE1-MP:USE1_OutputTokenCount-Units']),
        ('AmazonBedrock',GEMMA,lambda a:a.get('model')==GEMMA and a.get('service_tier')=='standard')]:
        url=f'https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/{offer}/current/us-east-1/index.json'
        with urlopen(url,timeout=30) as response:catalog=json.load(response)
        rate=dict(currency='USD',source=url,published=catalog['publicationDate'],dimensions=[])
        for sku,item in catalog['products'].items():
            a=item['attributes']
            if not select(a) or a.get('inferenceType') not in ['Input tokens','Output tokens']:continue
            for term in catalog['terms']['OnDemand'].get(sku,{}).values():
                for price in term['priceDimensions'].values():
                    scale={'1M tokens':1,'1K tokens':1000,'tokens':1_000_000}.get(price['unit'])
                    if scale is None:raise ValueError('Unknown token price unit')
                    key='input' if a['inferenceType']=='Input tokens' else 'output'
                    value=Decimal(price['pricePerUnit']['USD'])*scale
                    if key in rate and Decimal(rate[key])!=value:raise ValueError('Ambiguous applicable price')
                    rate[key]=str(value);rate['dimensions'].append(dict(sku=sku,unit=price['unit'],effective=term['effectiveDate'],usage=a['usagetype']))
        if not all(k in rate and Decimal(rate[k]).is_finite() and Decimal(rate[k])>0 for k in ['input','output']):raise ValueError('Verified model pricing unavailable')
        results[model]=rate
    return results


class Adapters:
    def __init__(self):
        self.session=boto3.Session(region_name=REGION)
        config=Config(retries={'mode':'standard','total_max_attempts':1},connect_timeout=5,read_timeout=180)
        self.runtime=self.session.client('bedrock-runtime',config=config)
        self.control=self.session.client('bedrock',config=config)
        self.sts=self.session.client('sts',config=config)
        self.http=URLLib3Session(timeout=(5,180))
        self.next_call=0
    def mantle(self,path,body=None):
        # Fixed AWS endpoint, refreshed existing credentials, no redirects or HTTP retries.
        credentials=self.session.get_credentials()
        if credentials is None:raise RuntimeError('AWS credentials unavailable')
        request=AWSRequest(method='GET' if body is None else 'POST',url=HOST+path,
            data=json.dumps(body,ensure_ascii=False).encode() if body is not None else None,
            headers={'Content-Type':'application/json','OpenAI-Project':'default'})
        SigV4Auth(credentials.get_frozen_credentials(),'bedrock-mantle',REGION).add_auth(request)
        response=self.http.send(request.prepare())
        if response.status_code!=200:raise RuntimeError(f'MantleHTTP{response.status_code}')
        return json.loads(response.content)
    def preflight(self):
        self.sts.get_caller_identity() # Validate sign-in; do not retain account/credential data.
        profile=self.control.get_inference_profile(inferenceProfileIdentifier=SONNET)
        if profile['status']!='ACTIVE':raise RuntimeError('Sonnet profile unavailable')
        models=self.mantle('/v1/models')
        if GEMMA not in {m['id'] for m in models['data']}:raise RuntimeError('Gemma model not listed')
        projects=self.mantle('/v1/organization/projects')
        if not any(p['id']=='default' and p.get('status','active')=='active' for p in projects['data']):raise RuntimeError('Existing default project unavailable')
        return dict(authenticated=True,sonnet_profile=SONNET,gemma_listed=True,default_project=True,region=REGION)
    def request(self,model,contract,system,payload,max_output):
        schema=simplify(contract.model_json_schema())
        system=system+'\nReturn only one JSON object matching this schema. Do not include Markdown or reasoning text.\n'+json.dumps(schema)
        message=json.dumps(payload,ensure_ascii=False,default=str)
        if model==SONNET:
            return dict(modelId=model,system=[{'text':system}],messages=[{'role':'user','content':[{'text':message}]}],
                inferenceConfig={'maxTokens':max_output,'temperature':0},outputConfig={'textFormat':{'type':'json_schema','structure':{'jsonSchema':{'name':contract.__name__,'schema':json.dumps(schema)}}}})
        if model!=GEMMA:raise ValueError('Model outside approved comparison')
        return dict(model=model,messages=[{'role':'system','content':system},{'role':'user','content':message}],
            max_tokens=max_output,temperature=0,reasoning_effort='low',stream=False,service_tier='default')
    def call(self,budget,model,contract,system,payload,role,case,max_output):
        request=self.request(model,contract,system,payload,max_output)
        # Credential/serialization errors before reservation cannot make an inference call.
        credentials=self.session.get_credentials()
        if credentials is None:raise RuntimeError('AWS credentials unavailable')
        credentials.get_frozen_credentials()
        wait=self.next_call-time.monotonic()
        if wait>0:time.sleep(wait)
        attempt=budget.reserve(model,role,case,request,max_output)
        started=time.monotonic();self.next_call=started+6.8
        try:
            if model==SONNET:
                response=self.runtime.converse(**request)
                text=''.join(p.get('text','') for p in response['output']['message']['content'])
                usage=response.get('usage',{});incoming=usage.get('inputTokens');outgoing=usage.get('outputTokens')
                complete=response.get('stopReason') in {'end_turn','stop_sequence'}
                request_id=response.get('ResponseMetadata',{}).get('RequestId')
            else:
                response=self.mantle('/openai/v1/chat/completions',request)
                choice=response['choices'][0];text=choice['message'].get('content')
                usage=response.get('usage',{});incoming=usage.get('prompt_tokens');outgoing=usage.get('completion_tokens')
                complete=choice.get('finish_reason')=='stop';request_id=response.get('id')
            budget.settle(attempt,incoming,outgoing,int((time.monotonic()-started)*1000))
        except BudgetStopped:raise
        except Exception as exc:
            # An unsuccessful attempt with unknown usage retains the full reservation and halts.
            attempt.update(state='usage_unavailable',error=type(exc).__name__+(':'+str(exc) if str(exc).startswith('MantleHTTP') else ''))
            budget.save();raise BudgetStopped('Inference failed with unknown usage; stop without retry') from exc
        return dict(text=text if isinstance(text,str) else '',complete=complete,attempt=attempt['number'],request_id=request_id)
