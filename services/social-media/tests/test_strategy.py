def _seed(client):
    client.post('/api/v1/accounts', json={'platform':'twitter','account_handle':'@omni','credentials':{}})

def test_recommendations(client):
    _seed(client)
    r = client.get('/api/v1/strategy/recommendations')
    assert r.status_code == 200
    assert len(r.json()['recommendations']) >= 1

def test_100m_plan(client):
    _seed(client)
    r = client.post('/api/v1/strategy/100m-plan')
    assert r.status_code == 200
    assert any(p['target'] == 100000000 for p in r.json()['phases'])
