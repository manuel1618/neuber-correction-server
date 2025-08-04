"""
Routes
"""

from fastapi import FastAPI
from fastapi.templating import Jinja2Templates

from app.api.routes.index_routes import mk_index_routes
from app.api.routes.material_routes import mk_material_routes
from app.api.routes.neuber_routes import mk_neuber_routes


def mk_routes(app: FastAPI, templates: Jinja2Templates):
    """Add routes to the FastAPI app"""

    mk_index_routes(app, templates)
    mk_material_routes(app)
    mk_neuber_routes(app)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(mk_routes, host="0.0.0.0", port=8000)
