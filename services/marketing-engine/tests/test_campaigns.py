def _create_campaign(client):
    r = client.post('/api/v1/campaigns', json={'name': 'Q1 Growth', 'campaign_type': 'email_blast', 'channels': ['email']})
    assert r.status_code == 201
    return r.json()['id']

def test_create_campaign(client):
    cid = _create_campaign(client)
    assert cid

def test_launch_campaign(client):
    cid = _create_campaign(client)
    r = client.post(f'/api/v1/campaigns/{cid}/launch')
    assert r.status_code == 200
    assert r.json()['status'] == 'active'

def test_pause_and_resume(client):
    cid = _create_campaign(client)
    client.post(f'/api/v1/campaigns/{cid}/launch')
    p = client.post(f'/api/v1/campaigns/{cid}/pause')
    assert p.json()['status'] == 'paused'
    r = client.post(f'/api/v1/campaigns/{cid}/resume')
    assert r.json()['status'] == 'active'

def test_duplicate_campaign(client):
    cid = _create_campaign(client)
    r = client.post(f'/api/v1/campaigns/{cid}/duplicate')
    assert r.status_code == 201
    assert r.json()['name'].startswith('Copy of')

def test_delete_only_draft(client):
    cid = _create_campaign(client)
    client.post(f'/api/v1/campaigns/{cid}/launch')
    r = client.delete(f'/api/v1/campaigns/{cid}')
    assert r.status_code == 409
