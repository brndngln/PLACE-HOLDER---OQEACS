def _lead(client):
    r = client.post('/api/v1/leads', json={'email':'a@example.com', 'source':'website', 'company_size':80, 'job_title':'CTO', 'industry':'tech'})
    assert r.status_code == 201
    return r.json()['id']

def test_capture_lead(client):
    lid = _lead(client)
    r = client.get(f'/api/v1/leads/{lid}')
    assert r.status_code == 200
    assert r.json()['score'] >= 0

def test_lead_scoring(client):
    lid = _lead(client)
    client.post(f'/api/v1/leads/{lid}/activity', json={'activity_type':'page_visit', 'metadata': {'page_url':'/pricing'}})
    client.post(f'/api/v1/leads/{lid}/activity', json={'activity_type':'download', 'metadata': {}})
    r = client.post(f'/api/v1/leads/{lid}/score')
    assert r.status_code == 200
    assert r.json()['score'] >= 35

def test_lead_nurture_enrollment(client):
    lid = _lead(client)
    r = client.post(f'/api/v1/leads/{lid}/nurture', json={'sequence_id':'seq-1'})
    assert r.status_code == 200
    assert r.json()['status'] == 'nurturing'

def test_bulk_import(client):
    r = client.post('/api/v1/leads/bulk', json={'leads':[{'email':'b@example.com','source':'email'},{'email':'c@example.com','source':'paid_ad'}]})
    assert r.status_code == 200
    assert r.json()['created'] == 2

def test_gdpr_delete(client):
    lid = _lead(client)
    d = client.delete(f'/api/v1/leads/{lid}')
    assert d.status_code == 200
    g = client.get(f'/api/v1/leads/{lid}')
    assert g.status_code == 404
