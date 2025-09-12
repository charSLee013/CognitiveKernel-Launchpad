"""
Google Search Engine implementation for CognitiveKernel-Pro
Embedded anti-bot bypass techniques from googlesearch library
"""

import random
import time
from typing import List, Generator
from urllib.parse import unquote
from .base import BaseSearchEngine, SearchResult, SearchEngine, SearchEngineError

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError as e:
    raise SearchEngineError(
        "Required dependencies not installed. Install with: pip install requests beautifulsoup4"
    ) from e


def _get_random_user_agent() -> str:
    """Generate random Lynx-based user agent to avoid detection"""
    lynx_version = f"Lynx/{random.randint(2, 3)}.{random.randint(8, 9)}.{random.randint(0, 2)}"
    libwww_version = f"libwww-FM/{random.randint(2, 3)}.{random.randint(13, 15)}"
    ssl_mm_version = f"SSL-MM/{random.randint(1, 2)}.{random.randint(3, 5)}"
    openssl_version = f"OpenSSL/{random.randint(1, 3)}.{random.randint(0, 4)}.{random.randint(0, 9)}"
    return f"{lynx_version} {libwww_version} {ssl_mm_version} {openssl_version}"


def _google_search_request(query: str, num_results: int, timeout: int = 10) -> requests.Response:
    """Make Google search request with anti-bot protection"""
    response = requests.get(
        url="https://www.google.com/search",
        headers={
            "User-Agent": _get_random_user_agent(),
            "Accept": "*/*"
        },
        params={
            "q": query,
            "num": num_results + 2,  # Get extra to account for filtering
            "hl": "en",
            "gl": "us",
            "safe": "off",
        },
        timeout=timeout,
        verify=True,
        cookies={
            'CONSENT': 'PENDING+987',  # Bypasses Google consent page
            'SOCS': 'CAESHAgBEhIaAB',   # Additional consent bypass
        }
    )
    response.raise_for_status()
    return response


def _parse_google_results(html: str) -> Generator[SearchResult, None, None]:
    """Parse Google search results from HTML using precise CSS selectors"""
    soup = BeautifulSoup(html, "html.parser")
    result_blocks = soup.find_all("div", class_="ezO2md")  # Precise Google result selector

    for result in result_blocks:
        # Extract link
        link_tag = result.find("a", href=True)
        if not link_tag:
            continue

        # Extract title
        title_tag = link_tag.find("span", class_="CVA68e") if link_tag else None

        # Extract description
        description_tag = result.find("span", class_="FrIlee")

        if link_tag and title_tag:
            # Clean and decode URL
            raw_url = link_tag["href"]
            if raw_url.startswith("/url?q="):
                url = unquote(raw_url.split("&")[0].replace("/url?q=", ""))
            else:
                url = raw_url

            title = title_tag.text.strip() if title_tag else "No title"
            description = description_tag.text.strip() if description_tag else "No description"

            yield SearchResult(title=title, url=url, description=description)


class GoogleSearchEngine(BaseSearchEngine):
    """Google Search implementation with embedded anti-bot bypass techniques"""

    def __init__(self, max_results: int = 7, sleep_interval: float = 0.5):
        super().__init__(max_results)
        self.sleep_interval = sleep_interval

    @property
    def engine_type(self) -> SearchEngine:
        return SearchEngine.GOOGLE

    def search(self, query: str) -> List[SearchResult]:
        """
        Perform Google search using embedded anti-bot techniques

        Args:
            query: Search query string

        Returns:
            List of SearchResult objects

        Raises:
            SearchEngineError: If search fails - LET IT CRASH!
        """
        if not query or not query.strip():
            raise SearchEngineError("Query cannot be empty")

        try:
            # Make request with anti-bot protection
            response = _google_search_request(
                query=query.strip(),
                num_results=self.max_results,
                timeout=10
            )

            # Parse results using precise CSS selectors
            results = list(_parse_google_results(response.text))

            # Limit to requested number of results
            limited_results = results[:self.max_results]

            # Add sleep interval to avoid rate limiting
            if self.sleep_interval > 0:
                time.sleep(self.sleep_interval)

            return limited_results

        except requests.RequestException as e:
            # Network or HTTP errors
            raise SearchEngineError(f"Google search network error: {str(e)}") from e
        except Exception as e:
            # Check for anti-bot detection
            error_msg = str(e).lower()
            if any(indicator in error_msg for indicator in [
                'blocked', 'captcha', 'unusual traffic', 'rate limit', 'consent'
            ]):
                raise SearchEngineError(
                    f"Google blocked the request (anti-bot protection): {str(e)}. "
                    "Try increasing sleep_interval or using a proxy."
                ) from e
            else:
                raise SearchEngineError(f"Google search failed: {str(e)}") from e
