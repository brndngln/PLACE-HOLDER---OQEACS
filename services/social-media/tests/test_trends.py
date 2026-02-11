def test_scan_trends(client):
    r = client.post('/api/v1/trends/scan')
    assert r.status_code == 200
    assert len(r.json()['trends']) >= 3

def test_create_post_from_trend(client):
    t = client.post('/api/v1/trends/scan').json()['trends'][0]['id']
    r = client.post(f'/api/v1/trends/{t}/create-post', json={'platforms':['twitter']})
    assert r.status_code == 200
    assert 'twitter' in r.json()['posts']
