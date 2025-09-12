"""
Search components for CognitiveKernel-Pro
Provides unified search interface with multiple backend support
"""

from .base import BaseSearchEngine, SearchResult
from .google_search import GoogleSearchEngine
from .duckduckgo_search import DuckDuckGoSearchEngine
from .factory import SearchEngineFactory
from .config import SearchConfigManager

__all__ = [
    'BaseSearchEngine',
    'SearchResult',
    'GoogleSearchEngine',
    'DuckDuckGoSearchEngine',
    'SearchEngineFactory',
    'SearchConfigManager'
]
