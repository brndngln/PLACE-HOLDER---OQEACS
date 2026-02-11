def _campaign(client):
    return client.post('/api/v1/campaigns', json={'name':'AB', 'campaign_type':'email_blast', 'channels':['email']}).json()['id']

def test_create_ab_test(client):
    cid = _campaign(client)
    r = client.post(f'/api/v1/ab-tests/{cid}/create', json={'variants':[{'label':'A','traffic_weight':0.5},{'label':'B','traffic_weight':0.5}]})
    assert r.status_code == 200
    assert len(r.json()['variants']) == 2

def test_record_events(client):
    cid = _campaign(client)
    client.post(f'/api/v1/ab-tests/{cid}/create')
    for _ in range(10):
        client.post(f'/api/v1/ab-tests/{cid}/record', json={'variant_label':'A','event_type':'impressions','value':1})
    r = client.get(f'/api/v1/ab-tests/{cid}/results')
    assert r.status_code == 200
    assert r.json()['variants'][0]['impressions'] >= 10

def test_declare_winner(client):
    cid = _campaign(client)
    c = client.post(f'/api/v1/ab-tests/{cid}/create').json()
    winner = c['variants'][0]['id']
    r = client.post(f'/api/v1/ab-tests/{cid}/declare-winner', json={'variant_id': winner})
    assert r.status_code == 200
    assert r.json()['winner_variant_id'] == winner
