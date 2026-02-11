def test_add_competitor(client):
    r = client.post('/api/v1/competitors', json={'platform':'twitter','handle':'@rival'})
    assert r.status_code == 201
    assert r.json()['account_handle'] == '@rival'

def test_competitor_analysis(client):
    cid = client.post('/api/v1/competitors', json={'platform':'linkedin','handle':'rivalco'}).json()['id']
    r = client.post(f'/api/v1/competitors/{cid}/analyze')
    assert r.status_code == 200
    assert 'latest_post' in r.json()

def test_content_gaps(client):
    client.post('/api/v1/competitors', json={'platform':'twitter','handle':'@r1'})
    r = client.get('/api/v1/competitors/content-gaps?our_topics=automation')
    assert r.status_code == 200
    assert 'gaps' in r.json()
