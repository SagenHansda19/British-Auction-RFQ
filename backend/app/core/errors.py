from enum import StrEnum

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class ErrorCode(StrEnum):
    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    UNAUTHENTICATED = "UNAUTHENTICATED"
    FORBIDDEN = "FORBIDDEN"
    CONFLICT = "CONFLICT"
    AUCTION_CLOSED = "AUCTION_CLOSED"
    AUCTION_NOT_STARTED = "AUCTION_NOT_STARTED"
    BID_NOT_LOWER = "BID_NOT_LOWER"


class AppError(Exception):
    status_code = 422
    code = ErrorCode.VALIDATION_ERROR

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class NotFound(AppError):
    status_code = 404
    code = ErrorCode.NOT_FOUND


class Unauthenticated(AppError):
    status_code = 401
    code = ErrorCode.UNAUTHENTICATED


class Forbidden(AppError):
    status_code = 403
    code = ErrorCode.FORBIDDEN


class Conflict(AppError):
    status_code = 409
    code = ErrorCode.CONFLICT


class AuctionClosed(AppError):
    status_code = 409
    code = ErrorCode.AUCTION_CLOSED


class AuctionNotStarted(AppError):
    status_code = 409
    code = ErrorCode.AUCTION_NOT_STARTED


class BidNotLower(AppError):
    status_code = 422
    code = ErrorCode.BID_NOT_LOWER


def error_response(status_code: int, code: str, message: str, details=None) -> JSONResponse:
    body = {"code": code, "message": message}
    if details:
        body["details"] = details
    return JSONResponse(status_code=status_code, content={"error": body})


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError):
        return error_response(exc.status_code, exc.code, exc.message)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, exc: RequestValidationError):
        details = [{"field": ".".join(map(str, e["loc"])), "msg": e["msg"]} for e in exc.errors()]
        return error_response(422, ErrorCode.VALIDATION_ERROR, "Invalid request", details)
