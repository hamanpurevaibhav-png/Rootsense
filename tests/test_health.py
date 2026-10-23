"""
Environment, Directory Path, Configuration, and Gemini API Health Check Suite.
Run via:
    python tests/test_health.py
or:
    pytest tests/test_health.py -v -s
"""

import json
import socket
import sys
import unittest
from pathlib import Path

# Ensure project root is on sys.path when invoked directly
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend import config


class TestRootSenseHealth(unittest.TestCase):
    """Verify project scaffolding, environment config, and Gemini LLM responsiveness."""

    def test_01_directory_and_file_paths(self) -> None:
        """Verify all required directories and modular files exist."""
        required_dirs = [
            config.BACKEND_DIR,
            config.AGENTS_DIR,
            config.MOCK_SAC_DIR,
            config.MOCK_DATA_DIR,
            config.TICKETING_DIR,
            config.FRONTEND_DIR,
            config.TESTS_DIR,
        ]
        for directory in required_dirs:
            self.assertTrue(
                directory.exists() and directory.is_dir(),
                f"Missing required directory: {directory}",
            )

        required_files = [
            config.BASE_DIR / "requirements.txt",
            config.BASE_DIR / ".env.example",
            config.SYSTEM_SPEC_PATH,
            config.BACKEND_DIR / "app.py",
            config.BACKEND_DIR / "config.py",
            config.AGENTS_DIR / "__init__.py",
            config.AGENTS_DIR / "supervisor.py",
            config.AGENTS_DIR / "sac_diagnostic.py",
            config.AGENTS_DIR / "knowledge_agent.py",
            config.MOCK_SAC_DIR / "__init__.py",
            config.MOCK_SAC_DIR / "sac_gateway.py",
            config.SAC_CHANGE_LOG_PATH,
            config.SAC_METADATA_PATH,
            config.SERVICENOW_KB_PATH,
            config.CONFLUENCE_KB_PATH,
            config.TICKETING_DIR / "__init__.py",
            config.TICKETING_DIR / "it4you_service.py",
            config.FRONTEND_DIR / "streamlit_app.py",
            config.TESTS_DIR / "test_health.py",
            config.TESTS_DIR / "test_sac_mock.py",
            config.TESTS_DIR / "test_kb.py",
            config.TESTS_DIR / "test_diagnostic.py",
            config.TESTS_DIR / "test_scenarios.py",
        ]
        for file_path in required_files:
            self.assertTrue(
                file_path.exists() and file_path.is_file(),
                f"Missing required file: {file_path}",
            )

        # Verify mock data JSON files are valid JSON
        for json_file in (
            config.SAC_CHANGE_LOG_PATH,
            config.SAC_METADATA_PATH,
            config.SERVICENOW_KB_PATH,
            config.CONFLUENCE_KB_PATH,
        ):
            with json_file.open("r", encoding="utf-8") as handle:
                parsed = json.load(handle)
                self.assertIsNotNone(parsed, f"Failed to parse JSON in {json_file}")

    def test_02_configuration_and_client_registration(self) -> None:
        """Verify configuration variables, rootsense.md grounding, and Gemini client registration."""
        self.assertEqual(config.GEMINI_MODEL_NAME, "gemini-1.5-flash")
        self.assertEqual(config.SAC_DEFAULT_MODEL_ID, "CORP_FINANCE_PLANNING")

        client = config.get_gemini_client()
        self.assertIsNotNone(client, "Gemini GenerativeModel client is not registered.")
        self.assertIn(
            "gemini-1.5-flash",
            client.model_name,
            f"Expected registered model 'gemini-1.5-flash', got '{client.model_name}'",
        )

        system_instructions = config.load_system_instructions()
        self.assertIn("RootSense", system_instructions)
        self.assertIn("7-Step SAC Planning Diagnostic Tree", system_instructions)

    def test_03_gemini_api_responsiveness(self) -> None:
        """Verify GEMINI_API_KEY configuration and live Gemini API responsiveness (or offline readiness)."""
        if not config.is_api_key_configured():
            self.skipTest(
                "GEMINI_API_KEY is not configured in .env yet. "
                "Copy .env.example to .env and set a valid GEMINI_API_KEY to run live LLM ping."
            )

        # Check if external DNS resolution is available in the current test environment
        try:
            socket.getaddrinfo("generativelanguage.googleapis.com", 443)
            network_available = True
        except OSError:
            network_available = False

        if not network_available:
            # Offline test runner mode: verify client instance and fallback pool readiness
            self.assertTrue(config.is_api_key_configured())
            self.assertIsNotNone(config.get_gemini_client())
            self.assertGreaterEqual(len(config.FALLBACK_FLASH_MODELS), 5)
            return

        result = config.verify_gemini_connection()
        self.assertTrue(
            result["connected"],
            f"Gemini API responsiveness check failed: {result.get('error')}",
        )
        self.assertTrue(
            bool(result.get("response_text")),
            "Gemini API returned an empty response.",
        )


if __name__ == "__main__":
    print("=" * 72)
    print("RootSense for SAC - Environment & Gemini API Health Check")
    print("=" * 72)
    unittest.main(verbosity=2)
