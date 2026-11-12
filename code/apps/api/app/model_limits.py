"""Database-coordinated inference pacing; never holds a lock during inference."""
import os
import time
from datetime import timedelta
from app.db import engine,sql

def pace(model,region):
    rpm=float(os.getenv("BEDROCK_REQUESTS_PER_MINUTE","9"))
    if not 0<rpm<=10000:
        raise ValueError("BEDROCK_REQUESTS_PER_MINUTE must be between 0 and 10000.")
    with engine.begin() as conn:
        sql(conn,"""INSERT INTO model_request_slots(model,region,next_at) VALUES(:model,:region,now())
            ON CONFLICT DO NOTHING""",model=model,region=region)
        row=sql(conn,"""SELECT next_at,clock_timestamp() AS now FROM model_request_slots
            WHERE model=:model AND region=:region FOR UPDATE""",model=model,region=region).one()
        scheduled=max(row.next_at,row.now)
        delay=(scheduled-row.now).total_seconds()
        if delay>90:
            raise RuntimeError("The inference queue is busy. Retry shortly.")
        sql(conn,"UPDATE model_request_slots SET next_at=:next WHERE model=:model AND region=:region",
            model=model,region=region,next=scheduled+timedelta(seconds=60/rpm))
    if delay>0:
        time.sleep(delay)
