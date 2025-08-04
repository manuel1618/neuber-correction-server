"""
Pydantic models
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from pydantic import BaseModel


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
