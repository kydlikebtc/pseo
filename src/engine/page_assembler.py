"""
pSEO Page Assembly Engine.
Orchestrates data fetching, LLM generation, template assembly, and schema injection.
Implements the core pSEO formula: Template × Structured Data × Automation

Supported page types (aligned with the SEO playbook):
- Alternative  : /alternatives/{tool}       — Commercial intent (Buyers)
- Comparison   : /compare/{tool-a}-vs-{tool-b} — Commercial intent (Buyers)
- Listicle     : /best/{category}           — Informational intent (Discoverers)
- Tutorial     : /how-to/{task}/{tool}      — Informational intent (Learners)
- Landing      : /tools/{tool}              — Transactional intent (Buyers)
- Internal Link Map: generate_internal_link_map() — SEO weight guidance system
"""
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from src.models import Tool, Category, ToolCategory, PSEOPage, KeywordMatrix, get_session
from src.engine.llm_generator import LLMContentGenerator
from src.utils.helpers import slugify, count_words, build_json_ld_software, build_json_ld_faq
from src.config import settings


class PageAssembler:
    """
    Assembles pSEO pages by combining structured DB data with LLM-generated content.

    Implements the full ICP (Ideal Customer Profile) segmentation from the playbook:
    - Buyers   → Alternative + Comparison pages (Commercial intent)
    - Learners → Tutorial pages (Informational intent)
    - Converters → Landing pages (Transactional intent)
    """

    def __init__(self, session: Optional[Session] = None):
        self.session = session or get_session()
        self.llm = LLMContentGenerator()

    def _get_tool_by_slug(self, slug: str) -> Optional[Tool]:
        return self.session.query(Tool).filter(Tool.slug == slug, Tool.is_active == True).first()

    def _get_tools_in_category(self, category_slug: str, exclude_slug: str = None, limit: int = 5) -> list[Tool]:
        query = (
            self.session.query(Tool)
            .join(ToolCategory, Tool.id == ToolCategory.tool_id)
            .join(Category, ToolCategory.category_id == Category.id)
            .filter(Category.slug == category_slug, Tool.is_active == True)
            .order_by(Tool.rating.desc())
        )
        if exclude_slug:
            query = query.filter(Tool.slug != exclude_slug)
        return query.limit(limit).all()

    def _save_page(
        self,
        page_type: str,
        primary_keyword: str,
        url_path: str,
        template_id: str,
        content: dict,
        schema: dict,
        primary_tool_id: str = None,
        category_id: str = None,
    ) -> PSEOPage:
        """Shared helper to persist a generated page to the database."""
        # Calculate word count from all text fields
        text_parts = []
        for key in ["intro", "why_look_for_alternatives", "conclusion", "advanced_tips",
                    "hero_headline", "hero_subheadline", "comparison_summary"]:
            val = content.get(key, "")
            if isinstance(val, str):
                text_parts.append(val)
        # Also count nested text
        for key in ["detailed_comparison"]:
            val = content.get(key, {})
            if isinstance(val, dict):
                text_parts.extend(str(v) for v in val.values())
        wc = count_words(" ".join(text_parts))

        page = PSEOPage(
            page_type=page_type,
            primary_keyword=primary_keyword,
            url_path=url_path,
            template_id=template_id,
            title=content.get("title", primary_keyword),
            meta_description=content.get("meta_description", ""),
            h1=content.get("h1", primary_keyword),
            generated_content=content,
            schema_json=schema,
            word_count=wc,
            status="Draft",
            primary_tool_id=primary_tool_id,
            category_id=category_id,
        )
        self.session.add(page)
        self.session.commit()
        self.session.refresh(page)
        print(f"[Assembler] Created {page_type} page: {url_path} ({wc} words)")
        return page

    # -------------------------------------------------------------------------
    # Commercial Intent Pages (Buyers)
    # -------------------------------------------------------------------------

    def assemble_alternative_page(self, target_slug: str, category_slug: str) -> Optional[PSEOPage]:
        """
        Assemble a '{tool} alternatives' page.
        URL: /alternatives/{tool-slug}
        Intent: Commercial — readers evaluating whether to switch tools.
        """
        target_tool = self._get_tool_by_slug(target_slug)
        if not target_tool:
            print(f"[Assembler] Tool not found: {target_slug}")
            return None

        alternatives = self._get_tools_in_category(category_slug, exclude_slug=target_slug, limit=6)
        if len(alternatives) < 2:
            print(f"[Assembler] Not enough alternatives for {target_slug}")
            return None

        url_path = f"/alternatives/{target_slug}"
        primary_keyword = f"{target_tool.name} alternatives"

        existing = self.session.query(PSEOPage).filter(PSEOPage.url_path == url_path).first()
        if existing:
            print(f"[Assembler] Page already exists: {url_path}")
            return existing

        print(f"[Assembler] Generating alternative page for: {target_tool.name}")
        content = self.llm.generate_alternatives_page(
            target_tool=target_tool.to_dict(),
            alternatives=[t.to_dict() for t in alternatives],
            primary_keyword=primary_keyword
        )

        faqs = content.get("faqs", [])
        schema = build_json_ld_faq(faqs) if faqs else {}

        return self._save_page(
            page_type="Alternative",
            primary_keyword=primary_keyword,
            url_path=url_path,
            template_id="alternatives_v1",
            content=content,
            schema=schema,
            primary_tool_id=target_tool.id,
        )

    def assemble_comparison_page(self, slug_a: str, slug_b: str) -> Optional[PSEOPage]:
        """
        Assemble a 'Tool A vs Tool B' comparison page.
        URL: /compare/{tool-a}-vs-{tool-b}
        Intent: Commercial — readers making a final purchase decision.
        """
        tool_a = self._get_tool_by_slug(slug_a)
        tool_b = self._get_tool_by_slug(slug_b)

        if not tool_a or not tool_b:
            print(f"[Assembler] One or both tools not found: {slug_a}, {slug_b}")
            return None

        url_path = f"/compare/{slug_a}-vs-{slug_b}"
        primary_keyword = f"{tool_a.name} vs {tool_b.name}"

        existing = self.session.query(PSEOPage).filter(PSEOPage.url_path == url_path).first()
        if existing:
            return existing

        print(f"[Assembler] Generating comparison page: {primary_keyword}")
        content = self.llm.generate_comparison_page(
            tool_a=tool_a.to_dict(),
            tool_b=tool_b.to_dict(),
            primary_keyword=primary_keyword
        )

        faqs = content.get("faqs", [])
        schema = build_json_ld_faq(faqs) if faqs else {}

        return self._save_page(
            page_type="Comparison",
            primary_keyword=primary_keyword,
            url_path=url_path,
            template_id="comparison_v1",
            content=content,
            schema=schema,
            primary_tool_id=tool_a.id,
        )

    # -------------------------------------------------------------------------
    # Informational Intent Pages (Discoverers & Learners)
    # -------------------------------------------------------------------------

    def assemble_listicle_page(self, category_slug: str, limit: int = 10) -> Optional[PSEOPage]:
        """
        Assemble a 'Best X tools' listicle page (Hub page in internal link architecture).
        URL: /best/{category-slug}
        Intent: Informational — readers discovering options for the first time.
        """
        category = self.session.query(Category).filter(Category.slug == category_slug).first()
        if not category:
            print(f"[Assembler] Category not found: {category_slug}")
            return None

        tools = self._get_tools_in_category(category_slug, limit=limit)
        if len(tools) < 3:
            print(f"[Assembler] Not enough tools in category: {category_slug}")
            return None

        url_path = f"/best/{category_slug}"
        primary_keyword = f"best {category.name.lower()}"

        existing = self.session.query(PSEOPage).filter(PSEOPage.url_path == url_path).first()
        if existing:
            return existing

        print(f"[Assembler] Generating listicle page for category: {category.name}")
        content = self.llm.generate_listicle_page(
            tools=[t.to_dict() for t in tools],
            category_name=category.name,
            primary_keyword=primary_keyword
        )

        faqs = content.get("faqs", [])
        schema = build_json_ld_faq(faqs) if faqs else {}

        return self._save_page(
            page_type="Listicle",
            primary_keyword=primary_keyword,
            url_path=url_path,
            template_id="listicle_v1",
            content=content,
            schema=schema,
            category_id=category.id,
        )

    def assemble_tutorial_page(
        self,
        tool_slug: str,
        task: str,
        target_audience: str = "beginners"
    ) -> Optional[PSEOPage]:
        """
        Assemble a 'How to use X for Y' tutorial page.
        URL: /how-to/{task-slug}/{tool-slug}
        Intent: Informational — Learners in the ICP model seeking step-by-step guidance.

        Args:
            tool_slug: The tool to write the tutorial for.
            task: The task to accomplish (e.g. "generate images from text").
            target_audience: "beginners", "intermediate", or "advanced".
        """
        tool = self._get_tool_by_slug(tool_slug)
        if not tool:
            print(f"[Assembler] Tool not found: {tool_slug}")
            return None

        task_slug = slugify(task)
        url_path = f"/how-to/{task_slug}/{tool_slug}"
        primary_keyword = f"how to use {tool.name} for {task}"

        existing = self.session.query(PSEOPage).filter(PSEOPage.url_path == url_path).first()
        if existing:
            print(f"[Assembler] Page already exists: {url_path}")
            return existing

        print(f"[Assembler] Generating tutorial page: {primary_keyword}")
        content = self.llm.generate_tutorial_page(
            tool=tool.to_dict(),
            task=task,
            primary_keyword=primary_keyword,
            target_audience=target_audience
        )

        faqs = content.get("faqs", [])
        # Tutorial pages use HowTo schema
        schema = {
            "@context": "https://schema.org",
            "@type": "HowTo",
            "name": content.get("title", primary_keyword),
            "description": content.get("meta_description", ""),
            "step": [
                {
                    "@type": "HowToStep",
                    "position": s.get("step_number", i + 1),
                    "name": s.get("heading", ""),
                    "text": s.get("description", "")
                }
                for i, s in enumerate(content.get("steps", []))
            ]
        }
        # Also add FAQ schema if present
        if faqs:
            faq_schema = build_json_ld_faq(faqs)
            schema = [schema, faq_schema]

        return self._save_page(
            page_type="Tutorial",
            primary_keyword=primary_keyword,
            url_path=url_path,
            template_id="tutorial_v1",
            content=content,
            schema=schema if isinstance(schema, dict) else {"schemas": schema},
            primary_tool_id=tool.id,
        )

    # -------------------------------------------------------------------------
    # Transactional Intent Pages (Converters)
    # -------------------------------------------------------------------------

    def assemble_landing_page(
        self,
        tool_slug: str,
        cta_action: str = "Start Free Trial"
    ) -> Optional[PSEOPage]:
        """
        Assemble a tool landing/feature page.
        URL: /tools/{tool-slug}
        Intent: Transactional — readers ready to sign up or buy.
        Uses SoftwareApplication schema for rich snippets.
        """
        tool = self._get_tool_by_slug(tool_slug)
        if not tool:
            print(f"[Assembler] Tool not found: {tool_slug}")
            return None

        url_path = f"/tools/{tool_slug}"
        primary_keyword = f"{tool.name} - {tool.description[:50] if tool.description else 'AI Tool'}"

        existing = self.session.query(PSEOPage).filter(PSEOPage.url_path == url_path).first()
        if existing:
            print(f"[Assembler] Page already exists: {url_path}")
            return existing

        print(f"[Assembler] Generating landing page for: {tool.name}")
        content = self.llm.generate_landing_page(
            tool=tool.to_dict(),
            primary_keyword=tool.name,
            cta_action=cta_action
        )

        # Landing pages use SoftwareApplication schema for rich snippets
        schema = build_json_ld_software(tool.to_dict())

        return self._save_page(
            page_type="Landing",
            primary_keyword=tool.name,
            url_path=url_path,
            template_id="landing_v1",
            content=content,
            schema=schema,
            primary_tool_id=tool.id,
        )

    # -------------------------------------------------------------------------
    # Internal Link Architecture
    # -------------------------------------------------------------------------

    def generate_internal_link_map(self, site_name: str = None) -> dict:
        """
        Generate an internal linking strategy for all published/draft pages.
        Implements the 'internal links as weight guidance system' from the playbook.
        Hub pages (listicles) link to spoke pages (alternatives, comparisons).
        Spoke pages link back to hubs and to related spokes.

        Returns a dict with the full link map and priority recommendations.
        """
        if not site_name:
            site_name = settings.site_url

        pages = self.session.query(PSEOPage).filter(
            PSEOPage.status.in_(["Draft", "Published"])
        ).all()

        if len(pages) < 2:
            print("[Assembler] Not enough pages to generate internal link map")
            return {}

        pages_data = [
            {
                "url_path": p.url_path,
                "page_type": p.page_type,
                "primary_keyword": p.primary_keyword,
                "title": p.title,
            }
            for p in pages
        ]

        print(f"[Assembler] Generating internal link map for {len(pages)} pages...")
        link_map = self.llm.generate_internal_link_map(
            pages=pages_data,
            site_name=site_name
        )
        return link_map

    # -------------------------------------------------------------------------
    # Batch Operations
    # -------------------------------------------------------------------------

    def batch_generate_alternatives(self, category_slug: str) -> list[PSEOPage]:
        """
        Batch generate alternative pages for all tools in a category.
        Core pSEO automation: one category → N alternative pages.
        """
        tools = self._get_tools_in_category(category_slug)
        pages = []
        for tool in tools:
            page = self.assemble_alternative_page(tool.slug, category_slug)
            if page:
                pages.append(page)
        return pages

    def batch_generate_comparisons(self, category_slug: str) -> list[PSEOPage]:
        """
        Batch generate all pairwise comparison pages for tools in a category.
        N tools → N*(N-1)/2 comparison pages.
        """
        tools = self._get_tools_in_category(category_slug, limit=20)
        pages = []
        for i, tool_a in enumerate(tools):
            for tool_b in tools[i + 1:]:
                page = self.assemble_comparison_page(tool_a.slug, tool_b.slug)
                if page:
                    pages.append(page)
        return pages

    def batch_generate_tutorials(self, tool_slug: str, tasks: list[str]) -> list[PSEOPage]:
        """
        Batch generate tutorial pages for a tool across multiple tasks.
        One tool × N tasks → N tutorial pages.
        """
        pages = []
        for task in tasks:
            page = self.assemble_tutorial_page(tool_slug, task)
            if page:
                pages.append(page)
        return pages

    # -------------------------------------------------------------------------
    # Page Management
    # -------------------------------------------------------------------------

    def publish_page(self, page_id: str) -> bool:
        """Mark a draft page as published."""
        page = self.session.query(PSEOPage).filter(PSEOPage.id == page_id).first()
        if not page:
            return False
        page.status = "Published"
        page.published_at = datetime.utcnow()
        self.session.commit()
        return True

    def publish_all_drafts(self) -> int:
        """Publish all draft pages. Returns count of published pages."""
        drafts = self.session.query(PSEOPage).filter(PSEOPage.status == "Draft").all()
        for page in drafts:
            page.status = "Published"
            page.published_at = datetime.utcnow()
        self.session.commit()
        return len(drafts)

    def get_pages_summary(self) -> dict:
        """Get a summary of all pages by type and status."""
        pages = self.session.query(PSEOPage).all()
        summary = {
            "total": len(pages),
            "by_type": {},
            "by_status": {},
        }
        for page in pages:
            summary["by_type"][page.page_type] = summary["by_type"].get(page.page_type, 0) + 1
            summary["by_status"][page.status] = summary["by_status"].get(page.status, 0) + 1
        return summary

    def close(self):
        self.session.close()
