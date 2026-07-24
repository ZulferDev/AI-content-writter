"""Pydantic models for AI Pipeline."""

from pydantic import BaseModel, Field
from typing import Optional


class ContentIdea(BaseModel):
    """Single content idea from ide agent."""
    title: str
    alt_text_image: str
    reason: str
    purpose: str
    suggested_categories: list[str] = Field(default_factory=list)


class IdeationOutput(BaseModel):
    """Output from ideation task."""
    ideas: list[ContentIdea]


class ResearchSummary(BaseModel):
    """Research summary for a single idea."""
    ide_index: int
    title: str
    sources: list[str] = Field(default_factory=list)
    summary: str


class SubAgentScore(BaseModel):
    """Score from a single review sub-agent."""
    name: str
    score: float = Field(ge=1, le=10)
    notes: str = Field(default="")


class ReviewResult(BaseModel):
    """Review result for a single article."""
    article_title: str
    scores: list[SubAgentScore]
    total_score: float
    max_score: float = 50.0
    threshold: float = 40.0
    needs_editing: bool


class ReviewData(BaseModel):
    """Review data to store in Supabase. Matches actual LLM output shape."""
    scores: dict[str, float]
    final_weighted_score: float
    max_score: float = 10.0
    threshold: float = 8.0
    needs_editing: bool
    feedback: dict = Field(default_factory=lambda: {"ai_actions": [], "user_actions": []})
    summary: str = Field(default="")


class FinalArticle(BaseModel):
    """Final article ready for Supabase insert. Matches actual LLM output shape."""
    title: str
    slug: str = ""
    description: str
    content: str
    categories: list[str] = Field(default_factory=list)
    author: str = Field(default="Tim Pelajarsenja")
    editor: str = Field(default="Fajar Hadi Tama")
    alt_text_image: str = Field(default="")
    ai_generated: bool = Field(default=True)
    is_draft: bool = Field(default=True)
    review_score: float = 0.0
    review_data: ReviewData

    def ensure_slug(self) -> str:
        """Generate slug if empty."""
        if not self.slug or self.slug.strip() == "":
            from utils.supabase_client import SupabaseClient
            self.slug = SupabaseClient.generate_slug(self.title)
        return self.slug
