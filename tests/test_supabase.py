"""Tests for Supabase client functions."""

import pytest
from utils.supabase_client import SupabaseClient


class TestGenerateSlug:
    def test_basic_slug(self):
        slug = SupabaseClient.generate_slug("Cara Belajar Efektif")
        assert slug == "cara-belajar-efektif"

    def test_slug_with_special_chars(self):
        slug = SupabaseClient.generate_slug("Tips & Trik Belajar 2026!")
        assert slug == "tips-trik-belajar-2026"

    def test_slug_handles_multiple_spaces(self):
        slug = SupabaseClient.generate_slug("A  B  C")
        assert slug == "a-b-c"

    def test_slug_strips_leading_trailing_dashes(self):
        slug = SupabaseClient.generate_slug(" -Hello- ")
        assert slug == "hello"

    def test_slug_empty_string(self):
        slug = SupabaseClient.generate_slug("!!!")
        assert slug == ""
