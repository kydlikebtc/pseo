"""
Tests for the data collector / database seeder module.
"""
import pytest
from src.models.database import Tool, Category, ToolCategory
from src.engine.data_collector import DataCollector


@pytest.fixture
def collector(db_session):
    """Create a DataCollector with test session."""
    c = DataCollector()
    c.session = db_session
    return c


class TestDataCollector:

    def test_seed_sample_data(self, collector):
        """Test that seed_sample_data creates tools and categories."""
        collector.seed_sample_data()

        # Check categories created
        categories = collector.session.query(Category).all()
        assert len(categories) >= 3
        cat_slugs = [c.slug for c in categories]
        assert "ai-image-generator" in cat_slugs
        assert "ai-writing-assistant" in cat_slugs
        assert "ai-video-generator" in cat_slugs

        # Check tools created
        tools = collector.session.query(Tool).all()
        assert len(tools) >= 8

        tool_slugs = [t.slug for t in tools]
        assert "midjourney" in tool_slugs
        assert "dall-e-3" in tool_slugs
        assert "chatgpt" in tool_slugs

    def test_seed_idempotent(self, collector):
        """Seeding twice should not create duplicate records."""
        collector.seed_sample_data()
        count_after_first = collector.session.query(Tool).count()

        collector.seed_sample_data()
        count_after_second = collector.session.query(Tool).count()

        assert count_after_first == count_after_second

    def test_add_tool(self, collector):
        """Test adding a single tool to the database."""
        # First create a category
        cat = Category(name="Test Category", slug="test-cat", intent_type="Commercial")
        collector.session.add(cat)
        collector.session.commit()

        tool_data = {
            "name": "New Tool",
            "slug": "new-tool",
            "description": "A brand new AI tool",
            "pricing_model": "Freemium",
            "starting_price": 0.0,
            "features": ["Feature 1"],
            "pros": ["Pro 1"],
            "cons": ["Con 1"],
            "rating": 4.0,
        }

        tool = collector.add_tool(tool_data, "test-cat")
        assert tool is not None
        assert tool.name == "New Tool"
        assert tool.slug == "new-tool"

        # Verify relationship
        rel = collector.session.query(ToolCategory).filter(
            ToolCategory.tool_id == tool.id
        ).first()
        assert rel is not None

    def test_add_tool_missing_category(self, collector):
        """Adding a tool with non-existent category should return None."""
        tool_data = {
            "name": "Orphan Tool",
            "slug": "orphan-tool",
            "pricing_model": "Free",
            "starting_price": 0.0,
        }
        tool = collector.add_tool(tool_data, "nonexistent-category")
        assert tool is None

    def test_tools_have_required_fields(self, collector):
        """All seeded tools should have required SEO fields populated."""
        collector.seed_sample_data()
        tools = collector.session.query(Tool).all()

        for tool in tools:
            assert tool.name, f"Tool {tool.id} missing name"
            assert tool.slug, f"Tool {tool.id} missing slug"
            assert tool.description, f"Tool {tool.slug} missing description"
            assert tool.pricing_model, f"Tool {tool.slug} missing pricing_model"
            assert isinstance(tool.features, list), f"Tool {tool.slug} features should be list"
            assert isinstance(tool.pros, list), f"Tool {tool.slug} pros should be list"
            assert isinstance(tool.cons, list), f"Tool {tool.slug} cons should be list"
