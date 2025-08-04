"""
Neuber Correction Server

This server provides an API for stress correction using the Neuber method.
It allows users to upload materials and perform stress corrections.
"""

import base64
import io
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import matplotlib.pyplot as plt
import yaml
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from neuber_correction import (
    MaterialForNeuberCorrection,
    NeuberCorrection,
    NeuberSolverSettings,
)
from pydantic import BaseModel

app = FastAPI(title="Neuber Correction Server", version="1.0.0")

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Templates
templates = Jinja2Templates(directory="app/templates")

# Store custom materials per session (in production, use proper session management)
custom_materials: Dict[str, Dict[str, Any]] = {}


# Load materials
def load_materials():
    """Load materials from YAML file"""
    materials_file = Path("materials/materials.yaml")
    if materials_file.exists():
        with open(materials_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            # Convert new format to old format for compatibility
            if "materials" in data and isinstance(data["materials"], list):
                materials_dict = {}
                for material in data["materials"]:
                    if "id" in material and "properties" in material:
                        materials_dict[material["id"]] = {
                            "yield_strength": material["properties"].get("fty", 0),
                            "sigma_u": material["properties"].get("ftu", 0),
                            "elastic_mod": material["properties"].get("E", 0),
                            "eps_u": material["properties"].get("epsilon_u", 0),
                            "description": material.get("name", material["id"]),
                        }
                return {"materials": materials_dict}
            return data
    return {"materials": {}}


# Pydantic models
class CorrectionRequest(BaseModel):
    """
    Class for correction request
    """

    material_name: str
    stress_values: List[float]
    custom_material: Optional[Dict[str, Any]] = None


class CorrectionResponse(BaseModel):
    """
    Class for correction response
    """

    original_stresses: List[float]
    corrected_stresses: List[float]
    material_properties: dict
    plot_data: Optional[str] = None


class ManualMaterialRequest(BaseModel):
    """
    Class for manual material request
    """

    name: str
    yield_strength: float
    sigma_u: float
    elastic_mod: float
    eps_u: float
    description: Optional[str] = None


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Main page with form"""
    materials = load_materials()
    return templates.TemplateResponse(
        "index.html", {"request": request, "materials": materials["materials"]}
    )


@app.post("/api/correct")
async def correct_stresses(request: CorrectionRequest):
    """API endpoint for stress correction"""
    materials = load_materials()

    # Check if using custom material
    if request.custom_material:
        material_props = request.custom_material
    else:
        if request.material_name not in materials["materials"]:
            raise HTTPException(status_code=400, detail="Material not found")
        material_props = materials["materials"][request.material_name]

    material = MaterialForNeuberCorrection(
        yield_strength=material_props["yield_strength"],
        sigma_u=material_props["sigma_u"],
        elastic_mod=material_props["elastic_mod"],
        eps_u=material_props["eps_u"],
    )

    neuber_settings = NeuberSolverSettings(
        tolerance=1e-6,
        max_iterations=10000,
        memoization_precision=1e-6,
    )

    neuber = NeuberCorrection(material=material, settings=neuber_settings)

    corrected_stresses = neuber.correct_stress_values(request.stress_values)

    return CorrectionResponse(
        original_stresses=request.stress_values,
        corrected_stresses=corrected_stresses,
        material_properties={
            "yield_strength": material.yield_strength,
            "sigma_u": material.sigma_u,
            "elastic_mod": material.elastic_mod,
            "eps_u": material.eps_u,
        },
    )


@app.post("/api/plot")
async def generate_plot(
    material_name: str = Form(...),
    stress_value: float = Form(...),
    custom_material: Optional[str] = Form(None),
):
    """Generate and return Neuber diagram plot"""
    materials = load_materials()

    # Parse custom material if provided
    if custom_material:
        try:
            material_props = json.loads(custom_material)
        except json.JSONDecodeError as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid custom material format: {e}",
            ) from e
    else:
        # Check if material exists in materials dictionary
        if material_name not in materials["materials"]:
            raise HTTPException(
                status_code=400, detail=f"Material '{material_name}' not found"
            )
        material_props = materials["materials"][material_name]

    # Validate material properties
    if not material_props:
        raise HTTPException(status_code=400, detail="Invalid material properties")

    required_props = ["yield_strength", "sigma_u", "elastic_mod", "eps_u"]
    missing_props = [prop for prop in required_props if prop not in material_props]
    if missing_props:
        raise HTTPException(
            status_code=400,
            detail=f"Material missing required properties: {missing_props}",
        )

    material = MaterialForNeuberCorrection(
        yield_strength=material_props["yield_strength"],
        sigma_u=material_props["sigma_u"],
        elastic_mod=material_props["elastic_mod"],
        eps_u=material_props["eps_u"],
    )

    neuber_settings = NeuberSolverSettings(
        tolerance=1e-6,
        max_iterations=10000,
        memoization_precision=1e-6,
    )

    neuber = NeuberCorrection(material=material, settings=neuber_settings)

    # Generate plot
    fig, _ = neuber.plot_neuber_diagram(
        stress_value,
        show_plot=False,
        plot_file="neuber_diagram.png",
        plot_pretty_name=f"{material_name} Neuber Diagram",
    )

    # Convert plot to base64 string
    img_buffer = io.BytesIO()
    fig.savefig(img_buffer, format="png", dpi=300, bbox_inches="tight")
    img_buffer.seek(0)
    img_str = base64.b64encode(img_buffer.getvalue()).decode()

    plt.close(fig)

    return {"plot_data": f"data:image/png;base64,{img_str}"}


@app.post("/api/upload-materials")
async def upload_materials(file: UploadFile = File(...)):
    """Upload custom materials.yaml file"""
    if not file.filename.endswith(".yaml") and not file.filename.endswith(".yml"):
        raise HTTPException(status_code=400, detail="File must be a YAML file")

    try:
        content = await file.read()
        materials_data = yaml.safe_load(content.decode("utf-8"))

        # Validate the structure
        if not isinstance(materials_data, dict) or "materials" not in materials_data:
            raise HTTPException(
                status_code=400,
                detail="Invalid YAML structure. Must contain 'materials' key",
            )

        # Handle new format (array of materials)
        if isinstance(materials_data["materials"], list):
            materials_dict = {}
            for material in materials_data["materials"]:
                if (
                    not isinstance(material, dict)
                    or "id" not in material
                    or "properties" not in material
                ):
                    raise HTTPException(
                        status_code=400,
                        detail="Invalid material format. Each material must have 'id' and 'properties' fields",
                    )

                props = material["properties"]
                required_props = ["fty", "ftu", "E", "epsilon_u"]
                missing_props = [prop for prop in required_props if prop not in props]
                if missing_props:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Material '{material['id']}' missing required properties: {missing_props}",
                    )

                # Convert to internal format
                materials_dict[material["id"]] = {
                    "yield_strength": props["fty"],
                    "sigma_u": props["ftu"],
                    "elastic_mod": props["E"],
                    "eps_u": props["epsilon_u"],
                    "description": material.get("name", material["id"]),
                }

            materials_data["materials"] = materials_dict

        # Handle old format (dict of materials)
        elif isinstance(materials_data["materials"], dict):
            # Validate each material has required properties
            for name, props in materials_data["materials"].items():
                required_props = ["yield_strength", "sigma_u", "elastic_mod", "eps_u"]
                missing_props = [prop for prop in required_props if prop not in props]
                if missing_props:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Material '{name}' missing required properties: {missing_props}",
                    )
        else:
            raise HTTPException(
                status_code=400,
                detail="Materials must be either a list (new format) or dictionary (old format)",
            )

        # Store in session (in production, use proper session management)
        session_id = "default"  # In production, get from session
        custom_materials[session_id] = materials_data["materials"]

        return {
            "message": "Materials uploaded successfully",
            "materials": materials_data["materials"],
            "count": len(materials_data["materials"]),
        }

    except yaml.YAMLError as e:
        raise HTTPException(status_code=400, detail=f"Invalid YAML format: {e}") from e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing file: {e}",
        ) from e


@app.post("/api/manual-material")
async def add_manual_material(request: ManualMaterialRequest):
    """Add a manually defined material"""
    session_id = "default"  # In production, get from session

    if session_id not in custom_materials:
        custom_materials[session_id] = {}

    # Add the material
    custom_materials[session_id][request.name] = {
        "yield_strength": request.yield_strength,
        "sigma_u": request.sigma_u,
        "elastic_mod": request.elastic_mod,
        "eps_u": request.eps_u,
        "description": request.description or f"Manual material: {request.name}",
    }

    return {
        "message": "Material added successfully",
        "material": custom_materials[session_id][request.name],
    }


@app.get("/api/materials")
async def get_materials():
    """Get available materials (including custom ones)"""
    base_materials = load_materials()
    session_id = "default"  # In production, get from session

    # Combine base materials with custom materials
    all_materials = base_materials["materials"].copy()
    if session_id in custom_materials:
        all_materials.update(custom_materials[session_id])

    return {"materials": all_materials}


@app.delete("/api/materials/{material_name}")
async def delete_custom_material(material_name: str):
    """Delete a custom material"""
    session_id = "default"  # In production, get from session

    if session_id not in custom_materials:
        raise HTTPException(status_code=404, detail="No custom materials found")

    if material_name not in custom_materials[session_id]:
        raise HTTPException(status_code=404, detail="Material not found")

    del custom_materials[session_id][material_name]

    return {"message": f"Material '{material_name}' deleted successfully"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
