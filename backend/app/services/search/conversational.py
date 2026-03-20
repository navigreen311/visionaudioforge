"""Conversational search — context-aware query refinement and follow-up suggestions."""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# Common stop words to filter out during keyword extraction
_STOP_WORDS = frozenset({
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "need", "dare", "ought",
    "to", "of", "in", "for", "on", "with", "at", "by", "from", "as",
    "into", "through", "during", "before", "after", "above", "below",
    "between", "out", "off", "over", "under", "again", "further", "then",
    "once", "here", "there", "when", "where", "why", "how", "all", "each",
    "every", "both", "few", "more", "most", "other", "some", "such", "no",
    "nor", "not", "only", "own", "same", "so", "than", "too", "very",
    "just", "because", "but", "and", "or", "if", "while", "about",
    "it", "its", "this", "that", "these", "those", "i", "me", "my",
    "we", "our", "you", "your", "he", "him", "his", "she", "her",
    "they", "them", "their", "what", "which", "who", "whom",
    "show", "find", "search", "get", "give", "now", "also", "like",
    "similar", "ones", "results", "please", "want", "see",
})

# Temporal keywords that may map to date filters
_TEMPORAL_KEYWORDS = {
    "today": "today",
    "yesterday": "yesterday",
    "last week": "last_week",
    "last hour": "last_hour",
    "this morning": "today",
    "tonight": "today",
    "recent": "last_week",
    "latest": "today",
}


class ConversationalSearch:
    """Search with conversational context for query refinement."""

    async def search_with_context(
        self,
        query: str,
        conversation_history: list[str],
        workspace_id: str,
    ) -> dict[str, Any]:
        """Refine a query using conversation history and execute the search.

        V1 implementation: simple keyword extraction from the last 3 messages
        in history, merged with the current query to build an enriched query.

        Args:
            query: Current user query.
            conversation_history: Previous queries/messages in the conversation.
            workspace_id: Workspace to search within.

        Returns:
            Dict with ``results``, ``refined_query``, and ``suggestions``.
        """
        refined_query = self._refine_query(query, conversation_history)

        # Execute search with the refined query
        results: list[dict] = []
        try:
            from app.services.search.embeddings import EmbeddingService
            from app.services.search.faiss_index import FAISSIndexService
            from app.services.search.search_service import CrossModalSearchService

            embedding_svc = EmbeddingService()
            index_svc = FAISSIndexService(dimension=512)
            index_svc.create_index("flat")
            search_svc = CrossModalSearchService(
                embedding_svc=embedding_svc,
                index_svc=index_svc,
                db_session=None,
            )
            results = await search_svc.search_by_text(query=refined_query, k=10)
        except Exception:
            logger.exception("Conversational search execution failed")

        suggestions = await self.suggest_follow_ups(query, results)

        return {
            "results": results,
            "refined_query": refined_query,
            "suggestions": suggestions,
        }

    async def suggest_follow_ups(
        self,
        query: str,
        results: list[dict[str, Any]],
    ) -> list[str]:
        """Generate follow-up search suggestions based on query and results.

        Args:
            query: The query that was executed.
            results: Search results returned.

        Returns:
            List of suggested follow-up queries.
        """
        suggestions: list[str] = []

        if results:
            suggestions.append(f"Show similar to result #1")

            # Suggest filtering by the most common asset type in results
            asset_types = [r.get("asset_type", "unknown") for r in results if r.get("asset_type") != "unknown"]
            if asset_types:
                top_type = max(set(asset_types), key=asset_types.count)
                suggestions.append(f"Filter by {top_type}")

            suggestions.append("Search in audio instead")
        else:
            suggestions.append("Try a broader search term")
            suggestions.append("Search in a different modality")

        # Add temporal suggestion
        suggestions.append(f"Show '{query}' from yesterday")

        return suggestions

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _refine_query(self, query: str, history: list[str]) -> str:
        """Merge keywords from the last 3 history messages into the query.

        Handles contextual references like "similar ones" or "from yesterday"
        by combining keywords from prior context.
        """
        if not history:
            return query

        # Take last 3 messages
        recent = history[-3:]

        # Check if current query is a contextual follow-up (short or referential)
        query_words = self._extract_keywords(query)
        is_followup = len(query_words) <= 2 or any(
            w in query.lower() for w in ["similar", "same", "those", "them", "more", "another"]
        )

        if not is_followup:
            return query

        # Extract keywords from history and merge
        history_keywords: list[str] = []
        for msg in recent:
            history_keywords.extend(self._extract_keywords(msg))

        # Deduplicate while preserving order
        seen: set[str] = set()
        merged: list[str] = []
        # Current query keywords first
        for kw in query_words:
            if kw not in seen:
                seen.add(kw)
                merged.append(kw)
        # Then history keywords
        for kw in history_keywords:
            if kw not in seen:
                seen.add(kw)
                merged.append(kw)

        # Check for temporal references in the current query
        temporal = self._extract_temporal(query)
        if temporal:
            merged.append(temporal)

        refined = " ".join(merged) if merged else query
        logger.info("Refined query: %r → %r", query, refined)
        return refined

    @staticmethod
    def _extract_keywords(text: str) -> list[str]:
        """Extract meaningful keywords from a text string."""
        words = re.findall(r"[a-zA-Z0-9]+", text.lower())
        return [w for w in words if w not in _STOP_WORDS and len(w) > 1]

    @staticmethod
    def _extract_temporal(text: str) -> str:
        """Extract temporal reference from text."""
        text_lower = text.lower()
        for phrase, label in _TEMPORAL_KEYWORDS.items():
            if phrase in text_lower:
                return label
        return ""
