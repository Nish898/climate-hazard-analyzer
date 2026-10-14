import logging
import time
import uuid

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field, ValidationError
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from . import db, service
from .config import settings
from .logging_config import request_id_var, setup_logging
from .openmeteo import UpstreamError, geocode
from .schemas import AnalyzeParams

setup_logging()
log = logging.getLogger("api")
limiter = Limiter(key_func=get_remote_address, default_limits=[settings.rate_limit_default])

app = FastAPI(title="Climate Hazard Trend Analyzer", version="1.0.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Middleware order matters: the one added last is outermost. Rate limiting is innermost, then request
# logging (which also turns crashes into JSON 500s), then CORS, so even error responses carry CORS headers.
app.add_middleware(SlowAPIMiddleware)  # applies the default limit to routes without their own


@app.middleware("http")
async def request_logging(request: Request, call_next):
    rid = uuid.uuid4().hex[:12]
    request_id_var.set(rid)
    start = time.perf_counter()
    fields = {"method": request.method, "path": request.url.path, "client": get_remote_address(request)}
    try:
        response = await call_next(request)
    except Exception:
        log.exception("Unhandled error", extra={**fields, "status": 500, "duration_ms": _ms(start)})
        response = JSONResponse(status_code=500, content={"detail": "Internal server error", "request_id": rid})
    else:
        status = response.status_code
        level = logging.ERROR if status >= 500 else logging.WARNING if status >= 400 else logging.INFO
        if request.url.path == "/api/health" and status == 200:
            level = logging.DEBUG  # the container healthcheck hits this every few seconds
        log.log(level, "request completed", extra={**fields, "status": status, "duration_ms": _ms(start)})
    response.headers["X-Request-ID"] = rid
    return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_list,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)


def _ms(start: float) -> float:
    return round((time.perf_counter() - start) * 1000, 1)


def _format_errors(errors) -> str:
    """One readable string; field errors are prefixed with the field name."""
    parts = []
    for e in errors:
        loc = [str(x) for x in e.get("loc", ()) if x not in ("query", "body")]
        msg = e["msg"].removeprefix("Value error, ")
        parts.append(f"{loc[-1]}: {msg}" if loc else msg)
    return "; ".join(parts)


@app.exception_handler(UpstreamError)
async def upstream_handler(_: Request, exc: UpstreamError):
    log.warning("Upstream error: %s", exc)
    return JSONResponse(status_code=502, content={"detail": "Weather data provider is unavailable, try again shortly."})


@app.exception_handler(service.NoDataError)
async def no_data_handler(_: Request, exc: service.NoDataError):
    log.warning("No data: %s", exc)
    return JSONResponse(status_code=422, content={"detail": str(exc)})


@app.exception_handler(RequestValidationError)
async def validation_handler(_: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={"detail": _format_errors(exc.errors())})


def params(
    lat: float = Query(..., description="Latitude (or one box corner)"),
    lon: float = Query(..., description="Longitude (or one box corner)"),
    lat2: float | None = Query(None),
    lon2: float | None = Query(None),
    start: int = Query(1990),
    end: int = Query(2020),
    hazard: str = Query("heatwave"),
) -> AnalyzeParams:
    try:
        return AnalyzeParams(lat=lat, lon=lon, lat2=lat2, lon2=lon2, start=start, end=end, hazard=hazard)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=_format_errors(exc.errors()))


@app.get("/api/health")
@limiter.exempt
def health():
    """Liveness."""
    return {"status": "ok"}


@app.get("/api/ready")
@limiter.exempt
def ready():
    """Readiness: the database answers."""
    if not db.ping():
        return JSONResponse(status_code=503, content={"status": "unavailable", "database": "down"})
    return {"status": "ok", "database": "up"}


@app.get("/api/analyze")
@limiter.limit(settings.rate_limit_analyze)
def analyze(request: Request, p: AnalyzeParams = Depends(params)):
    return service.analyze(p)


@app.get("/api/export.csv")
@limiter.limit(settings.rate_limit_analyze)
def export_csv(request: Request, p: AnalyzeParams = Depends(params)):
    csv = service.to_csv(service.analyze(p))
    lat, lon = p.center
    return Response(
        csv,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="heatwaves_{lat}_{lon}_{p.start}-{p.end}.csv"'},
    )


class ClientLog(BaseModel):
    """Browser error report. Untrusted input that ends up in the logs, so every field is length-bounded."""

    kind: str = Field(max_length=40)
    message: str = Field(max_length=500)
    stack: str | None = Field(default=None, max_length=2000)
    url: str | None = Field(default=None, max_length=300)


client_log = logging.getLogger("client")


@app.post("/api/client-log", status_code=204)
@limiter.limit(settings.rate_limit_client_log)
def receive_client_log(request: Request, report: ClientLog):
    """Writes a frontend error into the server logs."""
    client_log.warning(
        "frontend error",
        extra={"kind": report.kind, "detail": report.message, "stack": report.stack, "page": report.url,
               "user_agent": (request.headers.get("user-agent") or "")[:200]},
    )
    return Response(status_code=204)


@app.get("/api/geocode")
def search_places(q: str = Query(..., min_length=2, max_length=80)):
    q = q.strip()
    if len(q) < 2:
        raise HTTPException(status_code=422, detail="Search text must be at least 2 characters")
    return {"results": geocode(q)}
