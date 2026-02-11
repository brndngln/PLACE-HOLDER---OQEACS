def test_connect_account(client):
    r = client.post('/api/v1/accounts', json={'platform':'twitter','account_handle':'@omni','credentials':{'token':'x'}})
    assert r.status_code == 201
    assert r.json()['platform'] == 'twitter'

def test_list_accounts(client):
    client.post('/api/v1/accounts', json={'platform':'linkedin','account_handle':'omni','credentials':{}})
    r = client.get('/api/v1/accounts')
    assert r.status_code == 200
    assert len(r.json()) == 1

def test_account_overview(client):
    client.post('/api/v1/accounts', json={'platform':'twitter','account_handle':'@omni','credentials':{}})
    r = client.get('/api/v1/accounts/overview')
    assert r.status_code == 200
    assert 'total_followers' in r.json()
