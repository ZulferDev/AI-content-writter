"""Supabase REST API client for AI Pipeline."""

import os
import re
import httpx


class SupabaseClient:
    """Minimal Supabase REST API client using service role key."""

    def __init__(self):
        self.url = os.environ.get("SUPABASE_URL", "")
        self.key = os.environ.get("SUPABASE_SERVICE_KEY", "")
        if not self.url or not self.key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
        self.rest_url = f"{self.url}/rest/v1"
        self.headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }

    def get_existing_titles(self) -> list[str]:
        """Fetch all existing blog post titles (for deduplication)."""
        with httpx.Client(timeout=30) as client:
            resp = client.get(
                f"{self.rest_url}/blog_posts",
                headers=self.headers,
                params={"select": "title", "order": "created_at.desc"},
            )
            resp.raise_for_status()
            data = resp.json()
            return [item["title"] for item in data]

    def get_existing_articles(self) -> list[dict]:
        """Fetch all existing articles with title, slug, and categories."""
        with httpx.Client(timeout=30) as client:
            resp = client.get(
                f"{self.rest_url}/blog_posts",
                headers=self.headers,
                params={"select": "title,slug,categories"},
            )
            resp.raise_for_status()
            return resp.json()

    def insert_blog_post(self, post: dict) -> dict:
        """Insert a new blog post. Returns the inserted row."""
        with httpx.Client(timeout=30) as client:
            resp = client.post(
                f"{self.rest_url}/blog_posts",
                headers=self.headers,
                json=post,
            )
            resp.raise_for_status()
            data = resp.json()
            return data[0] if isinstance(data, list) else data

    def insert_many_blog_posts(self, posts: list[dict]) -> list[dict]:
        """Insert multiple blog posts. Returns inserted rows."""
        with httpx.Client(timeout=60) as client:
            resp = client.post(
                f"{self.rest_url}/blog_posts",
                headers=self.headers,
                json=posts,
            )
            resp.raise_for_status()
            data = resp.json()
            return data if isinstance(data, list) else [data]

    @staticmethod
    def generate_slug(title: str) -> str:
        """Generate URL-safe slug from title."""
        slug = title.lower()
        slug = re.sub(r"[^a-z0-9]+", "-", slug)
        slug = slug.strip("-")
        return slug
