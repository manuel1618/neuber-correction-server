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
        return templates.TemplateResponse(
            "index.html", {"request": request, "materials": materials["materials"]}
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

        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.0",
            "database": db_status,
            "session_count": session_count,
        }
