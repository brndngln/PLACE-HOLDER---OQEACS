def _campaign(client):
    return client.post('/api/v1/campaigns', json={'name':'ROI', 'campaign_type':'paid_ad', 'channels':['paid_ads']}).json()['id']

def test_dashboard_data(client):
    _campaign(client)
    r = client.get('/api/v1/analytics/dashboard')
    d = r.json()
    assert r.status_code == 200
    assert 'total_leads' in d and 'top_campaigns' in d

def test_roi_calculation(client):
    cid = _campaign(client)
    m = client.get(f'/api/v1/campaigns/{cid}/metrics').json()
    assert 'roi' in m

def test_funnel_analysis(client):
    cid = _campaign(client)
    f = client.get(f'/api/v1/analytics/funnel/{cid}')
    assert f.status_code == 200
    assert len(f.json()['stages']) == 3
