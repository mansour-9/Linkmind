"""Frozen cases, strict scoring and a durable, fail-closed evaluation budget."""
from pathlib import Path
from decimal import Decimal
from dataclasses import dataclass
import hashlib
import json
import os
import unicodedata
from app.parsers import parse_document
from app.contracts import Extraction, validate_extraction

FIXTURES=Path(__file__).resolve().parents[3]/'fixtures'/'m32'


def digest(data):return hashlib.sha256(data).hexdigest()


def cases(root=FIXTURES):
    manifest=json.loads((root/'manifest.json').read_text(encoding='utf-8'))
    result=[]
    for case in manifest['cases']:
        raw=(root/case['filename']).read_bytes()
        if digest(raw)!=case['sha256']:raise ValueError('Frozen source checksum mismatch')
        passages=[dict(id=f"{case['id']}:{i}",text=p.text,locator=p.locator) for i,p in enumerate(parse_document(case['filename'],raw),1)]
        result.append({**case,'passages':passages,'passage_sha256':digest(json.dumps(passages,ensure_ascii=False,sort_keys=True).encode())})
    return manifest,result


def norm(value):return ' '.join(unicodedata.normalize('NFC',str(value)).casefold().split())


def metric(expected,observed):
    expected=set(expected);observed=set(observed);tp=len(expected&observed)
    return dict(tp=tp,fp=len(observed-expected),fn=len(expected-observed),precision=tp/len(observed) if observed else None,
        recall=tp/len(expected) if expected else None,missing=sorted(expected-observed),extra=sorted(observed-expected))


def score(result,case,scoring):
    expected=case['expected'];mapping={};used=set();observed_entities=[]
    for item in result.entities:
        identifiers={(i.namespace,norm(i.value)) for i in item.identifiers}
        matches=[e for e in expected['entities'] if e['kind']==item.kind and
            (norm(item.name) in {norm(e['name']),*map(norm,scoring['entity_name_aliases'].get(e['key'],[]))} or
             identifiers&{(i['namespace'],norm(i['value'])) for i in e['identifiers']})]
        if len(matches)==1:
            key=matches[0]['key'];mapping[item.key]=key
            observed_entities.append(key if key not in used else 'duplicate:'+item.key);used.add(key)
        else:mapping[item.key]='unmatched:'+item.key;observed_entities.append(mapping[item.key])
    identifiers=lambda e:[(e['key'],i['namespace'],norm(i['value'])) for i in e['identifiers']]
    observed_ids=[(mapping[e.key],i.namespace,norm(i.value)) for e in result.entities for i in e.identifiers]
    def claim(e,p,v,start,end):
        value=scoring['value_aliases'].get(norm(v),norm(v))
        return (e,scoring['claim_aliases'].get(p,p),value,str(start or ''),str(end or ''))
    def relationship(s,p,t,start,end):
        if p in scoring['inverted_relationships']:s,t,p=t,s,scoring['inverted_relationships'][p]
        return (s,scoring['relationship_aliases'].get(p,p),t,str(start or ''),str(end or ''))
    expected_rel=[relationship(r['source'],r['predicate'],r['target'],r['effective_from'],r['effective_to']) for r in expected['relationships']]
    observed_rel=[relationship(mapping[r.source_key],r.predicate,mapping[r.target_key],r.effective_from,r.effective_to) for r in result.relationships]
    reversed_count=sum((t,p,s,start,end) in expected_rel and (s,p,t,start,end) not in expected_rel for s,p,t,start,end in observed_rel)
    return dict(entities=metric([e['key'] for e in expected['entities']],observed_entities),
        identifiers=metric([x for e in expected['entities'] for x in identifiers(e)],observed_ids),
        claims=metric([claim(c['entity'],c['predicate'],c['value'],c['effective_from'],c['effective_to']) for c in expected['claims']],
            [claim(mapping[c.entity_key],c.predicate,c.value,c.effective_from,c.effective_to) for c in result.claims]),
        relationships=metric(expected_rel,observed_rel),incorrect_relationship_direction=reversed_count,
        forbidden_entities=[e.name for e in result.entities if norm(e.name) in set(map(norm,expected['forbidden_names']))])


def validate(text,passages):
    # No JSON fence stripping, partial parsing, coercion or quote repair.
    result=Extraction.model_validate_json(text,strict=True)
    return validate_extraction(result,passages)


def assertions(result):
    names={e.key:e.name for e in result.entities}
    rows=[dict(text=f'{e.kind}: {e.name}',identifiers=[i.model_dump() for i in e.identifiers],evidence=[c.model_dump() for c in e.evidence]) for e in result.entities]
    rows += [dict(text=f'{names[c.entity_key]}: {c.predicate} = {c.value}',effective_from=c.effective_from,effective_to=c.effective_to,evidence=[e.model_dump() for e in c.evidence]) for c in result.claims]
    rows += [dict(text=f'{names[r.source_key]} {r.predicate} {names[r.target_key]}',effective_from=r.effective_from,effective_to=r.effective_to,evidence=[e.model_dump() for e in r.evidence]) for r in result.relationships]
    return rows


class BudgetStopped(RuntimeError):pass


class Budget:
    """Persist a reservation before sending; unresolved/unknown usage stops all calls."""
    def __init__(self,path,prices,identity,max_attempts=24,usd='5'):
        if not isinstance(max_attempts,int) or isinstance(max_attempts,bool) or not 0<max_attempts<=24 or not Decimal(usd).is_finite() or not 0<Decimal(usd)<=5:raise ValueError('Approved limits cannot be expanded')
        for rate in prices.values():
            if rate.get('currency')!='USD' or any(not Decimal(str(rate[k])).is_finite() or Decimal(str(rate[k]))<=0 for k in ['input','output']):raise ValueError('Valid USD token prices required')
        self.path=Path(path);self.prices=prices;self.max_attempts=max_attempts;self.limit=Decimal(usd)
        self.path.parent.mkdir(parents=True,exist_ok=True)
        # Exclusive creation prevents a new process silently resetting an existing approved run.
        with self.path.open('x',encoding='utf-8') as stream:
            self.data=dict(identity=identity,max_attempts=max_attempts,projected_usd_limit=str(self.limit),attempts=[])
            json.dump(self.data,stream,indent=2)
    def save(self):
        temp=self.path.with_suffix('.pending');temp.write_text(json.dumps(self.data,indent=2,default=str),encoding='utf-8');os.replace(temp,self.path)
    def cost(self,model,incoming,outgoing):
        rate=self.prices[model]
        return (Decimal(incoming)*Decimal(str(rate['input']))+Decimal(outgoing)*Decimal(str(rate['output'])))/1_000_000
    def reserve(self,model,role,case,request,max_output):
        attempts=self.data['attempts']
        if any(a['state']!='settled' for a in attempts):raise BudgetStopped('Unresolved or missing usage; no more requests allowed')
        if len(attempts)>=self.max_attempts:raise BudgetStopped('Inference attempt limit reached')
        # UTF-8 bytes plus framing allowance is a conservative token bound, not a tokenizer estimate.
        incoming=len(json.dumps(request,ensure_ascii=False,default=str).encode())+4096
        reservation=self.cost(model,incoming,max_output)
        consumed=sum(Decimal(a['cost_usd']) for a in attempts)
        if consumed+reservation>self.limit:raise BudgetStopped('Projected-spend limit would be exceeded')
        attempt=dict(number=len(attempts)+1,model=model,role=role,case=case,state='reserved',input_bound=incoming,
            output_bound=max_output,reserved_usd=str(reservation),cost_usd=str(reservation))
        attempts.append(attempt);self.save();return attempt
    def settle(self,attempt,incoming,outgoing,latency_ms,error=None):
        if any(not isinstance(x,int) or isinstance(x,bool) or x<0 for x in (incoming,outgoing)):
            attempt.update(state='usage_unavailable',latency_ms=latency_ms,error=error);self.save();raise BudgetStopped('Usage unavailable; run stopped')
        cost=self.cost(attempt['model'],incoming,outgoing)
        if incoming>attempt['input_bound'] or outgoing>attempt['output_bound'] or cost>Decimal(attempt['reserved_usd']):
            attempt.update(state='bound_exceeded',input_tokens=incoming,output_tokens=outgoing,cost_usd=str(cost),latency_ms=latency_ms);self.save();raise BudgetStopped('Token reservation exceeded; run stopped')
        attempt.update(state='settled',input_tokens=incoming,output_tokens=outgoing,cost_usd=str(cost),latency_ms=latency_ms,error=error);self.save()
