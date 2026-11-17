"""Summarize immutable pilot observations without repairing or rescoring raw failures."""
import argparse
import json
import statistics
from collections import Counter
from decimal import Decimal
from pathlib import Path
from diagnostics.m32_core import cases
from diagnostics.m32_live import GEMMA,SONNET


def summarize(report,manifest):
    observed={c['id']:c for c in manifest['cases']};attempts=report['ledger']['attempts'];models={}
    for model in [GEMMA,SONNET]:
        rows=[r for r in report['rows'] if r['model']==model];metrics={}
        for group in ['entities','identifiers','claims','relationships']:
            totals=Counter()
            for row in rows:
                expected=observed[row['case']]['expected']
                expected_count=sum(len(e['identifiers']) for e in expected['entities']) if group=='identifiers' else len(expected[group])
                if row['status']=='accepted_first_pass' and 'gold' in row:
                    totals.update({key:row['gold'][group][key] for key in ['tp','fp','fn']})
                else:totals['fn']+=expected_count
            metrics[group]={**dict(totals),'precision':totals['tp']/(totals['tp']+totals['fp']) if totals['tp']+totals['fp'] else None,
                'recall':totals['tp']/(totals['tp']+totals['fn']) if totals['tp']+totals['fn'] else None}
        cost={}
        selected=[]
        for row in rows:
            ids=[row[role]['attempt'] for role in ['extraction','verification'] if role in row]
            selected.extend(a for a in attempts if a['number'] in ids)
        for role in ['extraction','verification']:
            subset=[a for a in selected if a['role']==role]
            cost[role]=dict(attempts=len(subset),input_tokens=sum(a.get('input_tokens',0) for a in subset),output_tokens=sum(a.get('output_tokens',0) for a in subset),
                estimated_usd=str(sum(Decimal(a['cost_usd']) for a in subset)),median_latency_ms=statistics.median(a['latency_ms'] for a in subset) if subset else None)
        matched=metrics['claims'].get('tp',0)+metrics['relationships'].get('tp',0)
        pipeline_cost=sum(Decimal(a['cost_usd']) for a in selected)
        models[model]=dict(cases=len(rows),statuses=dict(Counter(r['status'] for r in rows)),
            schema_valid=sum(r['schema_valid'] for r in rows),exact_citations_valid=sum(r['exact_citations_valid'] for r in rows),
            passed_existing_gates=sum(r['status']=='accepted_first_pass' for r in rows),
            verifier_reported_unsupported=sum(r.get('unsupported_assertions',0) for r in rows),
            gold_direction_errors=sum(r.get('gold',{}).get('incorrect_relationship_direction',0) for r in rows),
            accepted_output_gold_metrics=metrics,cost=cost,pipeline_estimated_usd=str(pipeline_cost),
            estimated_cost_per_matched_gold_claim_or_relationship=str(pipeline_cost/matched) if matched else None,
            schema_failure_detail='All six returned fenced JSON; no fences stripped and no failed outputs admitted.' if model==GEMMA else None)
    return dict(status=report['status'],total_attempts=len(attempts),unused_attempt_allowance=24-len(attempts),
        estimated_usd=str(sum(Decimal(a['cost_usd']) for a in attempts)),all_usage_accounted=all(a['state']=='settled' for a in attempts),
        models=models,recommendation='Keep the current production model. Gemma is not a drop-in replacement under this tested strict-output integration; repair and grounding gaps also need attention in the Sonnet pipeline.',
        limitations=report['limitations']+[
            'Schema-failed Gemma content precision/recall is not assessed. Zero accepted-output recall describes integration yield, not intrinsic factual quality.',
            'Frozen tuple metrics count representations: a supported target_database edge is a literal mismatch for expected uses; no post-response alias changes were made.',
            'One reversed assigned_to edge passed common verification. Gold/manual source review is required alongside the model judge.',
            'A cost-per-matched-record denominator can count a claim and relationship for the same source fact; it is not semantic-fact deduplication.',
            'No repair/retry runs or extra requests consumed the seven unused verifier slots.'])


def main():
    parser=argparse.ArgumentParser();parser.add_argument('report',type=Path);parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    manifest,_=cases();report=json.loads(args.report.read_text(encoding='utf-8'))
    result=summarize(report,manifest);args.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({key:result[key] for key in ['status','total_attempts','estimated_usd','all_usage_accounted']}))


if __name__=='__main__':main()
