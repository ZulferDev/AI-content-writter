"""Tests for main.py utility functions."""

import json
import pytest
from main import strip_mdx_frontmatter, parse_json_from_output


class TestStripMdxFrontmatter:
    def test_strips_codeblock_wrapper(self):
        input_text = "```mdx\n# Hello\n\nSome content\n```"
        result = strip_mdx_frontmatter(input_text)
        assert "# Hello" not in result
        assert "Some content" in result

    def test_strips_yaml_frontmatter(self):
        input_text = "---\ntitle: Test\nslug: test\n---\n\n# Hello\n\nBody here"
        result = strip_mdx_frontmatter(input_text)
        assert "title: Test" not in result
        assert "Body here" in result

    def test_strips_leading_h1(self):
        input_text = "# Hello\n\nBody content"
        result = strip_mdx_frontmatter(input_text)
        assert "# Hello" not in result
        assert "Body content" in result

    def test_returns_empty_string(self):
        assert strip_mdx_frontmatter("") == ""
        assert strip_mdx_frontmatter(None) is None

    def test_handles_plain_text(self):
        text = "Just some plain text without any formatting"
        assert strip_mdx_frontmatter(text) == text

    def test_strips_backtick_only(self):
        input_text = "```\n# Hello\n\nContent\n```"
        result = strip_mdx_frontmatter(input_text)
        assert "Content" in result


class TestParseJsonFromOutput:
    def test_extracts_json_from_text(self):
        output = "Here is the result: {\"title\": \"Test\", \"score\": 8.5}"
        result = parse_json_from_output(output)
        assert result == {"title": "Test", "score": 8.5}

    def test_raises_on_no_json(self):
        with pytest.raises(ValueError, match="Could not parse JSON"):
            parse_json_from_output("No JSON here at all")

    def test_handles_nested_json(self):
        output = 'Result: {"outer": {"inner": [1, 2, 3]}}'
        result = parse_json_from_output(output)
        assert result["outer"]["inner"] == [1, 2, 3]


