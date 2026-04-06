"""
Tests for database models and data integrity.
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.models.database import (
    Base, Tool, Category, ToolCategory, PSEOPage,
    Competitor, BacklinkOpportunity, SEOAuditResult
)


def test_tool_creation(db_session):
    """Test creating a Tool record with all fields."""
    tool = Tool(
        name="TestTool",
        slug="test-tool",
        description="A test AI tool",
        pricing_model="Freemium",
        starting_price=0.0,
        features=["Feature A", "Feature B"],
        pros=["Pro 1"],
        cons=["Con 1"],
        rating=4.5,
    )
    db_session.add(tool)
    db_session.commit()

    fetched = db_session.query(Tool).filter(Tool.slug == "test-tool").first()
    assert fetched is not None
    assert fetched.name == "TestTool"
    assert fetched.pricing_model == "Freemium"
    assert fetched.features == ["Feature A", "Feature B"]
    assert fetched.rating == 4.5
    assert fetched.is_active is True


def test_tool_to_dict(db_session):
    """Test Tool.to_dict() serialization."""
    tool = Tool(
        name="DictTool",
        slug="dict-tool",
        description="Testing to_dict",
        pricing_model="Paid",
        starting_price=29.0,
        features=["F1"],
        pros=["P1"],
        cons=["C1"],
        rating=4.0,
    )
    db_session.add(tool)
    db_session.commit()

    d = tool.to_dict()
    assert d["name"] == "DictTool"
    assert d["slug"] == "dict-tool"
    assert d["starting_price"] == 29.0
    assert isinstance(d["features"], list)


def test_category_creation(db_session):
    """Test creating a Category record."""
    cat = Category(
        name="AI Writing",
        slug="ai-writing",
        primary_keyword="ai writing assistant",
        intent_type="Commercial"
    )
    db_session.add(cat)
    db_session.commit()

    fetched = db_session.query(Category).filter(Category.slug == "ai-writing").first()
    assert fetched is not None
    assert fetched.intent_type == "Commercial"


def test_tool_category_relationship(db_session, sample_tools):
    """Test many-to-many relationship between Tool and Category."""
    category = sample_tools["category"]
    tools = sample_tools["tools"]

    # Query tools in category
    result = (
        db_session.query(Tool)
        .join(ToolCategory, Tool.id == ToolCategory.tool_id)
        .filter(ToolCategory.category_id == category.id)
        .all()
    )
    assert len(result) == 3
    slugs = [t.slug for t in result]
    assert "midjourney" in slugs
    assert "dall-e-3" in slugs


def test_pseo_page_creation(db_session, sample_tools):
    """Test creating a PSEOPage record."""
    tool = sample_tools["tools"][0]
    page = PSEOPage(
        page_type="Alternative",
        primary_keyword="midjourney alternatives",
        url_path="/alternatives/midjourney",
        template_id="alternatives_v1",
        title="Best Midjourney Alternatives",
        meta_description="Find the best alternatives to Midjourney",
        generated_content={"intro": "Test content"},
        word_count=850,
        status="Draft",
        primary_tool_id=tool.id,
    )
    db_session.add(page)
    db_session.commit()

    fetched = db_session.query(PSEOPage).filter(PSEOPage.url_path == "/alternatives/midjourney").first()
    assert fetched is not None
    assert fetched.page_type == "Alternative"
    assert fetched.word_count == 850
    assert fetched.status == "Draft"
    assert fetched.generated_content["intro"] == "Test content"


def test_competitor_and_backlink(db_session):
    """Test Competitor and BacklinkOpportunity models."""
    competitor = Competitor(
        domain="competitor.com",
        domain_rating=55,
        monthly_traffic=500000,
        seo_traffic_ratio=0.75,
    )
    db_session.add(competitor)
    db_session.flush()

    opp = BacklinkOpportunity(
        competitor_id=competitor.id,
        source_url="https://blog.example.com/ai-tools",
        source_domain="blog.example.com",
        domain_rating=42,
        context_snippet="Great AI tool directory",
        link_type="DoFollow",
        status="New",
    )
    db_session.add(opp)
    db_session.commit()

    fetched_comp = db_session.query(Competitor).filter(Competitor.domain == "competitor.com").first()
    assert fetched_comp is not None
    assert len(fetched_comp.backlink_opportunities) == 1
    assert fetched_comp.backlink_opportunities[0].domain_rating == 42


def test_seo_audit_result(db_session):
    """Test SEOAuditResult model."""
    result = SEOAuditResult(
        url="https://test-site.com/alternatives/midjourney",
        audit_type="Full",
        has_h1=True,
        h1_count=1,
        has_meta_description=True,
        has_schema=True,
        missing_alt_count=0,
        broken_links_count=0,
        issues=[],
        passed=True,
    )
    db_session.add(result)
    db_session.commit()

    fetched = db_session.query(SEOAuditResult).filter(
        SEOAuditResult.url == "https://test-site.com/alternatives/midjourney"
    ).first()
    assert fetched is not None
    assert fetched.passed is True
    assert fetched.issues == []
