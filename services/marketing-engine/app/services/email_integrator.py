async def send_email_batch(*args, **kwargs):
    return {'sent': len(kwargs.get('recipients', []))}
