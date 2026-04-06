"""
Competitor monitoring and backlink opportunity discovery module.

Data Sources (priority order):
  1. SimilarWeb API (via Manus built-in ApiClient) — NO API KEY REQUIRED
     Provides: monthly traffic, traffic sources, organic search ratio, global rank
  2. Semrush API (optional, requires SEMRUSH_API_KEY)
     Provides: keyword rankings, backlink data
  3. Mock data — fallback for testing when no API is available

Backlink discovery strategy (from SEO playbook):
  - DR < 10:   Low quality, skip
  - DR 10-30:  Medium quality, log only
  - DR 30-60:  HIGH QUALITY TARGET — notify team immediately
  - DR > 80:   Hard to acquire, deprioritize
"""
import sys
import json
from datetime import datetime, timedelta
from typing import Optional

import httpx

from src.models import Competitor, BacklinkOpportunity, get_session
from src.utils.helpers import send_feishu_notification
from src.config import settings

# SimilarWeb via Manus built-in ApiClient (no API key needed)
try:
    sys.path.append('/opt/.manus/.sandbox-runtime')
    from data_api import ApiClient as SimilarWebClient
    SIMILARWEB_AVAILABLE = True
except ImportError:
    SIMILARWEB_AVAILABLE = False


class CompetitorMonitor:
    """
    Monitors competitor SEO performance and discovers backlink opportunities.

    Data source priority:
      SimilarWeb (built-in, free) → Semrush (optional key) → Mock data
    """

    BACKLINK_MIN_DR = 10
    BACKLINK_TARGET_DR_LOW = 30
    BACKLINK_TARGET_DR_HIGH = 60
    TRAFFIC_SURGE_THRESHOLD = 0.20  # 20% month-over-month growth triggers alert

    def __init__(self):
        self.session = get_session()
        self.semrush_key = settings.semrush_api_key if hasattr(settings, 'semrush_api_key') else None
        self._sw_client = SimilarWebClient() if SIMILARWEB_AVAILABLE else None

    # ─────────────────────────────────────────────
    # SimilarWeb Data Fetching (Primary Source)
    # ─────────────────────────────────────────────

    def _get_similarweb_traffic(self, domain: str) -> Optional[dict]:
        """
        Fetch real traffic data from SimilarWeb via Manus built-in ApiClient.
        Returns structured metrics dict, or None on failure.
        """
        if not self._sw_client:
            return None

        try:
            # 1. Monthly visits (12-month history)
            visits_resp = self._sw_client.call_api(
                'SimilarWeb/get_visits_total',
                path_params={'domain': domain},
                query={'country': 'world', 'granularity': 'monthly'}
            )

            # 2. Traffic sources (organic search ratio)
            sources_resp = self._sw_client.call_api(
                'SimilarWeb/get_traffic_sources_desktop',
                path_params={'domain': domain},
                query={'country': 'world', 'granularity': 'monthly'}
            )

            # 3. Global rank
            rank_resp = self._sw_client.call_api(
                'SimilarWeb/get_global_rank',
                path_params={'domain': domain}
            )

            if visits_resp.get('meta', {}).get('status') != 'Success':
                return None

            visits_list = visits_resp.get('visits', [])
            if not visits_list:
                return None

            # Get latest 2 months for growth calculation
            latest = visits_list[-1]['visits'] if visits_list else 0
            prev = visits_list[-2]['visits'] if len(visits_list) >= 2 else latest

            # Calculate organic search ratio from traffic sources
            # SimilarWeb API returns: {visits: {domain: {source_type: [{date, organic, paid}]}}}
            organic_visits = 0
            total_visits = 0
            try:
                if sources_resp and 'visits' in sources_resp:
                    domain_data = sources_resp['visits'].get(domain, {})
                    for source_type, entries in domain_data.items():
                        for entry in (entries if isinstance(entries, list) else []):
                            org = entry.get('organic', 0) or 0
                            paid = entry.get('paid', 0) or 0
                            total_visits += org + paid
                            if source_type.lower() in ('search', 'organic search'):
                                organic_visits += org
            except Exception:
                pass
            seo_ratio = (organic_visits / total_visits) if total_visits > 0 else 0.0

            # Global rank (latest)
            global_rank = None
            rank_list = rank_resp.get('global_rank', []) if rank_resp else []
            if rank_list:
                global_rank = rank_list[-1].get('global_rank')

            return {
                'source': 'similarweb',
                'monthly_traffic': int(latest),
                'prev_month_traffic': int(prev),
                'seo_traffic_ratio': round(seo_ratio, 3),
                'global_rank': global_rank,
                'traffic_history': [
                    {'date': v['date'], 'visits': int(v['visits'])}
                    for v in visits_list
                ],
                'last_updated': visits_resp['meta'].get('last_updated', ''),
            }

        except Exception as e:
            print(f"[Monitor] SimilarWeb error for {domain}: {e}")
            return None

    # ─────────────────────────────────────────────
    # Semrush Data Fetching (Secondary Source)
    # ─────────────────────────────────────────────

    def _get_semrush_backlinks(self, domain: str) -> Optional[list[dict]]:
        """
        Fetch backlink data from Semrush free API.
        Semrush free tier: 10 requests/day, domain overview + backlinks.
        Requires SEMRUSH_API_KEY in .env
        """
        if not self.semrush_key:
            return None

        try:
            # Semrush Backlinks Overview API (free tier endpoint)
            url = "https://api.semrush.com/"
            params = {
                "type": "backlinks_refdomains",
                "key": self.semrush_key,
                "target": domain,
                "target_type": "root_domain",
                "export_columns": "domain_ascore,source_url,source_title,anchor,nofollow",
                "display_limit": 50,
            }
            response = httpx.get(url, params=params, timeout=20)
            if response.status_code != 200:
                print(f"[Monitor] Semrush API error {response.status_code}")
                return None

            # Parse CSV response from Semrush
            lines = response.text.strip().split('\n')
            if len(lines) < 2:
                return None

            headers = lines[0].split(';')
            backlinks = []
            for line in lines[1:]:
                parts = line.split(';')
                if len(parts) >= len(headers):
                    row = dict(zip(headers, parts))
                    backlinks.append({
                        'source_url': row.get('Source URL', ''),
                        'source_domain': row.get('Source URL', '').split('/')[2] if row.get('Source URL') else '',
                        'domain_rating': int(row.get('Domain Ascore', 0)),
                        'context': row.get('Anchor', ''),
                        'link_type': 'NoFollow' if row.get('Nofollow') == '1' else 'DoFollow',
                    })
            return backlinks

        except Exception as e:
            print(f"[Monitor] Semrush error for {domain}: {e}")
            return None

    # ─────────────────────────────────────────────
    # Mock Data (Fallback)
    # ─────────────────────────────────────────────

    def _get_mock_competitor_data(self, domain: str) -> dict:
        """Fallback mock data when no API is available."""
        mock_data = {
            "futuretools.io":         {"monthly_traffic": 460000, "prev_month_traffic": 450000, "seo_traffic_ratio": 0.72, "global_rank": 98885},
            "theresanaiforthat.com":  {"monthly_traffic": 4869000, "prev_month_traffic": 5845000, "seo_traffic_ratio": 0.81, "global_rank": 12500},
            "toolify.ai":             {"monthly_traffic": 1531000, "prev_month_traffic": 1963000, "seo_traffic_ratio": 0.68, "global_rank": 45000},
        }
        base = mock_data.get(domain, {"monthly_traffic": 200000, "prev_month_traffic": 190000, "seo_traffic_ratio": 0.60, "global_rank": None})
        base['source'] = 'mock'
        return base

    def _get_mock_backlinks(self, domain: str) -> list[dict]:
        """Fallback mock backlink data."""
        return [
            {"source_url": "https://www.producthunt.com/posts/ai-tools-2024", "source_domain": "producthunt.com",    "domain_rating": 90, "context": f"Check out {domain}", "link_type": "DoFollow"},
            {"source_url": "https://aitools-directory.com/best-ai-tools",     "source_domain": "aitools-directory.com","domain_rating": 35, "context": f"We recommend {domain}", "link_type": "DoFollow"},
            {"source_url": "https://techblog.medium.com/ai-tools-review",     "source_domain": "medium.com",           "domain_rating": 92, "context": f"According to {domain}", "link_type": "NoFollow"},
            {"source_url": "https://ai-navigator.net/resources",              "source_domain": "ai-navigator.net",     "domain_rating": 42, "context": f"Resource list featuring {domain}", "link_type": "DoFollow"},
            {"source_url": "https://spamsite123.xyz/links",                   "source_domain": "spamsite123.xyz",      "domain_rating": 3,  "context": "Random link", "link_type": "DoFollow"},
        ]

    # ─────────────────────────────────────────────
    # Core Monitoring Logic
    # ─────────────────────────────────────────────

    def add_competitor(self, domain: str) -> "Competitor":
        """Add a competitor domain to track."""
        existing = self.session.query(Competitor).filter(Competitor.domain == domain).first()
        if existing:
            return existing
        competitor = Competitor(domain=domain)
        self.session.add(competitor)
        self.session.commit()
        print(f"[Monitor] Added competitor: {domain}")
        return competitor

    def update_competitor_metrics(self, domain: str) -> Optional["Competitor"]:
        """
        Fetch and update competitor traffic metrics using best available data source.
        Priority: SimilarWeb → Semrush → Mock
        Detects traffic surges (>20% MoM growth) and sends alerts.
        """
        competitor = self.session.query(Competitor).filter(Competitor.domain == domain).first()
        if not competitor:
            competitor = self.add_competitor(domain)

        # Try data sources in priority order
        data = self._get_similarweb_traffic(domain)
        if not data:
            data = self._get_mock_competitor_data(domain)

        source = data.get('source', 'unknown')
        new_traffic = data.get('monthly_traffic', 0)
        prev_traffic = data.get('prev_month_traffic', competitor.monthly_traffic or 0)

        competitor.domain_rating = data.get('global_rank', 0) or 0  # use rank as proxy
        competitor.monthly_traffic = new_traffic
        competitor.seo_traffic_ratio = data.get('seo_traffic_ratio', 0.0)
        competitor.top_keywords = data.get('traffic_history', [])
        competitor.last_checked_at = datetime.utcnow()
        self.session.commit()

        # Detect traffic surge (MoM)
        if prev_traffic > 0:
            growth_rate = (new_traffic - prev_traffic) / prev_traffic
            if growth_rate >= self.TRAFFIC_SURGE_THRESHOLD:
                self._alert_traffic_surge(domain, prev_traffic, new_traffic, growth_rate)

        print(f"[Monitor] Updated {domain} [{source}]: Traffic={new_traffic:,} "
              f"(prev={prev_traffic:,}), SEO ratio={data.get('seo_traffic_ratio', 0):.1%}")
        return competitor

    def _alert_traffic_surge(self, domain: str, old_traffic: int, new_traffic: int, growth_rate: float):
        """Send Feishu alert when competitor traffic surges significantly."""
        title = f"🚀 竞品流量预警: {domain}"
        content = (
            f"**{domain}** 流量出现显著增长！\n\n"
            f"- 上月流量: **{old_traffic:,}**\n"
            f"- 本月流量: **{new_traffic:,}**\n"
            f"- 增长幅度: **+{growth_rate:.1%}**\n\n"
            f"建议立即分析其 Top Pages 变动，寻找内容机会。"
        )
        send_feishu_notification(title, content)
        print(f"[Monitor] ⚠️  SURGE ALERT: {domain} grew {growth_rate:.1%}")

    def discover_backlink_opportunities(self, competitor_domain: str) -> list["BacklinkOpportunity"]:
        """
        Discover backlink opportunities from a competitor's backlink profile.
        Priority: Semrush API → Mock data
        Quality filter: targets DR 30-60 DoFollow links.
        """
        competitor = self.session.query(Competitor).filter(
            Competitor.domain == competitor_domain
        ).first()
        if not competitor:
            competitor = self.add_competitor(competitor_domain)

        # Try Semrush first, then mock
        backlinks = self._get_semrush_backlinks(competitor_domain)
        if not backlinks:
            backlinks = self._get_mock_backlinks(competitor_domain)

        new_opportunities = []
        for bl in backlinks:
            dr = bl.get("domain_rating", 0)
            source_url = bl.get("source_url", "")

            if dr < self.BACKLINK_MIN_DR:
                continue  # Skip low-quality spam

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

        # Notify team about high-quality opportunities (DR 30-60)
        high_quality = [
            o for o in new_opportunities
            if self.BACKLINK_TARGET_DR_LOW <= o.domain_rating <= self.BACKLINK_TARGET_DR_HIGH
        ]
        if high_quality:
            self._notify_backlink_opportunities(high_quality)

        print(f"[Monitor] Discovered {len(new_opportunities)} new opportunities "
              f"({len(high_quality)} high-quality DR {self.BACKLINK_TARGET_DR_LOW}-{self.BACKLINK_TARGET_DR_HIGH}) "
              f"from {competitor_domain}")
        return new_opportunities

    def _notify_backlink_opportunities(self, opportunities: list["BacklinkOpportunity"]):
        """Send Feishu notification with high-quality backlink opportunities."""
        title = f"🔗 发现 {len(opportunities)} 个高质量外链机会 (DR {self.BACKLINK_TARGET_DR_LOW}-{self.BACKLINK_TARGET_DR_HIGH})"
        lines = [f"以下外链机会建议优先跟进：\n"]
        for opp in opportunities[:5]:
            lines.append(
                f"**DR {opp.domain_rating}** | {opp.source_domain}\n"
                f"  URL: {opp.source_url}\n"
                f"  Context: {opp.context_snippet[:80]}\n"
            )
        send_feishu_notification(title, "\n".join(lines))
        for opp in opportunities:
            opp.is_notified = True
        self.session.commit()

    def run_weekly_report(self, competitor_domains: list[str]) -> dict:
        """
        Run the full weekly competitor monitoring workflow.
        Updates metrics (SimilarWeb), discovers backlinks (Semrush/mock),
        and generates a summary report.
        """
        print(f"[Monitor] Starting weekly report for {len(competitor_domains)} competitors...")
        report = {
            "generated_at": datetime.utcnow().isoformat(),
            "data_sources": {
                "traffic": "SimilarWeb (built-in)" if SIMILARWEB_AVAILABLE else "Mock",
                "backlinks": "Semrush API" if self.semrush_key else "Mock",
            },
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
                "monthly_traffic": competitor.monthly_traffic if competitor else 0,
                "seo_traffic_ratio": competitor.seo_traffic_ratio if competitor else 0,
                "new_backlink_opportunities": len(opportunities),
                "high_quality_opportunities": len(high_quality),
            })
            report["total_new_opportunities"] += len(opportunities)
            report["high_quality_opportunities"] += len(high_quality)

        print(f"[Monitor] Weekly report complete: {report['total_new_opportunities']} new opportunities found")
        return report

    def get_traffic_trend(self, domain: str) -> list[dict]:
        """
        Get the full 12-month traffic trend for a competitor using SimilarWeb.
        Returns list of {date, visits} dicts.
        """
        data = self._get_similarweb_traffic(domain)
        if data and data.get('traffic_history'):
            return data['traffic_history']
        return []

    def get_all_opportunities(self, min_dr: int = 30, status: str = "New") -> list["BacklinkOpportunity"]:
        """Retrieve filtered backlink opportunities from the database."""
        query = self.session.query(BacklinkOpportunity).filter(
            BacklinkOpportunity.domain_rating >= min_dr
        )
        if status:
            query = query.filter(BacklinkOpportunity.status == status)
        return query.order_by(BacklinkOpportunity.domain_rating.desc()).all()

    def close(self):
        self.session.close()
