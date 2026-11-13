from fastapi.testclient import TestClient
from app import main


def test_local_demo_authentication_without_preview_proxy(monkeypatch):
    monkeypatch.setattr(main,"LOCAL_PREVIEW",False)
    with TestClient(main.app) as client:
        assert client.get('/api/v1/demo/company',headers={'Authorization':'Bearer demo-amal'}).status_code==200
        assert client.get('/api/v1/demo/company',headers={'Authorization':'Bearer unknown'}).status_code==401


def test_preview_proxy_secret_and_identity_are_both_required(monkeypatch):
    monkeypatch.setattr(main,"LOCAL_PREVIEW",True)
    monkeypatch.setattr(main,"PREVIEW_SECRET","test-only-preview-secret")
    with TestClient(main.app) as client:
        headers={'Authorization':'Bearer demo-amal','X-Preview-Proxy':'test-only-preview-secret'}
        assert client.get('/api/v1/demo/company',headers=headers).status_code==200
        assert client.get('/api/v1/demo/company',headers={'Authorization':'Bearer demo-amal'}).status_code==403
        assert client.get('/api/v1/demo/company',headers={**headers,'Authorization':'Bearer unknown'}).status_code==401
    with TestClient(main.app,client=('203.0.113.10',12345)) as client:
        assert client.get('/api/v1/demo/company',headers={'Authorization':'Bearer demo-amal'}).status_code==403
