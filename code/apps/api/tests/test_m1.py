import hashlib
import json
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from uuid import UUID, uuid4

import pytest

from app import processing
from app.db import engine, sql
from app.fixture_provider import FIXTURES

BASE = "http://api:8000/api/v1"
AMAL, OMAR, NOUR = "demo-amal", "demo-omar", "demo-nour"


def request(path, token=None, body=None, content_type=None):
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if content_type:
        headers["Content-Type"] = content_type
    req = Request(BASE + path, data=body, headers=headers)
    try:
        with urlopen(req, timeout=8) as response:
            return response.status, response.read()
    except HTTPError as response:
        return response.code, response.read()


def upload(filename, payload, visibility, token=AMAL):
    boundary = uuid4().hex
    body = (
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"visibility\"\r\n\r\n{visibility}\r\n"
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{filename}\"\r\n"
        "Content-Type: text/plain\r\n\r\n"
    ).encode() + payload + f"\r\n--{boundary}--\r\n".encode()
    return request("/sources/upload", token, body, f"multipart/form-data; boundary={boundary}")


def read(path, token=AMAL):
    status, raw = request(path, token)
    assert status == 200, (status, raw)
    return json.loads(raw)


def await_job(job_id):
    for _ in range(40):
        job = read(f"/jobs/{job_id}")
        if job["status"] not in {"queued","processing"}:
            return job
        time.sleep(0.25)
    pytest.fail("Worker did not finish the upload")


def test_real_upload_pipeline_and_permissions():
    assert request("/graph")[0] == 401
    payload = FIXTURES["cloud-migration"].path.read_bytes()
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda _: upload("cloud-migration.md", payload, "team"), range(2)))
    assert all(status == 202 for status, _ in responses), responses
    first, second = (json.loads(raw) for _, raw in responses)
    assert first["id"] == second["id"]
    assert first["version_id"] == second["version_id"]
    assert upload("cloud-migration.md", payload, "private")[0] == 409
    assert await_job(first["id"])["status"] == "ready"
    # Graph assertions deliberately request optional enrichment; uploads default to text.
    from test_m2 import call
    assert call("/jobs/"+first["id"]+"/reprocess",body={})[0]==202
    assert await_job(first["id"])["enrichment_status"] == "ready"

    private = FIXTURES["private-review"].path.read_bytes()
    status, raw = upload("private-review.md", private, "private")
    assert status == 202, raw
    restricted = json.loads(raw)
    assert await_job(restricted["id"])["status"] == "ready"
    assert call("/jobs/"+restricted["id"]+"/reprocess",body={})[0]==202
    assert await_job(restricted["id"])["enrichment_status"] == "ready"

    graph = read("/graph")
    shared_nodes = [node for node in graph["nodes"] if node["version_id"] == first["version_id"]]
    assert len(shared_nodes) == 5
    shared_ids = {node["id"] for node in shared_nodes}
    assert len([edge for edge in graph["edges"] if edge["source"] in shared_ids]) == 4
    project = next(node for node in shared_nodes if node["name"] == "Project Alpha")
    claims = read(f"/entities/{project['id']}", OMAR)["claims"]
    assert {claim["predicate"].lower().replace(" ","_") for claim in claims} == {"managed_by", "target_database"}
    assert all(claim["quote"].encode() in payload for claim in claims)
    cite = read(f"/evidence/{claims[0]['chunk_id']}", OMAR)
    assert cite["quote"] == claims[0]["quote"]
    assert request(f"/documents/{first['version_id']}/download", OMAR) == (200, payload)

    cedar = next(node for node in graph["nodes"]
                 if node["name"] == "Project Cedar" and node["version_id"] == restricted["version_id"])
    cedar_claim = read(f"/entities/{cedar['id']}")["claims"][0]
    private_ids = {node["id"] for node in graph["nodes"] if node["version_id"] == restricted["version_id"]}
    for other in (OMAR, NOUR):
        visible = read("/graph", other)
        assert private_ids.isdisjoint(node["id"] for node in visible["nodes"])
        assert all(edge["source"] not in private_ids and edge["target"] not in private_ids for edge in visible["edges"])
        assert restricted["id"] not in {job["id"] for job in read("/sources", other)}
        assert request(f"/jobs/{restricted['id']}", other)[0] == 404
        assert request(f"/entities/{cedar['id']}", other)[0] == 404
        assert request(f"/evidence/{cedar_claim['chunk_id']}", other)[0] == 404
        assert request(f"/documents/{restricted['version_id']}/download", other)[0] == 404
    assert request(f"/entities/{project['id']}", NOUR)[0] == 404
    assert request(f"/documents/{first['version_id']}/download", NOUR)[0] == 404


def test_unknown_text_and_invalid_uploads():
    status, raw = upload("unrecognized.txt", "اختبار محلي\nUnrecognized upload.".encode(), "private", NOUR)
    assert status == 202, raw
    job = json.loads(raw)
    for _ in range(40):
        result = read(f"/jobs/{job['id']}", NOUR)
        if result["status"] not in {"queued","processing"}:
            break
        time.sleep(0.25)
    assert result["status"] == "ready" and result["enrichment_status"] == "not_requested"
    assert job["version_id"] not in {node["version_id"] for node in read("/graph", NOUR)["nodes"]}
    assert upload("unsupported.pdf", b"plain text", "private")[0] == 422
    assert upload("invalid.txt", b"\xff\xff", "private")[0] == 422
    assert upload("too-large.txt", b"x" * (20 * 1024 * 1024 + 1), "private")[0] == 413
