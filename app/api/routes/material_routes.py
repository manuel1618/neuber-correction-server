"""
Material routes
"""

import time

import yaml
from fastapi import FastAPI, HTTPException, Request, UploadFile

from app.models.models import ManualMaterialRequest, load_materials
from app.utils.session import (
    check_rate_limit,
    get_user_materials,
    log_usage,
    save_user_materials,
    update_session_activity,
)


def mk_material_routes(
    app: FastAPI,
):
    """Add material routes to the FastAPI app"""

    @app.post("/api/upload-materials")
    async def upload_materials(request: Request, file: UploadFile):
        """Upload custom materials.yaml file"""
        start_time = time.time()
        session_id = request.state.session_id
        ip_address = request.state.ip_address

        # Rate limiting: simplified generous limits
        if not check_rate_limit(request.app.state.db, f"upload:{ip_address}"):
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Please try again later.",
            )

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

            # Store in session-specific storage
            save_user_materials(session_id, materials_data["materials"])

            # Update session activity
            update_session_activity(request.app.state.db, session_id, ip_address)

            duration_ms = int((time.time() - start_time) * 1000)
            log_usage(
                request.app.state.db,
                session_id,
                "/api/upload-materials",
                duration_ms,
                True,
                ip_address,
            )

            return {
                "message": "Materials uploaded successfully",
                "materials": materials_data["materials"],
                "count": len(materials_data["materials"]),
            }

        except yaml.YAMLError as e:
            duration_ms = int((time.time() - start_time) * 1000)
            log_usage(
                request.app.state.db,
                session_id,
                "/api/upload-materials",
                duration_ms,
                False,
                ip_address,
                str(e),
            )
            raise HTTPException(
                status_code=400, detail=f"Invalid YAML format: {e}"
            ) from e
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            log_usage(
                request.app.state.db,
                session_id,
                "/api/upload-materials",
                duration_ms,
                False,
                ip_address,
                str(e),
            )
            raise HTTPException(
                status_code=500,
                detail=f"Error processing file: {e}",
            ) from e

    @app.post("/api/manual-material")
    async def add_manual_material(
        request: Request,
        material_request: ManualMaterialRequest,
    ):
        """Add a manually defined material"""
        start_time = time.time()
        session_id = request.state.session_id
        ip_address = request.state.ip_address

        # Rate limiting: simplified generous limits
        if not check_rate_limit(request.app.state.db, f"manual:{session_id}"):
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Please try again later.",
            )

        try:
            # Get current user materials
            user_materials = get_user_materials(session_id)

            # Add the material
            user_materials[material_request.name] = {
                "yield_strength": material_request.yield_strength,
                "sigma_u": material_request.sigma_u,
                "elastic_mod": material_request.elastic_mod,
                "eps_u": material_request.eps_u,
                "description": material_request.description
                or f"Manual material: {material_request.name}",
            }

            # Save updated materials
            save_user_materials(session_id, user_materials)

            # Update session activity
            update_session_activity(request.app.state.db, session_id, ip_address)

            duration_ms = int((time.time() - start_time) * 1000)
            log_usage(
                request.app.state.db,
                session_id,
                "/api/manual-material",
                duration_ms,
                True,
                ip_address,
            )

            return {
                "message": "Material added successfully",
                "material": {
                    "name": material_request.name,
                    **user_materials[material_request.name],
                },
            }
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            log_usage(
                request.app.state.db,
                session_id,
                "/api/manual-material",
                duration_ms,
                False,
                ip_address,
                str(e),
            )
            raise

    @app.get("/api/materials")
    async def get_materials(request: Request):
        """Get available materials (including custom ones)"""
        start_time = time.time()
        session_id = request.state.session_id
        ip_address = request.state.ip_address

        # Rate limiting: simplified generous limits
        allowed, rate_info = check_rate_limit(request.app.state.db, f"get:{session_id}")
        if not allowed:
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Please try again later.",
            )

        try:
            base_materials = load_materials()
            user_materials = get_user_materials(session_id)

            # Combine base materials with user materials
            all_materials = base_materials["materials"].copy()
            all_materials.update(user_materials)

            # Update session activity
            update_session_activity(request.app.state.db, session_id, ip_address)

            duration_ms = int((time.time() - start_time) * 1000)
            log_usage(
                request.app.state.db,
                session_id,
                "/api/materials",
                duration_ms,
                True,
                ip_address,
            )

            from fastapi.responses import JSONResponse

            response = JSONResponse(content={"materials": all_materials})

            # Set rate limiting headers
            response.headers["X-RateLimit-Limit"] = str(rate_info["limit"])
            response.headers["X-RateLimit-Remaining"] = str(rate_info["remaining"])
            response.headers["X-RateLimit-Reset"] = str(rate_info["reset"])

            return response
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            log_usage(
                request.app.state.db,
                session_id,
                "/api/materials",
                duration_ms,
                False,
                ip_address,
                str(e),
            )
            raise

    @app.get("/api/materials/{material_name}")
    async def get_specific_material(request: Request, material_name: str):
        """Get a specific material by name"""
        start_time = time.time()
        session_id = request.state.session_id
        ip_address = request.state.ip_address

        # Rate limiting: simplified generous limits
        if not check_rate_limit(request.app.state.db, f"get_specific:{session_id}"):
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Please try again later.",
            )

        try:
            base_materials = load_materials()
            user_materials = get_user_materials(session_id)

            # Combine base materials with user materials
            all_materials = base_materials["materials"].copy()
            all_materials.update(user_materials)

            if material_name not in all_materials:
                raise HTTPException(status_code=404, detail="Material not found")

            material_data = all_materials[material_name]

            # Update session activity
            update_session_activity(request.app.state.db, session_id, ip_address)

            duration_ms = int((time.time() - start_time) * 1000)
            log_usage(
                request.app.state.db,
                session_id,
                f"/api/materials/{material_name}",
                duration_ms,
                True,
                ip_address,
            )

            return {"material": {"name": material_name, **material_data}}
        except HTTPException:
            raise
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            log_usage(
                request.app.state.db,
                session_id,
                f"/api/materials/{material_name}",
                duration_ms,
                False,
                ip_address,
                str(e),
            )
            raise

    @app.delete("/api/materials/{material_name}")
    async def delete_custom_material(request: Request, material_name: str):
        """Delete a custom material"""
        start_time = time.time()
        session_id = request.state.session_id
        ip_address = request.state.ip_address

        # Rate limiting: simplified generous limits
        if not check_rate_limit(request.app.state.db, f"delete:{session_id}"):
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Please try again later.",
            )

        try:
            user_materials = get_user_materials(session_id)

            if material_name not in user_materials:
                raise HTTPException(status_code=404, detail="Material not found")

            # Remove the material
            del user_materials[material_name]
            save_user_materials(session_id, user_materials)

            # Update session activity
            update_session_activity(request.app.state.db, session_id, ip_address)

            duration_ms = int((time.time() - start_time) * 1000)
            log_usage(
                request.app.state.db,
                session_id,
                f"/api/materials/{material_name}",
                duration_ms,
                True,
                ip_address,
            )

            return {"message": f"Material '{material_name}' deleted successfully"}
        except HTTPException:
            raise
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            log_usage(
                request.app.state.db,
                session_id,
                f"/api/materials/{material_name}",
                duration_ms,
                False,
                ip_address,
                str(e),
            )
            raise
