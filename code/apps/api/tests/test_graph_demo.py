from collections import Counter
from contextlib import contextmanager
import hashlib
import importlib.util
import json
from pathlib import Path
from uuid import UUID,uuid4
import pytest
from app import processing
from app.artifacts import save
from app.db import engine,sql
from app.graph_demo import MANIFEST,ROOT,graph_demo_records
from app.parsers import parse_document
from test_m2 import call,wait


def test_graph_demo_generator_is_deterministic_and_exactly_cited():
    spec=importlib.util.spec_from_file_location('demo_generator',ROOT.parent/'generate_graph_demo.py')
    generator=importlib.util.module_from_spec(spec);spec.loader.exec_module(generator)
    generated=generator.generate()
    assert generated==generator.generate()
    assert all((ROOT/name).read_bytes()==content.encode('utf-8') for name,content in generated.items())
    assert len(MANIFEST['fixtures'])==2
    assert MANIFEST['entity_count']==38 and MANIFEST['entity_occurrence_count']==76 and MANIFEST['relationship_count']==105
    assert Counter(e['kind'] for e in MANIFEST['fixtures'][0]['entities'])=={'project':4,'person':12,'team':6,'task':8,'decision':4,'technology':4}
    seen=set()
    for fixture in MANIFEST['fixtures']:
        content=(ROOT/fixture['filename']).read_bytes();lines=content.decode().splitlines()
        passages=[dict(id=str(uuid4()),text=p.text,locator=p.locator) for p in parse_document(fixture['filename'],content)]
        result=processing.mock_extract(content,passages)
        assert len(result.entities)==38
        bykey={entity['key']:entity for entity in fixture['entities']}
        for entity,record in zip(result.entities,fixture['entities']):
            assert entity.evidence[0].quote==lines[record['line']-1]
            assert entity.name in entity.evidence[0].quote
            assert all(identifier.value in entity.evidence[0].quote for identifier in entity.identifiers)
        for relationship,record in zip(result.relationships,fixture['relationships']):
            quote=relationship.evidence[0].quote
            assert quote==lines[record['line']-1]
            assert bykey[record['source_key']]['name'] in quote and bykey[record['target_key']]['name'] in quote
            assert generator.PHRASES[record['predicate']] in quote
            seen.add((record['source_key'],record['predicate'],record['target_key']))
        assert graph_demo_records(content+b'\n') is None
    assert len(seen)==105
    assert MANIFEST['fixtures'][0]['entities'][0]['line']!=MANIFEST['fixtures'][1]['entities'][0]['line']


def test_bedrock_mode_graph_fixture_never_calls_models(monkeypatch):
    fixture=MANIFEST['fixtures'][0];content=(ROOT/fixture['filename']).read_bytes()
    did,vid,jid=uuid4(),uuid4(),uuid4();org=UUID('00000000-0000-4000-8000-000000000001');owner=UUID('00000000-0000-4000-8000-000000000101')
    checksum=hashlib.sha256(content).hexdigest();artifact=save(org,checksum,content)
    with engine.connect() as conn:
        tx=conn.begin()
        try:
            sql(conn,"INSERT INTO documents(id,organization_id,owner_id,filename,visibility) VALUES(:id,:org,:owner,:filename,'team')",id=did,org=org,owner=owner,filename=fixture['filename'])
            sql(conn,"INSERT INTO document_versions(id,organization_id,document_id,filename,checksum,byte_count,artifact_key) VALUES(:id,:org,:doc,:filename,:checksum,:size,:artifact)",id=vid,org=org,doc=did,filename=fixture['filename'],checksum=checksum,size=len(content),artifact=artifact)
            sql(conn,"INSERT INTO processing_jobs(id,organization_id,version_id,owner_id,checksum,available_at,enrichment_requested) VALUES(:id,:org,:version,:owner,:checksum,now()-interval '100 days',true)",id=jid,org=org,version=vid,owner=owner,checksum=checksum)
            class TestEngine:
                @contextmanager
                def begin(self):
                    with conn.begin_nested(): yield conn
            def forbidden(*args,**kwargs): pytest.fail('Synthetic graph demo attempted a paid model call')
            monkeypatch.setattr(processing,'engine',TestEngine());monkeypatch.setattr(processing,'configured',lambda:True)
            monkeypatch.setattr(processing,'extract_bedrock_batches',forbidden);monkeypatch.setattr(processing,'embed',forbidden)
            import app.conflict_detection as conflicts
            monkeypatch.setattr(conflicts,'assess',forbidden)
            before=sql(conn,'SELECT count(*) FROM ai_usage').scalar_one()
            assert processing.process_one()
            row=sql(conn,"SELECT status,error FROM processing_jobs WHERE id=:id",id=jid).one()
            assert row.status=='ready',row.error
            version=sql(conn,"SELECT extraction_provider,embedding_status FROM document_versions WHERE id=:id",id=vid).one()
            assert tuple(version)==('graph-demo-fixture','unavailable')
            assert sql(conn,'SELECT count(*) FROM ai_usage').scalar_one()==before
        finally: tx.rollback()


def test_graph_demo_load_is_idempotent_and_connected_with_exact_counts():
    expected=call('/demo/graph-dataset')[1]
    assert (expected['entity_count'],expected['entity_occurrence_count'],expected['relationship_count'])==(38,76,105)
    jobs=[]
    try:
        status,loaded=call('/demo/graph-dataset/load',body={});assert status==202
        jobs=loaded['jobs'];assert len(jobs)==2
        for job in jobs: wait(job)
        status,summary=call('/demo/graph-dataset/status');assert status==200 and summary['ready'],summary
        assert (summary['entity_count'],summary['entity_occurrence_count'],summary['relationship_count'])==(38,76,105)
        again=call('/demo/graph-dataset/load',body={})[1]
        assert {job['id'] for job in again['jobs']}=={job['id'] for job in jobs}
        # A second viewer in the same organization reuses team-visible sources.
        other=call('/demo/graph-dataset/load','demo-omar',body={})[1]
        assert {job['id'] for job in other['jobs']}=={job['id'] for job in jobs}
        assert call('/demo/graph-dataset/status','demo-nour')[1]['source_count']==0
        atlas=call('/graph/search?q=DEMO-ATLAS')[1]['nodes'][0]
        assert atlas['name']=='Project Atlas'
        graph=call('/graph/explore?root='+atlas['id']+'&depth=3&limit=30')[1]
        immediate=call('/graph/explore?root='+atlas['id']+'&depth=1&limit=30')[1]
        assert len(graph['nodes'])>len(immediate['nodes'])
        assert 'Project Delta' in {n['name'] for n in graph['nodes']}
        assert graph['root_connection_count']>=10
        assert {'Project Atlas','Amal','Platform Engineering'}.issubset({n['name'] for n in graph['nodes']})
        assert 'contributes_to' in {edge['label'] for edge in graph['edges']}
        people=call('/graph/search?q=amal%40demo.linkmind.local')[1]['nodes']
        assert len(people)==1 and people[0]['name']=='Amal'
        cross=call('/graph/explore?root='+people[0]['id']+'&depth=1&limit=40')[1]
        assert {'Project Delta','Project Atlas'}.issubset({n['name'] for n in cross['nodes']})
        assert graph['visible_edge_count']<=120 and graph['visible_node_count']<=80
        rami=call('/graph/search?q=rami%40demo.linkmind.local')[1]
        assert rami['total']==1 and rami['nodes'][0]['connection_count']>=4
        edge=graph['edges'][0];evidence=call('/evidence/'+edge['chunk_id'])[1]
        names={node['id']:node['name'] for node in graph['nodes']}
        assert names[edge['source']] in evidence['quote'] and names[edge['target']] in evidence['quote']
        assert call('/evidence/'+edge['chunk_id'],'demo-nour')[0]==404
        assert call('/graph/overview?q=DEMO-ATLAS')[1]['entity']['name']=='Project Atlas'
        assert {'owned_by','member_of','contributes_to','informs','collaborates_with','advises'}.issubset(set(call('/graph/relationships')[1]))
    finally:
        for job in jobs: call('/documents/'+job['document_id'],method='DELETE')
