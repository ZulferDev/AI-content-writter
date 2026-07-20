"""SearXNG search tool for AI Pipeline."""

import logging
import os
from typing import Type, Union, Any

import httpx
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

SEARXNG_BASE_URL = os.environ.get("SEARXNG_BASE_URL", "http://localhost:8888")


# ---- Input Schemas ----

class SearxngSearchInput(BaseModel):
    query: str = Field(description="Search query string")
    max_results: int = Field(default=30, description="Maximum number of results to return")


class SearxngMultiSearchInput(BaseModel):
    queries: Any = Field(
        description="Comma-separated string of search queries OR a list of search query strings"
    )
    max_results_per_query: int = Field(
        default=15, description="Max results per query"
    )


# ---- CrewAI Tools ----

class SearxngSearchTool(BaseTool):
    name: str = "searxng_search"
    description: str = (
        "Search the web using SearXNG. Returns a list of results with title, url, and snippet. "
        "Use this to find sources and references for content research."
    )
    args_schema: Type[BaseModel] = SearxngSearchInput

    def _run(self, query: str, max_results: int = 30) -> str:
        params = {
            "q": query,
            "format": "json",
            "categories": "general",
            "language": "id",
        }

        try:
            with httpx.Client(timeout=30) as client:
                resp = client.get(f"{SEARXNG_BASE_URL}/search", params=params)
                resp.raise_for_status()
                data = resp.json()
        except httpx.ConnectError:
            raise RuntimeError(
                f"SearXNG server tidak tersedia di {SEARXNG_BASE_URL}. "
                "Pastikan SearXNG server berjalan. Pipeline dihentikan."
            )
        except httpx.HTTPStatusError as e:
            raise RuntimeError(
                f"SearXNG HTTP error {e.response.status_code}: {e}. "
                "Pipeline dihentikan."
            )
        except Exception as e:
            raise RuntimeError(
                f"SearXNG search error: {e}. Pipeline dihentikan."
            )

        results = []
        for item in data.get("results", [])[:max_results]:
            results.append(
                {
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "snippet": item.get("content", ""),
                }
            )

        logger.info("SearXNG: found %d results for query '%s'", len(results), query)

        if not results:
            return f"Tidak ditemukan hasil untuk query: {query}"

        lines = [f"Hasil pencarian untuk: {query}\n"]
        for i, r in enumerate(results, 1):
            lines.append(f"{i}. {r['title']}")
            lines.append(f"   URL: {r['url']}")
            lines.append(f"   Snippet: {r['snippet']}\n")

        return "\n".join(lines)


class SearxngMultiSearchTool(BaseTool):
    name: str = "searxng_multi_search"
    description: str = (
        "Search multiple queries using SearXNG and deduplicate results by URL. "
        "Use this when you need to research a topic from multiple angles."
    )
    args_schema: Type[BaseModel] = SearxngMultiSearchInput

    def _run(self, queries: Any, max_results_per_query: int = 15) -> str:
        if isinstance(queries, list):
            query_list = [str(q).strip() for q in queries if str(q).strip()]
        elif isinstance(queries, str):
            query_list = [q.strip() for q in queries.split(",") if q.strip()]
        else:
            query_list = [str(queries).strip()]
        
        seen_urls: set[str] = set()
        all_results: list[dict] = []
        errors: list[str] = []

        for query in query_list:
            params = {
                "q": query,
                "format": "json",
                "categories": "general",
                "language": "id",
            }
            try:
                with httpx.Client(timeout=30) as client:
                    resp = client.get(f"{SEARXNG_BASE_URL}/search", params=params)
                    resp.raise_for_status()
                    data = resp.json()
            except httpx.ConnectError:
                raise RuntimeError(
                    f"SearXNG server tidak tersedia di {SEARXNG_BASE_URL}. "
                    "Pastikan SearXNG server berjalan. Pipeline dihentikan."
                )
            except Exception as e:
                errors.append(f"Query '{query}': {e}")
                logger.warning("SearXNG search error for query '%s': %s", query, e)
                continue

            for item in data.get("results", [])[:max_results_per_query]:
                url = item.get("url", "")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    all_results.append(
                        {
                            "title": item.get("title", ""),
                            "url": url,
                            "snippet": item.get("content", ""),
                        }
                    )

        logger.info(
            "Total unique results from %d queries: %d", len(query_list), len(all_results)
        )

        if errors:
            logger.warning("SearXNG errors encountered: %s", "; ".join(errors))

        if not all_results:
            return f"Tidak ditemukan hasil dari {len(query_list)} query"

        lines = [f"Hasil pencarian gabungan dari {len(query_list)} query:\n"]
        for i, r in enumerate(all_results, 1):
            lines.append(f"{i}. {r['title']}")
            lines.append(f"   URL: {r['url']}")
            lines.append(f"   Snippet: {r['snippet']}\n")

        return "\n".join(lines)
