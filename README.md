# RootSense for SAC — Neuro-Symbolic Agentic Diagnostic Engine

**RootSense** is an enterprise-grade Agentic AI Diagnostic Assistant developed for **SAP Analytics Cloud (SAC) Planning**, powered by **Neuro-SAN** and **Google Gemini** (`config/llm_config.hocon` Gemini 3.x Flash fallback pool).

It combines deterministic programmatic checks (**Symbolic**) with grounded generative synthesis (**Neural**) to troubleshoot unexplained planning values, private/public version discrepancies, non-additive formula rollups, and Data Locking Console slice locks—with automated **IT4You** escalation payload generation.

---

## Architecture & Directory Structure

```text
rootsense-sac/
├── backend/
│   ├── app.py                      # FastAPI API server
│   ├── config.py                   # Environment setup, corporate SSL, & Gemini LLM config
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── supervisor.py           # Neuro-SAN Agentic router (AAOSA Front-Man)
│   │   ├── sac_diagnostic.py       # 7-Step SAC Planning Diagnostic core logic
│   │   └── knowledge_agent.py      # RAG agent (ServiceNow, Confluence)
│   ├── mock_sac/
│   │   ├── __init__.py
│   │   ├── sac_gateway.py          # Simulated SAC REST API client
│   │   └── data/                   # JSON Mock DB
│   │       ├── sac_change_log.json
│   │       ├── sac_metadata.json
│   │       ├── servicenow_kb.json
│   │       └── confluence_kb.json
│   └── ticketing/
│       ├── __init__.py
│       └── it4you_service.py       # IT4You Escalation Validator
├── config/
│   └── llm_config.hocon            # Neuro-SAN Gemini 3.x Flash fallback pool
├── frontend/
│   └── streamlit_app.py            # Dual-panel Streamlit client interface
├── tests/
│   ├── test_health.py              # Dependency, path, & Gemini API health check
│   ├── test_sac_mock.py            # Mock SAC Gateway & fixture unit tests
│   ├── test_kb.py                  # Knowledge Base RAG tests
│   ├── test_diagnostic.py          # 7-Step Diagnostic Tree tests
│   └── test_scenarios.py           # End-to-end scenario & IT4You payload tests
├── rootsense.md                    # System specification & source of truth
├── setup_env.ps1                   # Automated uv environment bootstrapper
├── .env.example                    # Environment variable template
└── requirements.txt                # Project dependencies
```

---

## Quick Start (`uv`)

```powershell
# 1. Bootstrap .venv and install dependencies
.\setup_env.ps1

# 2. Run Health & Mock SAC Gateway Test Suites
.\.venv\Scripts\python.exe tests/test_health.py
.\.venv\Scripts\python.exe tests/test_sac_mock.py
```
