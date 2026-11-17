import json
from pathlib import Path
import boto3
from decimal import Decimal
from app.db import engine,sql
from app.inference_budget import status

account=boto3.Session(region_name='us-east-1').client('sts').get_caller_identity()['Account']
print(json.dumps({'account':account,'before':dict(status())},default=str))
with engine.begin() as conn:
    run=sql(conn,"SELECT * FROM inference_budget_runs WHERE id='northstar-sonnet-2026-11-12' FOR UPDATE").mappings().one()
    if Decimal(run.reserved_usd) < Decimal("0.0562848000"):
        raise RuntimeError('Unexpected reservation bound')
    sql(conn,"UPDATE inference_budget_runs SET paused=false WHERE id='northstar-sonnet-2026-11-12'")
print(json.dumps({'after':dict(status())},default=str))
