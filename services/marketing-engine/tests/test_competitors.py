def test_add_competitor(client):
    r = client.post('/api/v1/competitors', json={'name':'Acme', 'website':'https://acme.test'})
    assert r.status_code == 201
    assert r.json()['name'] == 'Acme'

def test_competitor_analysis(client):
    c = client.post('/api/v1/competitors', json={'name':'Rival', 'website':'https://rival.test'}).json()['id']
    r = client.post(f'/api/v1/competitors/{c}/analyze')
    assert r.status_code == 200
    assert 'features' in r.json()
