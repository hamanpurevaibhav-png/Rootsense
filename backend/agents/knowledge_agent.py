"""
Enterprise Knowledge Base RAG Agent (ServiceNow & Confluence) for RootSense.
Grounded in rootsense.md Section 2.C (Enterprise Knowledge Agent - RAG) and
Neuro-SAN AAOSA protocol standards.
"""

import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from backend import config


class KnowledgeBaseAgent:
    """
    Enterprise Knowledge Base Agent (RAG) that searches across resolved
    ServiceNow IT Helpdesk Incidents and Confluence Standard Operating Procedures (SOPs).

    Supports:
    - Dynamic loading of ServiceNow and Confluence JSON corpora via backend/config.py
    - Hybrid TF-IDF Cosine Similarity + Morphological Stemming + Phrase/Keyword Intersection
    - Optional Gemini LLM Reranking / Grounded Answer Synthesis
    - Neuro-SAN AAOSA Determine & Fulfill protocol methods for Supervisor routing
    """

    STOP_WORDS: Set[str] = {
        "a", "an", "and", "are", "as", "at", "be", "by", "can", "do", "does",
        "for", "from", "how", "i", "in", "into", "is", "it", "my", "of", "on",
        "or", "our", "the", "their", "this", "to", "was", "we", "what", "when",
        "where", "which", "who", "why", "with",
    }

    SYNONYM_EXPANSIONS: Dict[str, List[str]] = {
        "percentage": ["percent", "pct", "ratio", "margin"],
        "percentages": ["percent", "pct", "ratio", "margin"],
        "percent": ["percentage", "pct", "ratio", "margin"],
        "pct": ["percent", "percentage", "ratio"],
        "sum": ["add", "total", "aggregation", "rollup"],
        "summing": ["sum", "add", "aggregation", "rollup"],
        "sso": ["single", "sign", "saml", "login", "authentication", "vpn"],
        "vpn": ["tunnel", "sso", "timeout", "connection", "network"],
        "locked": ["lock", "greyed", "readonly", "console"],
        "greyed": ["locked", "lock", "readonly", "cannot", "edit"],
        "vanished": ["overwrite", "overwriting", "disappear", "revert"],
        "overwritten": ["overwrite", "overwriting", "data", "action"],
        "divide": ["division", "zero", "ndiv0", "na", "formula"],
        "division": ["divide", "zero", "ndiv0", "na", "formula"],
    }

    def __init__(
        self,
        servicenow_kb_path: Optional[Path] = None,
        confluence_kb_path: Optional[Path] = None,
        use_llm_rerank: bool = False,
    ) -> None:
        self.servicenow_kb_path: Path = Path(servicenow_kb_path or config.SERVICENOW_KB_PATH)
        self.confluence_kb_path: Path = Path(confluence_kb_path or config.CONFLUENCE_KB_PATH)
        self.use_llm_rerank: bool = use_llm_rerank

        self.servicenow_records: List[Dict[str, Any]] = self._load_json_list(self.servicenow_kb_path)
        self.confluence_records: List[Dict[str, Any]] = self._load_json_list(self.confluence_kb_path)
        self.documents: List[Dict[str, Any]] = self._build_unified_corpus()

        # Precompute IDF weights and document TF-IDF vectors for fast, deterministic retrieval
        self._doc_tokens: List[List[str]] = []
        self._idf: Dict[str, float] = {}
        self._doc_vectors: List[Dict[str, float]] = []
        self._build_tfidf_index()

    @staticmethod
    def _load_json_list(file_path: Path) -> List[Dict[str, Any]]:
        """Load and validate a JSON list file from disk."""
        if not file_path.exists():
            raise FileNotFoundError(f"Knowledge base file not found: {file_path}")
        with file_path.open("r", encoding="utf-8") as fp:
            data = json.load(fp)
        if not isinstance(data, list):
            raise ValueError(f"Expected JSON list in {file_path}, got {type(data).__name__}")
        return data

    def _build_unified_corpus(self) -> List[Dict[str, Any]]:
        """Normalize ServiceNow and Confluence records into a unified searchable corpus."""
        corpus: List[Dict[str, Any]] = []

        for item in self.servicenow_records:
            item_id = str(item.get("item_id") or item.get("ticket_id") or item.get("id") or "").strip()
            resolution_text = str(item.get("resolution") or item.get("content") or "").strip()
            symptoms_text = str(item.get("symptoms") or "").strip()
            corpus.append(
                {
                    "item_id": item_id,
                    "id": item_id,
                    "title": str(item.get("title", "")).strip(),
                    "category": str(item.get("category", "ServiceNow Incident")).strip(),
                    "source": str(item.get("source", "ServiceNow")).strip(),
                    "resolution": resolution_text,
                    "content": resolution_text,
                    "symptoms": symptoms_text,
                    "keywords": [str(k).lower().strip() for k in item.get("keywords", [])],
                    "is_user_fixable": bool(item.get("is_user_fixable", True)),
                }
            )

        for item in self.confluence_records:
            item_id = str(item.get("item_id") or item.get("page_id") or item.get("id") or "").strip()
            content_text = str(item.get("content") or item.get("resolution") or "").strip()
            corpus.append(
                {
                    "item_id": item_id,
                    "id": item_id,
                    "title": str(item.get("title", "")).strip(),
                    "category": str(item.get("category", "Confluence SOP")).strip(),
                    "source": str(item.get("source", "Confluence")).strip(),
                    "resolution": content_text,
                    "content": content_text,
                    "symptoms": "",
                    "keywords": [str(k).lower().strip() for k in item.get("keywords", [])],
                    "is_user_fixable": bool(item.get("is_user_fixable", True)),
                }
            )

        return corpus

    @classmethod
    def _stem_token(cls, token: str) -> str:
        """Apply lightweight morphological normalization for domain terms."""
        tok = token.lower().strip()
        if tok in ("percentages", "percentage"):
            return "percent"
        if tok in ("overwriting", "overwritten", "overwrites"):
            return "overwrite"
        if tok in ("locked", "locking", "locks"):
            return "lock"
        if tok in ("calculations", "calculated", "calculating"):
            return "calculat"
        if tok in ("adjustments", "adjusted", "adjusting"):
            return "adjust"
        if len(tok) > 5 and tok.endswith("ing"):
            return tok[:-3]
        if len(tok) > 4 and tok.endswith("ed"):
            return tok[:-2]
        if len(tok) > 4 and tok.endswith("es"):
            return tok[:-2]
        if len(tok) > 3 and tok.endswith("s") and not tok.endswith("ss"):
            return tok[:-1]
        return tok

    @classmethod
    def _tokenize(cls, text: str, expand_synonyms: bool = False) -> List[str]:
        """Extract normalized word tokens, stems, and adjacent bigrams."""
        raw_tokens = re.findall(r"[a-z0-9_]+(?:\.[0-9]+)?", text.lower())
        filtered: List[str] = []
        for raw in raw_tokens:
            if raw in cls.STOP_WORDS:
                continue
            filtered.append(raw)
            stemmed = cls._stem_token(raw)
            if stemmed != raw:
                filtered.append(stemmed)
            if expand_synonyms and raw in cls.SYNONYM_EXPANSIONS:
                for syn in cls.SYNONYM_EXPANSIONS[raw]:
                    filtered.append(syn)
                    filtered.append(cls._stem_token(syn))

        # Add bigrams of primary non-stopword tokens for phrase sensitivity
        base_words = [cls._stem_token(t) for t in raw_tokens if t not in cls.STOP_WORDS]
        for idx in range(len(base_words) - 1):
            filtered.append(f"{base_words[idx]}_{base_words[idx + 1]}")

        return filtered

    def _build_tfidf_index(self) -> None:
        """Build weighted TF-IDF vectors for every document in the unified corpus."""
        num_docs = len(self.documents)
        if num_docs == 0:
            return

        doc_freq: Counter[str] = Counter()
        self._doc_tokens = []

        for doc in self.documents:
            # Weight title and explicit keywords higher than body text
            weighted_text_parts = [
                doc["item_id"],
                (doc["title"] + " ") * 3,
                (" ".join(doc["keywords"]) + " ") * 3,
                (doc["category"] + " ") * 2,
                doc["symptoms"],
                doc["resolution"],
            ]
            full_text = " ".join(weighted_text_parts)
            tokens = self._tokenize(full_text, expand_synonyms=True)
            self._doc_tokens.append(tokens)
            for unique_tok in set(tokens):
                doc_freq[unique_tok] += 1

        self._idf = {
            term: math.log((1.0 + num_docs) / (1.0 + df)) + 1.0
            for term, df in doc_freq.items()
        }

        self._doc_vectors = []
        for tokens in self._doc_tokens:
            tf_counts = Counter(tokens)
            total_terms = max(len(tokens), 1)
            vec: Dict[str, float] = {}
            for term, count in tf_counts.items():
                tf = count / total_terms
                vec[term] = tf * self._idf.get(term, 1.0)
            self._doc_vectors.append(vec)

    @staticmethod
    def _cosine_similarity(vec_a: Dict[str, float], vec_b: Dict[str, float]) -> float:
        """Compute cosine similarity between two sparse term dictionaries."""
        if not vec_a or not vec_b:
            return 0.0
        common_terms = set(vec_a.keys()) & set(vec_b.keys())
        if not common_terms:
            return 0.0
        dot = sum(vec_a[t] * vec_b[t] for t in common_terms)
        norm_a = math.sqrt(sum(v * v for v in vec_a.values()))
        norm_b = math.sqrt(sum(v * v for v in vec_b.values()))
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return dot / (norm_a * norm_b)

    def _compute_hybrid_score(self, query: str, doc_idx: int) -> float:
        """
        Combine TF-IDF cosine similarity with exact keyword/phrase and token-intersection
        bonuses, clamped cleanly into [0.0, 1.0].
        """
        doc = self.documents[doc_idx]
        q_lower = query.lower().strip()
        if not q_lower:
            return 0.0

        # Direct ID match
        if doc["item_id"].lower() in q_lower:
            return 0.99

        q_tokens = self._tokenize(q_lower, expand_synonyms=True)
        if not q_tokens:
            return 0.0

        q_counts = Counter(q_tokens)
        q_total = max(len(q_tokens), 1)
        q_vec = {
            term: (cnt / q_total) * self._idf.get(term, 1.0)
            for term, cnt in q_counts.items()
        }

        cosine = self._cosine_similarity(q_vec, self._doc_vectors[doc_idx])

        # Token intersection ratio on primary query terms
        raw_q_words = [
            self._stem_token(w)
            for w in re.findall(r"[a-z0-9_]+", q_lower)
            if w not in self.STOP_WORDS
        ]
        doc_token_set = set(self._doc_tokens[doc_idx])
        if raw_q_words:
            matched_words = sum(1 for w in raw_q_words if w in doc_token_set)
            token_overlap = matched_words / len(raw_q_words)
        else:
            token_overlap = 0.0

        # Phrase / keyword bonus
        phrase_bonus = 0.0
        title_lower = doc["title"].lower()
        body_lower = f"{title_lower} {doc['category'].lower()} {doc['resolution'].lower()} {doc['symptoms'].lower()}"
        for kw in doc["keywords"]:
            if kw and kw in q_lower:
                phrase_bonus += 0.22
            else:
                kw_stems = [self._stem_token(w) for w in re.findall(r"[a-z0-9_]+", kw) if w not in self.STOP_WORDS]
                if kw_stems and all(s in raw_q_words for s in kw_stems):
                    phrase_bonus += 0.16

        # Title token overlap bonus
        title_stems = {self._stem_token(w) for w in re.findall(r"[a-z0-9_]+", title_lower) if w not in self.STOP_WORDS}
        if raw_q_words and title_stems:
            title_hits = sum(1 for w in raw_q_words if w in title_stems)
            phrase_bonus += 0.18 * (title_hits / len(raw_q_words))

        # Body direct substring bonus for multi-word queries
        if len(q_lower) >= 4 and q_lower in body_lower:
            phrase_bonus += 0.20

        raw_score = (0.45 * cosine) + (0.35 * token_overlap) + min(phrase_bonus, 0.45)
        if raw_score <= 0.0:
            return 0.0
        return round(min(max(raw_score, 0.0), 0.99), 4)

    def search_knowledge_base(self, query: str, limit: int = 3) -> List[Dict[str, Any]]:
        """
        Perform semantic-style hybrid search over ServiceNow Incidents and Confluence SOPs.

        Returns structured search cards containing:
        - item_id / id (Ticket ID or Confluence Page ID)
        - title
        - category
        - source ("ServiceNow" or "Confluence")
        - match_score (float in 0.0 to 1.0)
        - resolution / content (the resolution or SOP guidance text)
        - is_user_fixable (bool)
        """
        if not query or not query.strip():
            return []

        scored_cards: List[Tuple[float, Dict[str, Any]]] = []
        for idx, doc in enumerate(self.documents):
            score = self._compute_hybrid_score(query, idx)
            card: Dict[str, Any] = {
                "item_id": doc["item_id"],
                "id": doc["id"],
                "title": doc["title"],
                "category": doc["category"],
                "source": doc["source"],
                "match_score": score,
                "resolution": doc["resolution"],
                "content": doc["content"],
                "is_user_fixable": doc["is_user_fixable"],
            }
            scored_cards.append((score, card))

        scored_cards.sort(key=lambda pair: pair[0], reverse=True)
        top_cards = [card for score, card in scored_cards[: max(limit, 1)] if score > 0.0]

        if not top_cards and scored_cards:
            top_cards = [card for _, card in scored_cards[: max(limit, 1)]]

        return top_cards

    def synthesize_rag_response(
        self,
        query: str,
        limit: int = 3,
        use_llm: bool = False,
    ) -> Dict[str, Any]:
        """
        Retrieve top KB records and synthesize a grounded resolution response.
        Uses deterministic citation formatting by default, or calls Gemini when use_llm=True.
        """
        matches = self.search_knowledge_base(query=query, limit=limit)
        if not matches:
            return {
                "query": query,
                "top_match": None,
                "matches": [],
                "grounded_answer": "No matching ServiceNow or Confluence knowledge base records were found.",
                "requires_escalation": True,
            }

        best = matches[0]
        default_answer = (
            f"[{best['source']} {best['item_id']}] {best['title']} "
            f"(Category: {best['category']}, Match Score: {best['match_score']:.2f}): "
            f"{best['resolution']}"
        )

        if use_llm and config.is_api_key_configured():
            try:
                context_block = "\n".join(
                    f"- {m['item_id']} ({m['source']} | {m['title']}): {m['resolution']}"
                    for m in matches
                )
                prompt = (
                    f"You are the RootSense Enterprise Knowledge Base Agent.\n"
                    f"User Inquiry: {query}\n\n"
                    f"Retrieved Knowledge Base Records:\n{context_block}\n\n"
                    f"Provide a concise, accurate resolution strictly grounded in the retrieved records, "
                    f"explicitly citing the ID ({best['item_id']})."
                )
                default_answer = config.generate_content_with_fallback(prompt=prompt)
            except Exception:
                pass

        return {
            "query": query,
            "top_match": best,
            "matches": matches,
            "grounded_answer": default_answer,
            "requires_escalation": not bool(best.get("is_user_fixable", True)),
        }

    # -----------------------------------------------------------------------
    # Neuro-SAN AAOSA Protocol Support (Determine / Fulfill)
    # -----------------------------------------------------------------------
    def aaosa_determine(self, inquiry: str) -> Dict[str, Any]:
        """
        Evaluate an inquiry under the Neuro-SAN AAOSA 'Determine' mode and
        return a structured claim with Strength (1-10) and Relevant (Yes/No).
        """
        matches = self.search_knowledge_base(inquiry, limit=1)
        top_score = matches[0]["match_score"] if matches else 0.0
        strength = max(1, min(10, int(round(top_score * 10))))
        relevant = "Yes" if top_score >= 0.25 else "No"
        return {
            "Name": "KnowledgeBaseAgent",
            "Inquiry": inquiry,
            "Mode": "Determine",
            "Relevant": relevant,
            "Strength": strength,
            "Claim": "All" if top_score >= 0.55 else "Partial",
            "Requirements": None,
            "TopMatchId": matches[0]["item_id"] if matches else None,
            "TopMatchScore": top_score,
        }

    def aaosa_fulfill(self, inquiry: str, limit: int = 3) -> Dict[str, Any]:
        """
        Fulfill an inquiry under the Neuro-SAN AAOSA 'Fulfill' mode.
        """
        rag_result = self.synthesize_rag_response(query=inquiry, limit=limit, use_llm=False)
        return {
            "Name": "KnowledgeBaseAgent",
            "Inquiry": inquiry,
            "Mode": "Fulfill",
            "Response": rag_result,
        }
