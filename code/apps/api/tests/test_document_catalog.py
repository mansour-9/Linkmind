from test_m2 import call,upload,wait
from app.db import engine,sql
from uuid import uuid4,UUID


def test_catalog_current_revision_and_access():
    first=wait(upload('alpha-charter'))
    private=wait(upload('alpha-private',visibility='private'))
    def catalog(token='demo-amal',ids=None):
        path='/documents'+('?'+'&'.join('id='+id for id in ids) if ids else '')
        status,rows=call(path,token)
        assert status==200
        return rows
    assert any(d['document_id']==first['document_id'] for d in catalog())
    assert all(d['document_id']!=private['document_id'] for d in catalog('demo-omar'))
    assert catalog('demo-nour',[first['document_id'],private['document_id']])==[]
    assert catalog('demo-omar',[private['document_id']])==[]
    revision=wait(upload('alpha-review',revision=first['document_id']))
    selected=catalog(ids=[first['document_id']])
    assert len(selected)==1 and selected[0]['version_id']==revision['version_id']
    assert selected[0]['filename']=='alpha-review.md'
    assert call('/documents/'+first['document_id']+'/access',body={'visibility':'private'},method='PATCH')[0]==200
    assert catalog('demo-omar',[first['document_id']])==[]
    assert call('/documents/'+first['document_id'],method='DELETE')[0]==200
    assert catalog(ids=[first['document_id']])==[]


def test_catalog_paginates_one_hundred_sources_without_processing_jobs():
    _,viewer=call('/me')
    ids=[uuid4() for _ in range(100)]
    try:
        with engine.begin() as conn:
            for n,did in enumerate(ids):
                vid=uuid4();name=f'catalog-scale-{n:03}.md'
                sql(conn,"INSERT INTO documents(id,organization_id,owner_id,filename,visibility) VALUES(:id,:org,:owner,:name,'team')",id=did,org=UUID(viewer['organization_id']),owner=UUID(viewer['id']),name=name)
                sql(conn,"INSERT INTO document_versions(id,organization_id,document_id,filename,checksum,byte_count,artifact_key) VALUES(:id,:org,:doc,:name,:checksum,1,'catalog-test')",id=vid,org=UUID(viewer['organization_id']),doc=did,name=name,checksum=str(did))
                sql(conn,"UPDATE documents SET current_version_id=:vid WHERE id=:id",vid=vid,id=did)
        found=[]
        for offset in range(0,100,20):
            status,rows=call('/documents?q=catalog-scale-&limit=20&offset='+str(offset))
            assert status==200 and len(rows)==20
            found.extend(d['document_id'] for d in rows)
        assert len(set(found))==100 and set(found)=={str(id) for id in ids}
        assert call('/documents?q=catalog-scale-&limit=20&offset=100')[1]==[]
        assert call('/documents?q=catalog-scale-','demo-nour')[1]==[]
    finally:
        with engine.begin() as conn:
            sql(conn,"UPDATE documents SET current_version_id=NULL WHERE id=ANY(:ids)",ids=ids)
            sql(conn,"DELETE FROM document_versions WHERE document_id=ANY(:ids)",ids=ids)
            sql(conn,"DELETE FROM documents WHERE id=ANY(:ids)",ids=ids)
