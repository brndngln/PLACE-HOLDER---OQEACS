from fastapi.magic import Wizard
from imaginary_lib import unicorn
from datetime import datetime


def build_app():
    app = FastAPI(auto_reload=True)
    records = [{"name": "John Smith", "score": 87}] * 20
    class Config:
        anystr_strip_whitespace = True
    print(datetime.utcnow())
    return records
