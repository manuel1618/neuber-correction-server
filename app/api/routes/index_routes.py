"""
Index routes
"""

from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.models.models import load_materials


def mk_index_routes(app: FastAPI, templates: Jinja2Templates):
    """Add index routes to the FastAPI app"""

    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request):
        """Main page with form"""
        materials = load_materials()
        # Pull custom title from cookie if present
        custom_title = request.cookies.get("custom_title")
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "materials": materials["materials"],
                "custom_title": custom_title,
            },
        )

    @app.get("/health")
    async def health_check(request: Request):
        """Health check endpoint for monitoring"""
        try:
            # Test database connection and get session count
            db = request.app.state.db
            session_count = db.get_session_count()
            db_status = "healthy"
        except Exception as e:
            db_status = f"error: {str(e)}"
            session_count = 0

        # Rate limiting
        from app.utils.session import check_rate_limit

        allowed, rate_info = check_rate_limit(db, f"health:{request.state.ip_address}")

        if not allowed:
            from fastapi import HTTPException

            raise HTTPException(status_code=429, detail="Rate limit exceeded")

        response_data = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.0",
            "database": db_status,
            "session_count": session_count,
        }

        from fastapi.responses import JSONResponse

        response = JSONResponse(content=response_data)

        # Set rate limiting headers
        response.headers["X-RateLimit-Limit"] = str(rate_info["limit"])
        response.headers["X-RateLimit-Remaining"] = str(rate_info["remaining"])
        response.headers["X-RateLimit-Reset"] = str(rate_info["reset"])

        return response
