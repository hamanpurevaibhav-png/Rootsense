"""
Environment setup, corporate SSL configuration, Neuro-SAN alignment,
and Gemini LLM configuration for RootSense SAC.
Grounded in rootsense.md and test_neurosan configuration standards.
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional

from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# 1. Directory & File Path Resolution
# ---------------------------------------------------------------------------
BASE_DIR: Path = Path(__file__).resolve().parent.parent
BACKEND_DIR: Path = BASE_DIR / "backend"
AGENTS_DIR: Path = BACKEND_DIR / "agents"
MOCK_SAC_DIR: Path = BACKEND_DIR / "mock_sac"
MOCK_DATA_DIR: Path = MOCK_SAC_DIR / "data"
TICKETING_DIR: Path = BACKEND_DIR / "ticketing"
FRONTEND_DIR: Path = BASE_DIR / "frontend"
TESTS_DIR: Path = BASE_DIR / "tests"

CERTS_DIR: Path = BASE_DIR / ".certs"
CA_BUNDLE_PATH: Path = CERTS_DIR / "ca_bundle.pem"
ENV_FILE_PATH: Path = BASE_DIR / ".env"
ENV_EXAMPLE_PATH: Path = BASE_DIR / ".env.example"
SYSTEM_SPEC_PATH: Path = BASE_DIR / "rootsense.md"

# Mock SAC & Enterprise KB Data Paths
SAC_CHANGE_LOG_PATH: Path = MOCK_DATA_DIR / "sac_change_log.json"
SAC_METADATA_PATH: Path = MOCK_DATA_DIR / "sac_metadata.json"
SERVICENOW_KB_PATH: Path = MOCK_DATA_DIR / "servicenow_kb.json"
CONFLUENCE_KB_PATH: Path = MOCK_DATA_DIR / "confluence_kb.json"
SUBMITTED_TICKETS_PATH: Path = MOCK_DATA_DIR / "submitted_tickets.json"


# ---------------------------------------------------------------------------
# 2. Corporate SSL Certificate Bundle Setup (Learned from test_neurosan)
# ---------------------------------------------------------------------------
def configure_corporate_ssl() -> Optional[str]:
    """
    Configure corporate CA bundle (.certs/ca_bundle.pem) for HTTPS/REST/gRPC
    calls to Google Gemini APIs, matching test_neurosan/start_neurosan.ps1.
    """
    os.environ.setdefault("PYTHONUTF8", "1")
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    if CA_BUNDLE_PATH.exists():
        ca_str = str(CA_BUNDLE_PATH)
        os.environ["SSL_CERT_FILE"] = ca_str
        os.environ["REQUESTS_CA_BUNDLE"] = ca_str
        os.environ["CURL_CA_BUNDLE"] = ca_str
        os.environ["GRPC_DEFAULT_SSL_ROOTS_FILE_PATH"] = ca_str
        return ca_str
    return None


ACTIVE_CA_BUNDLE: Optional[str] = configure_corporate_ssl()

# ---------------------------------------------------------------------------
# 3. Environment Variable Loading & Neuro-SAN Key Alignment
# ---------------------------------------------------------------------------
load_dotenv(dotenv_path=ENV_FILE_PATH, override=True)

import warnings
with warnings.catch_warnings():
    warnings.filterwarnings("ignore", category=FutureWarning)
    import google.generativeai as genai  # noqa: E402

# Support both GEMINI_API_KEY (RootSense spec) and GOOGLE_API_KEY (Neuro-SAN spec)
GEMINI_API_KEY: str = (
    os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or ""
).strip().strip('"').strip("'")

if GEMINI_API_KEY:
    os.environ["GEMINI_API_KEY"] = GEMINI_API_KEY
    os.environ["GOOGLE_API_KEY"] = GEMINI_API_KEY

# Primary registered model per Prompt 1 + Neuro-SAN llm_config.hocon fallback chain
GEMINI_MODEL_NAME: str = "gemini-1.5-flash"
FALLBACK_FLASH_MODELS: tuple[str, ...] = (
    "gemini-3.5-flash",
    "gemini-3.6-flash",
    "gemini-3.5-flash-lite",
    "gemini-3-flash-preview",
    "gemini-3.8-flash",
    "gemini-2.5-flash",
    "gemini-2.0-flash",
)

BACKEND_HOST: str = os.getenv("BACKEND_HOST", "127.0.0.1")
BACKEND_PORT: int = int(os.getenv("BACKEND_PORT", "8000"))
SAC_DEFAULT_MODEL_ID: str = os.getenv("SAC_DEFAULT_MODEL_ID", "CORP_FINANCE_PLANNING")
DEFAULT_CALLER_EMAIL: str = os.getenv("DEFAULT_CALLER_EMAIL", "analyst.user@cognizant.com")

# Toggle between simulated SAC fixtures and live SAC REST APIs
USE_MOCK_SAC: bool = os.getenv("USE_MOCK_SAC", "True").strip().lower() in ("true", "1", "yes")


def load_system_instructions() -> str:
    """Load the authoritative RootSense system specification from rootsense.md."""
    if SYSTEM_SPEC_PATH.exists():
        return SYSTEM_SPEC_PATH.read_text(encoding="utf-8")
    return (
        "You are RootSense, an industry-grade Agentic Diagnostic Assistant developed by "
        "Cognizant AI Lab, powered by Neuro-SAN and Gemini."
    )


def is_api_key_configured(api_key: Optional[str] = None) -> bool:
    """Return True if a valid non-placeholder Gemini/Google API key is configured."""
    key = (
        api_key
        if api_key is not None
        else (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or GEMINI_API_KEY)
    ).strip().strip('"').strip("'")
    return bool(key) and key not in (
        "your_gemini_api_key_here",
        "PASTE_YOUR_GEMINI_API_KEY_HERE",
    )


def initialize_gemini_client(
    api_key: Optional[str] = None,
    model_name: str = GEMINI_MODEL_NAME,
) -> genai.GenerativeModel:
    """
    Configure google-generativeai with GEMINI_API_KEY / GOOGLE_API_KEY from .env,
    register the Gemini LLM client (gemini-1.5-flash) using REST transport for
    corporate SSL compatibility, and print a clean connection status.
    """
    configure_corporate_ssl()
    active_key = (
        api_key
        if api_key is not None
        else (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or GEMINI_API_KEY)
    ).strip().strip('"').strip("'")

    ssl_status = "CA_BUNDLE_LOADED" if ACTIVE_CA_BUNDLE else "SYSTEM_CERTS"

    if is_api_key_configured(active_key):
        genai.configure(api_key=active_key, transport="rest")
        client = genai.GenerativeModel(model_name=model_name)
        print(
            f"[RootSense Config] Environment: LOADED | "
            f"LLM Client: {model_name} | "
            f"SSL: {ssl_status} | "
            f"API Key: CONFIGURED ({active_key[:6]}...) | "
            f"Status: READY"
        )
    else:
        client = genai.GenerativeModel(model_name=model_name)
        print(
            f"[RootSense Config] Environment: LOADED | "
            f"LLM Client: {model_name} | "
            f"SSL: {ssl_status} | "
            f"API Key: NOT SET (update .env) | "
            f"Status: STANDBY"
        )
    return client


def get_gemini_client() -> genai.GenerativeModel:
    """Return the registered Gemini GenerativeModel instance."""
    return llm_client


def generate_content_with_fallback(
    prompt: str,
    system_instruction: Optional[str] = None,
) -> str:
    """
    Generate content using the Neuro-SAN Gemini 3.x Flash fallback pool
    (gemini-3.5-flash -> gemini-3.6-flash -> gemini-3.5-flash-lite ->
    gemini-3-flash-preview -> gemini-3.8-flash) defined in config/llm_config.hocon.
    """
    configure_corporate_ssl()
    active_key = (
        os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or GEMINI_API_KEY
    ).strip().strip('"').strip("'")
    genai.configure(api_key=active_key, transport="rest")

    # Prioritize the active Gemini 3.x Flash fallback pool, plus registered model
    pool = (*FALLBACK_FLASH_MODELS, GEMINI_MODEL_NAME)
    last_error: Optional[Exception] = None

    for model_name in pool:
        try:
            kwargs: Dict[str, Any] = {"model_name": model_name}
            if system_instruction:
                kwargs["system_instruction"] = system_instruction
            model = genai.GenerativeModel(**kwargs)
            response = model.generate_content(prompt)
            text = (response.text or "").strip()
            if text:
                return text
        except Exception as exc:
            last_error = exc
            continue

    raise RuntimeError(f"All Gemini models in fallback pool failed. Last error: {last_error}")


def verify_gemini_connection(prompt: str = "Respond with the single word: ONLINE") -> Dict[str, Any]:
    """
    Execute a live responsiveness check against the Google Gemini API.
    Attempts the registered model (gemini-1.5-flash) first, then walks the
    Neuro-SAN Gemini Flash fallback chain (gemini-3.5-flash, gemini-3.6-flash,
    gemini-3.5-flash-lite, etc.) configured in test_neurosan/config/llm_config.hocon.
    """
    configure_corporate_ssl()
    load_dotenv(dotenv_path=ENV_FILE_PATH, override=True)
    active_key = (
        os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or GEMINI_API_KEY
    ).strip().strip('"').strip("'")

    if not is_api_key_configured(active_key):
        status_report = {
            "connected": False,
            "registered_model": GEMINI_MODEL_NAME,
            "active_model": None,
            "response_text": None,
            "error": "GEMINI_API_KEY / GOOGLE_API_KEY is missing in .env",
        }
        print(f"[RootSense Health] Gemini API Connection: FAILED ({status_report['error']})")
        return status_report

    genai.configure(api_key=active_key, transport="rest")
    models_to_try = (GEMINI_MODEL_NAME, *FALLBACK_FLASH_MODELS)
    last_error: Optional[str] = None

    for candidate_model in models_to_try:
        try:
            model = genai.GenerativeModel(model_name=candidate_model)
            response = model.generate_content(prompt)
            reply_text = (response.text or "").strip()
            if reply_text:
                print(
                    f"[RootSense Health] Gemini API Connection: VERIFIED | "
                    f"Registered: {GEMINI_MODEL_NAME} | Active Model: {candidate_model} | "
                    f"Response: {reply_text[:60]}"
                )
                return {
                    "connected": True,
                    "registered_model": GEMINI_MODEL_NAME,
                    "active_model": candidate_model,
                    "response_text": reply_text,
                    "error": None,
                }
        except Exception as exc:
            last_error = str(exc)
            continue

    print(f"[RootSense Health] Gemini API Connection: ERROR ({last_error})")
    return {
        "connected": False,
        "registered_model": GEMINI_MODEL_NAME,
        "active_model": None,
        "response_text": None,
        "error": last_error,
    }


# Register default Gemini client on module load
llm_client: genai.GenerativeModel = initialize_gemini_client()
