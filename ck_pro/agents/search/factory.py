"""
Search Engine Factory for CognitiveKernel-Pro
Strict factory pattern - Let it crash, no fallbacks
"""

from typing import Dict, Type
from .base import BaseSearchEngine, SearchEngine, SearchEngineError
from .google_search import GoogleSearchEngine
from .duckduckgo_search import DuckDuckGoSearchEngine


class SearchEngineFactory:
    """Factory for creating search engines - STRICT, NO FALLBACKS"""

    # Registry of available search engines - ONLY TWO
    _engines: Dict[SearchEngine, Type[BaseSearchEngine]] = {
        SearchEngine.GOOGLE: GoogleSearchEngine,
        SearchEngine.DUCKDUCKGO: DuckDuckGoSearchEngine,
    }

    # Global default backend
    _default_backend: SearchEngine = SearchEngine.GOOGLE
    
    @classmethod
    def create(cls, engine_type: SearchEngine, max_results: int = 7) -> BaseSearchEngine:
        """
        Create a search engine instance - STRICT, NO FALLBACKS

        Args:
            engine_type: SearchEngine enum value
            max_results: Maximum number of results

        Returns:
            BaseSearchEngine instance

        Raises:
            SearchEngineError: If engine creation fails - LET IT CRASH!
        """
        if not isinstance(engine_type, SearchEngine):
            raise SearchEngineError(f"Invalid engine type: {engine_type}. Must be SearchEngine enum.")

        engine_class = cls._engines.get(engine_type)
        if not engine_class:
            raise SearchEngineError(f"No implementation for engine: {engine_type}")

        try:
            return engine_class(max_results=max_results)
        except Exception as e:
            raise SearchEngineError(f"Failed to create {engine_type.value} search engine: {str(e)}") from e

    @classmethod
    def create_default(cls, max_results: int = 7) -> BaseSearchEngine:
        """Create a search engine using the default backend"""
        return cls.create(cls._default_backend, max_results)

    @classmethod
    def set_default_backend(cls, engine_type: SearchEngine) -> None:
        """Set the global default search backend"""
        if not isinstance(engine_type, SearchEngine):
            raise SearchEngineError(f"Invalid engine type: {engine_type}. Must be SearchEngine enum.")
        cls._default_backend = engine_type

    @classmethod
    def get_default_backend(cls) -> SearchEngine:
        """Get the current default search backend"""
        return cls._default_backend

    @classmethod
    def list_supported_engines(cls) -> list[SearchEngine]:
        """List all supported search engines"""
        return list(cls._engines.keys())
