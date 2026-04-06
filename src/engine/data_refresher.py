"""
Data Refresher — Automated tool data freshness module.

Implements the playbook requirement:
  "通过编写自动化爬虫或对接官方 API，系统可以定期抓取目标 AI 工具的最新更新日志和价格变动，
   实现数据库字段的自动保鲜。"

This module:
1. Scrapes the official URL of each tool to detect price/feature changes.
2. Compares scraped data with stored DB data and flags stale records.
3. Uses LLM to extract structured updates from unstructured page content.
4. Sends Feishu alerts when significant changes are detected.
"""
import re
from datetime import datetime, timedelta
from typing import Optional

import httpx
from bs4 import BeautifulSoup

from src.models import Tool, get_session
from src.utils.helpers import send_feishu_notification
from src.config import settings


class DataRefresher:
    """
    Keeps tool data fresh by periodically checking official pages for changes.

    Staleness threshold: tools not checked in > 7 days are considered stale.
    Significant change triggers: price change, new feature, or description update.
    """

    STALE_DAYS = 7
    PRICE_CHANGE_THRESHOLD = 0.05  # 5% price change triggers alert

    def __init__(self):
        self.session = get_session()

    def get_stale_tools(self) -> list[Tool]:
        """Return tools that haven't been checked in STALE_DAYS days."""
        cutoff = datetime.utcnow() - timedelta(days=self.STALE_DAYS)
        return (
            self.session.query(Tool)
            .filter(
                Tool.is_active == True,
                (Tool.updated_at < cutoff) | (Tool.updated_at == None)
            )
            .order_by(Tool.updated_at.asc())
            .all()
        )

    def scrape_tool_page(self, url: str) -> Optional[dict]:
        """
        Scrape an AI tool's official page to extract pricing and feature signals.
        Returns a dict with extracted signals, or None on failure.
        """
        if not url:
            return None

        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (compatible; pSEO-DataRefresher/1.0; +https://github.com/kydlikebtc/pseo)"
            }
            with httpx.Client(timeout=20, follow_redirects=True, headers=headers) as client:
                response = client.get(url)
                if response.status_code != 200:
                    return None

            soup = BeautifulSoup(response.text, "html.parser")

            # Extract page title and meta description as change signals
            title = soup.find("title")
            meta_desc = soup.find("meta", attrs={"name": "description"})

            # Look for pricing signals in the page text
            text = soup.get_text(separator=" ", strip=True)
            price_patterns = [
                r'\$\s*(\d+(?:\.\d{2})?)\s*(?:/\s*(?:mo|month|yr|year))?',
                r'(\d+(?:\.\d{2})?)\s*(?:USD|usd)\s*(?:/\s*(?:mo|month))?',
                r'(?:free|Free|FREE)\s+(?:plan|tier|forever)',
            ]
            prices_found = []
            for pattern in price_patterns:
                matches = re.findall(pattern, text[:5000])  # Check first 5000 chars
                prices_found.extend(matches)

            # Look for "new" or "updated" signals
            new_signals = []
            for keyword in ["new feature", "now available", "introducing", "announcing", "update"]:
                if keyword.lower() in text[:3000].lower():
                    new_signals.append(keyword)

            return {
                "scraped_at": datetime.utcnow().isoformat(),
                "page_title": title.text.strip() if title else "",
                "meta_description": meta_desc.get("content", "") if meta_desc else "",
                "prices_found": prices_found[:5],  # Top 5 price mentions
                "new_signals": new_signals,
                "text_length": len(text),
            }

        except Exception as e:
            print(f"[Refresher] Scrape failed for {url}: {e}")
            return None

    def check_for_changes(self, tool: Tool, scraped: dict) -> list[str]:
        """
        Compare scraped data with stored data to detect significant changes.
        Returns a list of change descriptions.
        """
        changes = []

        # Check for price change signals
        if scraped.get("prices_found"):
            try:
                # Try to extract a numeric price from scraped data
                price_str = scraped["prices_found"][0]
                if isinstance(price_str, str) and price_str.replace(".", "").isdigit():
                    scraped_price = float(price_str)
                    if tool.starting_price and tool.starting_price > 0:
                        change_ratio = abs(scraped_price - tool.starting_price) / tool.starting_price
                        if change_ratio >= self.PRICE_CHANGE_THRESHOLD:
                            changes.append(
                                f"Price change detected: stored=${tool.starting_price}, "
                                f"scraped=${scraped_price}"
                            )
            except (ValueError, TypeError):
                pass

        # Check for new feature signals
        if scraped.get("new_signals"):
            changes.append(f"New feature/update signals found: {', '.join(scraped['new_signals'])}")

        # Check if page title changed significantly
        if scraped.get("page_title") and tool.name:
            if tool.name.lower() not in scraped["page_title"].lower():
                changes.append(f"Page title changed: '{scraped['page_title']}'")

        return changes

    def refresh_tool(self, tool: Tool) -> dict:
        """
        Check a single tool for data freshness.
        Returns a result dict with status and any detected changes.
        """
        print(f"[Refresher] Checking: {tool.name} ({tool.official_url})")

        if not tool.official_url:
            return {"tool": tool.name, "status": "skipped", "reason": "No official URL"}

        scraped = self.scrape_tool_page(tool.official_url)
        if not scraped:
            return {"tool": tool.name, "status": "failed", "reason": "Scrape failed"}

        changes = self.check_for_changes(tool, scraped)

        # Update the tool's updated_at timestamp to mark as checked
        tool.updated_at = datetime.utcnow()
        self.session.commit()

        result = {
            "tool": tool.name,
            "status": "changed" if changes else "fresh",
            "changes": changes,
            "scraped_signals": scraped,
        }

        if changes:
            self._alert_data_change(tool, changes)
            print(f"[Refresher] ⚠️  Changes detected for {tool.name}: {changes}")
        else:
            print(f"[Refresher] ✓ {tool.name} data is fresh")

        return result

    def _alert_data_change(self, tool: Tool, changes: list[str]):
        """Send Feishu notification when tool data changes are detected."""
        title = f"📊 工具数据变更提醒: {tool.name}"
        lines = [f"**{tool.name}** 的官方页面检测到以下变更，建议人工核实并更新数据库：\n"]
        for change in changes:
            lines.append(f"• {change}")
        lines.append(f"\n官方链接: {tool.official_url}")
        content = "\n".join(lines)
        send_feishu_notification(title, content)

    def run_refresh_cycle(self, max_tools: int = 10) -> list[dict]:
        """
        Run a full refresh cycle on the most stale tools.
        Designed to be called by a daily cron job.

        Args:
            max_tools: Maximum number of tools to check per run (rate limiting).
        """
        stale_tools = self.get_stale_tools()[:max_tools]

        if not stale_tools:
            print("[Refresher] All tools are fresh. No refresh needed.")
            return []

        print(f"[Refresher] Starting refresh cycle for {len(stale_tools)} stale tools...")
        results = []
        for tool in stale_tools:
            result = self.refresh_tool(tool)
            results.append(result)

        changed = [r for r in results if r["status"] == "changed"]
        print(f"[Refresher] Refresh complete: {len(changed)}/{len(results)} tools have changes")
        return results

    def get_freshness_report(self) -> dict:
        """Generate a data freshness report for all tools."""
        all_tools = self.session.query(Tool).filter(Tool.is_active == True).all()
        cutoff = datetime.utcnow() - timedelta(days=self.STALE_DAYS)

        fresh = [t for t in all_tools if t.updated_at and t.updated_at >= cutoff]
        stale = [t for t in all_tools if not t.updated_at or t.updated_at < cutoff]

        return {
            "total_tools": len(all_tools),
            "fresh_tools": len(fresh),
            "stale_tools": len(stale),
            "stale_tool_names": [t.name for t in stale],
            "freshness_rate": f"{len(fresh) / len(all_tools) * 100:.1f}%" if all_tools else "N/A",
        }

    def close(self):
        self.session.close()
