"""
Tests for utility helper functions.
"""
import pytest
from src.utils.helpers import slugify, count_words, build_json_ld_software, build_json_ld_faq


def test_slugify_basic():
    """Test basic slug generation."""
    assert slugify("Hello World") == "hello-world"
    assert slugify("AI Image Generator") == "ai-image-generator"
    assert slugify("ChatGPT") == "chatgpt"


def test_slugify_special_chars():
    """Test slug generation with special characters."""
    assert slugify("Tool A & Tool B") == "tool-a-tool-b"
    assert slugify("  spaces  ") == "spaces"
    assert slugify("multiple---dashes") == "multiple-dashes"


def test_slugify_numbers():
    """Test slug with numbers."""
    assert slugify("DALL-E 3") == "dall-e-3"
    assert slugify("GPT-4o") == "gpt-4o"


def test_count_words_basic():
    """Test basic word counting."""
    assert count_words("Hello world") == 2
    assert count_words("The quick brown fox jumps") == 5


def test_count_words_empty():
    """Test word counting with empty/None input."""
    assert count_words("") == 0
    assert count_words(None) == 0


def test_count_words_punctuation():
    """Test word counting ignores punctuation."""
    assert count_words("Hello, world!") == 2
    assert count_words("One. Two. Three.") == 3


def test_build_json_ld_software():
    """Test JSON-LD SoftwareApplication schema generation."""
    tool_data = {
        "name": "TestTool",
        "description": "A test tool",
        "official_url": "https://testtool.com",
        "starting_price": 9.99,
        "rating": 4.5,
    }
    schema = build_json_ld_software(tool_data)

    assert schema["@context"] == "https://schema.org"
    assert schema["@type"] == "SoftwareApplication"
    assert schema["name"] == "TestTool"
    assert schema["offers"]["price"] == "9.99"
    assert schema["aggregateRating"]["ratingValue"] == "4.5"


def test_build_json_ld_faq():
    """Test JSON-LD FAQPage schema generation."""
    faqs = [
        {"question": "What is TestTool?", "answer": "A test tool for testing."},
        {"question": "Is it free?", "answer": "Yes, it has a free tier."},
    ]
    schema = build_json_ld_faq(faqs)

    assert schema["@context"] == "https://schema.org"
    assert schema["@type"] == "FAQPage"
    assert len(schema["mainEntity"]) == 2
    assert schema["mainEntity"][0]["@type"] == "Question"
    assert schema["mainEntity"][0]["name"] == "What is TestTool?"
    assert schema["mainEntity"][1]["acceptedAnswer"]["text"] == "Yes, it has a free tier."


def test_build_json_ld_faq_empty():
    """Test FAQ schema with empty list."""
    schema = build_json_ld_faq([])
    assert schema["mainEntity"] == []
