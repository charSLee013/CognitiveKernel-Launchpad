"""
Search configuration management for CognitiveKernel-Pro
Strict configuration with Pydantic validation
"""

from pydantic import BaseModel, Field, validator
from .base import SearchEngine
from .factory import SearchEngineFactory


class SearchConfig(BaseModel):
    """Search configuration with Pydantic validation"""
    backend: SearchEngine = Field(default=SearchEngine.GOOGLE, description="Search engine backend")
    max_results: int = Field(default=7, ge=1, le=100, description="Maximum search results")

    @validator('backend')
    def validate_backend(cls, v):
        """Validate search engine backend"""
        if not isinstance(v, SearchEngine):
            # Try to convert string to enum
            if isinstance(v, str):
                try:
                    return SearchEngine(v.lower())
                except ValueError:
                    raise ValueError(f"Invalid search backend: {v}. Must be one of: {[e.value for e in SearchEngine]}")
            raise ValueError(f"Invalid search backend type: {type(v)}")
        return v


class SearchConfigManager:
    """Manages global search configuration - STRICT, NO AUTO-FALLBACKS"""

    _config: SearchConfig = SearchConfig()
    _initialized: bool = False

    @classmethod
    def initialize(cls, config: SearchConfig) -> None:
        """
        Initialize search configuration with validated config

        Args:
            config: SearchConfig instance

        Raises:
            SearchEngineError: If configuration is invalid
        """
        cls._config = config
        SearchEngineFactory.set_default_backend(config.backend)
        cls._initialized = True
        print(f"🔍 Search backend configured: {config.backend.value}")

    @classmethod
    def initialize_from_backend(cls, backend: SearchEngine, max_results: int = 7) -> None:
        """
        Initialize search configuration from backend enum

        Args:
            backend: SearchEngine enum value
            max_results: Maximum search results
        """
        config = SearchConfig(backend=backend, max_results=max_results)
        cls.initialize(config)

    @classmethod
    def initialize_from_string(cls, backend_str: str, max_results: int = 7) -> None:
        """
        Initialize search configuration from backend string

        Args:
            backend_str: Search backend string (will be validated)
            max_results: Maximum search results

        Raises:
            ValueError: If backend string is invalid
        """
        config = SearchConfig(backend=backend_str, max_results=max_results)
        cls.initialize(config)

    @classmethod
    def get_config(cls) -> SearchConfig:
        """Get current search configuration"""
        return cls._config

    @classmethod
    def get_current_backend(cls) -> SearchEngine:
        """Get the current configured backend"""
        return cls._config.backend

    @classmethod
    def is_initialized(cls) -> bool:
        """Check if search configuration is initialized"""
        return cls._initialized

    @classmethod
    def reset(cls) -> None:
        """Reset configuration to default (mainly for testing)"""
        cls._config = SearchConfig()
        cls._initialized = False
        SearchEngineFactory.set_default_backend(SearchEngine.GOOGLE)
