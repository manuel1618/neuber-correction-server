"""
Neuber calculation routes
"""

import base64
import io
import json
import time
from typing import Optional

import matplotlib.pyplot as plt
from fastapi import FastAPI, Form, HTTPException, Request
from neuber_correction import (
    MaterialForNeuberCorrection,
    NeuberCorrection,
    NeuberSolverSettings,
)

from app.models.models import CorrectionRequest, CorrectionResponse, load_materials
from app.utils.session import (
    check_rate_limit,
    get_user_materials,
    log_usage,
    update_session_activity,
)


def mk_neuber_routes(app: FastAPI):
    """Add neuber calculation routes to the FastAPI app"""

    @app.post("/api/correct")
    async def correct_stresses(
        request: Request,
        correction_request: CorrectionRequest,
    ):
        """API endpoint for stress correction"""
        start_time = time.time()
        session_id = request.state.session_id
        ip_address = request.state.ip_address

        # Rate limiting: simplified generous limits
        if not check_rate_limit(request.app.state.db, f"calculate:{session_id}"):
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Please try again later.",
            )

        try:
            materials = load_materials()

            # Check if using custom material
            if correction_request.custom_material:
                material_props = correction_request.custom_material
            else:
                # Get user materials
                user_materials = get_user_materials(session_id)
                all_materials = materials["materials"].copy()
                all_materials.update(user_materials)

                if correction_request.material_name not in all_materials:
                    raise HTTPException(status_code=404, detail="Material not found")
                material_props = all_materials[correction_request.material_name]

            # Create material with optional hardening exponent
            material_kwargs = {
                "yield_strength": material_props["yield_strength"],
                "sigma_u": material_props["sigma_u"],
                "elastic_mod": material_props["elastic_mod"],
                "eps_u": material_props["eps_u"],
            }

            # Add hardening exponent if available
            if (
                "ramberg_osgood_n" in material_props
                and material_props["ramberg_osgood_n"] is not None
            ):
                material_kwargs["hardening_exponent"] = material_props[
                    "ramberg_osgood_n"
                ]

            material = MaterialForNeuberCorrection(**material_kwargs)

            neuber_settings = NeuberSolverSettings(
                tolerance=1e-6,
                max_iterations=10000,
                memoization_precision=1e-6,
            )

            neuber = NeuberCorrection(material=material, settings=neuber_settings)

            corrected_stresses = neuber.correct_stress_values(
                correction_request.stress_values
            )

            # Update session activity
            update_session_activity(request.app.state.db, session_id, ip_address)

            duration_ms = int((time.time() - start_time) * 1000)
            log_usage(
                request.app.state.db,
                session_id,
                "/api/correct",
                duration_ms,
                True,
                ip_address,
            )

            return CorrectionResponse(
                original_stresses=correction_request.stress_values,
                corrected_stresses=corrected_stresses,
                material_properties={
                    "yield_strength": material.yield_strength,
                    "sigma_u": material.sigma_u,
                    "elastic_mod": material.elastic_mod,
                    "eps_u": material.eps_u,
                },
            )
        except HTTPException:
            raise
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            log_usage(
                request.app.state.db,
                session_id,
                "/api/correct",
                duration_ms,
                False,
                ip_address,
                str(e),
            )
            raise HTTPException(
                status_code=500, detail=f"Calculation error: {str(e)}"
            ) from e

    @app.post("/api/plot")
    async def generate_plot(
        request: Request,
        material_name: str = Form(...),
        stress_value: float = Form(...),
        custom_material: Optional[str] = Form(None),
        custom_title: Optional[str] = Form(None),
    ):
        """Generate and return Neuber diagram plot"""
        start_time = time.time()
        session_id = request.state.session_id
        ip_address = request.state.ip_address

        # Rate limiting: simplified generous limits
        if not check_rate_limit(request.app.state.db, f"plot:{session_id}"):
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Please try again later.",
            )

        try:
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
                # Get user materials
                user_materials = get_user_materials(session_id)
                all_materials = materials["materials"].copy()
                all_materials.update(user_materials)

                # Check if material exists in materials dictionary
                if material_name not in all_materials:
                    raise HTTPException(
                        status_code=404, detail=f"Material '{material_name}' not found"
                    )
                material_props = all_materials[material_name]

            # Validate material properties
            if not material_props:
                raise HTTPException(
                    status_code=400, detail="Invalid material properties"
                )

            required_props = ["yield_strength", "sigma_u", "elastic_mod", "eps_u"]
            missing_props = [
                prop for prop in required_props if prop not in material_props
            ]
            if missing_props:
                raise HTTPException(
                    status_code=400,
                    detail=f"Material missing required properties: {missing_props}",
                )

            # Create material with optional hardening exponent
            material_kwargs = {
                "yield_strength": material_props["yield_strength"],
                "sigma_u": material_props["sigma_u"],
                "elastic_mod": material_props["elastic_mod"],
                "eps_u": material_props["eps_u"],
            }

            # Add hardening exponent if available
            if (
                "ramberg_osgood_n" in material_props
                and material_props["ramberg_osgood_n"] is not None
            ):
                material_kwargs["hardening_exponent"] = material_props[
                    "ramberg_osgood_n"
                ]

            material = MaterialForNeuberCorrection(**material_kwargs)

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
                plot_pretty_name=custom_title or f"{material_name} Neuber Diagram",
            )

            # Convert plot to base64 string
            img_buffer = io.BytesIO()
            fig.savefig(img_buffer, format="png", dpi=300, bbox_inches="tight")
            img_buffer.seek(0)
            img_str = base64.b64encode(img_buffer.getvalue()).decode()

            plt.close(fig)

            # Update session activity
            update_session_activity(request.app.state.db, session_id, ip_address)

            duration_ms = int((time.time() - start_time) * 1000)
            log_usage(
                request.app.state.db,
                session_id,
                "/api/plot",
                duration_ms,
                True,
                ip_address,
            )

            return {"plot_data": f"data:image/png;base64,{img_str}"}
        except HTTPException:
            raise
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            log_usage(
                request.app.state.db,
                session_id,
                "/api/plot",
                duration_ms,
                False,
                ip_address,
                str(e),
            )
            raise HTTPException(
                status_code=500, detail=f"Plot generation error: {str(e)}"
            ) from e
