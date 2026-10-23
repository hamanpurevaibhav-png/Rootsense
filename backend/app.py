"""
FastAPI API Server for RootSense SAC Diagnostic Engine.
"""

from fastapi import FastAPI
from backend.config import GEMINI_MODEL_NAME, SAC_DEFAULT_MODEL_ID, is_api_key_configured

app = FastAPI(
    title="RootSense for SAC Diagnostic Engine",
    description="Neuro-Symbolic Agentic AI Diagnostic Assistant for SAP Analytics Cloud Planning",
    version="1.0.0",
)


@app.get("/health")
def health_check() -> dict:
    """Return service and LLM configuration health status."""
    return {
        "status": "healthy",
        "service": "RootSense for SAC",
        "registered_model": GEMINI_MODEL_NAME,
        "default_sac_model": SAC_DEFAULT_MODEL_ID,
        "api_key_configured": is_api_key_configured(),
    }
