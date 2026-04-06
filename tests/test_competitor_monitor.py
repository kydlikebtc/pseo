"""
Tests for the competitor monitoring and backlink discovery module.
Uses mock data to test without real Ahrefs API credentials.
"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

from src.models.database import Base, Competitor, BacklinkOpportunity
from src.monitor.competitor_monitor import CompetitorMonitor


@pytest.fixture
def monitor(db_session):
    """Create a CompetitorMonitor with test session."""
    m = CompetitorMonitor()
    m.session = db_session
    return m


class TestCompetitorMonitor:

    def test_add_competitor(self, monitor):
        """Test adding a competitor domain."""
        comp = monitor.add_competitor("competitor.com")
        assert comp.domain == "competitor.com"
        assert comp.id is not None

    def test_add_competitor_idempotent(self, monitor):
        """Adding the same competitor twice should return the same record."""
        comp1 = monitor.add_competitor("same-domain.com")
        comp2 = monitor.add_competitor("same-domain.com")
        assert comp1.id == comp2.id

    def test_update_competitor_metrics_mock(self, monitor):
        """Test updating competitor metrics using mock data."""
        # No Ahrefs key → uses mock data
        comp = monitor.update_competitor_metrics("futuretools.io")
        assert comp is not None
        assert comp.domain == "futuretools.io"
        assert comp.domain_rating > 0
        assert comp.monthly_traffic > 0
        assert comp.last_checked_at is not None

    def test_traffic_surge_detection(self, monitor):
        """Test that traffic surge alerts are triggered correctly."""
        # Add competitor with low initial traffic
        comp = monitor.add_competitor("surge-test.com")
        comp.monthly_traffic = 100000
        monitor.session.commit()

        # Mock the notification function
        with patch("src.monitor.competitor_monitor.send_feishu_notification") as mock_notify:
            # Manually simulate a surge
            old_traffic = 100000
            new_traffic = 150000  # 50% growth > 20% threshold
            growth_rate = (new_traffic - old_traffic) / old_traffic
            monitor._alert_traffic_surge("surge-test.com", old_traffic, new_traffic, growth_rate)
            mock_notify.assert_called_once()
            call_args = mock_notify.call_args[0]
            assert "surge-test.com" in call_args[0]

    def test_backlink_quality_filter(self, monitor):
        """Test that backlink quality filter correctly categorizes links."""
        comp = monitor.add_competitor("filter-test.com")

        # Discover backlinks (uses mock data)
        opportunities = monitor.discover_backlink_opportunities("filter-test.com")

        # All opportunities should meet minimum DR threshold
        for opp in opportunities:
            assert opp.domain_rating >= monitor.BACKLINK_MIN_DR

        # Verify low-quality links (DR < 10) are filtered out
        all_in_db = monitor.session.query(BacklinkOpportunity).all()
        for opp in all_in_db:
            assert opp.domain_rating >= monitor.BACKLINK_MIN_DR

    def test_high_quality_backlinks_notified(self, monitor):
        """Test that high-quality backlinks (DR 30-60) trigger notifications."""
        with patch("src.monitor.competitor_monitor.send_feishu_notification") as mock_notify:
            opportunities = monitor.discover_backlink_opportunities("futuretools.io")

            high_quality = [
                o for o in opportunities
                if monitor.BACKLINK_TARGET_DR_LOW <= o.domain_rating <= monitor.BACKLINK_TARGET_DR_HIGH
            ]

            if high_quality:
                mock_notify.assert_called()

    def test_get_all_opportunities_filter(self, monitor):
        """Test filtering opportunities by minimum DR."""
        monitor.discover_backlink_opportunities("futuretools.io")

        # Get high-quality only
        high_quality = monitor.get_all_opportunities(min_dr=30)
        for opp in high_quality:
            assert opp.domain_rating >= 30

        # Get all above minimum
        all_opps = monitor.get_all_opportunities(min_dr=10)
        assert len(all_opps) >= len(high_quality)

    def test_weekly_report_structure(self, monitor):
        """Test that weekly report returns correct structure."""
        domains = ["futuretools.io", "theresanaiforthat.com"]
        report = monitor.run_weekly_report(domains)

        assert "generated_at" in report
        assert "competitors" in report
        assert len(report["competitors"]) == 2
        assert "total_new_opportunities" in report
        assert "high_quality_opportunities" in report

        for comp_data in report["competitors"]:
            assert "domain" in comp_data
            assert "domain_rating" in comp_data
            assert "monthly_traffic" in comp_data
