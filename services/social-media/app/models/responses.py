from pydantic import BaseModel

class GenericResponse(BaseModel):
    ok: bool = True
    message: str = 'ok'
