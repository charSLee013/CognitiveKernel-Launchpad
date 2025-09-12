#

from .utils import KwargsInitializable, rprint

class Tool(KwargsInitializable):
    def __init__(self, **kwargs):
        self.name = ""
        super().__init__(**kwargs)

    def get_function_definition(self, short: bool):
        raise NotImplementedError("To be implemented")

    def __call__(self, *args, **kwargs):
        raise NotImplementedError("To be implemented")

# --
# useful tools

class StopResult(dict):
    pass

class StopTool(Tool):
    def __init__(self, agent=None):
        super().__init__(name="stop")
        self.agent = agent

    def get_function_definition(self, short: bool):
        if short:
            return """- def stop(output: str, log: str) -> Dict:  # Finalize and formalize the answer when the task is complete."""
        else:
            return """- stop
```python
def stop(output: str, log: str) -> dict:
    \""" Finalize and formalize the answer when the task is complete.
    Args:
        output (str): The concise, well-formatted final answer to the task.
        log (str): Brief notes or reasoning about how the answer was determined.
    Returns:
        dict: A dictionary with the following structure:
            {
                'output': <str>  # The well-formatted answer, strictly following any specified output format.
                'log': <str>     # Additional notes, such as steps taken, issues encountered, or relevant context.
            }
    Examples:
        >>> answer = stop(output="Inter Miami", log="Task completed. The answer was found using official team sources.")
        >>> print(answer)
    \"""
```"""

    def __call__(self, output: str, log: str):
        ret = StopResult(output=output, log=log)
        if self.agent is not None:
            self.agent.put_final_result(ret)  # mark end and put final result
        return ret

class AskLLMTool(Tool):
    def __init__(self, llm=None):
        super().__init__(name="ask_llm")
        self.llm = llm

    def set_llm(self, llm):
        self.llm = llm

    def get_function_definition(self, short: bool):
        if short:
            return """- def ask_llm(query: str) -> str:  # Directly query the language model for tasks that do not require external tools."""
        else:
            return """- ask_llm
```python
def ask_llm(query: str) -> str:
    \""" Directly query the language model for tasks that do not require external tools.
    Args:
        query (str): The specific question or instruction for the LLM.
    Returns:
        str: The LLM's generated response.
    Notes:
        - Use this function for fact-based or reasoning tasks that can be answered without web search or external data.
        - Phrase the query clearly and specifically.
    Examples:
        >>> answer = ask_llm(query="What is the capital city of the USA?")
        >>> print(answer)
    \"""
```"""

    def __call__(self, query: str):
        messages = [{"role": "system", "content": "You are a helpful assistant. Answer the user's query with your internal knowledge. Ensure to follow the required output format if specified."}, {"role": "user", "content": query}]
        response = self.llm(messages)
        return response

class SimpleSearchTool(Tool):
    """
    Simple web search tool for CognitiveKernel-Pro

    Supports exactly TWO search engines:
    - "google": Built-in Google search implementation (no external dependencies)
    - "duckduckgo": DuckDuckGo search using external ddgs library

    The tool follows strict "let it crash" principle - errors are raised immediately
    rather than being silently handled or falling back to alternative engines.

    Args:
        llm: Language model instance (optional)
        max_results: Maximum number of search results (1-100, default: 7)
        list_enum: Whether to enumerate results with numbers (default: True)
        backend: Search engine backend ("google" | "duckduckgo" | None for default)

    Raises:
        ValueError: If backend is not "google" or "duckduckgo"
        RuntimeError: If search engine initialization fails
        SearchEngineError: If search operation fails

    Example:
        # Use default search engine (google)
        tool = SimpleSearchTool()

        # Explicitly specify search engine
        tool = SimpleSearchTool(backend="duckduckgo")

        # Perform search
        results = tool("Python programming")
    """
    def __init__(self, llm=None, max_results=7, list_enum=True, backend=None, **kwargs):
        super().__init__(name="simple_web_search")
        self.llm = llm
        self.max_results = max_results
        self.list_enum = list_enum
        self.backend = backend  # None means use configured default
        self.search_engine = None
        self._initialize_search_engine()
        # --

    def _initialize_search_engine(self):
        """Initialize search engine using factory pattern - STRICT, NO FALLBACKS"""
        try:
            from .search.factory import SearchEngineFactory
            from .search.config import SearchConfigManager
            from .search.base import SearchEngine

            if self.backend is None:
                # Use configured default backend
                self.search_engine = SearchEngineFactory.create_default(max_results=self.max_results)
            else:
                # Convert string backend to enum and use explicitly specified backend
                if isinstance(self.backend, str):
                    try:
                        engine_enum = SearchEngine(self.backend.lower())
                    except ValueError:
                        raise ValueError(f"Invalid search backend: {self.backend}. Must be one of: {[e.value for e in SearchEngine]}")
                else:
                    engine_enum = self.backend

                self.search_engine = SearchEngineFactory.create(
                    engine_type=engine_enum,
                    max_results=self.max_results
                )
        except Exception as e:
            # LET IT CRASH - don't hide the error
            raise RuntimeError(f"Failed to initialize search engine {self.backend or 'default'}: {e}") from e

    def set_llm(self, llm):
        self.llm = llm  # might be useful for formatting?

    def get_function_definition(self, short: bool):
            if short:
                return """- def simple_web_search(query: str) -> str:  # Perform a quick web search using a search engine for straightforward information needs."""
            else:
                return """- simple_web_search
```python
def simple_web_search(query: str) -> str:
    \""" Perform a quick web search using a search engine for straightforward information needs.
    Args:
        query (str): A simple, well-phrased search term or question.
    Returns:
        str: A string containing search results, including titles, URLs, and snippets.
    Notes:
        - Use for quick lookups or when you need up-to-date information.
        - Avoid complex or multi-step queries; keep the query simple and direct.
        - Do not use for tasks requiring deep reasoning or multi-source synthesis.
    Examples:
        >>> answer = simple_web_search(query="latest iPhone")
        >>> print(answer)
    \"""
```"""

    def __call__(self, query: str):
        """Execute search - LET IT CRASH if there are issues"""
        if not self.search_engine:
            raise RuntimeError("Search engine not initialized. This should not happen.")

        # Use the new search engine interface - let exceptions propagate
        results = self.search_engine.search(query)

        # Convert to the expected format
        search_results = []
        for result in results:
            search_results.append({
                "title": result.title,
                "link": result.url,
                "content": result.description
            })

        if len(search_results) == 0:
            ret = "Search Results: No results found! Try a less restrictive/simpler query."
        elif self.list_enum:
            ret = "Search Results:\n" + "\n".join([f"({ii}) title={repr(vv['title'])}, link={repr(vv['link'])}, content={repr(vv['content'])}" for ii, vv in enumerate(search_results)])
        else:
            ret = "Search Results:\n" + "\n".join([f"- title={repr(vv['title'])}, link={repr(vv['link'])}, content={repr(vv['content'])}" for ii, vv in enumerate(search_results)])
        return ret
