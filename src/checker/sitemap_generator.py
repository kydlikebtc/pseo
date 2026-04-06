"""
Sitemap generator for pSEO pages.
Automatically generates sitemap.xml from published pages in the database.
"""
from datetime import datetime
from typing import Optional
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom

from src.models import PSEOPage, get_session
from src.config import settings


class SitemapGenerator:
    """
    Generates sitemap.xml from published pSEO pages.
    Supports priority and changefreq configuration per page type.
    """

    PAGE_TYPE_CONFIG = {
        "Alternative": {"priority": "0.8", "changefreq": "weekly"},
        "Comparison": {"priority": "0.8", "changefreq": "weekly"},
        "Listicle": {"priority": "0.9", "changefreq": "daily"},
        "Tutorial": {"priority": "0.7", "changefreq": "monthly"},
        "Landing": {"priority": "1.0", "changefreq": "daily"},
    }

    def __init__(self):
        self.session = get_session()
        self.site_url = settings.site_url.rstrip("/")

    def generate(self, output_path: str = "sitemap.xml", include_drafts: bool = False) -> str:
        """
        Generate sitemap.xml from database pages.
        Returns the XML string and optionally writes to file.
        """
        query = self.session.query(PSEOPage)
        if not include_drafts:
            query = query.filter(PSEOPage.status == "Published")

        pages = query.order_by(PSEOPage.updated_at.desc()).all()

        urlset = Element("urlset")
        urlset.set("xmlns", "http://www.sitemaps.org/schemas/sitemap/0.9")

        for page in pages:
            url_elem = SubElement(urlset, "url")

            loc = SubElement(url_elem, "loc")
            loc.text = f"{self.site_url}{page.url_path}"

            lastmod = SubElement(url_elem, "lastmod")
            updated = page.updated_at or page.created_at or datetime.utcnow()
            lastmod.text = updated.strftime("%Y-%m-%d")

            config = self.PAGE_TYPE_CONFIG.get(page.page_type, {"priority": "0.7", "changefreq": "weekly"})

            changefreq = SubElement(url_elem, "changefreq")
            changefreq.text = config["changefreq"]

            priority = SubElement(url_elem, "priority")
            priority.text = config["priority"]

        # Pretty print XML
        xml_str = minidom.parseString(tostring(urlset, encoding="unicode")).toprettyxml(indent="  ")
        # Remove the extra XML declaration added by toprettyxml
        xml_str = "\n".join(xml_str.split("\n")[1:])
        xml_output = f'<?xml version="1.0" encoding="UTF-8"?>\n{xml_str}'

        if output_path:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(xml_output)
            print(f"[Sitemap] Generated {output_path} with {len(pages)} URLs")

        return xml_output

    def close(self):
        self.session.close()
