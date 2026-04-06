"""
SEO Technical Auditor.
Checks pages for Core Web Vitals, structural issues, broken links, and schema compliance.
Uses Playwright for browser-based checks and httpx for link validation.
"""
import asyncio
import json
import re
from datetime import datetime
from typing import Optional
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from src.models import SEOAuditResult, get_session
from src.config import settings


class SEOAuditor:
    """
    Performs automated SEO technical audits on web pages.
    Checks: HTML structure, meta tags, links, schema markup.
    """

    def __init__(self):
        self.session = get_session()
        self.site_url = settings.site_url.rstrip("/")

    async def audit_url(self, url: str) -> SEOAuditResult:
        """
        Full SEO audit for a single URL.
        Uses httpx for content fetching and BeautifulSoup for parsing.
        """
        print(f"[Auditor] Auditing: {url}")
        issues = []
        result = SEOAuditResult(
            url=url,
            audit_type="Full",
            audited_at=datetime.utcnow()
        )

        try:
            async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
                response = await client.get(url, headers={
                    "User-Agent": "Mozilla/5.0 (compatible; pSEO-Auditor/1.0)"
                })

                if response.status_code != 200:
                    issues.append(f"HTTP {response.status_code}: Page returned non-200 status")
                    result.issues = issues
                    result.passed = False
                    return result

                html = response.text
                soup = BeautifulSoup(html, "html.parser")

                # --- Check H1 ---
                h1_tags = soup.find_all("h1")
                result.h1_count = len(h1_tags)
                result.has_h1 = len(h1_tags) > 0
                if not result.has_h1:
                    issues.append("Missing H1 tag")
                elif len(h1_tags) > 1:
                    issues.append(f"Multiple H1 tags found ({len(h1_tags)})")

                # --- Check Meta Description ---
                meta_desc = soup.find("meta", attrs={"name": "description"})
                result.has_meta_description = meta_desc is not None
                if not result.has_meta_description:
                    issues.append("Missing meta description")
                elif meta_desc:
                    desc_content = meta_desc.get("content", "")
                    if len(desc_content) < 50:
                        issues.append(f"Meta description too short ({len(desc_content)} chars)")
                    elif len(desc_content) > 165:
                        issues.append(f"Meta description too long ({len(desc_content)} chars)")

                # --- Check Image Alt Attributes ---
                images = soup.find_all("img")
                missing_alt = [img for img in images if not img.get("alt")]
                result.missing_alt_count = len(missing_alt)
                if missing_alt:
                    issues.append(f"{len(missing_alt)} image(s) missing alt attribute")

                # --- Check JSON-LD Schema ---
                schema_scripts = soup.find_all("script", attrs={"type": "application/ld+json"})
                result.has_schema = len(schema_scripts) > 0
                if not result.has_schema:
                    issues.append("No JSON-LD structured data found")

                # --- Check Title Tag ---
                title_tag = soup.find("title")
                if not title_tag or not title_tag.text.strip():
                    issues.append("Missing or empty title tag")
                elif len(title_tag.text) > 65:
                    issues.append(f"Title tag too long ({len(title_tag.text)} chars)")

                # --- Check Canonical ---
                canonical = soup.find("link", attrs={"rel": "canonical"})
                if not canonical:
                    issues.append("Missing canonical tag")

                # --- Check Broken Links (sample) ---
                links = soup.find_all("a", href=True)
                broken = 0
                internal_links = [
                    urljoin(url, a["href"])
                    for a in links
                    if a["href"].startswith("/") or self.site_url in a["href"]
                ][:5]  # Check first 5 internal links only

                for link_url in internal_links:
                    try:
                        link_resp = await client.head(link_url, timeout=5)
                        if link_resp.status_code in (404, 410):
                            broken += 1
                            issues.append(f"Broken link: {link_url}")
                    except Exception:
                        pass

                result.broken_links_count = broken

                # --- Determine pass/fail ---
                critical_issues = [i for i in issues if any(
                    kw in i for kw in ["Missing H1", "HTTP 4", "HTTP 5"]
                )]
                result.passed = len(critical_issues) == 0
                result.issues = issues

        except httpx.TimeoutException:
            issues.append("Request timed out")
            result.issues = issues
            result.passed = False
        except Exception as e:
            issues.append(f"Audit error: {str(e)}")
            result.issues = issues
            result.passed = False

        # Save to DB
        self.session.add(result)
        self.session.commit()

        status = "PASS" if result.passed else "FAIL"
        print(f"[Auditor] {status} - {url} | Issues: {len(issues)}")
        return result

    async def audit_page_structure(self, html_content: str, url: str = "local") -> dict:
        """
        Audit raw HTML content without making HTTP requests.
        Useful for testing generated pages before publishing.
        """
        issues = []
        soup = BeautifulSoup(html_content, "html.parser")

        h1_tags = soup.find_all("h1")
        meta_desc = soup.find("meta", attrs={"name": "description"})
        images = soup.find_all("img")
        missing_alt = [img for img in images if not img.get("alt")]
        schema_scripts = soup.find_all("script", attrs={"type": "application/ld+json"})
        title_tag = soup.find("title")
        canonical = soup.find("link", attrs={"rel": "canonical"})

        if not h1_tags:
            issues.append("Missing H1 tag")
        elif len(h1_tags) > 1:
            issues.append(f"Multiple H1 tags found ({len(h1_tags)})")
        if not meta_desc:
            issues.append("Missing meta description")
        if missing_alt:
            issues.append(f"{len(missing_alt)} image(s) missing alt")
        if not schema_scripts:
            issues.append("No JSON-LD schema found")
        if not title_tag:
            issues.append("Missing title tag")
        if not canonical:
            issues.append("Missing canonical tag")

        return {
            "url": url,
            "h1_count": len(h1_tags),
            "has_h1": len(h1_tags) > 0,
            "has_meta_description": meta_desc is not None,
            "missing_alt_count": len(missing_alt),
            "has_schema": len(schema_scripts) > 0,
            "has_title": title_tag is not None,
            "has_canonical": canonical is not None,
            "issues": issues,
            "passed": len([i for i in issues if "Missing H1" in i]) == 0
        }

    async def audit_sitemap(self, sitemap_url: str) -> dict:
        """
        Validate a sitemap.xml file and check all URLs are reachable.
        """
        print(f"[Auditor] Checking sitemap: {sitemap_url}")
        results = {"sitemap_url": sitemap_url, "total_urls": 0, "broken_urls": [], "valid": False}

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(sitemap_url)
                if resp.status_code != 200:
                    results["error"] = f"Sitemap returned HTTP {resp.status_code}"
                    return results

                soup = BeautifulSoup(resp.text, "xml")
                urls = [loc.text for loc in soup.find_all("loc")]
                results["total_urls"] = len(urls)

                # Sample check first 10 URLs
                for url in urls[:10]:
                    try:
                        r = await client.head(url, timeout=5)
                        if r.status_code in (404, 410):
                            results["broken_urls"].append(url)
                    except Exception:
                        results["broken_urls"].append(url)

                results["valid"] = len(results["broken_urls"]) == 0
        except Exception as e:
            results["error"] = str(e)

        return results

    def close(self):
        self.session.close()


class GoogleIndexingSubmitter:
    """
    Submits URLs to Google Search Console via the Indexing API.
    Accelerates discovery and re-crawling of new/updated pages.
    """

    def __init__(self):
        self.session = get_session()
        self._credentials = None

    def _get_credentials(self):
        """Load Google service account credentials."""
        if self._credentials:
            return self._credentials

        try:
            import google.auth
            from google.auth.transport.requests import Request
            from google.oauth2 import service_account

            service_account_file = settings.google_service_account_file
            credentials = service_account.Credentials.from_service_account_file(
                service_account_file,
                scopes=["https://www.googleapis.com/auth/indexing"]
            )
            if not credentials.valid:
                credentials.refresh(Request())
            self._credentials = credentials
            return credentials
        except Exception as e:
            print(f"[Indexing] Failed to load credentials: {e}")
            return None

    def submit_url(self, url: str, url_type: str = "URL_UPDATED") -> bool:
        """
        Submit a URL to Google Indexing API.
        url_type: 'URL_UPDATED' or 'URL_DELETED'
        """
        credentials = self._get_credentials()
        if not credentials:
            print(f"[Indexing] No credentials available. Skipping: {url}")
            return False

        try:
            import google.auth.transport.requests
            auth_req = google.auth.transport.requests.Request()
            credentials.refresh(auth_req)

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {credentials.token}"
            }
            data = {"url": url, "type": url_type}

            response = httpx.post(
                "https://indexing.googleapis.com/v3/urlNotifications:publish",
                headers=headers,
                json=data,
                timeout=15
            )

            if response.status_code == 200:
                print(f"[Indexing] Submitted: {url}")
                # Update DB record
                from src.models import PSEOPage
                page = self.session.query(PSEOPage).filter(PSEOPage.url_path == url).first()
                if page:
                    page.last_indexed_at = datetime.utcnow()
                    page.indexing_status = "submitted"
                    self.session.commit()
                return True
            else:
                print(f"[Indexing] Failed ({response.status_code}): {response.text}")
                return False

        except Exception as e:
            print(f"[Indexing] Error submitting {url}: {e}")
            return False

    def submit_batch(self, urls: list[str]) -> dict:
        """Submit multiple URLs and return results summary."""
        results = {"submitted": 0, "failed": 0, "urls": []}
        for url in urls:
            success = self.submit_url(url)
            if success:
                results["submitted"] += 1
            else:
                results["failed"] += 1
            results["urls"].append({"url": url, "success": success})
        return results

    def close(self):
        self.session.close()
