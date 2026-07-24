#!/usr/bin/env python
"""
AI Content Pipeline - Entry Point
"""

import argparse
import json
import logging
import os
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import yaml

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("ai-pipeline")

PROJECT_ROOT = Path(__file__).parent
CONFIG_DIR = PROJECT_ROOT / "config"
OUTPUT_DIR = PROJECT_ROOT / "output"

def load_niche_config(niche: str = "pendidikan") -> dict:
    config_path = CONFIG_DIR / "niche.yaml"
    with open(config_path) as f:
        config = yaml.safe_load(f)
    return config

def strip_mdx_frontmatter(content: str) -> str:
    if not content: return content
    text = content.strip()
    text = re.sub(r"^```(?:mdx)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    text = re.sub(r"^---\s*\n(.*?)\n---\s*\n", "", text, flags=re.DOTALL)
    text = re.sub(r"^#\s+.+\n+", "", text, count=1)
    return text.strip()

def save_output(articles: list[dict], output_path: Path):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)

def insert_to_supabase(articles: list[dict]) -> list[dict]:
    from utils.supabase_client import SupabaseClient
    client = SupabaseClient()
    return client.insert_many_blog_posts(articles)

def parse_json_from_output(output: str) -> dict:
    """Extract JSON from crew output."""
    json_match = re.search(r"\{.*\}", output, re.DOTALL)
    if json_match:
        return json.loads(json_match.group())
    raise ValueError(f"Could not parse JSON from output: {output}")

def prepare_article(article: dict, allowed_categories: list[str] | None = None) -> dict | None:
    """Clean and validate article before insert. Returns None if duplicate."""
    from utils.supabase_client import SupabaseClient

    article["content"] = strip_mdx_frontmatter(article.get("content", ""))
    article.setdefault("ai_generated", True)
    article.setdefault("is_draft", True)
    article.setdefault("author", "Tim Pelajarsenja")
    article.setdefault("editor", "Fajar Hadi Tama")

    slug = article.get("slug", "")
    if not slug or slug.strip() == "":
        article["slug"] = SupabaseClient.generate_slug(article.get("title", "untitled"))

    if not article.get("pub_date"):
        article["pub_date"] = datetime.now(timezone.utc).isoformat()

    categories = article.get("categories", [])
    if allowed_categories:
        valid = [c for c in categories if c in allowed_categories]
        if not valid:
            logger.warning(f"No valid categories for '{article.get('title')}'. Falling back to first allowed category.")
            valid = [allowed_categories[0]]
        article["categories"] = valid

    return article

def run_pipeline(niche: str):
    niche_config = load_niche_config(niche)

    from crew.content_crew import IdeationCrew, ArticleCrew
    from utils.supabase_client import SupabaseClient

    supabase = SupabaseClient()

    existing_articles = supabase.get_existing_articles()
    existing_titles = [a["title"] for a in existing_articles]
    existing_slugs = {a.get("slug", "") for a in existing_articles}
    logger.info(f"Found {len(existing_titles)} existing articles for deduplication")

    allowed_categories = niche_config.get("categories", [])
    category_counts = Counter()
    for article in existing_articles:
        for cat in (article.get("categories") or []):
            if cat in allowed_categories:
                category_counts[cat] += 1
    category_distribution = "\n".join(
        f"  - {cat}: {category_counts.get(cat, 0)} artikel"
        for cat in allowed_categories
    )

    phase1_inputs = {
        "niche": niche,
        "target_audience": niche_config.get("target_audience", "pelajar Indonesia"),
        "existing_content_list": "\n".join(existing_titles) if existing_titles else "Belum ada konten.",
        "allowed_categories": ", ".join(allowed_categories),
    }
    phase1_result = IdeationCrew().crew().kickoff(inputs=phase1_inputs)
    idea = parse_json_from_output(str(phase1_result))

    all_articles = []
    errors = []

    try:
        logger.info(f"Processing article: {idea.get('title', 'Untitled')}")
        article_inputs = {
            "title": idea["title"],
            "purpose": idea.get("purpose", ""),
            "target_audience": niche_config.get("target_audience", "pelajar Indonesia"),
            "suggested_categories": ", ".join(idea.get("suggested_categories", [])),
            "research_summary": idea.get("research", ""),
            "alt_text_image": idea.get("alt_text_image", ""),
        }
        result = ArticleCrew().crew().kickoff(inputs=article_inputs)
        article = parse_json_from_output(str(result))

        article = prepare_article(article, allowed_categories)
        if article and article["slug"] not in existing_slugs:
            insert_to_supabase([article])
            existing_slugs.add(article["slug"])
            all_articles.append(article)
            logger.info(f"Article inserted successfully (slug: {article.get('slug')})")
        elif article:
            logger.warning(f"Duplicate slug '{article['slug']}' — skipping '{article.get('title')}'")
            errors.append({"title": article.get("title", "Unknown"), "error": "Duplicate slug"})
        else:
            logger.warning("Article preparation returned None — skipping")

    except Exception as e:
        logger.error(f"Failed to process article: {e}", exc_info=True)
        errors.append({"title": idea.get("title", "Unknown"), "error": str(e)})

    if all_articles:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_output(all_articles, OUTPUT_DIR / f"final_{timestamp}.json")

    if errors:
        logger.warning(f"Completed with {len(errors)} error(s)")
        save_output(errors, OUTPUT_DIR / f"errors_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")

    logger.info(f"Pipeline complete: {len(all_articles)} articles saved, {len(errors)} errors")

def main():
    parser = argparse.ArgumentParser(description="AI Content Pipeline")
    parser.add_argument("--niche", type=str, default="pendidikan")
    args = parser.parse_args()
    try:
        run_pipeline(args.niche)
    except Exception as e:
        logger.error("Pipeline failed: %s", e, exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
