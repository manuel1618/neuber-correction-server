"""
Pydantic models
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from pydantic import BaseModel, Field, field_validator

# Constants
MATERIALS_FILE = Path("materials/materials.yaml")


class CorrectionRequest(BaseModel):
    """
    Class for correction request
    """

    material_name: str = Field(..., min_length=1, description="Material name")
    stress_values: List[float] = Field(
        ..., min_items=1, description="List of stress values"
    )
    custom_material: Optional[Dict[str, Any]] = None

    @field_validator("stress_values")
    @classmethod
    def validate_stress_values(cls, v):
        """Validate that stress values are numeric and positive"""
        if not all(isinstance(x, (int, float)) for x in v):
            raise ValueError("All stress values must be numeric")
        if not all(x > 0 for x in v):
            raise ValueError("All stress values must be positive")
        return v

    @field_validator("material_name")
    @classmethod
    def validate_material_name(cls, v):
        """Validate that material name is not empty"""
        if not v or not v.strip():
            raise ValueError("Material name cannot be empty")
        return v.strip()


class CorrectionResponse(BaseModel):
    """
    Class for correction response
    """

    original_stresses: List[float] = Field(..., description="Original stress values")
    corrected_stresses: List[float] = Field(..., description="Corrected stress values")
    material_properties: dict = Field(..., description="Material properties")
    plot_data: Optional[str] = None

    @field_validator("corrected_stresses")
    @classmethod
    def validate_array_lengths(cls, v, info):
        """Validate that original and corrected stress arrays have the same length"""
        if (
            info.data
            and "original_stresses" in info.data
            and len(v) != len(info.data["original_stresses"])
        ):
            raise ValueError(
                "Original and corrected stress arrays must have the same length"
            )
        return v


class ManualMaterialRequest(BaseModel):
    """
    Class for manual material request
    """

    name: str = Field(..., min_length=1, description="Material name")
    yield_strength: float = Field(..., gt=0, description="Yield strength")
    sigma_u: float = Field(..., gt=0, description="Ultimate tensile strength")
    elastic_mod: float = Field(..., gt=0, description="Elastic modulus")
    eps_u: float = Field(..., gt=0, description="Ultimate strain")
    ramberg_osgood_n: Optional[float] = Field(
        None, gt=0, description="Ramberg-Osgood hardening exponent"
    )
    description: Optional[str] = None

    @field_validator(
        "yield_strength", "sigma_u", "elastic_mod", "eps_u", "ramberg_osgood_n"
    )
    @classmethod
    def validate_positive_values(cls, v):
        """Validate that all material properties are positive"""
        if v is not None and v <= 0:
            raise ValueError("Material properties must be positive")
        return v

    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        """Validate that material name is not empty"""
        if not v or not v.strip():
            raise ValueError("Material name cannot be empty")
        return v.strip()


def load_materials():
    """Load materials from YAML file"""
    materials_file = (
        Path(MATERIALS_FILE) if isinstance(MATERIALS_FILE, str) else MATERIALS_FILE
    )

    # Try to load from the specified file
    try:
        if materials_file.exists():
            with open(materials_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                # Convert new format to old format for compatibility
                if "materials" in data and isinstance(data["materials"], list):
                    materials_dict = {}
                    valid_materials = 0
                    total_materials = len(data["materials"])

                    for material in data["materials"]:
                        if "id" in material and "properties" in material:
                            materials_dict[material["id"]] = {
                                "yield_strength": material["properties"].get("fty", 0),
                                "sigma_u": material["properties"].get("ftu", 0),
                                "elastic_mod": material["properties"].get("E", 0),
                                "eps_u": material["properties"].get("epsilon_u", 0),
                                "ramberg_osgood_n": material["properties"].get(
                                    "ramberg_osgood_n"
                                )
                                or material["properties"].get(
                                    "ramber_osgood_n"
                                ),  # Handle typo in YAML
                                "ramberg_osgood_n_source": material["properties"].get(
                                    "ramberg_osgood_n_source"
                                ),
                                "description": material.get("name", material["id"]),
                            }
                            valid_materials += 1

                    # If we have materials but none are valid, fall back to defaults
                    if total_materials > 0 and valid_materials == 0:
                        # File has materials but they're invalid, fall back to defaults
                        pass
                    else:
                        # Return the materials dict (even if empty for valid empty files)
                        return {"materials": materials_dict}
    except (yaml.YAMLError, OSError, IOError):
        # Fall back to default materials on any error
        pass

    # If the specified file failed or had invalid materials, try to load from the default materials file
    default_materials_file = Path("materials/materials.yaml")
    if default_materials_file.exists() and default_materials_file != materials_file:
        try:
            with open(default_materials_file, "r", encoding="utf-8") as f:
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
                                "ramberg_osgood_n": material["properties"].get(
                                    "ramberg_osgood_n"
                                )
                                or material["properties"].get(
                                    "ramber_osgood_n"
                                ),  # Handle typo in YAML
                                "ramberg_osgood_n_source": material["properties"].get(
                                    "ramberg_osgood_n_source"
                                ),
                                "description": material.get("name", material["id"]),
                            }
                    return {"materials": materials_dict}
                return data
        except (yaml.YAMLError, OSError, IOError):
            pass

    return {"materials": {}}
