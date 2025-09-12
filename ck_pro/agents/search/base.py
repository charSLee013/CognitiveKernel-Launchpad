"""
Base search engine interface for CognitiveKernel-Pro
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class SearchEngine(str, Enum):
    """Supported search engines - strict enum constraint"""
    GOOGLE = "google"
    DUCKDUCKGO = "duckduckgo"


class SearchResult(BaseModel):
    """Standardized search result format with Pydantic validation"""
    title: str = Field(..., min_length=1, description="Search result title")
    url: str = Field(..., min_length=1, description="Search result URL")
    description: str = Field(default="", description="Search result description")

    class Config:
        # Automatically strip whitespace
        str_strip_whitespace = True


class BaseSearchEngine(ABC):
    """Abstract base class for search engines - Let it crash principle"""

    def __init__(self, max_results: int = 7):
        if max_results <= 0:
            raise ValueError("max_results must be positive")
        self.max_results = max_results

    @abstractmethod
    def search(self, query: str) -> List[SearchResult]:
        """
        Perform search and return standardized results

        Args:
            query: Search query string

        Returns:
            List of SearchResult objects

        Raises:
            SearchEngineError: If search fails - LET IT CRASH!
        """
        pass

    @property
    @abstractmethod
    def engine_type(self) -> SearchEngine:
        """Return the search engine type enum"""
        pass


class SearchEngineError(Exception):
    """Base exception for search engine errors"""
    pass


class SearchEngineUnavailableError(SearchEngineError):
    """Raised when search engine is not available"""
    pass


class SearchEngineTimeoutError(SearchEngineError):
    """Raised when search times out"""
    pass
