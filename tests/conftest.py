"""
Pytest configuration and shared fixtures for the pSEO test suite.
Uses an in-memory SQLite database for isolation.
"""
import os
import pytest

# Set test environment BEFORE importing any src modules
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["OPENAI_API_KEY"] = "test-key-not-real"
os.environ["LLM_MODEL"] = "gpt-4.1-mini"  # Any model name accepted
os.environ["SITE_URL"] = "https://test-site.com"
os.environ["FEISHU_WEBHOOK_URL"] = ""
os.environ["AHREFS_API_KEY"] = ""

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.models.database import Base, Tool, Category, ToolCategory, engine, init_db, get_session


@pytest.fixture(scope="function")
def db_session():
    """
    Provide a clean in-memory database session for each test.
    Creates all tables, yields session, then drops all tables.
    """
    # Use in-memory SQLite for tests
    test_engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=test_engine)
    session = Session(test_engine)
    yield session
    session.close()
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def sample_tools(db_session):
    """Create sample tools and categories for testing."""
    # Create category
    category = Category(
        id="cat-001",
        name="AI Image Generator",
        slug="ai-image-generator",
        primary_keyword="ai image generator",
        intent_type="Commercial"
    )
    db_session.add(category)
    db_session.flush()

    # Create tools
    tools_data = [
        {
            "id": "tool-001",
            "name": "Midjourney",
            "slug": "midjourney",
            "description": "AI image generation via Discord",
            "official_url": "https://midjourney.com",
            "pricing_model": "Paid",
            "starting_price": 10.0,
            "features": ["Text-to-image", "Upscaling"],
            "pros": ["High quality", "Artistic style"],
            "cons": ["No free tier", "Discord only"],
            "use_cases": ["Digital art", "Marketing"],
            "rating": 4.7,
        },
        {
            "id": "tool-002",
            "name": "DALL-E 3",
            "slug": "dall-e-3",
            "description": "OpenAI image generation",
            "official_url": "https://openai.com/dall-e-3",
            "pricing_model": "Freemium",
            "starting_price": 0.0,
            "features": ["Text-to-image", "ChatGPT integration"],
            "pros": ["Free tier", "Prompt accuracy"],
            "cons": ["Less artistic", "Rate limits"],
            "use_cases": ["Content creation", "Prototyping"],
            "rating": 4.5,
        },
        {
            "id": "tool-003",
            "name": "Stable Diffusion",
            "slug": "stable-diffusion",
            "description": "Open-source image generation",
            "official_url": "https://stability.ai",
            "pricing_model": "Free",
            "starting_price": 0.0,
            "features": ["Text-to-image", "Local deployment"],
            "pros": ["Free", "Open-source"],
            "cons": ["Technical setup", "Hardware needed"],
            "use_cases": ["Research", "Custom models"],
            "rating": 4.3,
        },
    ]

    tools = []
    for td in tools_data:
        tool = Tool(**td)
        db_session.add(tool)
        db_session.flush()
        rel = ToolCategory(tool_id=tool.id, category_id=category.id)
        db_session.add(rel)
        tools.append(tool)

    db_session.commit()
    return {"category": category, "tools": tools}
