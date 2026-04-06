"""
Tests for the sitemap generator module.
"""
import pytest
from datetime import datetime

from src.models.database import PSEOPage
from src.checker.sitemap_generator import SitemapGenerator


@pytest.fixture
def generator(db_session):
    """Create a SitemapGenerator with test session."""
    g = SitemapGenerator()
    g.session = db_session
    return g


@pytest.fixture
def published_pages(db_session):
    """Create sample published and draft pages."""
    pages = [
        PSEOPage(
            page_type="Listicle",
            primary_keyword="best ai image generators",
            url_path="/best/ai-image-generator",
            title="Best AI Image Generators",
            status="Published",
            published_at=datetime.utcnow(),
        ),
        PSEOPage(
            page_type="Alternative",
            primary_keyword="midjourney alternatives",
            url_path="/alternatives/midjourney",
            title="Midjourney Alternatives",
            status="Published",
            published_at=datetime.utcnow(),
        ),
        PSEOPage(
            page_type="Comparison",
            primary_keyword="midjourney vs dall-e 3",
            url_path="/compare/midjourney-vs-dall-e-3",
            title="Midjourney vs DALL-E 3",
            status="Draft",  # This should be excluded by default
        ),
    ]
    for page in pages:
        db_session.add(page)
    db_session.commit()
    return pages


class TestSitemapGenerator:

    def test_generate_excludes_drafts(self, generator, published_pages):
        """Sitemap should only include published pages by default."""
        xml = generator.generate(output_path=None)
        assert "/best/ai-image-generator" in xml
        assert "/alternatives/midjourney" in xml
        assert "/compare/midjourney-vs-dall-e-3" not in xml

    def test_generate_includes_drafts_when_requested(self, generator, published_pages):
        """Sitemap should include drafts when include_drafts=True."""
        xml = generator.generate(output_path=None, include_drafts=True)
        assert "/compare/midjourney-vs-dall-e-3" in xml

    def test_generate_valid_xml_structure(self, generator, published_pages):
        """Generated sitemap should have valid XML structure."""
        xml = generator.generate(output_path=None)
        assert '<?xml version="1.0" encoding="UTF-8"?>' in xml
        assert "<urlset" in xml
        assert "<url>" in xml
        assert "<loc>" in xml
        assert "<lastmod>" in xml
        assert "<changefreq>" in xml
        assert "<priority>" in xml

    def test_generate_correct_priorities(self, generator, published_pages):
        """Listicle pages should have higher priority than alternative pages."""
        xml = generator.generate(output_path=None)
        # Listicle priority is 0.9, Alternative is 0.8
        assert "0.9" in xml  # Listicle
        assert "0.8" in xml  # Alternative

    def test_generate_site_url_prefix(self, generator, published_pages):
        """URLs should be prefixed with the site URL."""
        xml = generator.generate(output_path=None)
        assert "https://test-site.com/best/ai-image-generator" in xml

    def test_generate_empty_db(self, generator):
        """Generating sitemap with no pages should return valid empty sitemap."""
        xml = generator.generate(output_path=None)
        assert "<urlset" in xml
        assert "<url>" not in xml

    def test_generate_writes_file(self, generator, published_pages, tmp_path):
        """Test that sitemap is written to file correctly."""
        output_file = str(tmp_path / "sitemap.xml")
        generator.generate(output_path=output_file)

        with open(output_file, "r") as f:
            content = f.read()

        assert "<urlset" in content
        assert "/best/ai-image-generator" in content
