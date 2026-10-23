"""
Neuro-SAN CodedTool wrapper for the Enterprise Knowledge Base RAG Agent.
Searches ServiceNow Incidents and Confluence SOP Wiki articles.
"""

from pathlib import Path
import sys
from typing import Any, Dict

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

try:
    from neuro_san.interfaces.coded_tool import CodedTool
except ImportError:
    class CodedTool:
        """Fallback CodedTool base class when neuro-san is not active."""

from backend.agents.knowledge_agent import KnowledgeBaseAgent  # noqa: E402


class EnterpriseKBRAGTool(CodedTool):
    """
    Executes hybrid semantic + keyword retrieval across ServiceNow and Confluence records.
    """

    async def async_invoke(self, args: Dict[str, Any], sly_data: Dict[str, Any]) -> Dict[str, Any]:
        query = str(args.get("query", "")).strip()
        top_k = int(args.get("top_k", 3))
        kb_agent = KnowledgeBaseAgent()
        result = kb_agent.search(query=query, top_k=top_k)

        payload = result.model_dump()
        sly_data["kb_rag_matches"] = payload.get("matched_cards", [])
        return payload
