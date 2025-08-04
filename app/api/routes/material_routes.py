"""
Material routes
"""

import yaml
from fastapi import FastAPI, File, HTTPException, UploadFile

from app.models.models import ManualMaterialRequest, load_materials


def mk_material_routes(
    app: FastAPI,
    custom_materials: dict,
):
    """Add material routes to the FastAPI app"""

    @app.post("/api/upload-materials")
    async def upload_materials(file: UploadFile = File(...)):
        """Upload custom materials.yaml file"""
        if not file.filename.endswith(".yaml") and not file.filename.endswith(".yml"):
            raise HTTPException(status_code=400, detail="File must be a YAML file")

        try:
            content = await file.read()
            materials_data = yaml.safe_load(content.decode("utf-8"))

            # Validate the structure
            if (
                not isinstance(materials_data, dict)
                or "materials" not in materials_data
            ):
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
                    missing_props = [
                        prop for prop in required_props if prop not in props
                    ]
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
                    required_props = [
                        "yield_strength",
                        "sigma_u",
                        "elastic_mod",
                        "eps_u",
                    ]
                    missing_props = [
                        prop for prop in required_props if prop not in props
                    ]
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
            raise HTTPException(
                status_code=400, detail=f"Invalid YAML format: {e}"
            ) from e
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
