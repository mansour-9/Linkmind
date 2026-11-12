import json
from uuid import UUID,uuid4
from app.db import engine,sql
from app.main import ANSWER_VALIDATION_VERSION
from test_m2 import call

def test_history_suppresses_superseded_validation_policy():
    status,conversation=call("/conversations",body={"title":"Policy regression"})
    assert status==201
    response={"statements":[],"insufficient_evidence":True,"provider":"test","evidence":[]}
    with engine.begin() as conn:
        for policy in ("legacy",ANSWER_VALIDATION_VERSION):
            sql(conn,"""INSERT INTO conversation_turns(id,organization_id,conversation_id,question,response,dependency_ids,validation_version)
               VALUES(:id,'00000000-0000-4000-8000-000000000001',:conversation,:question,CAST(:response AS jsonb),'[]'::jsonb,:policy)""",
               id=uuid4(),conversation=UUID(conversation["id"]),question=policy,response=json.dumps(response),policy=policy)
    status,history=call("/conversations/"+conversation["id"])
    assert status==200
    turns={t["question"]:t for t in history["turns"]}
    assert turns["legacy"]["suppressed"] and turns["legacy"]["response"] is None
    assert not turns[ANSWER_VALIDATION_VERSION]["suppressed"]
    assert turns[ANSWER_VALIDATION_VERSION]["response"]==response
