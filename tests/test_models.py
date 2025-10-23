"""
Tests for Pydantic models and material loading
"""

import os
import tempfile
from unittest.mock import patch

import pytest
import yaml

from app.models.models import (
    CorrectionRequest,
    CorrectionResponse,
    ManualMaterialRequest,
    load_materials,
)


class TestPydanticModels:
    """Test Pydantic model validation and behavior"""

    def test_correction_request_valid(self):
        """Test valid CorrectionRequest creation"""
        request = CorrectionRequest(
            material_name="test_material", stress_values=[400.0, 500.0, 600.0]
        )

        assert request.material_name == "test_material"
        assert request.stress_values == [400.0, 500.0, 600.0]
        assert request.custom_material is None

    def test_correction_request_with_custom_material(self):
        """Test CorrectionRequest with custom material"""
        custom_material = {
            "yield_strength": 350.0,
            "sigma_u": 500.0,
            "elastic_mod": 210000.0,
            "eps_u": 0.15,
        }

        request = CorrectionRequest(
            material_name="custom_material",
            stress_values=[400.0, 500.0],
            custom_material=custom_material,
        )

        assert request.material_name == "custom_material"
        assert request.stress_values == [400.0, 500.0]
        assert request.custom_material == custom_material

    def test_correction_request_invalid_stress_values(self):
        """Test CorrectionRequest with invalid stress values"""
        with pytest.raises(ValueError):
            CorrectionRequest(
                material_name="test_material", stress_values=["invalid", "values"]
            )

    def test_correction_request_empty_stress_values(self):
        """Test CorrectionRequest with empty stress values"""
        with pytest.raises(ValueError):
            CorrectionRequest(material_name="test_material", stress_values=[])

    def test_correction_request_missing_material_name(self):
        """Test CorrectionRequest with missing material name"""
        with pytest.raises(ValueError):
            CorrectionRequest(material_name="", stress_values=[400.0, 500.0])

    def test_correction_response_valid(self):
        """Test valid CorrectionResponse creation"""
        response = CorrectionResponse(
            original_stresses=[400.0, 500.0],
            corrected_stresses=[380.0, 470.0],
            material_properties={
                "fty": 350.0,
                "ftu": 500.0,
                "E": 210000.0,
                "epsilon_u": 0.15,
            },
        )

        assert response.original_stresses == [400.0, 500.0]
        assert response.corrected_stresses == [380.0, 470.0]
        assert response.material_properties["fty"] == 350.0

    def test_correction_response_length_mismatch(self):
        """Test CorrectionResponse with mismatched array lengths"""
        with pytest.raises(ValueError):
            CorrectionResponse(
                original_stresses=[400.0, 500.0],
                corrected_stresses=[380.0],  # Different length
                material_properties={
                    "fty": 350.0,
                    "ftu": 500.0,
                    "E": 210000.0,
                    "epsilon_u": 0.15,
                },
            )

    def test_manual_material_request_valid(self):
        """Test valid ManualMaterialRequest creation"""
        request = ManualMaterialRequest(
            name="test_steel",
            yield_strength=350.0,
            sigma_u=500.0,
            elastic_mod=210000.0,
            eps_u=0.15,
            description="Test steel material",
        )

        assert request.name == "test_steel"
        assert request.yield_strength == 350.0
        assert request.sigma_u == 500.0
        assert request.elastic_mod == 210000.0
        assert request.eps_u == 0.15
        assert request.description == "Test steel material"

    def test_manual_material_request_optional_description(self):
        """Test ManualMaterialRequest without description"""
        request = ManualMaterialRequest(
            name="test_steel",
            yield_strength=350.0,
            sigma_u=500.0,
            elastic_mod=210000.0,
            eps_u=0.15,
        )

        assert request.name == "test_steel"
        assert request.description is None

    def test_manual_material_request_with_hardening_exponent(self):
        """Test ManualMaterialRequest with hardening exponent"""
        request = ManualMaterialRequest(
            name="test_steel",
            yield_strength=350.0,
            sigma_u=500.0,
            elastic_mod=210000.0,
            eps_u=0.15,
            ramberg_osgood_n=15.5,
            description="Test steel with hardening exponent",
        )

        assert request.name == "test_steel"
        assert request.ramberg_osgood_n == 15.5
        assert request.description == "Test steel with hardening exponent"

    def test_manual_material_request_optional_hardening_exponent(self):
        """Test ManualMaterialRequest without hardening exponent"""
        request = ManualMaterialRequest(
            name="test_steel",
            yield_strength=350.0,
            sigma_u=500.0,
            elastic_mod=210000.0,
            eps_u=0.15,
        )

        assert request.name == "test_steel"
        assert request.ramberg_osgood_n is None

    def test_manual_material_request_invalid_hardening_exponent(self):
        """Test ManualMaterialRequest with invalid hardening exponent"""
        with pytest.raises(ValueError):
            ManualMaterialRequest(
                name="test_steel",
                yield_strength=350.0,
                sigma_u=500.0,
                elastic_mod=210000.0,
                eps_u=0.15,
                ramberg_osgood_n=-5.0,  # Negative value
            )

    def test_manual_material_request_invalid_values(self):
        """Test ManualMaterialRequest with invalid values"""
        with pytest.raises(ValueError):
            ManualMaterialRequest(
                name="test_steel",
                yield_strength=-350.0,  # Negative value
                sigma_u=500.0,
                elastic_mod=210000.0,
                eps_u=0.15,
            )


class TestMaterialLoading:
    """Test material loading functionality"""

    def test_load_materials_default(self):
        """Test loading default materials"""
        materials = load_materials()

        assert "materials" in materials
        materials_dict = materials["materials"]
        assert len(materials_dict) > 0

        # Check that materials have required properties
        for _, props in materials_dict.items():
            assert "yield_strength" in props
            assert "sigma_u" in props
            assert "elastic_mod" in props
            assert "eps_u" in props
            assert "description" in props

    def test_load_materials_from_file(self):
        """Test loading materials from a custom file"""
        test_materials = {
            "materials": [
                {
                    "id": "test_steel",
                    "name": "Test Steel",
                    "properties": {
                        "fty": 350,
                        "ftu": 500,
                        "E": 210000,
                        "epsilon_u": 0.15,
                    },
                }
            ]
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as tmp:
            yaml.dump(test_materials, tmp)
            tmp_path = tmp.name

        try:
            with patch("app.models.models.MATERIALS_FILE", tmp_path):
                materials = load_materials()

                assert "materials" in materials
                materials_dict = materials["materials"]
                assert "test_steel" in materials_dict
                assert materials_dict["test_steel"]["yield_strength"] == 350
        finally:
            os.unlink(tmp_path)

    def test_load_materials_with_hardening_exponent(self):
        """Test loading materials with hardening exponent"""
        test_materials = {
            "materials": [
                {
                    "id": "test_steel_with_n",
                    "name": "Test Steel with Hardening Exponent",
                    "properties": {
                        "fty": 350,
                        "ftu": 500,
                        "E": 210000,
                        "epsilon_u": 0.15,
                        "ramberg_osgood_n": 18.5,
                    },
                }
            ]
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as tmp:
            yaml.dump(test_materials, tmp)
            tmp_path = tmp.name

        try:
            with patch("app.models.models.MATERIALS_FILE", tmp_path):
                materials = load_materials()

                assert "materials" in materials
                materials_dict = materials["materials"]
                assert "test_steel_with_n" in materials_dict
                material_props = materials_dict["test_steel_with_n"]
                assert material_props["yield_strength"] == 350
                assert material_props["ramberg_osgood_n"] == 18.5
        finally:
            os.unlink(tmp_path)

    def test_load_materials_with_typo_hardening_exponent(self):
        """Test loading materials with typo in hardening exponent field name"""
        test_materials = {
            "materials": [
                {
                    "id": "test_steel_typo",
                    "name": "Test Steel with Typo",
                    "properties": {
                        "fty": 350,
                        "ftu": 500,
                        "E": 210000,
                        "epsilon_u": 0.15,
                        "ramber_osgood_n": 20.0,  # Note the typo
                    },
                }
            ]
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as tmp:
            yaml.dump(test_materials, tmp)
            tmp_path = tmp.name

        try:
            with patch("app.models.models.MATERIALS_FILE", tmp_path):
                materials = load_materials()

                assert "materials" in materials
                materials_dict = materials["materials"]
                assert "test_steel_typo" in materials_dict
                material_props = materials_dict["test_steel_typo"]
                assert material_props["yield_strength"] == 350
                assert material_props["ramberg_osgood_n"] == 20.0  # Should handle typo
        finally:
            os.unlink(tmp_path)

    def test_load_materials_invalid_file(self):
        """Test loading materials from invalid file"""
        with patch("app.models.models.MATERIALS_FILE", "/nonexistent/file.yaml"):
            # Should fall back to default materials
            materials = load_materials()
            assert "materials" in materials
            assert len(materials["materials"]) > 0

    def test_load_materials_invalid_yaml(self):
        """Test loading materials from invalid YAML file"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as tmp:
            tmp.write("invalid: yaml: content: [")
            tmp_path = tmp.name

        try:
            with patch("app.models.models.MATERIALS_FILE", tmp_path):
                # Should fall back to default materials
                materials = load_materials()
                assert "materials" in materials
                assert len(materials["materials"]) > 0
        finally:
            os.unlink(tmp_path)

    def test_load_materials_missing_required_fields(self):
        """Test loading materials with missing required fields"""
        invalid_materials = {
            "materials": [
                {
                    "id": "test_steel",
                    "name": "Test Steel",
                    # Missing properties
                }
            ]
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as tmp:
            yaml.dump(invalid_materials, tmp)
            tmp_path = tmp.name

        try:
            with patch("app.models.models.MATERIALS_FILE", tmp_path):
                # Should fall back to default materials
                materials = load_materials()
                assert "materials" in materials
                assert len(materials["materials"]) > 0
        finally:
            os.unlink(tmp_path)

    def test_load_materials_empty_file(self):
        """Test loading materials from empty file"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as tmp:
            yaml.dump({"materials": []}, tmp)
            tmp_path = tmp.name

        try:
            with patch("app.models.models.MATERIALS_FILE", tmp_path):
                materials = load_materials()
                assert "materials" in materials
                assert len(materials["materials"]) == 0
        finally:
            os.unlink(tmp_path)


class TestModelValidation:
    """Test model validation edge cases"""

    def test_stress_values_validation(self):
        """Test stress values validation"""
        # Valid stress values
        request = CorrectionRequest(
            material_name="test", stress_values=[100.0, 200.0, 300.0]
        )
        assert len(request.stress_values) == 3

        # Invalid stress values (negative)
        with pytest.raises(ValueError):
            CorrectionRequest(
                material_name="test", stress_values=[100.0, -200.0, 300.0]
            )

    def test_custom_material_validation(self):
        """Test custom material validation in CorrectionRequest"""
        # Valid custom material
        custom_material = {
            "yield_strength": 350.0,
            "sigma_u": 500.0,
            "elastic_mod": 210000.0,
            "eps_u": 0.15,
        }

        request = CorrectionRequest(
            material_name="custom",
            stress_values=[400.0],
            custom_material=custom_material,
        )
        assert request.custom_material is not None

    def test_model_serialization(self):
        """Test model serialization to JSON"""
        request = CorrectionRequest(
            material_name="test_material", stress_values=[400.0, 500.0]
        )

        # Should be serializable
        json_data = request.json()
        assert "material_name" in json_data
        assert "stress_values" in json_data

    def test_model_deserialization(self):
        """Test model deserialization from JSON"""
        json_data = {"material_name": "test_material", "stress_values": [400.0, 500.0]}

        request = CorrectionRequest.parse_obj(json_data)
        assert request.material_name == "test_material"
        assert request.stress_values == [400.0, 500.0]


class TestModelIntegration:
    """Integration tests for models"""

    def test_full_correction_workflow(self):
        """Test a complete correction workflow with models"""
        # Create request
        request = CorrectionRequest(
            material_name="test_steel",
            stress_values=[400.0, 500.0, 600.0],
            custom_material={
                "yield_strength": 350.0,
                "sigma_u": 500.0,
                "elastic_mod": 210000.0,
                "eps_u": 0.15,
            },
        )

        # Create response
        response = CorrectionResponse(
            original_stresses=request.stress_values,
            corrected_stresses=[380.0, 470.0, 560.0],
            material_properties=request.custom_material,
        )

        # Validate
        assert len(response.original_stresses) == len(response.corrected_stresses)
        assert len(response.original_stresses) == len(request.stress_values)

        # Check that corrections are reasonable
        for orig, corr in zip(response.original_stresses, response.corrected_stresses):
            assert (
                corr <= orig
            )  # Corrected stress should be less than or equal to original

    def test_manual_material_workflow(self):
        """Test manual material creation workflow"""
        # Create manual material request
        material_request = ManualMaterialRequest(
            name="custom_steel",
            yield_strength=350.0,
            sigma_u=500.0,
            elastic_mod=210000.0,
            eps_u=0.15,
            description="Custom steel alloy",
        )

        # Use in correction request
        correction_request = CorrectionRequest(
            material_name=material_request.name,
            stress_values=[400.0, 500.0],
            custom_material={
                "yield_strength": material_request.yield_strength,
                "sigma_u": material_request.sigma_u,
                "elastic_mod": material_request.elastic_mod,
                "eps_u": material_request.eps_u,
            },
        )

        # Validate consistency
        assert correction_request.material_name == material_request.name
        assert (
            correction_request.custom_material["yield_strength"]
            == material_request.yield_strength
        )
