import logging
import time
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from contextvars import ContextVar

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.router import router as api_v1_router
from app.common.contracts import ApiResponse, AppError, ErrorResponse, success
from app.core.config import get_settings
from app.core.database import close_database, get_db_session
from app.infrastructure.adapters import MinioStorage, RedisCache

request_id_context: ContextVar[str] = ContextVar("request_id", default="-")
settings = get_settings()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    logging.basicConfig(format="%(asctime)s %(levelname)s %(message)s", level=logging.INFO)
    yield
    await close_database()


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Local-First enterprise foundation.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
settings.local_storage_path.mkdir(parents=True, exist_ok=True)
app.mount(
    "/local-media",
    StaticFiles(directory=str(settings.local_storage_path)),
    name="local-media",
)
app.include_router(api_v1_router)


@app.middleware("http")
async def context(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request.state.request_id = request_id
    token = request_id_context.set(request_id)
    started = time.perf_counter()
    try:
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
    finally:
        logger.info(
            "request_id=%s method=%s path=%s elapsed_ms=%.2f",
            request_id,
            request.method,
            request.url.path,
            (time.perf_counter() - started) * 1000,
        )
        request_id_context.reset(token)


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            code=exc.code, message=exc.message, request_id=request.state.request_id
        ).model_dump(),
    )


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content=ErrorResponse(
            code="VALIDATION_ERROR",
            message="Request validation failed",
            request_id=request.state.request_id,
        ).model_dump(),
    )


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception(
        "unhandled_exception request_id=%s method=%s path=%s",
        request.state.request_id,
        request.method,
        request.url.path,
        exc_info=exc,
    )
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            code="INTERNAL_SERVER_ERROR",
            message="An unexpected server error occurred.",
            request_id=request.state.request_id,
        ).model_dump(),
    )


@app.get("/health/live", response_model=ApiResponse[dict[str, str]], tags=["health"])
async def live(request: Request) -> ApiResponse[dict[str, str]]:
    return success({"status": "alive"}, request.state.request_id)


@app.get("/health/ready", response_model=ApiResponse[dict[str, str]], tags=["health"])
async def ready(
    request: Request, session: AsyncSession = Depends(get_db_session)
) -> ApiResponse[dict[str, str]] | JSONResponse:
    try:
        await session.execute(text("SELECT 1"))
        if settings.redis_enabled:
            await RedisCache().healthcheck()
        if settings.minio_enabled:
            await MinioStorage().healthcheck()
    except Exception as exc:
        logger.warning("readiness_failed request_id=%s error=%s", request.state.request_id, exc)
        return JSONResponse(
            status_code=503,
            content=ErrorResponse(
                code="DEPENDENCY_UNAVAILABLE",
                message="A required service is unavailable.",
                request_id=request.state.request_id,
            ).model_dump(),
        )
    return success({"status": "ready", "database": "mysql"}, request.state.request_id)
