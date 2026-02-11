def _account(client):
    return client.post('/api/v1/accounts', json={'platform':'twitter','account_handle':'@omni','credentials':{}}).json()['id']

def _post(client, account_id):
    return client.post('/api/v1/posts', json={'text':'thread content', 'platform':'twitter', 'account_id':account_id, 'media_urls':[], 'format':'thread'}).json()['id']

def test_generate_twitter_content(client):
    r = client.post('/api/v1/content/generate', json={'topic':'agentic coding','platforms':['twitter'],'content_pillar':'educational','tone':'bold','include_hashtags':True})
    text = r.json()['posts']['twitter']['text']
    assert len(text) <= 280

def test_generate_linkedin_content(client):
    r = client.post('/api/v1/content/generate', json={'topic':'enterprise quality','platforms':['linkedin'],'content_pillar':'professional','tone':'professional','include_hashtags':True})
    assert len(r.json()['posts']['linkedin']['text']) <= 3000

def test_generate_instagram_content(client):
    r = client.post('/api/v1/content/generate', json={'topic':'build in public','platforms':['instagram'],'content_pillar':'inspiring','tone':'casual','include_hashtags':True})
    assert 'hashtags' in r.json()['posts']['instagram']

def test_repurpose_twitter_to_linkedin(client):
    aid = _account(client)
    pid = _post(client, aid)
    r = client.post('/api/v1/content/repurpose', json={'source_post_id': pid, 'target_platforms':['linkedin']})
    assert 'linkedin' in r.json()['variants']

def test_hashtag_research(client):
    r = client.post('/api/v1/content/hashtag-research', json={'topic':'ai', 'platform':'twitter', 'count':5})
    assert len(r.json()['hashtags']) == 5
