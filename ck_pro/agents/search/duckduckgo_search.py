"""
DuckDuckGo Search Engine implementation for CognitiveKernel-Pro
Uses external ddgs library for reliable search functionality
"""

from typing import List
from .base import BaseSearchEngine, SearchResult, SearchEngine, SearchEngineError


class DuckDuckGoSearchEngine(BaseSearchEngine):
    """DuckDuckGo Search implementation using external ddgs library"""

    def __init__(self, max_results: int = 7):
        super().__init__(max_results)
        self._ddgs = None
        self._initialize_ddgs()

    def _initialize_ddgs(self):
        """Initialize DuckDuckGo search using ddgs library"""
        try:
            from ddgs import DDGS
            self._ddgs = DDGS()
        except ImportError as e:
            raise SearchEngineError(
                "ddgs library not installed. Install with: pip install ddgs>=3.0.0"
            ) from e

    @property
    def engine_type(self) -> SearchEngine:
        return SearchEngine.DUCKDUCKGO

    def search(self, query: str) -> List[SearchResult]:
        """
        Perform DuckDuckGo search using ddgs library

        Args:
            query: Search query string

        Returns:
            List of SearchResult objects

        Raises:
            SearchEngineError: If search fails - LET IT CRASH!
        """
        if not query or not query.strip():
            raise SearchEngineError("Query cannot be empty")

        if not self._ddgs:
            raise SearchEngineError("DuckDuckGo search not initialized")

        try:
            # Use ddgs library for search
            raw_results = self._ddgs.text(
                query.strip(),
                max_results=self.max_results
            )

            # Convert to standardized format
            results = []
            for result in raw_results:
                search_result = SearchResult(
                    title=result.get('title', ''),
                    url=result.get('href', ''),
                    description=result.get('body', '')
                )
                results.append(search_result)

            return results

        except Exception as e:
            raise SearchEngineError(f"DuckDuckGo search failed: {str(e)}") from e

