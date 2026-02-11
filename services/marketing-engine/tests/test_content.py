def test_generate_ad_copy(client):
    r = client.post('/api/v1/content/generate/ad-copy', json={'product_description':'AI coding suite', 'target_audience':'CTOs', 'tone':'bold', 'channel':'email', 'variant_count':5})
    assert r.status_code == 200
    assert len(r.json()['variants']) == 5

def test_generate_email(client):
    r = client.post('/api/v1/content/generate/email', json={'purpose':'announce', 'audience':'founders', 'product':'omni'})
    data = r.json()
    assert len(data['subject_lines']) == 5
    assert '<html>' in data['body_html']

def test_generate_landing_page(client):
    r = client.post('/api/v1/content/generate/landing-page', json={'product':'omni', 'value_proposition':'ship faster', 'target_audience':'dev teams', 'cta_goal':'book demo', 'style':'modern'})
    data = r.json()
    assert '<meta name=' in data['html']
    assert '<form' in data['html']

def test_generate_seo_article(client):
    r = client.post('/api/v1/content/generate/seo-article', json={'primary_keyword':'agentic coding', 'secondary_keywords':['automation'], 'target_length':1200, 'audience':'engineers'})
    data = r.json()
    assert data['word_count'] > 50
    assert 'article_html' in data

def test_generate_content_calendar(client):
    r = client.post('/api/v1/calendar/generate', json={'goals':['growth'], 'channels':['email','seo'], 'days':30})
    assert r.status_code == 200
    assert len(r.json()['entries']) >= 3
