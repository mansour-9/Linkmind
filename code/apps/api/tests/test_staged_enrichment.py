from types import SimpleNamespace
from uuid import UUID,uuid4

import pytest
from fastapi import HTTPException

from app import main,processing,retrieval,enrichment_staging as staging,conflict_detection
from app.contracts import Extraction
from app.db import sql
from app.fixture_provider import FIXTURES
from test_search_readiness import workspace,source,viewer,OMAR,fail


def enriched(conn):
    job=source(conn,FIXTURES['cloud-migration'].path.read_bytes())
    assert processing.process_one()
    assert main.job(job.id,viewer())['entity_count']>0
    return job


def snapshot(conn,version):
    return {table:sql(conn,f'SELECT id FROM live_{table} WHERE version_id=:id ORDER BY id',id=version).scalars().all()
            for table in ('entities','claims','relationships')}


def test_staged_activation_keeps_search_citations_and_invalidates_prior_answers(workspace):
    job=enriched(workspace)
    prior=snapshot(workspace,job.version_id)
    canonical_ids=sql(workspace,'SELECT canonical_id FROM live_entities WHERE version_id=:id ORDER BY canonical_id',id=job.version_id).scalars().all()
    chunks=sql(workspace,'SELECT id,text,locator FROM chunks WHERE version_id=:id ORDER BY id',id=job.version_id).all()
    conversation=main.create_conversation(main.NewConversation(document_ids=[job.document_id]),viewer())
    main.ask(conversation['id'],main.Question(question='Project Alpha'),viewer())
    queued=main.reprocess(job.id,viewer())
    candidate=queued['staged_version_id']
    assert queued['preserved_enrichment'] and queued['enrichment_status']=='queued'
    assert queued['staged_activation_state']=='staged'
    assert snapshot(workspace,job.version_id)==prior
    assert retrieval.search(viewer(),'Project Alpha',[job.document_id],semantic=False)
    with pytest.raises(HTTPException) as pending:
        main.reprocess(job.id,viewer())
    assert pending.value.status_code==409
    assert processing.process_one()
    current=main.job(job.id,viewer())
    assert current['status']=='ready' and current['active_enrichment_version_id']==candidate
    assert current['staged_activation_state']=='live'
    assert sql(workspace,'SELECT activation_state FROM document_versions WHERE id=:id',id=job.version_id).scalar()=='rolled_back'
    assert sql(workspace,'SELECT current_version_id FROM documents WHERE id=:id',id=job.document_id).scalar()==job.version_id
    assert sql(workspace,'SELECT id,text,locator FROM chunks WHERE version_id=:id ORDER BY id',id=job.version_id).all()==chunks
    assert snapshot(workspace,job.version_id)['entities']!=prior['entities']
    assert len(snapshot(workspace,job.version_id)['entities'])==len(prior['entities'])
    assert sql(workspace,'SELECT canonical_id FROM live_entities WHERE version_id=:id ORDER BY canonical_id',id=job.version_id).scalars().all()==canonical_ids
    assert main.history(conversation['id'],viewer())['turns'][0]['suppressed']
    assert main.evidence(chunks[0].id,viewer())['quote']==chunks[0].text
    assert sql(workspace,'SELECT count(*) FROM entities WHERE version_id=:id',id=job.version_id).scalar()==2*len(prior['entities'])


@pytest.mark.parametrize('failure',['extraction','exact_quote','conflict','empty'])
def test_failed_staging_retains_live_facts_and_can_retry(workspace,monkeypatch,failure):
    job=enriched(workspace)
    prior=snapshot(workspace,job.version_id)
    original=processing.mock_extract
    if failure=='extraction':
        monkeypatch.setattr(processing,'mock_extract',fail)
    elif failure=='exact_quote':
        def bad(content,passages):
            result=original(content,passages)
            result.entities[0].evidence[0].quote='Not present in the source'
            return result
        monkeypatch.setattr(processing,'mock_extract',bad)
    elif failure=='empty':
        monkeypatch.setattr(processing,'mock_extract',lambda *args:Extraction(entities=[],claims=[],relationships=[]))
    else:
        monkeypatch.setattr(processing,'configured',lambda:True)
        monkeypatch.setattr(processing,'extract_bedrock_batches',lambda passages,scope:[original(FIXTURES['cloud-migration'].path.read_bytes(),passages)])
        monkeypatch.setattr(conflict_detection,'assess',fail)
    first=main.reprocess(job.id,viewer())['staged_version_id']
    assert processing.process_one()
    result=main.job(job.id,viewer())
    assert result['status']=='enrichment_staged_failed' and result['search_status']=='ready'
    assert result['preserved_enrichment'] and result['can_retry']
    assert result['staged_activation_state']=='rolled_back'
    assert snapshot(workspace,job.version_id)==prior
    assert retrieval.search(viewer(),'Project Alpha',[job.document_id],semantic=False)
    monkeypatch.setattr(processing,'mock_extract',original)
    monkeypatch.setattr(processing,'configured',lambda:False)
    retry=main.retry(job.id,viewer())
    assert retry['staged_version_id']!=first
    assert processing.process_one()
    assert main.job(job.id,viewer())['status']=='ready'


def test_later_revision_cannot_be_overwritten_by_staged_old_revision(workspace,monkeypatch):
    job=enriched(workspace)
    original=processing.mock_extract
    new=[]
    def superseded(content,passages):
        if not new:
            new.append(source(workspace,b'CurrentRevisionZebra is the only current source text.',document=job.document_id))
            assert processing.process_one()
        return original(content,passages)
    main.reprocess(job.id,viewer())
    monkeypatch.setattr(processing,'mock_extract',superseded)
    assert processing.process_one()
    assert main.job(job.id,viewer())['status']=='enrichment_staged_failed'
    assert sql(workspace,'SELECT current_version_id FROM documents WHERE id=:id',id=job.document_id).scalar()==new[0].version_id
    assert sql(workspace,"""SELECT count(*) FROM live_entities e JOIN documents d ON d.id=:document
        WHERE e.version_id=d.current_version_id""",document=job.document_id).scalar()==0
    assert retrieval.search(viewer(),'CurrentRevisionZebra',[job.document_id],semantic=False)


def test_staging_requires_management_and_revocation_blocks_derived_access(workspace):
    job=enriched(workspace)
    with pytest.raises(HTTPException) as forbidden:
        main.reprocess(job.id,viewer(OMAR))
    assert forbidden.value.status_code==403
    main.reprocess(job.id,viewer())
    main.change_access(job.document_id,main.AccessChange(visibility='private'),viewer())
    assert not retrieval.search(viewer(OMAR),'Project Alpha',[job.document_id],semantic=False)
    assert processing.process_one()
    canonical=sql(workspace,'SELECT canonical_id FROM live_entities WHERE version_id=:id LIMIT 1',id=job.version_id).scalar_one()
    with pytest.raises(HTTPException) as hidden:
        main.graph(viewer(OMAR),root=canonical,q='',limit=150)
    assert hidden.value.status_code==404
    assert main.entity_detail(workspace,viewer(),canonical)['id']==canonical


def test_unverified_candidate_cannot_be_published(workspace):
    job=enriched(workspace)
    queued=main.reprocess(job.id,viewer())
    token=uuid4()
    sql(workspace,"UPDATE processing_jobs SET status='processing',lease_token=:token,lease_until=clock_timestamp()+interval '5 minutes' WHERE id=:id",id=job.id,token=token)
    fake=SimpleNamespace(**vars(job),organization_id=viewer().organization_id,lease_token=token,staged_version_id=queued['staged_version_id'])
    prior=snapshot(workspace,job.version_id)
    with pytest.raises(ValueError,match='verified staged candidate'):
        processing.publish(workspace,fake,Extraction(entities=[],claims=[],relationships=[]),[],'fixture')
    assert snapshot(workspace,job.version_id)==prior


def test_expired_staged_attempt_retains_live_generation(workspace):
    job=enriched(workspace)
    prior=snapshot(workspace,job.version_id)
    queued=main.reprocess(job.id,viewer())
    sql(workspace,"UPDATE processing_jobs SET status='processing',attempts=3,lease_until=clock_timestamp()-interval '1 minute' WHERE id=:id",id=job.id)
    assert processing.process_one() is False
    assert main.job(job.id,viewer())['status']=='enrichment_staged_failed'
    assert snapshot(workspace,job.version_id)==prior
    assert sql(workspace,'SELECT activation_state FROM document_versions WHERE id=:id',id=queued['staged_version_id']).scalar()=='rolled_back'


def test_generation_foreign_key_cannot_target_another_source(workspace):
    from sqlalchemy.exc import IntegrityError
    one=enriched(workspace)
    two=enriched(workspace)
    candidate=main.reprocess(one.id,viewer())['staged_version_id']
    with pytest.raises(IntegrityError):
        with workspace.begin_nested():
            sql(workspace,'UPDATE processing_jobs SET staged_version_id=:candidate WHERE id=:id',candidate=candidate,id=two.id)


def test_failed_refresh_does_not_reduce_available_company_knowledge(workspace,monkeypatch):
    from app.company_demo import ROOT
    job=source(workspace,(ROOT/'atlas-charter.md').read_bytes())
    assert processing.process_one()
    before=main.company_status(workspace,viewer())['enriched']
    main.reprocess(job.id,viewer())
    monkeypatch.setattr(processing,'mock_extract',fail)
    assert processing.process_one()
    assert main.company_status(workspace,viewer())['enriched']==before
