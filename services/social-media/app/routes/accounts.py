from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from app.models.requests import ConnectAccountRequest

router = APIRouter()
ACCOUNTS = {}

@router.post('/api/v1/accounts', status_code=201)
async def connect_account(payload: ConnectAccountRequest):
    aid = str(len(ACCOUNTS)+1)
    ACCOUNTS[aid] = {'id': aid, 'platform': payload.platform, 'account_handle': payload.account_handle, 'follower_count': 1000, 'following_count': 50, 'post_count': 0, 'is_verified': False, 'is_active': True, 'last_synced_at': datetime.now(timezone.utc).isoformat()}
    return ACCOUNTS[aid]

@router.get('/api/v1/accounts')
async def list_accounts():
    return list(ACCOUNTS.values())

@router.get('/api/v1/accounts/overview')
async def overview():
    by = {}
    for acc in ACCOUNTS.values():
        by[acc['platform']] = by.get(acc['platform'], 0) + int(acc['follower_count'])
    return {'total_accounts': len(ACCOUNTS), 'total_followers': sum(by.values()), 'followers_by_platform': by}

@router.get('/api/v1/accounts/{account_id}')
async def get_account(account_id: str):
    if account_id not in ACCOUNTS:
        raise HTTPException(status_code=404, detail='account not found')
    return ACCOUNTS[account_id]

@router.put('/api/v1/accounts/{account_id}')
async def update_account(account_id: str, payload: dict):
    if account_id not in ACCOUNTS:
        raise HTTPException(status_code=404, detail='account not found')
    ACCOUNTS[account_id].update(payload)
    ACCOUNTS[account_id]['last_synced_at'] = datetime.now(timezone.utc).isoformat()
    return ACCOUNTS[account_id]

@router.delete('/api/v1/accounts/{account_id}')
async def delete_account(account_id: str):
    if account_id not in ACCOUNTS:
        raise HTTPException(status_code=404, detail='account not found')
    ACCOUNTS.pop(account_id, None)
    return {'deleted': True}

@router.post('/api/v1/accounts/{account_id}/sync')
async def sync_account(account_id: str):
    if account_id not in ACCOUNTS:
        raise HTTPException(status_code=404, detail='account not found')
    ACCOUNTS[account_id]['follower_count'] += 25
    ACCOUNTS[account_id]['last_synced_at'] = datetime.now(timezone.utc).isoformat()
    return ACCOUNTS[account_id]
