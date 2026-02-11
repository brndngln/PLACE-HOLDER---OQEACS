from __future__ import annotations


def test_health(client):
    r = client.get('/health')
    assert r.status_code == 200
    assert r.json()['status'] == 'healthy'


def test_info(client):
    r = client.get('/info')
    assert r.status_code == 200
    assert r.json()['system_number'] == 5


def test_ready(client):
    r = client.get('/ready')
    assert r.status_code in (200, 503)
    assert 'status' in r.json()


def test_metrics(client):
    r = client.get('/metrics')
    assert r.status_code == 200
    assert 'http_requests_total' in r.text


def test_post_endpoint(client):
    # Uses first POST endpoint if available
    targets = [
        '/api/v1/templates/recommend',
        '/api/v1/tasks/decompose',
        '/api/v1/projects/decompose',
        '/api/v1/classify',
        '/api/v1/validate',
        '/api/v1/apis/ingest',
        '/api/v1/generate',
        '/api/v1/snapshots',
        '/api/v1/retrospectives',
        '/api/v1/runtimes/build',
    ]
    for t in targets:
        r = client.post(t, json={'description': 'test', 'payload': {'a': 1}})
        if r.status_code not in (404, 405):
            assert r.status_code in (200, 201, 202)
            assert isinstance(r.json(), dict)
            return
    assert False, 'no matching POST endpoint found'


def test_get_endpoint(client):
    targets = [
        '/api/v1/templates',
        '/api/v1/runtimes',
        '/api/v1/costs',
        '/api/v1/retrospectives',
        '/api/v1/apis',
        '/api/v1/scans',
    ]
    for t in targets:
        r = client.get(t)
        if r.status_code not in (404, 405):
            assert r.status_code == 200
            return
    assert False, 'no matching GET endpoint found'


def test_not_found_shape(client):
    r = client.get('/api/v1/does-not-exist')
    assert r.status_code == 404


def test_openapi(client):
    r = client.get('/openapi.json')
    assert r.status_code == 200
    assert 'paths' in r.json()
