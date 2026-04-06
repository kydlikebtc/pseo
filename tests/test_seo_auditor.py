"""
Tests for the SEO auditor module.
Uses mock HTML content to test structural checks without making HTTP requests.
"""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.checker.seo_auditor import SEOAuditor


@pytest.fixture
def auditor(db_session):
    """Create an SEOAuditor with test session."""
    a = SEOAuditor()
    a.session = db_session
    return a


# ---- HTML Fixtures ----

GOOD_HTML = """<!DOCTYPE html>
<html>
<head>
    <title>Best Midjourney Alternatives 2025</title>
    <meta name="description" content="Discover the top 10 Midjourney alternatives for AI image generation in 2025.">
    <link rel="canonical" href="https://test-site.com/alternatives/midjourney">
    <script type="application/ld+json">{"@type": "FAQPage"}</script>
</head>
<body>
    <h1>Best Midjourney Alternatives</h1>
    <img src="hero.png" alt="AI image generation comparison">
    <p>Content here...</p>
</body>
</html>"""

MISSING_H1_HTML = """<!DOCTYPE html>
<html>
<head>
    <title>Page Title</title>
    <meta name="description" content="A description here.">
    <link rel="canonical" href="https://test-site.com/page">
</head>
<body>
    <h2>Subtitle without H1</h2>
</body>
</html>"""

MULTIPLE_H1_HTML = """<!DOCTYPE html>
<html>
<head>
    <title>Page Title</title>
    <meta name="description" content="A description.">
    <link rel="canonical" href="https://test-site.com/page">
</head>
<body>
    <h1>First H1</h1>
    <h1>Second H1</h1>
</body>
</html>"""

MISSING_META_HTML = """<!DOCTYPE html>
<html>
<head>
    <title>Page Title</title>
    <link rel="canonical" href="https://test-site.com/page">
</head>
<body>
    <h1>Heading</h1>
</body>
</html>"""

MISSING_ALT_HTML = """<!DOCTYPE html>
<html>
<head>
    <title>Page Title</title>
    <meta name="description" content="A description.">
    <link rel="canonical" href="https://test-site.com/page">
</head>
<body>
    <h1>Heading</h1>
    <img src="image1.png">
    <img src="image2.png" alt="">
    <img src="image3.png" alt="Has alt">
</body>
</html>"""


class TestSEOAuditorStructure:
    """Tests for HTML structure auditing (no HTTP requests)."""

    @pytest.mark.asyncio
    async def test_good_page_passes(self, auditor):
        """A well-structured page should pass all checks."""
        result = await auditor.audit_page_structure(GOOD_HTML, "https://test-site.com/test")
        assert result["has_h1"] is True
        assert result["h1_count"] == 1
        assert result["has_meta_description"] is True
        assert result["has_schema"] is True
        assert result["missing_alt_count"] == 0
        assert result["passed"] is True
        assert len(result["issues"]) == 0

    @pytest.mark.asyncio
    async def test_missing_h1_detected(self, auditor):
        """Missing H1 should be detected as a critical issue."""
        result = await auditor.audit_page_structure(MISSING_H1_HTML)
        assert result["has_h1"] is False
        assert result["h1_count"] == 0
        assert result["passed"] is False
        assert any("H1" in issue for issue in result["issues"])

    @pytest.mark.asyncio
    async def test_multiple_h1_detected(self, auditor):
        """Multiple H1 tags should be flagged."""
        result = await auditor.audit_page_structure(MULTIPLE_H1_HTML)
        assert result["h1_count"] == 2
        assert any("Multiple H1" in issue for issue in result["issues"])

    @pytest.mark.asyncio
    async def test_missing_meta_description_detected(self, auditor):
        """Missing meta description should be flagged."""
        result = await auditor.audit_page_structure(MISSING_META_HTML)
        assert result["has_meta_description"] is False
        assert any("meta description" in issue for issue in result["issues"])

    @pytest.mark.asyncio
    async def test_missing_alt_tags_detected(self, auditor):
        """Images without alt attributes should be counted."""
        result = await auditor.audit_page_structure(MISSING_ALT_HTML)
        # img1 has no alt, img2 has empty alt (still counts), img3 has alt
        assert result["missing_alt_count"] >= 1
        assert any("alt" in issue for issue in result["issues"])

    @pytest.mark.asyncio
    async def test_missing_schema_detected(self, auditor):
        """Missing JSON-LD schema should be flagged."""
        result = await auditor.audit_page_structure(MISSING_META_HTML)
        assert result["has_schema"] is False
        assert any("JSON-LD" in issue for issue in result["issues"])


class TestSEOAuditorHTTP:
    """Tests for HTTP-based auditing with mocked responses."""

    @pytest.mark.asyncio
    async def test_audit_url_success(self, auditor):
        """Test full URL audit with mocked HTTP response."""
        import httpx
        import respx

        with respx.mock:
            respx.get("https://test-site.com/test-page").mock(
                return_value=httpx.Response(200, text=GOOD_HTML)
            )
            result = await auditor.audit_url("https://test-site.com/test-page")

        assert result.has_h1 is True
        assert result.has_meta_description is True
        assert result.passed is True

    @pytest.mark.asyncio
    async def test_audit_url_404(self, auditor):
        """Test that 404 responses are handled gracefully."""
        import httpx
        import respx

        with respx.mock:
            respx.get("https://test-site.com/missing-page").mock(
                return_value=httpx.Response(404, text="Not Found")
            )
            result = await auditor.audit_url("https://test-site.com/missing-page")

        assert result.passed is False
        assert any("404" in issue for issue in result.issues)
