"""Tests for Pydantic models."""

import pytest
from utils.models import FinalArticle, ReviewData, ContentIdea, SubAgentScore


class TestFinalArticle:
    def test_default_slug_is_empty(self):
        data = {
            "title": "Test Article",
            "description": "A test",
            "content": "Body",
            "categories": ["Pendidikan"],
            "review_score": 8.5,
            "review_data": {
                "scores": {"eeat_trust": 8, "people_first": 9, "seo_ux": 7},
                "final_weighted_score": 8.5,
                "needs_editing": False,
                "feedback": [],
                "summary": "Good article",
            },
        }
        article = FinalArticle(**data)
        assert article.slug == ""
        assert article.author == "Tim Pelajarsenja"
        assert article.editor == "Fajar Hadi Tama"
        assert article.ai_generated is True
        assert article.is_draft is True

    def test_ensure_slug_generates_slug(self):
        data = {
            "title": "Cara Belajar Efektif di Rumah",
            "description": "A test",
            "content": "Body",
            "review_score": 8.0,
            "review_data": {
                "scores": {"eeat_trust": 8, "people_first": 8, "seo_ux": 8},
                "final_weighted_score": 8.0,
                "needs_editing": False,
                "feedback": [],
                "summary": "Solid article",
            },
        }
        article = FinalArticle(**data)
        slug = article.ensure_slug()
        assert slug == "cara-belajar-efektif-di-rumah"
        assert article.slug == slug

    def test_custom_author(self):
        data = {
            "title": "Test",
            "description": "Desc",
            "content": "Body",
            "author": "TIM PELAJARSENJA",
            "review_score": 7.5,
            "review_data": {
                "scores": {"eeat_trust": 7, "people_first": 8, "seo_ux": 7},
                "final_weighted_score": 7.5,
                "needs_editing": True,
                "feedback": ["Add more sources"],
                "summary": "Needs work",
            },
        }
        article = FinalArticle(**data)
        assert article.author == "TIM PELAJARSENJA"
        assert article.editor == "Fajar Hadi Tama"

    def test_review_data_structure(self):
        data = {
            "title": "Test",
            "description": "Desc",
            "content": "Body",
            "review_score": 8.0,
            "review_data": {
                "scores": {"eeat_trust": 8, "people_first": 8, "seo_ux": 8},
                "final_weighted_score": 8.0,
                "max_score": 10.0,
                "threshold": 8.0,
                "needs_editing": False,
                "feedback": [],
                "summary": "Pass",
            },
        }
        article = FinalArticle(**data)
        assert article.review_data.scores["eeat_trust"] == 8
        assert article.review_data.final_weighted_score == 8.0
        assert article.review_data.threshold == 8.0


class TestContentIdea:
    def test_default_categories(self):
        idea = ContentIdea(
            title="Test Idea",
            alt_text_image="Alt text",
            reason="Because",
            purpose="To test",
        )
        assert idea.suggested_categories == []

    def test_with_categories(self):
        idea = ContentIdea(
            title="Test",
            alt_text_image="Alt",
            reason="Reason",
            purpose="Purpose",
            suggested_categories=["Pendidikan", "Tips Belajar"],
        )
        assert len(idea.suggested_categories) == 2


class TestSubAgentScore:
    def test_score_bounds(self):
        with pytest.raises(ValueError):
            SubAgentScore(name="test", score=11, notes="Too high")

        with pytest.raises(ValueError):
            SubAgentScore(name="test", score=0, notes="Too low")

    def test_valid_score(self):
        score = SubAgentScore(name="EEAT Review", score=8, notes="Good")
        assert score.name == "EEAT Review"
        assert score.score == 8
