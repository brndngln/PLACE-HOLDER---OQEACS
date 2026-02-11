'''FastAPI dependency injection helpers.'''
from fastapi import Request

from src.service import OmniService


def get_service(request: Request) -> OmniService:
    '''Return initialized service from app state.'''
    return request.app.state.service
