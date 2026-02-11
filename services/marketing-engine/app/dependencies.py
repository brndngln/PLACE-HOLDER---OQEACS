from fastapi import Request

def get_correlation_id(request: Request) -> str:
    return getattr(request.state, 'correlation_id', '')
