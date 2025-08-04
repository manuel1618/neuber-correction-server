"""
Neuber Correction Server

This server provides an API for stress correction using the Neuber method.
It allows users to upload materials and perform stress corrections.
"""

import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.api.__main__ import mk_routes
from app.db.sqlite3 import SQLiteDatabase
from app.utils.session import get_client_ip, get_session_id

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

# Initialize database
db = SQLiteDatabase("neuber_correction.db")


@asynccontextmanager
async def lifespan(my_app: FastAPI):
    """Application lifespan events"""
    # Startup
    db.create_tables()
    my_app.state.db = db
    yield
    # Shutdown
    db.close()


app = FastAPI(title="Neuber Correction Server", version="1.0.0", lifespan=lifespan)

# Add rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Templates
templates = Jinja2Templates(directory="app/templates")


@app.middleware("http")
async def session_middleware(request: Request, call_next):
    """Middleware for session management and logging"""
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id

    # Get session ID
    session_id = get_session_id(request)
    request.state.session_id = session_id

    # Get client IP
    ip_address = get_client_ip(request)
    request.state.ip_address = ip_address

    try:
        response = await call_next(request)

        # Set session cookie if not present
        if "session_id" not in request.cookies:
            response.set_cookie(
                key="session_id",
                value=session_id,
                max_age=3600,  # 1 hour
                httponly=True,
                samesite="lax",
            )

        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id

        return response

    except Exception as e:
        raise e


# Add routes
mk_routes(app, templates)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
