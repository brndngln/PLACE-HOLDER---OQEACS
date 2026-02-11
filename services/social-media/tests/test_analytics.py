def _seed(client):
    aid = client.post('/api/v1/accounts', json={'platform':'twitter','account_handle':'@omni','credentials':{}}).json()['id']
    p = client.post('/api/v1/posts', json={'text':'viral', 'platform':'twitter', 'account_id':aid, 'media_urls':[], 'format':'text'}).json()['id']
    client.post(f'/api/v1/posts/{p}/publish')

def test_dashboard(client):
    _seed(client)
    r = client.get('/api/v1/analytics/dashboard')
    assert r.status_code == 200
    assert 'total_followers' in r.json()

def test_growth_projection(client):
    _seed(client)
    r = client.get('/api/v1/analytics/growth/projection')
    assert r.status_code == 200
    assert any(m['count'] == 100000000 for m in r.json()['projected_milestones'])

def test_viral_detection(client):
    _seed(client)
    r = client.get('/api/v1/analytics/posts/viral')
    assert r.status_code == 200
    assert len(r.json()) >= 1
