from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app import auto_agent, connection_oauth as oauth, connectors, main, notion_mcp
from app.connector_providers import ConnectionSpec, notion_page_id
from app.connector_transport import SourceFailure
from test_connection_oauth import begin, callback, local
from test_search_readiness import viewer, workspace


PAGE = 'abcdef0123456789abcdef0123456789'
OTHER = '0123456789abcdef0123456789abcdef'
URL = 'https://app.notion.com/p/'+PAGE


def source():
    return ConnectionSpec(kind='notion',name='Company handbook',scope_id='pending-scope',
        auth_method='oauth',notion_pages=[dict(title='Annual leave policy',url=URL+'?source=copy_link')])


def test_explicit_handbook_topic_wins_over_a_pronoun_in_the_same_question():
    assert auto_agent.handbook_question(
        'How many days of annual leave do AsterBridge employees receive, and are company holidays counted against it?')
    assert not auto_agent.handbook_question('What is it?')
    assert not auto_agent.handbook_question('What is the policy for this Jira project?')
    assert auto_agent.handbook_lookup('كم يوم إجازتي السنوية؟')=='annual leave policy'
    assert auto_agent.handbook_lookup('وش تشتغل الشركة؟')=='company and teams'


def test_notion_prefers_a_specific_policy_over_the_company_overview():
    spec = ConnectionSpec(kind='notion',name='Company handbook',scope_id='pending-scope',
        auth_method='oauth',notion_pages=[
            dict(title='AsterBridge Labs company and teams',url=URL),
            dict(title='AsterBridge Labs annual leave policy',url='https://app.notion.com/p/'+OTHER),
        ])
    provider=notion_mcp.NotionProvider(spec)
    assert provider.search(
        'How many days of annual leave do AsterBridge employees receive, and are company holidays counted against it?'
    )[0]['native_id']==OTHER
    assert provider.search('What is AsterBridge Labs?')[0]['native_id']==PAGE


def test_notion_allowlist_and_original_citation(monkeypatch):
    spec = source()
    assert spec.scope_id == PAGE
    assert notion_page_id('https://www.notion.so/Annual-leave-'+PAGE) == PAGE
    calls = []

    def fetch(tool,arguments):
        calls.append((tool,arguments))
        return dict(metadata={'type':'page'},url=URL,title='Annual leave policy',
                    text='Observation time\n<page>\n<content>\n25 working days.\n</content>\n</page>')

    def mcp(*args,**kwargs):
        assert kwargs['endpoint']==notion_mcp.ENDPOINT and kwargs['allowed']=={'notion-fetch','fetch'}
        return SimpleNamespace(tools={'notion-fetch':{}},call=fetch)

    monkeypatch.setattr(notion_mcp,'AtlassianMCP',mcp)
    provider=notion_mcp.NotionProvider(spec)
    assert provider.search('What is our annual leave policy?')[0]['native_id']==PAGE
    assert provider.search('private meeting')==[]
    with pytest.raises(SourceFailure) as denied:provider.get(OTHER)
    assert denied.value.code=='outside_scope' and not calls
    record=provider.get(PAGE)
    assert record.original_url==URL and record.content.endswith(b'25 working days.')
    assert record.updated is None and provider.authorize(PAGE).revision==record.revision
    assert calls==[('notion-fetch',{'id':PAGE})]*2


def test_notion_pkce_uses_existing_encrypted_login_and_requires_a_test_before_sync(local,monkeypatch):
    connection=connectors.create(viewer(),source())['id']
    monkeypatch.setattr(oauth,'register_notion',lambda redirect:'notion-test-client')
    state,cookie,data=begin(connection)
    assert data['authorization_url'].startswith('https://mcp.notion.com/authorize?')
    assert 'code_challenge_method=S256' in data['authorization_url']

    def exchange(config,**kwargs):
        assert config['client_id']=='notion-test-client' and not config['client_secret']
        assert config['provider']=='notion' and kwargs['verifier']
        return dict(access_token='fictional-notion-token',refresh_token='fictional-refresh',expires_at=10**12)

    monkeypatch.setattr(oauth,'exchange',exchange)
    assert callback(state,cookie).endswith('auth=connected')
    assert oauth.token_authorization(oauth.reference(connection),'mcp.notion.com')=='Bearer fictional-notion-token'
    with pytest.raises(SourceFailure):oauth.token_authorization(oauth.reference(connection),'api.notion.com')
    with main.engine.connect() as db:generation=connectors.owned(db,viewer(),connection).generation
    with pytest.raises(HTTPException) as denied:
        connectors.change_mode(viewer(),connection,connectors.ModeChange(mode='sync',expected_generation=generation))
    assert denied.value.status_code==409 and 'test' in denied.value.detail.lower()
