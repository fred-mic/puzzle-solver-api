"""HTTP-level regression tests for the API's bearer authentication."""
import os
from pathlib import Path
import secrets
import sys
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

PROJECT_ROOT = str(Path(__file__).resolve().parents[1])
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

TEST_TOKEN = "authentication-test-token"
# Satisfy import-time configuration without requiring a real deployment secret.
with patch.dict(os.environ, {"API_SECRET_TOKEN": TEST_TOKEN}):
    import main


class TestAuthentication(unittest.TestCase):
    def setUp(self):
        self.enterContext(patch.object(main.config, "API_SECRET_TOKEN", TEST_TOKEN))
        # Exercise real routing/security without loading artifacts or invoking A*.
        self.enterContext(patch.object(main.puzzle_service, "load_database"))
        self.state = [1, 2, 3, 4, 5, 6, 7, 0, 8]
        self.goal = [1, 2, 3, 4, 5, 6, 7, 8, 0]
        self.solve = self.enterContext(
            patch.object(
                main.puzzle_service,
                "solve_using_database",
                return_value=[tuple(self.state), tuple(self.goal)],
            )
        )
        self.client = self.enterContext(TestClient(main.app))

    def assert_unauthorized(self, response):
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.headers.get("WWW-Authenticate"), "Bearer")
        self.assertEqual(
            response.json(), {"detail": "Invalid or missing authentication token"}
        )
        self.solve.assert_not_called()

    def test_missing_credentials(self):
        response = self.client.post("/solve", json={"state": self.state})
        self.assert_unauthorized(response)

    def test_incorrect_credentials(self):
        response = self.client.post(
            "/solve",
            json={"state": self.state},
            headers={"Authorization": "Bearer incorrect-token"},
        )
        self.assert_unauthorized(response)

    def test_malformed_credentials(self):
        for authorization in (
            "",
            "Bearer",
            "Bearer ",
            "Basic " + TEST_TOKEN,
            "Token " + TEST_TOKEN,
            "Bearer " + TEST_TOKEN + " extra",
            "Bearer\t" + TEST_TOKEN,
        ):
            with self.subTest(authorization=authorization):
                self.solve.reset_mock()
                response = self.client.post(
                    "/solve",
                    json={"state": self.state},
                    headers={"Authorization": authorization},
                )
                self.assert_unauthorized(response)

    def test_non_ascii_credentials_are_rejected_without_server_error(self):
        response = self.client.post(
            "/solve",
            json={"state": self.state},
            headers={"Authorization": b"Bearer \xff"},
        )
        self.assert_unauthorized(response)

    def test_correct_credentials(self):
        response = self.client.post(
            "/solve",
            json={"state": self.state},
            headers={"Authorization": "Bearer " + TEST_TOKEN},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"solution": [self.state, self.goal]})
        self.solve.assert_called_once_with(tuple(self.state))

    def test_bearer_scheme_is_case_insensitive(self):
        response = self.client.post(
            "/solve",
            json={"state": self.state},
            headers={"Authorization": "bEaReR " + TEST_TOKEN},
        )
        self.assertEqual(response.status_code, 200)
        self.solve.assert_called_once_with(tuple(self.state))

    def test_token_comparison_uses_compare_digest(self):
        with patch("main.secrets.compare_digest", wraps=secrets.compare_digest) as compare:
            response = self.client.post(
                "/solve",
                json={"state": self.state},
                headers={"Authorization": "Bearer " + TEST_TOKEN},
            )
        self.assertEqual(response.status_code, 200)
        compare.assert_called_once_with(TEST_TOKEN.encode("utf-8"), TEST_TOKEN.encode("utf-8"))

    def test_health_check_remains_public(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")
        self.solve.assert_not_called()

    def test_cors_preflight_remains_public(self):
        response = self.client.options(
            "/solve",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "authorization,content-type",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.solve.assert_not_called()

    def test_openapi_declares_bearer_authentication(self):
        schema = self.client.get("/openapi.json").json()
        self.assertEqual(
            schema["paths"]["/solve"]["post"]["security"], [{"HTTPBearer": []}]
        )
        self.assertEqual(
            schema["components"]["securitySchemes"]["HTTPBearer"]["scheme"], "bearer"
        )


if __name__ == "__main__":
    unittest.main()
