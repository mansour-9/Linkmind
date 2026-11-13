import hashlib
import time
from uuid import UUID,uuid4

import pytest
from fastapi import HTTPException

from app import main,processing,retrieval
from app.company_demo import MANIFEST,ROOT,extract_fixture
from app.parsers import parse_document
from test_m2 import call
from test_search_readiness import workspace,source,viewer,OMAR


def test_exact_company_corpus_has_supported_records_and_rejects_edits():
    initial=[f for f in MANIFEST["fixtures"] if not f["revision_of"]]
    assert len(initial)==24 and len(MANIFEST["questions"])==15
    assert sum(f["visibility"]=="private" for f in initial)==1
    for fixture in MANIFEST["fixtures"]:
        content=(ROOT/fixture["filename"]).read_bytes()
        assert hashlib.sha256(content).hexdigest()==fixture["sha256"]
        passages=[dict(id=str(uuid4()),text=p.text,locator=p.locator) for p in parse_document(fixture["filename"],content)]
        result=extract_fixture(content,passages)
        assert result is not None and len(result.entities)==len(fixture["entities"])
        assert extract_fixture(content+b"An arbitrary new fact.",passages) is None
        assert processing.mock_extract(content,passages)==result


def test_company_loading_is_idempotent_and_source_permissions_apply():
    assert call('/demo/company/load','demo-omar',body={})[0]==403
    code,first=call('/demo/company/load',body={})
    assert code==202 and first['total']==24
    code,second=call('/demo/company/load',body={})
    assert code==202 and {j['document_id'] for j in first['jobs']}=={j['document_id'] for j in second['jobs']}
    deadline=time.monotonic()+90
    while time.monotonic()<deadline:
        status=call('/demo/company/status')[1]
        if status['enriched']==24:
            break
        time.sleep(.25)
    assert status['search_ready']==24 and status['enriched']==24
    private=next(j for j in status['jobs'] if j['fixture_key']=='ember-private-budget')
    assert call('/jobs/'+private['id'],'demo-omar')[0]==404
    assert call('/demo/company/files/ember-private-budget','demo-omar')[0]==404
    assert all(f['visibility']!='private' for f in call('/demo/company','demo-omar')[1]['files'])
    assert call('/demo/company/status','demo-omar')[1]['total']==23
    assert call('/demo/company/status','demo-omar')[1]['search_ready']==23
    assert call('/demo/company/status','demo-nour')[1]['search_ready']==0
    assert call('/demo/company/files/not-a-file')[0]==404


@pytest.mark.parametrize('question',['what is that ?','What is this about?','Summarize this document','لخص هذا الملف','tell me about this','what does this mean?'])
def test_selected_document_overview_does_not_need_matching_question_words(workspace,question):
    job=source(workspace,b'The invented Aurora protocol uses a Thursday readiness review.\nEscalations go to the shift coordinator.\n')
    assert processing.process_one()
    conversation=main.create_conversation(main.NewConversation(document_ids=[job.document_id]),viewer())
    response=main.ask(conversation['id'],main.Question(question=question),viewer())
    assert response['statements'] and response['coverage']['mode']=='document_overview'
    assert response['provider']=='mock-extractive'
    assert not response['coverage']['partial']
    assert all(p['document_id']==job.document_id for p in response['evidence'])


def test_greeting_and_ambiguous_reference_do_not_invoke_model(workspace,monkeypatch):
    monkeypatch.setattr(main,'answer',lambda *args,**kwargs: pytest.fail('Nonfactual guidance must not spend on inference'))
    conversation=main.create_conversation(main.NewConversation(),viewer())
    response=main.ask(conversation['id'],main.Question(question='hi ?'),viewer())
    assert response['provider']=='system' and 'Linkmind' in response['message']
    response=main.ask(conversation['id'],main.Question(question='what is that?'),viewer())
    assert response['provider']=='system' and 'Select a document' in response['message']
    other=main.create_conversation(main.NewConversation(),viewer())
    response=main.ask(other['id'],main.Question(question='what is that?'),viewer())
    assert response['provider']=='system' and 'Select a document' in response['message']


def test_selected_context_is_bounded_and_revocation_blocks_summaries(workspace):
    content='\n'.join(f'Passage {i}: original fictional operational context '+('detail '*16) for i in range(160)).encode()
    job=source(workspace,content)
    assert processing.process_one()
    evidence,coverage=retrieval.selected_context(viewer(),[job.document_id],limit=8,max_characters=1500)
    assert 0<len(evidence)<=8 and sum(len(p['text']) for p in evidence)<=1500
    assert coverage['partial'] and coverage['total_passages']==160
    conversation=main.create_conversation(main.NewConversation(document_ids=[job.document_id]),viewer(OMAR))
    response=main.ask(conversation['id'],main.Question(question='summarize this'),viewer(OMAR))
    assert response['coverage']['partial'] and response['statements']
    main.change_access(job.document_id,main.AccessChange(visibility='private'),viewer())
    with pytest.raises(HTTPException) as denied:
        main.ask(conversation['id'],main.Question(question='what is this about?'),viewer(OMAR))
    assert denied.value.status_code==404
    assert main.history(conversation['id'],viewer(OMAR))['turns'][0]['suppressed']


def test_budget_pause_leaves_search_ready_without_retry_churn(workspace,monkeypatch):
    from app.inference_budget import BudgetStopped
    job=source(workspace)
    def stop(*args):
        raise BudgetStopped('The Sonnet test budget is reached or paused.')
    monkeypatch.setattr(processing,'mock_extract',stop)
    assert processing.process_one()
    result=main.job(job.id,viewer())
    assert result['search_status']=='ready' and result['enrichment_status']=='unavailable'
    assert result['status']=='extraction_unavailable' and result['error_code']=='test_budget_stopped'
