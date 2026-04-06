"""
Tests for the pSEO Page Assembly Engine.
Mocks LLM calls to test the assembly logic without real API calls.
"""
import json
import pytest
from unittest.mock import patch, MagicMock

from src.models.database import PSEOPage
from src.engine.page_assembler import PageAssembler


# Mock LLM response for alternatives page
MOCK_ALTERNATIVES_CONTENT = {
    "title": "Top 5 Midjourney Alternatives in 2025 [Free & Paid]",
    "meta_description": "Looking for Midjourney alternatives? We tested 5 top AI image generators to find the best options for every budget.",
    "h1": "Best Midjourney Alternatives: Top 5 Picks for 2025",
    "intro": "Midjourney is one of the most popular AI image generators, but its Discord-only interface and lack of a free tier push many users to look for alternatives. Whether you need a free option, more control over outputs, or a simpler interface, there are excellent alternatives available.",
    "why_look_for_alternatives": "The main pain points with Midjourney include its mandatory paid subscription starting at $10/month and the requirement to use Discord, which can be cumbersome for professional workflows.",
    "alternatives": [
        {
            "tool_name": "DALL-E 3",
            "slug": "dall-e-3",
            "why_choose": "DALL-E 3 offers a free tier via ChatGPT and excels at following complex prompts accurately.",
            "best_for": "Users who want free access and tight prompt control",
            "key_differentiator": "Free tier with ChatGPT integration",
            "pricing_note": "Free via ChatGPT, or $20/month with ChatGPT Plus"
        }
    ],
    "comparison_table_note": "The table above compares key features across all alternatives.",
    "conclusion": "For most users, DALL-E 3 offers the best free alternative to Midjourney. For open-source flexibility, Stable Diffusion is unmatched.",
    "faqs": [
        {
            "question": "Is there a free alternative to Midjourney?",
            "answer": "Yes, DALL-E 3 via ChatGPT offers free image generation with high quality results."
        }
    ]
}

# Mock LLM response for comparison page
MOCK_COMPARISON_CONTENT = {
    "title": "Midjourney vs DALL-E 3: Which AI Image Generator is Better?",
    "meta_description": "Comparing Midjourney vs DALL-E 3 in 2025. Detailed analysis of features, pricing, and use cases.",
    "h1": "Midjourney vs DALL-E 3: Complete 2025 Comparison",
    "intro": "Both Midjourney and DALL-E 3 are leading AI image generators, but they serve different needs.",
    "quick_verdict": {
        "choose_tool_a_if": "You prioritize artistic quality and have a budget",
        "choose_tool_b_if": "You want a free option with accurate prompt following"
    },
    "detailed_comparison": {
        "features": "Midjourney excels in artistic quality while DALL-E 3 is better at prompt accuracy.",
        "pricing": "Midjourney starts at $10/month with no free tier. DALL-E 3 is free via ChatGPT.",
        "ease_of_use": "DALL-E 3 wins for ease of use with its ChatGPT interface.",
        "use_cases": "Midjourney is best for artistic projects; DALL-E 3 for content creation."
    },
    "conclusion": "Choose Midjourney for professional artistic work; DALL-E 3 for everyday content needs.",
    "faqs": [
        {
            "question": "Which is better for beginners?",
            "answer": "DALL-E 3 is better for beginners due to its simpler interface."
        }
    ]
}

# Mock LLM response for listicle page
MOCK_LISTICLE_CONTENT = {
    "title": "10 Best AI Image Generators in 2025",
    "meta_description": "We tested the best AI image generators. Here are our top picks for quality, price, and ease of use.",
    "h1": "Best AI Image Generators 2025: Top 10 Picks",
    "intro": "AI image generators have transformed creative workflows. Here are the best options available today.",
    "selection_criteria": "We evaluated tools based on image quality, pricing, ease of use, and feature set.",
    "tools": [
        {
            "tool_name": "Midjourney",
            "slug": "midjourney",
            "badge": "Best Overall",
            "summary": "The gold standard for AI art generation.",
            "pros": ["Exceptional quality", "Active community"],
            "cons": ["No free tier", "Discord only"],
            "pricing": "From $10/month",
            "best_for": "Professional artists and designers"
        }
    ],
    "conclusion": "Midjourney leads for quality, but DALL-E 3 is the best free option.",
    "faqs": [
        {
            "question": "What is the best free AI image generator?",
            "answer": "DALL-E 3 via ChatGPT is the best free option."
        }
    ]
}


@pytest.fixture
def assembler(db_session):
    """Create a PageAssembler with test session."""
    a = PageAssembler(session=db_session)
    return a


class TestPageAssembler:

    def test_assemble_alternative_page(self, assembler, sample_tools):
        """Test generating an alternatives page."""
        with patch.object(assembler.llm, "generate_alternatives_page",
                          return_value=MOCK_ALTERNATIVES_CONTENT):
            page = assembler.assemble_alternative_page("midjourney", "ai-image-generator")

        assert page is not None
        assert page.url_path == "/alternatives/midjourney"
        assert page.page_type == "Alternative"
        assert page.primary_keyword == "Midjourney alternatives"
        assert page.title == MOCK_ALTERNATIVES_CONTENT["title"]
        assert page.meta_description == MOCK_ALTERNATIVES_CONTENT["meta_description"]
        assert page.status == "Draft"
        assert page.word_count > 0
        assert page.schema_json is not None  # FAQ schema generated
        assert page.generated_content["intro"] == MOCK_ALTERNATIVES_CONTENT["intro"]

    def test_assemble_alternative_page_idempotent(self, assembler, sample_tools):
        """Generating the same page twice should return existing page."""
        with patch.object(assembler.llm, "generate_alternatives_page",
                          return_value=MOCK_ALTERNATIVES_CONTENT):
            page1 = assembler.assemble_alternative_page("midjourney", "ai-image-generator")
            page2 = assembler.assemble_alternative_page("midjourney", "ai-image-generator")

        assert page1.id == page2.id

    def test_assemble_alternative_page_missing_tool(self, assembler, sample_tools):
        """Should return None if tool doesn't exist."""
        page = assembler.assemble_alternative_page("nonexistent-tool", "ai-image-generator")
        assert page is None

    def test_assemble_comparison_page(self, assembler, sample_tools):
        """Test generating a comparison page."""
        with patch.object(assembler.llm, "generate_comparison_page",
                          return_value=MOCK_COMPARISON_CONTENT):
            page = assembler.assemble_comparison_page("midjourney", "dall-e-3")

        assert page is not None
        assert page.url_path == "/compare/midjourney-vs-dall-e-3"
        assert page.page_type == "Comparison"
        assert "midjourney" in page.primary_keyword.lower()
        assert "dall-e 3" in page.primary_keyword.lower()

    def test_assemble_listicle_page(self, assembler, sample_tools):
        """Test generating a listicle page."""
        with patch.object(assembler.llm, "generate_listicle_page",
                          return_value=MOCK_LISTICLE_CONTENT):
            page = assembler.assemble_listicle_page("ai-image-generator")

        assert page is not None
        assert page.url_path == "/best/ai-image-generator"
        assert page.page_type == "Listicle"
        assert "ai image generator" in page.primary_keyword.lower()

    def test_publish_page(self, assembler, sample_tools):
        """Test publishing a draft page."""
        with patch.object(assembler.llm, "generate_alternatives_page",
                          return_value=MOCK_ALTERNATIVES_CONTENT):
            page = assembler.assemble_alternative_page("midjourney", "ai-image-generator")

        assert page.status == "Draft"
        success = assembler.publish_page(page.id)
        assert success is True

        # Refresh
        assembler.session.refresh(page)
        assert page.status == "Published"
        assert page.published_at is not None

    def test_batch_generate_alternatives(self, assembler, sample_tools):
        """Test batch generating alternatives for all tools in a category."""
        with patch.object(assembler.llm, "generate_alternatives_page",
                          return_value=MOCK_ALTERNATIVES_CONTENT):
            pages = assembler.batch_generate_alternatives("ai-image-generator")

        # Should generate a page for each tool in the category
        assert len(pages) > 0
        for page in pages:
            assert page.page_type == "Alternative"
            assert page.url_path.startswith("/alternatives/")

    def test_schema_json_generated(self, assembler, sample_tools):
        """Test that JSON-LD schema is properly generated from FAQs."""
        with patch.object(assembler.llm, "generate_alternatives_page",
                          return_value=MOCK_ALTERNATIVES_CONTENT):
            page = assembler.assemble_alternative_page("midjourney", "ai-image-generator")

        assert page.schema_json is not None
        assert page.schema_json.get("@type") == "FAQPage"
        assert len(page.schema_json.get("mainEntity", [])) > 0
