"""
Material routes
"""

import base64
import io
import json
from typing import Optional

import matplotlib.pyplot as plt
from fastapi import FastAPI, Form, HTTPException
from neuber_correction import (
    MaterialForNeuberCorrection,
    NeuberCorrection,
    NeuberSolverSettings,
)

from app.models.models import CorrectionRequest, CorrectionResponse, load_materials


def mk_neuber_routes(app: FastAPI):
    """Add material routes to the FastAPI app"""

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
