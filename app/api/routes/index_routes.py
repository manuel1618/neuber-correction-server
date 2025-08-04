"""
Index routes
"""

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
