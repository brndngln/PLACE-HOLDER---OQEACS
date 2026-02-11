def _account(client):
    return client.post('/api/v1/accounts', json={'platform':'twitter','account_handle':'@omni','credentials':{}}).json()['id']

def test_create_draft(client):
    aid = _account(client)
    r = client.post('/api/v1/posts', json={'text':'hello', 'platform':'twitter', 'account_id':aid, 'media_urls':[], 'format':'text'})
    assert r.status_code == 201
    assert r.json()['status'] == 'draft'

def test_schedule_post(client):
    aid = _account(client)
    p = client.post('/api/v1/posts', json={'text':'schedule', 'platform':'twitter', 'account_id':aid, 'media_urls':[], 'format':'text'}).json()['id']
    r = client.post(f'/api/v1/posts/{p}/schedule', json={'scheduled_at':'2026-02-12T10:00:00Z'})
    assert r.json()['status'] == 'scheduled'

def test_publish_immediately(client):
    aid = _account(client)
    p = client.post('/api/v1/posts', json={'text':'publish', 'platform':'twitter', 'account_id':aid, 'media_urls':[], 'format':'text'}).json()['id']
    r = client.post(f'/api/v1/posts/{p}/publish')
    assert r.status_code == 200
    assert r.json()['status'] == 'published'
    assert r.json()['platform_post_id']

def test_cross_post(client):
    r = client.post('/api/v1/posts/cross-post', json={'text':'launch', 'platforms':['twitter','linkedin'], 'adapt_per_platform':True})
    assert r.status_code == 200
    assert len(r.json()['posts']) == 2

def test_bulk_schedule(client):
    rows = [{'text':'a','platform':'twitter','scheduled_at':'2026-02-12T09:00:00Z'}, {'text':'b','platform':'linkedin','scheduled_at':'2026-02-12T10:00:00Z'}]
    r = client.post('/api/v1/posts/bulk-schedule', json={'posts': rows})
    assert r.status_code == 200
    assert r.json()['scheduled'] == 2
