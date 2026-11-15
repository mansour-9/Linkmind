"""RF2: organization and discovery work with zero extracted facts or paid calls."""
from datetime import datetime, timezone
from io import BytesIO
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException, UploadFile
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from app import main, processing, repository, retrieval
from app.db import sql
from app.source_evidence import ResourceIdentity, SourceEvidence, FieldEvidence, EvidenceCoverage
from test_search_readiness import workspace, source, viewer, OMAR, AMAL, ORG


def ready(conn, content=b'RepositoryZebra handover details are retained.', **kwargs):
    job = source(conn, content, enrichment_requested=False, **kwargs)
    assert processing.process_one()
    return job


def group(name='Delivery', kind='project', who=None):
    return main.create_repository_group(repository.GroupCreate(name=name, kind=kind), who or viewer())


def attach(job, project=None, team=None, title=None, revision=0, who=None):
    return main.update_document_metadata(job.document_id, repository.MetadataChange(
        expected_revision=revision, title=title, project_id=project, team_id=team), who or viewer())


def test_catalog_metadata_topic_and_search_filters_need_no_graph(workspace, monkeypatch):
    monkeypatch.setattr(processing, 'enrich', lambda *a: pytest.fail('No graph workload'))
    first = ready(workspace)
    second = ready(workspace, b'Another RepositoryZebra document is unrelated.')
    project, team = group('Voyager'), group('Operations', 'team')
    before = sql(workspace, 'SELECT checksum,embedding_status FROM document_versions WHERE id=:id', id=first.version_id).one()
    data = attach(first, project['id'], team['id'], 'Support handbook')
    assert data['title'] == 'Support handbook' and data['filename'] == 'readiness.md'
    assert data['metadata_revision'] == 1 and data['native_id'] == str(first.document_id)
    assert before == sql(workspace, 'SELECT checksum,embedding_status FROM document_versions WHERE id=:id', id=first.version_id).one()
    for table in ('entities', 'claims', 'relationships', 'ai_usage'):
        assert sql(workspace, f'SELECT count(*) FROM {table} WHERE version_id=:id', id=first.version_id).scalar() == 0
    for query in ('Voyager', 'Operations', 'Support handbook', 'RepositoryZebra'):
        found = repository.resources(workspace, viewer(), query=query, filters={'project_id': project['id']})
        assert found['total'] == 1 and found['items'][0]['document_id'] == first.document_id
    for filters in ({'project_id': project['id']}, {'team_id': team['id']}, {'format': 'md', 'project_id': project['id']}):
        hits = retrieval.search(viewer(), 'RepositoryZebra', semantic=False, filters=filters)
        assert hits and {p['document_id'] for p in hits} == {first.document_id}
    assert retrieval.search(viewer(), 'Voyager', semantic=False)[0]['document_id'] == first.document_id
    assert not repository.resources(workspace, viewer(), query='RepositoryZebra', filters={'format': 'pdf'})['items']
    assert not retrieval.search(viewer(), 'RepositoryZebra', filters={'source_instance_id': uuid4()}, semantic=False)
    assert second.document_id != first.document_id


def test_private_groups_counts_sources_and_titles_reauthorize(workspace):
    owner_before = sum(s['resource_count'] for s in repository.source_catalog(workspace, viewer()))
    member_before = sum(s['resource_count'] for s in repository.source_catalog(workspace, viewer(OMAR)))
    job = ready(workspace, visibility='private')
    private = group('Hidden project title')
    attach(job, private['id'], title='Hidden document title')
    assert not repository.resources(workspace, viewer(OMAR), query='Hidden')['items']
    assert private['id'] not in {g['id'] for g in repository.groups(workspace, viewer(OMAR))}
    # Counts and last received dates are calculated only from accessible resources.
    assert sum(s['resource_count'] for s in repository.source_catalog(workspace, viewer())) == owner_before + 1
    assert sum(s['resource_count'] for s in repository.source_catalog(workspace, viewer(OMAR))) == member_before
    with pytest.raises(HTTPException) as exc:
        main.document_metadata(job.document_id, viewer(OMAR))
    assert exc.value.status_code == 404
    main.change_access(job.document_id, main.AccessChange(visibility='team'), viewer())
    assert private['id'] in {g['id'] for g in repository.groups(workspace, viewer(OMAR))}
    main.change_access(job.document_id, main.AccessChange(visibility='private'), viewer())
    assert private['id'] not in {g['id'] for g in repository.groups(workspace, viewer(OMAR))}
    other = main.Viewer(id=UUID('00000000-0000-4000-8000-000000000103'), organization_id=UUID('00000000-0000-4000-8000-000000000002'), name='Nour', organization='Other', role='member')
    assert not repository.resources(workspace, other, query='Hidden')['items']
    assert private['id'] not in {g['id'] for g in repository.groups(workspace, other)}
    main.delete(job.document_id, viewer())
    assert not repository.resources(workspace, viewer(), query='Hidden')['items']


def test_metadata_ownership_conflicts_and_group_kind_are_enforced(workspace):
    job = ready(workspace)
    project = group()
    data = attach(job, project['id'])
    with pytest.raises(HTTPException) as exc:
        attach(job, title='stale writer')
    assert exc.value.status_code == 409
    with pytest.raises(HTTPException) as exc:
        attach(job, title='unauthorized writer', revision=1, who=viewer(OMAR))
    assert exc.value.status_code == 403
    with pytest.raises(HTTPException) as exc:
        attach(job, team=project['id'], revision=1)
    assert exc.value.status_code == 404
    secret = group('Omar private group', who=viewer(OMAR))
    with pytest.raises(HTTPException):
        attach(job, project=secret['id'], revision=1)
    assert main.document_metadata(job.document_id, viewer())['metadata_revision'] == data['metadata_revision']
    assert sql(workspace, "SELECT actor_id FROM audit_events WHERE resource_id=:id AND action='update_document_metadata'", id=job.document_id).scalar() == AMAL


def test_groups_with_same_name_are_separate_and_new_revision_keeps_resource_identity(workspace):
    job = ready(workspace)
    a, b = group('Same name'), group('Same name')
    assert a['id'] != b['id']
    before = attach(job, a['id'], title='Human display title')
    passage = retrieval.search(viewer(), 'RepositoryZebra', [job.document_id], semantic=False)[0]
    revision = main.revision(job.document_id, viewer(), UploadFile(BytesIO(b'New revision has a fresh release checklist.'), filename='release.txt'))
    # Existing current source is retained while the revision is queued.
    assert main.document_metadata(job.document_id, viewer())['version_id'] == job.version_id
    assert processing.process_one()
    after = main.document_metadata(job.document_id, viewer())
    assert after['version_id'] == revision['version_id']
    for key in ('source_instance_id', 'native_id', 'project_id', 'custom_title', 'metadata_revision'):
        assert after[key] == before[key]
    evidence = main.evidence(UUID(passage['id']), viewer())
    assert evidence['provenance']['source_revision'] == str(job.version_id)
    assert evidence['quote'] == passage['text'] and evidence['provenance']['excerpt'] == passage['text']
    assert evidence['provenance']['identity']['native_id'] == str(job.document_id)
    assert evidence['provenance']['original_url'] is None and evidence['provenance']['source_updated_at'] is None
    assert evidence['provenance']['observed_at'] and evidence['provenance']['origin'] == 'stored'
    versions = main.document_versions(job.document_id, viewer(), limit=1, offset=0)
    assert versions['has_more'] and versions['items'][0]['current']
    assert main.document_versions(job.document_id, viewer(), limit=1, offset=1)['items'][0]['version_id'] == job.version_id
    main.change_access(job.document_id, main.AccessChange(visibility='private'), viewer())
    for call in (lambda: main.document_versions(job.document_id, viewer(OMAR), limit=20, offset=0), lambda: main.evidence(UUID(passage['id']), viewer(OMAR))):
        with pytest.raises(HTTPException) as exc:
            call()
        assert exc.value.status_code == 404


def test_pending_files_and_catalog_pagination_do_not_depend_on_jobs_cap(workspace):
    token = 'Pending' + uuid4().hex
    jobs = [source(workspace, (token + str(i)).encode(), enrichment_requested=False) for i in range(203)]
    for job in jobs:
        sql(workspace, 'UPDATE documents SET title=:title WHERE id=:id', title=token, id=job.document_id)
    first = repository.resources(workspace, viewer(), query=token, limit=40)
    last = repository.resources(workspace, viewer(), query=token, limit=40, offset=200)
    assert first['total'] == 203 and first['has_more'] and len(last['items']) == 3 and not last['has_more']
    assert not ({r['document_id'] for r in first['items']} & {r['document_id'] for r in last['items']})
    assert all(r['search_ready_at'] is None for r in first['items'])
    assert jobs[0].document_id in {r['document_id'] for r in last['items']}
    assert jobs[0].document_id not in {r['document_id'] for r in main.sources(viewer())}


def test_metadata_filter_rechecked_after_semantic_inference(workspace, monkeypatch):
    job = ready(workspace)
    project = group()
    attach(job, project['id'])
    monkeypatch.setattr(retrieval, 'configured', lambda: True)
    monkeypatch.setenv('BEDROCK_EMBEDDING_MODEL', 'rf2-test')
    def revoked(*args):
        sql(workspace, 'UPDATE documents SET project_id=NULL WHERE id=:id', id=job.document_id)
        return [1.0, 0.0, 0.0]
    monkeypatch.setattr(retrieval, 'embed', revoked)
    assert retrieval.search(viewer(), 'RepositoryZebra', filters={'project_id': project['id']}) == []


def test_source_qualified_native_ids_and_group_foreign_keys(workspace):
    source_ids = [uuid4(), uuid4()]
    for sid in source_ids:
        sql(workspace, "INSERT INTO source_instances(id,organization_id,kind,instance_key,name) VALUES(:id,:org,'fixture',:key,'Offline adapter fixture')", id=sid, org=ORG, key=str(sid))
    for sid in source_ids:
        sql(workspace, "INSERT INTO documents(id,organization_id,owner_id,filename,visibility,source_instance_id,native_id) VALUES(:id,:org,:owner,'issue.txt','private',:source,'TASK-7')", id=uuid4(), org=ORG, owner=AMAL, source=sid)
    with pytest.raises(IntegrityError):
        with workspace.begin_nested():
            sql(workspace, "INSERT INTO documents(id,organization_id,owner_id,filename,visibility,source_instance_id,native_id) VALUES(:id,:org,:owner,'collision.txt','private',:source,'TASK-7')", id=uuid4(), org=ORG, owner=AMAL, source=source_ids[0])
    team = group('Team identity', 'team')
    job = ready(workspace)
    with pytest.raises(IntegrityError):
        with workspace.begin_nested():
            sql(workspace, 'UPDATE documents SET project_id=:team WHERE id=:id', team=team['id'], id=job.document_id)
    identity = sql(workspace, "SELECT id,source_instance_id,native_id FROM documents WHERE source_instance_id=:id", id=source_ids[0]).one()
    # A reconnect uses the same instance identity; rotating connection credentials is
    # outside the resource key. No credential field exists in this repository contract.
    sql(workspace, "UPDATE source_instances SET name='Reconnected fixture' WHERE id=:id", id=source_ids[0])
    assert identity == sql(workspace, "SELECT id,source_instance_id,native_id FROM documents WHERE source_instance_id=:id", id=source_ids[0]).one()


def test_repository_http_filters_and_validation(workspace):
    client = TestClient(main.app)
    headers = {'Authorization': 'Bearer demo-amal'}
    job = ready(workspace)
    project = group()
    attach(job, project['id'])
    response = client.get('/api/v1/repository/resources', params={'project_id': str(project['id']), 'format': 'md'}, headers=headers)
    assert response.status_code == 200 and response.json()['total'] == 1
    assert client.get('/api/v1/repository/resources?after=2027-01-01&before=2026-01-01', headers=headers).status_code == 422
    assert client.get('/api/v1/repository/resources?format=exe', headers=headers).status_code == 422
    assert client.get('/api/v1/repository/resources?limit=41', headers=headers).status_code == 422
    assert client.get('/api/v1/repository/resources').status_code == 401
    assert client.get('/api/v1/search?q=RepositoryZebra&project_id=' + str(project['id']), headers=headers).json()[0]['document_id'] == str(job.document_id)


def live_fixture():
    identity = ResourceIdentity(organization_id=ORG, source_instance_id=uuid4(), resource_type='issue', native_id='DEMO-12')
    return dict(reference_id='offline-observation-1', identity=identity, origin='live',
        original_url='https://example.invalid/issues/DEMO-12', observed_at=datetime.now(timezone.utc),
        fields=[FieldEvidence(field='assignee', value={'account_id': 'fixture-user', 'display_name': 'Test person'})],
        access_dependencies=[identity], coverage=EvidenceCoverage(complete=False, description='Offline fixture: current assignee field only.'))


def test_live_evidence_preserves_field_semantics_without_persistence(workspace):
    before = sql(workspace, 'SELECT count(*) FROM documents').scalar()
    evidence = SourceEvidence(**live_fixture())
    assert evidence.excerpt is None and evidence.source_revision is None
    assert evidence.fields[0].field == 'assignee' and evidence.coverage.complete is False
    assert sql(workspace, 'SELECT count(*) FROM documents').scalar() == before


@pytest.mark.parametrize('change', ['fabricated_quote', 'missing_dependency', 'other_tenant', 'naive_time', 'stored_without_revision', 'no_support'])
def test_invalid_evidence_never_becomes_a_supported_quote(change):
    data = live_fixture()
    if change == 'fabricated_quote': data['excerpt'] = 'A made-up prose quotation for a JSON field.'
    elif change == 'missing_dependency': data['access_dependencies'] = []
    elif change == 'other_tenant': data['access_dependencies'].append(data['identity'].model_copy(update={'organization_id': uuid4()}))
    elif change == 'naive_time': data['observed_at'] = datetime.now()
    elif change == 'stored_without_revision': data['origin'] = 'stored'
    else: data['fields'] = []
    with pytest.raises(ValidationError):
        SourceEvidence(**data)
