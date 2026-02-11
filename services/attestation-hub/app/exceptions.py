from collections.abc import Callable
from fastapi import Request
from fastapi.responses import JSONResponse


class ServiceError(Exception):
    def __init__(self, message: str, status_code: int = 400, code: str = "service_error") -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code


async def service_error_handler(_: Request, exc: ServiceError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"error": exc.code, "message": exc.message})


exception_handlers: dict[type[Exception], Callable[..., JSONResponse]] = {
    ServiceError: service_error_handler,
}
