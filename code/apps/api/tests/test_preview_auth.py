from fastapi.testclient import TestClient
from app.main import app


def test_local_preview_authentication_and_loopback_guard():
    with TestClient(app,client=('127.0.0.1',12345)) as client:
        response=client.get('/api/v1/demo/company',headers={'Authorization':'Bearer demo-amal','X-Preview-Proxy':'northstar-local-preview-2026-11-12'})
        assert response.status_code in {200,403}
        bad=client.get('/api/v1/demo/company',headers={'Authorization':'Bearer unknown'})
        assert bad.status_code==401
    with TestClient(app,client=('203.0.113.10',12345)) as client:
        response=client.get('/api/v1/demo/company',headers={'Authorization':'Bearer demo-amal','X-Preview-Proxy':'northstar-local-preview-2026-11-12'})
        assert response.status_code==403
