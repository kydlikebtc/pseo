"""
Competitor monitoring and backlink opportunity discovery module.
Integrates with Ahrefs API (or mock data for testing) to track competitor
traffic trends and surface high-quality backlink opportunities.
"""
import json
from datetime import datetime, timedelta
from typing import Optional

import httpx

from src.models import Competitor, BacklinkOpportunity, get_session
from src.utils.helpers import send_feishu_notification
from src.config import settings


class CompetitorMonitor:
    """
    Monitors competitor SEO performance and discovers backlink opportunities.
    
    Quality filter for backlinks:
    - DR < 10: Low quality, skip
    - DR 10-30: Medium quality, log only
    - DR 30-60: HIGH QUALITY TARGET — notify team
    - DR > 80: Hard to acquire, deprioritize
    """

    BACKLINK_MIN_DR = 10
    BACKLINK_TARGET_DR_LOW = 30
    BACKLINK_TARGET_DR_HIGH = 60
    TRAFFIC_SURGE_THRESHOLD = 0.20  # 20% week-over-week growth

    def __init__(self):
        self.session = get_session()
        self.ahrefs_key = settings.ahrefs_api_key
        self.base_url = "https://api.ahrefs.com/v3"

    def _ahrefs_request(self, endpoint: str, params: dict) -> Optional[dict]:
        """Make an authenticated request to the Ahrefs API."""
        if not self.ahrefs_key:
            print("[Monitor] Ahrefs API key not configured. Using mock data.")
            return None

        headers = {"Authorization": f"Bearer {self.ahrefs_key}"}
        try:
            response = httpx.get(
                f"{self.base_url}/{endpoint}",
                params=params,
                headers=headers,
                timeout=30
            )
            if response.status_code == 200:
                return response.json()
            else:
                print(f"[Monitor] Ahrefs API error {response.status_code}: {response.text}")
                return None
        except Exception as e:
            print(f"[Monitor] Ahrefs request failed: {e}")
            return None

    def _get_mock_competitor_data(self, domain: str) -> dict:
        """
        Return mock competitor data for testing when Ahrefs API is unavailable.
        Simulates realistic SEO metrics.
        """
        mock_data = {
            "futuretools.io": {
                "domain_rating": 62,
                "monthly_traffic": 850000,
                "seo_traffic_ratio": 0.72,
                "top_keywords": [
                    {"keyword": "ai tools", "position": 3, "traffic": 45000},
                    {"keyword": "best ai image generator", "position": 5, "traffic": 28000},
                    {"keyword": "chatgpt alternatives", "position": 2, "traffic": 35000},
                ]
            },
            "theresanaiforthat.com": {
                "domain_rating": 58,
                "monthly_traffic": 620000,
                "seo_traffic_ratio": 0.81,
                "top_keywords": [
                    {"keyword": "ai tools directory", "position": 1, "traffic": 52000},
                    {"keyword": "ai for writing", "position": 4, "traffic": 18000},
                ]
            },
            "topai.tools": {
                "domain_rating": 45,
                "monthly_traffic": 320000,
                "seo_traffic_ratio": 0.68,
                "top_keywords": [
                    {"keyword": "top ai tools", "position": 6, "traffic": 22000},
                ]
            }
        }
        return mock_data.get(domain, {
            "domain_rating": 40,
            "monthly_traffic": 200000,
            "seo_traffic_ratio": 0.60,
            "top_keywords": []
        })

    def _get_mock_backlinks(self, domain: str) -> list[dict]:
        """Return mock backlink data for testing."""
        return [
            {
                "source_url": "https://www.producthunt.com/posts/ai-tools-2024",
                "source_domain": "producthunt.com",
                "domain_rating": 90,
                "context": f"Check out {domain} for amazing AI tools",
                "link_type": "DoFollow"
            },
            {
                "source_url": "https://aitools-directory.com/best-ai-tools",
                "source_domain": "aitools-directory.com",
                "domain_rating": 35,
                "context": f"We recommend {domain} as one of the best AI tool directories",
                "link_type": "DoFollow"
            },
            {
                "source_url": "https://techblog.medium.com/ai-tools-review",
                "source_domain": "medium.com",
                "domain_rating": 92,
                "context": f"According to {domain}, the AI landscape is changing",
                "link_type": "NoFollow"
            },
            {
                "source_url": "https://ai-navigator.net/resources",
                "source_domain": "ai-navigator.net",
                "domain_rating": 42,
                "context": f"Resource list featuring {domain}",
                "link_type": "DoFollow"
            },
            {
                "source_url": "https://spamsite123.xyz/links",
                "source_domain": "spamsite123.xyz",
                "domain_rating": 3,
                "context": "Random link",
                "link_type": "DoFollow"
            },
        ]

    def add_competitor(self, domain: str) -> Competitor:
        """Add a competitor domain to track."""
        existing = self.session.query(Competitor).filter(Competitor.domain == domain).first()
        if existing:
            return existing

        competitor = Competitor(domain=domain)
        self.session.add(competitor)
        self.session.commit()
        print(f"[Monitor] Added competitor: {domain}")
        return competitor

    def update_competitor_metrics(self, domain: str) -> Optional[Competitor]:
        """
        Fetch and update competitor traffic metrics.
        Detects traffic surges (>20% WoW growth) and sends alerts.
        """
        competitor = self.session.query(Competitor).filter(Competitor.domain == domain).first()
        if not competitor:
            competitor = self.add_competitor(domain)

        # Try Ahrefs API, fall back to mock data
        data = self._ahrefs_request("site-overview", {"target": domain, "mode": "domain"})
        if not data:
            data = self._get_mock_competitor_data(domain)

        old_traffic = competitor.monthly_traffic or 0
        new_traffic = data.get("monthly_traffic", 0)

        competitor.domain_rating = data.get("domain_rating", 0)
        competitor.monthly_traffic = new_traffic
        competitor.seo_traffic_ratio = data.get("seo_traffic_ratio", 0.0)
        competitor.top_keywords = data.get("top_keywords", [])
        competitor.last_checked_at = datetime.utcnow()

        self.session.commit()

        # Detect traffic surge
        if old_traffic > 0:
            growth_rate = (new_traffic - old_traffic) / old_traffic
            if growth_rate >= self.TRAFFIC_SURGE_THRESHOLD:
                self._alert_traffic_surge(domain, old_traffic, new_traffic, growth_rate)

        print(f"[Monitor] Updated {domain}: DR={competitor.domain_rating}, Traffic={new_traffic:,}")
        return competitor

    def _alert_traffic_surge(self, domain: str, old_traffic: int, new_traffic: int, growth_rate: float):
        """Send alert when competitor traffic surges significantly."""
        title = f"🚀 竞品流量预警: {domain}"
        content = (
            f"**{domain}** 流量出现显著增长！\n\n"
            f"- 上次流量: **{old_traffic:,}**\n"
            f"- 当前流量: **{new_traffic:,}**\n"
            f"- 增长幅度: **+{growth_rate:.1%}**\n\n"
            f"建议立即分析其 Top Pages 的变动，寻找内容机会。"
        )
        send_feishu_notification(title, content)
        print(f"[Monitor] SURGE ALERT: {domain} grew {growth_rate:.1%}")

    def discover_backlink_opportunities(self, competitor_domain: str) -> list[BacklinkOpportunity]:
        """
        Discover backlink opportunities from a competitor's backlink profile.
        Applies quality filter: targets DR 30-60 DoFollow links.
        """
        competitor = self.session.query(Competitor).filter(
            Competitor.domain == competitor_domain
        ).first()
        if not competitor:
            competitor = self.add_competitor(competitor_domain)

        # Try Ahrefs API, fall back to mock data
        data = self._ahrefs_request(
            "backlinks/all",
            {"target": competitor_domain, "mode": "domain", "limit": 100}
        )
        backlinks = data.get("backlinks", []) if data else self._get_mock_backlinks(competitor_domain)

        new_opportunities = []
        for bl in backlinks:
            dr = bl.get("domain_rating", 0)
            source_url = bl.get("source_url", "")

            # Quality filter
            if dr < self.BACKLINK_MIN_DR:
                continue  # Skip low-quality

            # Check if already tracked
            existing = self.session.query(BacklinkOpportunity).filter(
                BacklinkOpportunity.source_url == source_url
            ).first()
            if existing:
                continue

            opportunity = BacklinkOpportunity(
                competitor_id=competitor.id,
                source_url=source_url,
                source_domain=bl.get("source_domain", ""),
                domain_rating=dr,
                context_snippet=bl.get("context", ""),
                link_type=bl.get("link_type", "Unknown"),
                status="New",
                is_notified=False,
                discovered_at=datetime.utcnow()
            )
            self.session.add(opportunity)
            new_opportunities.append(opportunity)

        self.session.commit()

        # Notify team about high-quality opportunities
        high_quality = [
            o for o in new_opportunities
            if self.BACKLINK_TARGET_DR_LOW <= o.domain_rating <= self.BACKLINK_TARGET_DR_HIGH
        ]
        if high_quality:
            self._notify_backlink_opportunities(high_quality)

        print(f"[Monitor] Discovered {len(new_opportunities)} new opportunities "
              f"({len(high_quality)} high-quality) from {competitor_domain}")
        return new_opportunities

    def _notify_backlink_opportunities(self, opportunities: list[BacklinkOpportunity]):
        """Send Feishu notification with high-quality backlink opportunities."""
        title = f"🔗 发现 {len(opportunities)} 个高质量外链机会"
        lines = [f"以下外链机会 DR 在 {self.BACKLINK_TARGET_DR_LOW}-{self.BACKLINK_TARGET_DR_HIGH} 之间，建议优先跟进：\n"]

        for opp in opportunities[:5]:  # Show top 5
            lines.append(
                f"**DR {opp.domain_rating}** | {opp.source_domain}\n"
                f"  URL: {opp.source_url}\n"
                f"  Context: {opp.context_snippet[:80]}...\n"
            )

        content = "\n".join(lines)
        send_feishu_notification(title, content)

        # Mark as notified
        for opp in opportunities:
            opp.is_notified = True
        self.session.commit()

    def run_weekly_report(self, competitor_domains: list[str]) -> dict:
        """
        Run the full weekly competitor monitoring workflow.
        Updates metrics, discovers backlinks, and generates a summary report.
        """
        print(f"[Monitor] Starting weekly report for {len(competitor_domains)} competitors...")
        report = {
            "generated_at": datetime.utcnow().isoformat(),
            "competitors": [],
            "total_new_opportunities": 0,
            "high_quality_opportunities": 0,
        }

        for domain in competitor_domains:
            competitor = self.update_competitor_metrics(domain)
            opportunities = self.discover_backlink_opportunities(domain)

            high_quality = [
                o for o in opportunities
                if self.BACKLINK_TARGET_DR_LOW <= o.domain_rating <= self.BACKLINK_TARGET_DR_HIGH
            ]

            report["competitors"].append({
                "domain": domain,
                "domain_rating": competitor.domain_rating if competitor else 0,
                "monthly_traffic": competitor.monthly_traffic if competitor else 0,
                "new_backlink_opportunities": len(opportunities),
                "high_quality_opportunities": len(high_quality),
            })
            report["total_new_opportunities"] += len(opportunities)
            report["high_quality_opportunities"] += len(high_quality)

        print(f"[Monitor] Weekly report complete: {report['total_new_opportunities']} new opportunities found")
        return report

    def get_all_opportunities(self, min_dr: int = 30, status: str = "New") -> list[BacklinkOpportunity]:
        """Retrieve filtered backlink opportunities from the database."""
        query = self.session.query(BacklinkOpportunity).filter(
            BacklinkOpportunity.domain_rating >= min_dr
        )
        if status:
            query = query.filter(BacklinkOpportunity.status == status)
        return query.order_by(BacklinkOpportunity.domain_rating.desc()).all()

    def close(self):
        self.session.close()
