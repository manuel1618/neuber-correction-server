"""
Tests for hardening exponent (ramberg_osgood_n) functionality
"""

import json
import os
import tempfile
from unittest.mock import patch

import pytest
import yaml
from fastapi.testclient import TestClient

from app.main import app
from app.models.models import ManualMaterialRequest, load_materials


class TestHardeningExponentModels:
    """Test hardening exponent functionality in models"""

    def test_manual_material_request_with_hardening_exponent(self):
        """Test ManualMaterialRequest with hardening exponent"""
        request = ManualMaterialRequest(
            name="test_steel",
            yield_strength=350.0,
            sigma_u=500.0,
            elastic_mod=210000.0,
            eps_u=0.15,
            ramberg_osgood_n=18.5,
            description="Test steel with hardening exponent",
        )

        assert request.name == "test_steel"
        assert request.ramberg_osgood_n == 18.5
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

    def test_manual_material_request_zero_hardening_exponent(self):
        """Test ManualMaterialRequest with zero hardening exponent"""
        with pytest.raises(ValueError):
            ManualMaterialRequest(
                name="test_steel",
                yield_strength=350.0,
                sigma_u=500.0,
                elastic_mod=210000.0,
                eps_u=0.15,
                ramberg_osgood_n=0.0,  # Zero value
            )

    def test_manual_material_request_serialization(self):
        """Test ManualMaterialRequest serialization with hardening exponent"""
        request = ManualMaterialRequest(
            name="test_steel",
            yield_strength=350.0,
            sigma_u=500.0,
            elastic_mod=210000.0,
            eps_u=0.15,
            ramberg_osgood_n=18.5,
        )

        # Should be serializable
        json_data = request.model_dump()
        assert "ramberg_osgood_n" in json_data
        assert json_data["ramberg_osgood_n"] == 18.5

    def test_manual_material_request_deserialization(self):
        """Test ManualMaterialRequest deserialization with hardening exponent"""
        json_data = {
            "name": "test_steel",
            "yield_strength": 350.0,
            "sigma_u": 500.0,
            "elastic_mod": 210000.0,
            "eps_u": 0.15,
            "ramberg_osgood_n": 18.5,
        }

        request = ManualMaterialRequest.model_validate(json_data)
        assert request.name == "test_steel"
        assert request.ramberg_osgood_n == 18.5


class TestHardeningExponentMaterialLoading:
    """Test hardening exponent in material loading"""

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

    def test_load_materials_without_hardening_exponent(self):
        """Test loading materials without hardening exponent"""
        test_materials = {
            "materials": [
                {
                    "id": "test_steel_no_n",
                    "name": "Test Steel without Hardening Exponent",
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
                assert "test_steel_no_n" in materials_dict
                material_props = materials_dict["test_steel_no_n"]
                assert material_props["yield_strength"] == 350
                assert material_props["ramberg_osgood_n"] is None
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


class TestHardeningExponentAPI:
    """Test hardening exponent functionality in API routes"""

    def test_add_manual_material_with_hardening_exponent(self):
        """Test adding manual material with hardening exponent"""
        material_data = {
            "name": "test_steel_with_n",
            "yield_strength": 350.0,
            "sigma_u": 500.0,
            "elastic_mod": 210000.0,
            "eps_u": 0.15,
            "ramberg_osgood_n": 18.5,
            "description": "Test steel with hardening exponent",
        }

        with TestClient(app) as client:
            response = client.post("/api/manual-material", json=material_data)

            assert response.status_code == 200
            data = response.json()
            assert data["message"] == "Material added successfully"
            assert data["material"]["name"] == "test_steel_with_n"
            assert "ramberg_osgood_n" in data["material"]
            assert data["material"]["ramberg_osgood_n"] == 18.5

    def test_add_manual_material_optional_hardening_exponent(self):
        """Test adding manual material without hardening exponent"""
        material_data = {
            "name": "test_steel_no_n",
            "yield_strength": 350.0,
            "sigma_u": 500.0,
            "elastic_mod": 210000.0,
            "eps_u": 0.15,
            "description": "Test steel without hardening exponent",
        }

        with TestClient(app) as client:
            response = client.post("/api/manual-material", json=material_data)

            assert response.status_code == 200
            data = response.json()
            assert data["message"] == "Material added successfully"
            assert data["material"]["name"] == "test_steel_no_n"
            # Should not have ramberg_osgood_n field when not provided
            assert "ramberg_osgood_n" not in data["material"]

    def test_add_manual_material_invalid_hardening_exponent(self):
        """Test adding manual material with invalid hardening exponent"""
        material_data = {
            "name": "test_steel_invalid_n",
            "yield_strength": 350.0,
            "sigma_u": 500.0,
            "elastic_mod": 210000.0,
            "eps_u": 0.15,
            "ramberg_osgood_n": -5.0,  # Invalid negative value
            "description": "Test steel with invalid hardening exponent",
        }

        with TestClient(app) as client:
            response = client.post("/api/manual-material", json=material_data)

            assert response.status_code == 422  # Validation error

    def test_correct_stresses_with_hardening_exponent(self):
        """Test stress correction with hardening exponent"""
        custom_material = {
            "yield_strength": 350.0,
            "sigma_u": 500.0,
            "elastic_mod": 210000.0,
            "eps_u": 0.15,
            "ramberg_osgood_n": 18.5,
        }

        correction_data = {
            "material_name": "custom_test_material_with_n",
            "stress_values": [400.0, 500.0],
            "custom_material": custom_material,
        }

        with TestClient(app) as client:
            response = client.post("/api/correct", json=correction_data)
            assert response.status_code == 200
            data = response.json()

            assert "original_stresses" in data
            assert "corrected_stresses" in data
            assert "material_properties" in data
            assert len(data["original_stresses"]) == 2

    def test_correct_stresses_with_uploaded_material_hardening_exponent(self):
        """Test stress correction with uploaded material containing hardening exponent"""
        # First upload a material with hardening exponent
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
                        "ramberg_osgood_n": 20.0,
                    },
                }
            ]
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as tmp:
            yaml.dump(test_materials, tmp)
            tmp_path = tmp.name

        try:
            with TestClient(app) as client:
                # Upload material
                with open(tmp_path, "rb") as f:
                    response = client.post(
                        "/api/upload-materials",
                        files={
                            "file": ("test_materials.yaml", f, "application/x-yaml")
                        },
                    )
                assert response.status_code == 200

                # Test correction with uploaded material
                correction_data = {
                    "material_name": "test_steel_with_n",
                    "stress_values": [400.0, 500.0],
                }

                response = client.post("/api/correct", json=correction_data)
                assert response.status_code == 200
                data = response.json()

                assert "original_stresses" in data
                assert "corrected_stresses" in data
                assert "material_properties" in data
                assert len(data["original_stresses"]) == 2
        finally:
            os.unlink(tmp_path)

    def test_generate_plot_with_hardening_exponent(self):
        """Test plot generation with hardening exponent"""
        custom_material = {
            "yield_strength": 350.0,
            "sigma_u": 500.0,
            "elastic_mod": 210000.0,
            "eps_u": 0.15,
            "ramberg_osgood_n": 18.5,
        }

        plot_data = {
            "material_name": "custom_test_material_with_n",
            "stress_value": "400.0",
            "custom_material": json.dumps(custom_material),
        }

        with TestClient(app) as client:
            response = client.post("/api/plot", data=plot_data)
            assert response.status_code == 200
            data = response.json()

            assert "plot_data" in data
            assert data["plot_data"].startswith("data:image/png;base64,")

    def test_upload_materials_with_hardening_exponent(self):
        """Test uploading materials with hardening exponent"""
        test_materials = {
            "materials": [
                {
                    "id": "uploaded_steel_with_n",
                    "name": "Uploaded Steel with Hardening Exponent",
                    "properties": {
                        "fty": 350,
                        "ftu": 500,
                        "E": 210000,
                        "epsilon_u": 0.15,
                        "ramberg_osgood_n": 22.0,
                    },
                }
            ]
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as tmp:
            yaml.dump(test_materials, tmp)
            tmp_path = tmp.name

        try:
            with TestClient(app) as client:
                with open(tmp_path, "rb") as f:
                    response = client.post(
                        "/api/upload-materials",
                        files={
                            "file": ("test_materials.yaml", f, "application/x-yaml")
                        },
                    )

                assert response.status_code == 200
                data = response.json()
                assert "materials" in data
                assert "uploaded_steel_with_n" in data["materials"]
                assert data["count"] == 1
        finally:
            os.unlink(tmp_path)


class TestHardeningExponentIntegration:
    """Integration tests for hardening exponent functionality"""

    def test_full_workflow_with_hardening_exponent(self):
        """Test complete workflow with hardening exponent"""
        with TestClient(app) as client:
            # 1. Add manual material with hardening exponent
            material_data = {
                "name": "workflow_steel_with_n",
                "yield_strength": 350.0,
                "sigma_u": 500.0,
                "elastic_mod": 210000.0,
                "eps_u": 0.15,
                "ramberg_osgood_n": 18.5,
                "description": "Workflow test steel with hardening exponent",
            }

            response = client.post("/api/manual-material", json=material_data)
            assert response.status_code == 200

            # 2. Get materials to verify
            response = client.get("/api/materials")
            assert response.status_code == 200
            materials = response.json()["materials"]
            assert "workflow_steel_with_n" in materials
            assert materials["workflow_steel_with_n"]["ramberg_osgood_n"] == 18.5

            # 3. Perform correction
            correction_data = {
                "material_name": "workflow_steel_with_n",
                "stress_values": [400.0, 500.0],
            }
            response = client.post("/api/correct", json=correction_data)
            assert response.status_code == 200

            # 4. Generate plot
            plot_data = {
                "material_name": "workflow_steel_with_n",
                "stress_value": "400.0",
            }
            response = client.post("/api/plot", data=plot_data)
            assert response.status_code == 200

    def test_backward_compatibility_without_hardening_exponent(self):
        """Test backward compatibility without hardening exponent"""
        with TestClient(app) as client:
            # 1. Add manual material without hardening exponent
            material_data = {
                "name": "workflow_steel_no_n",
                "yield_strength": 350.0,
                "sigma_u": 500.0,
                "elastic_mod": 210000.0,
                "eps_u": 0.15,
                "description": "Workflow test steel without hardening exponent",
            }

            response = client.post("/api/manual-material", json=material_data)
            assert response.status_code == 200

            # 2. Get materials to verify
            response = client.get("/api/materials")
            assert response.status_code == 200
            materials = response.json()["materials"]
            assert "workflow_steel_no_n" in materials
            # Should not have ramberg_osgood_n field
            assert "ramberg_osgood_n" not in materials["workflow_steel_no_n"]

            # 3. Perform correction (should work without hardening exponent)
            correction_data = {
                "material_name": "workflow_steel_no_n",
                "stress_values": [400.0, 500.0],
            }
            response = client.post("/api/correct", json=correction_data)
            assert response.status_code == 200

            # 4. Generate plot (should work without hardening exponent)
            plot_data = {
                "material_name": "workflow_steel_no_n",
                "stress_value": "400.0",
            }
            response = client.post("/api/plot", data=plot_data)
            assert response.status_code == 200
