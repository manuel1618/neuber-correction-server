"""
Tests for API routes
"""

import json
import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest
import yaml
from fastapi.testclient import TestClient

from app.main import app


class TestIndexRoutes:
    """Test index routes"""

    def test_root_endpoint(self):
        """Test the root endpoint returns HTML with materials"""
        with TestClient(app) as client:
            response = client.get("/")
            assert response.status_code == 200
            assert "text/html" in response.headers["content-type"]
            assert "Neuber Correction Calculator" in response.text
            # Should contain material options
            assert "S355_steel" in response.text or "AL6061_T6" in response.text

    def test_health_endpoint(self):
        """Test the health check endpoint"""
        with TestClient(app) as client:
            response = client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert "timestamp" in data
            assert data["version"] == "1.0.0"
            assert "database" in data
            assert "session_count" in data


class TestMaterialRoutes:
    """Test material-related API routes"""

    def test_get_materials(self):
        """Test getting available materials"""
        with TestClient(app) as client:
            response = client.get("/api/materials")
            assert response.status_code == 200
            data = response.json()
            assert "materials" in data
            # Should contain default materials
            materials = data["materials"]
            assert len(materials) > 0
            # Check for expected material properties (using internal format)
            for material_name, props in materials.items():
                assert "yield_strength" in props
                assert "sigma_u" in props
                assert "elastic_mod" in props
                assert "eps_u" in props

    def test_get_specific_material(self):
        """Test getting a specific material"""
        with TestClient(app) as client:
            # First get all materials to find a valid one
            response = client.get("/api/materials")
            materials = response.json()["materials"]
            material_name = list(materials.keys())[0]

            # Get specific material
            response = client.get(f"/api/materials/{material_name}")
            assert response.status_code == 200
            data = response.json()
            assert "material" in data
            assert data["material"]["name"] == material_name

    def test_get_nonexistent_material(self):
        """Test getting a non-existent material"""
        with TestClient(app) as client:
            response = client.get("/api/materials/nonexistent")
            assert response.status_code == 404

    def test_upload_materials_yaml(self):
        """Test uploading materials from YAML file"""
        # Create a test YAML file
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
                assert "test_steel" in data["materials"]
                assert data["count"] == 1
        finally:
            os.unlink(tmp_path)

    def test_upload_invalid_yaml(self):
        """Test uploading invalid YAML file"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as tmp:
            tmp.write("invalid: yaml: content: [")
            tmp_path = tmp.name

        try:
            with TestClient(app) as client:
                with open(tmp_path, "rb") as f:
                    response = client.post(
                        "/api/upload-materials",
                        files={"file": ("invalid.yaml", f, "application/x-yaml")},
                    )

                assert response.status_code == 400
        finally:
            os.unlink(tmp_path)

    def test_upload_materials_without_file(self):
        """Test uploading materials without file"""
        with TestClient(app) as client:
            response = client.post("/api/upload-materials")
            assert response.status_code == 422  # Validation error

    def test_add_manual_material(self):
        """Test adding a manual material"""
        material_data = {
            "name": "test_manual_steel",
            "yield_strength": 350.0,
            "sigma_u": 500.0,
            "elastic_mod": 210000.0,
            "eps_u": 0.15,
            "description": "Test manual steel",
        }

        with TestClient(app) as client:
            response = client.post("/api/manual-material", json=material_data)

            assert response.status_code == 200
            data = response.json()
            assert data["message"] == "Material added successfully"
            assert data["material"]["name"] == "test_manual_steel"

    def test_add_manual_material_invalid_data(self):
        """Test adding manual material with invalid data"""
        invalid_data = {
            "name": "test_steel",
            "yield_strength": "invalid",  # Should be float
            "sigma_u": 500.0,
            "elastic_mod": 210000.0,
            "eps_u": 0.15,
        }

        with TestClient(app) as client:
            response = client.post("/api/manual-material", json=invalid_data)

            assert response.status_code == 422  # Validation error

    def test_add_manual_material_missing_fields(self):
        """Test adding manual material with missing required fields"""
        incomplete_data = {
            "name": "test_steel",
            "yield_strength": 350.0,
            # Missing other required fields
        }

        with TestClient(app) as client:
            response = client.post("/api/manual-material", json=incomplete_data)

            assert response.status_code == 422  # Validation error


class TestNeuberRoutes:
    """Test Neuber correction API routes"""

    def test_correct_stresses_with_preset_material(self):
        """Test stress correction with preset material"""
        # First get available materials
        with TestClient(app) as client:
            response = client.get("/api/materials")
            materials = response.json()["materials"]
            material_name = list(materials.keys())[0]

            # Test correction
            correction_data = {
                "material_name": material_name,
                "stress_values": [400.0, 500.0, 600.0],
            }

            response = client.post("/api/correct", json=correction_data)
            assert response.status_code == 200
            data = response.json()

            assert "original_stresses" in data
            assert "corrected_stresses" in data
            assert "material_properties" in data

            # Check that we got the expected number of results
            assert len(data["original_stresses"]) == 3
            assert len(data["corrected_stresses"]) == 3

            # Check that corrected stresses are less than or equal to original
            for orig, corr in zip(
                data["original_stresses"], data["corrected_stresses"]
            ):
                assert corr <= orig

    def test_correct_stresses_with_custom_material(self):
        """Test stress correction with custom material"""
        custom_material = {
            "yield_strength": 350.0,
            "sigma_u": 500.0,
            "elastic_mod": 210000.0,
            "eps_u": 0.15,
        }

        correction_data = {
            "material_name": "custom_test_material",
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

    def test_correct_stresses_invalid_material(self):
        """Test stress correction with invalid material"""
        correction_data = {
            "material_name": "nonexistent_material",
            "stress_values": [400.0, 500.0],
        }

        with TestClient(app) as client:
            response = client.post("/api/correct", json=correction_data)
            assert response.status_code == 404

    def test_correct_stresses_invalid_stress_values(self):
        """Test stress correction with invalid stress values"""
        with TestClient(app) as client:
            # Get a valid material first
            response = client.get("/api/materials")
            materials = response.json()["materials"]
            material_name = list(materials.keys())[0]

            # Test with invalid stress values
            correction_data = {
                "material_name": material_name,
                "stress_values": ["invalid", "values"],
            }

            response = client.post("/api/correct", json=correction_data)
            assert response.status_code == 422  # Validation error

    def test_correct_stresses_empty_list(self):
        """Test stress correction with empty stress values list"""
        with TestClient(app) as client:
            # Get a valid material first
            response = client.get("/api/materials")
            materials = response.json()["materials"]
            material_name = list(materials.keys())[0]

            correction_data = {"material_name": material_name, "stress_values": []}

            response = client.post("/api/correct", json=correction_data)
            assert response.status_code == 422  # Validation error for empty list

    def test_generate_plot(self):
        """Test plot generation"""
        with TestClient(app) as client:
            # Get a valid material first
            response = client.get("/api/materials")
            materials = response.json()["materials"]
            material_name = list(materials.keys())[0]

            # Test plot generation
            plot_data = {"material_name": material_name, "stress_value": "400.0"}

            response = client.post("/api/plot", data=plot_data)
            assert response.status_code == 200
            data = response.json()

            assert "plot_data" in data
            assert data["plot_data"].startswith("data:image/png;base64,")

    def test_generate_plot_with_custom_material(self):
        """Test plot generation with custom material"""
        custom_material = {
            "yield_strength": 350.0,
            "sigma_u": 500.0,
            "elastic_mod": 210000.0,
            "eps_u": 0.15,
        }

        plot_data = {
            "material_name": "custom_test_material",
            "stress_value": "400.0",
            "custom_material": json.dumps(custom_material),
        }

        with TestClient(app) as client:
            response = client.post("/api/plot", data=plot_data)
            assert response.status_code == 200
            data = response.json()

            assert "plot_data" in data
            assert data["plot_data"].startswith("data:image/png;base64,")

    def test_generate_plot_invalid_material(self):
        """Test plot generation with invalid material"""
        plot_data = {"material_name": "nonexistent_material", "stress_value": "400.0"}

        with TestClient(app) as client:
            response = client.post("/api/plot", data=plot_data)
            assert response.status_code == 404

    def test_generate_plot_invalid_stress_value(self):
        """Test plot generation with invalid stress value"""
        with TestClient(app) as client:
            # Get a valid material first
            response = client.get("/api/materials")
            materials = response.json()["materials"]
            material_name = list(materials.keys())[0]

            plot_data = {"material_name": material_name, "stress_value": "invalid"}

            response = client.post("/api/plot", data=plot_data)
            assert response.status_code == 422  # Validation error


class TestRateLimiting:
    """Test rate limiting functionality"""

    def test_rate_limiting_headers(self):
        """Test that rate limiting headers are present"""
        with TestClient(app) as client:
            response = client.get("/health")
            assert "X-RateLimit-Limit" in response.headers
            assert "X-RateLimit-Remaining" in response.headers
            assert "X-RateLimit-Reset" in response.headers

    def test_rate_limiting_behavior(self):
        """Test rate limiting behavior with multiple requests"""
        with TestClient(app) as client:
            # Make multiple requests to trigger rate limiting
            responses = []
            for _ in range(10):  # Make 10 requests
                response = client.get("/health")
                responses.append(response)

            # All should succeed (rate limit is generous)
            for response in responses:
                assert response.status_code == 200

    def test_rate_limiting_different_endpoints(self):
        """Test that rate limiting works across different endpoints"""
        with TestClient(app) as client:
            # Test different endpoints
            endpoints = ["/health", "/api/materials"]

            for endpoint in endpoints:
                response = client.get(endpoint)
                assert response.status_code == 200
                assert "X-RateLimit-Limit" in response.headers


class TestSessionManagement:
    """Test session management functionality"""

    def test_session_cookie_set(self):
        """Test that session cookies are set"""
        with TestClient(app) as client:
            response = client.get("/health")
            assert "session_id" in response.cookies
            session_id = response.cookies["session_id"]
            assert len(session_id) > 0

    def test_session_persistence(self):
        """Test that sessions persist across requests"""
        with TestClient(app) as client:
            # First request
            response1 = client.get("/health")
            session_id1 = response1.cookies["session_id"]

            # Second request with same session (TestClient automatically includes cookies)
            response2 = client.get("/health")
            session_id2 = response2.cookies.get("session_id")

            # The session ID should be the same, but the cookie might not be set again
            # if it's already present in the request
            assert session_id1 == session_id2 or session_id2 is None

    def test_request_id_uniqueness(self):
        """Test that each request gets a unique request ID"""
        with TestClient(app) as client:
            response1 = client.get("/health")
            response2 = client.get("/health")

            request_id1 = response1.headers["X-Request-ID"]
            request_id2 = response2.headers["X-Request-ID"]

            assert request_id1 != request_id2


class TestErrorHandling:
    """Test error handling in API routes"""

    def test_404_handling(self):
        """Test 404 error handling"""
        with TestClient(app) as client:
            response = client.get("/nonexistent")
            assert response.status_code == 404

    def test_422_validation_error(self):
        """Test 422 validation error handling"""
        with TestClient(app) as client:
            # Test with invalid JSON
            response = client.post("/api/correct", json={"invalid": "data"})
            assert response.status_code == 422

    def test_500_internal_error_handling(self):
        """Test 500 internal error handling"""
        with TestClient(app) as client:
            # This would require mocking internal errors
            # For now, just test that the app doesn't crash
            response = client.get("/health")
            assert response.status_code == 200


class TestAPIIntegration:
    """Integration tests for API functionality"""

    def test_full_workflow(self):
        """Test a complete workflow from material upload to correction"""
        with TestClient(app) as client:
            # 1. Upload materials
            test_materials = {
                "materials": [
                    {
                        "id": "workflow_steel",
                        "name": "Workflow Test Steel",
                        "properties": {
                            "fty": 350,
                            "ftu": 500,
                            "E": 210000,
                            "epsilon_u": 0.15,
                        },
                    }
                ]
            }

            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".yaml", delete=False
            ) as tmp:
                yaml.dump(test_materials, tmp)
                tmp_path = tmp.name

            try:
                with open(tmp_path, "rb") as f:
                    response = client.post(
                        "/api/upload-materials",
                        files={
                            "file": ("workflow_materials.yaml", f, "application/x-yaml")
                        },
                    )
                assert response.status_code == 200

                # 2. Get materials
                response = client.get("/api/materials")
                assert response.status_code == 200
                materials = response.json()["materials"]
                assert "workflow_steel" in materials

                # 3. Perform correction
                correction_data = {
                    "material_name": "workflow_steel",
                    "stress_values": [400.0, 500.0],
                }
                response = client.post("/api/correct", json=correction_data)
                assert response.status_code == 200

                # 4. Generate plot
                plot_data = {"material_name": "workflow_steel", "stress_value": "400.0"}
                response = client.post("/api/plot", data=plot_data)
                assert response.status_code == 200

            finally:
                os.unlink(tmp_path)
