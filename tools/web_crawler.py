"""Crawl4AI web crawler tool for AI Pipeline."""

import asyncio
import logging
from typing import Type

from crewai.tools import BaseTool
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

DEFAULT_BROWSER_CONFIG = BrowserConfig(
    headless=True,
    verbose=False,
)

DEFAULT_CRAWLER_CONFIG = CrawlerRunConfig(
    cache_mode="BYPASS",
    word_count_threshold=10,
)


# ---- Input Schemas ----

class WebCrawlInput(BaseModel):
    urls: str = Field(
        description="Comma-separated list of URLs to crawl"
    )
    timeout_per_url: int = Field(
        default=30, description="Timeout per URL in seconds"
    )
    max_chars_per_url: int = Field(
        default=5000, description="Max characters to extract per URL"
    )


# ---- Internal async helpers ----

async def _crawl_single(url: str, timeout: int = 30) -> dict:
    try:
        async with AsyncWebCrawler(config=DEFAULT_BROWSER_CONFIG) as crawler:
            result = await asyncio.wait_for(
                crawler.arun(url=url, config=DEFAULT_CRAWLER_CONFIG),
                timeout=timeout,
            )
            if result.success and result.markdown:
                markdown = result.markdown
                if isinstance(markdown, dict):
                    markdown = markdown.get("raw_markdown", "")
                return {"url": url, "markdown": markdown, "success": True, "error": None}
            else:
                error_msg = getattr(result, "error_message", "Unknown error")
                return {"url": url, "markdown": "", "success": False, "error": error_msg}
    except asyncio.TimeoutError:
        logger.warning("Timeout crawling %s", url)
        return {"url": url, "markdown": "", "success": False, "error": "Timeout"}
    except Exception as e:
        logger.warning("Error crawling %s: %s", url, e)
        return {"url": url, "markdown": "", "success": False, "error": str(e)}


async def _crawl_urls(
    urls: list[str], timeout_per_url: int = 30, max_concurrent: int = 3
) -> list[dict]:
    semaphore = asyncio.Semaphore(max_concurrent)

    async def _limited_crawl(url: str) -> dict:
        async with semaphore:
            return await _crawl_single(url, timeout_per_url)

    tasks = [_limited_crawl(url) for url in urls]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    successful = []
    for r in results:
        if isinstance(r, Exception):
            logger.warning("Crawl exception: %s", r)
            continue
        if r["success"]:
            successful.append(r)

    logger.info("Crawl4AI: %d/%d URLs crawled successfully", len(successful), len(urls))
    return successful


# ---- CrewAI Tool ----

class WebCrawlTool(BaseTool):
    name: str = "web_crawl"
    description: str = (
        "Crawl URLs and extract their content as markdown. "
        "Provide a comma-separated list of URLs. "
        "Returns extracted content from each successfully crawled URL."
    )
    args_schema: Type[BaseModel] = WebCrawlInput

    def _run(self, urls: str, timeout_per_url: int = 30, max_chars_per_url: int = 5000) -> str:
        url_list = [u.strip() for u in urls.split(",") if u.strip()]

        if not url_list:
            raise RuntimeError("Tidak ada URL yang diberikan. Pipeline dihentikan.")

        try:
            successful = asyncio.run(_crawl_urls(url_list, timeout_per_url))
        except Exception as e:
            raise RuntimeError(
                f"Crawl4AI gagal memproses URL: {e}. Pipeline dihentikan."
            )

        if not successful:
            raise RuntimeError(
                f"Gagal crawl {len(url_list)} URL. "
                "Pastikan URL valid dan bisa diakses. Pipeline dihentikan."
            )

        parts = []
        for r in successful:
            markdown = r.get("markdown", "")
            if markdown:
                truncated = markdown[:max_chars_per_url]
                parts.append(f"--- Sumber: {r['url']} ---\n{truncated}\n")

        if not parts:
            raise RuntimeError(
                f"Berhasil crawl {len(successful)} URL, "
                "namun tidak ada konten yang diekstrak. Pipeline dihentikan."
            )

        combined = "\n".join(parts)
        return combined[:50000]
