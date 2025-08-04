"""
Neuber Correction Server

This server provides an API for stress correction using the Neuber method.
It allows users to upload materials and perform stress corrections.
"""

from typing import Any, Dict

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.api.__main__ import mk_routes

app = FastAPI(title="Neuber Correction Server", version="1.0.0")

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Templates
templates = Jinja2Templates(directory="app/templates")

# Store custom materials per session (in production, use proper session management)
custom_materials: Dict[str, Dict[str, Any]] = {}


if __name__ == "__main__":
    import uvicorn

    mk_routes(app, custom_materials, templates)
    uvicorn.run(app, host="0.0.0.0", port=8000)
