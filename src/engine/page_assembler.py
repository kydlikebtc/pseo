"""
pSEO Page Assembly Engine.
Orchestrates data fetching, LLM generation, template assembly, and schema injection.
Implements the core pSEO formula: Template × Structured Data × Automation
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
    Supports three page types: Alternative, Comparison, Listicle.
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

    def assemble_alternative_page(self, target_slug: str, category_slug: str) -> Optional[PSEOPage]:
        """
        Assemble a '{tool} alternatives' page.
        e.g. /alternatives/midjourney
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

        # Check if page already exists
        existing = self.session.query(PSEOPage).filter(PSEOPage.url_path == url_path).first()
        if existing:
            print(f"[Assembler] Page already exists: {url_path}")
            return existing

        print(f"[Assembler] Generating alternative page for: {target_tool.name}")

        # Generate content via LLM
        content = self.llm.generate_alternatives_page(
            target_tool=target_tool.to_dict(),
            alternatives=[t.to_dict() for t in alternatives],
            primary_keyword=primary_keyword
        )

        # Build JSON-LD schema
        faqs = content.get("faqs", [])
        schema = build_json_ld_faq(faqs) if faqs else {}

        # Calculate word count
        full_text = " ".join([
            content.get("intro", ""),
            content.get("why_look_for_alternatives", ""),
            content.get("conclusion", ""),
        ])
        wc = count_words(full_text)

        # Create page record
        page = PSEOPage(
            page_type="Alternative",
            primary_keyword=primary_keyword,
            url_path=url_path,
            template_id="alternatives_v1",
            title=content.get("title", f"Best {target_tool.name} Alternatives"),
            meta_description=content.get("meta_description", ""),
            h1=content.get("h1", primary_keyword),
            generated_content=content,
            schema_json=schema,
            word_count=wc,
            status="Draft",
            primary_tool_id=target_tool.id,
        )

        self.session.add(page)
        self.session.commit()
        self.session.refresh(page)
        print(f"[Assembler] Created page: {url_path} ({wc} words)")
        return page

    def assemble_comparison_page(self, slug_a: str, slug_b: str) -> Optional[PSEOPage]:
        """
        Assemble a 'Tool A vs Tool B' comparison page.
        e.g. /compare/chatgpt-vs-claude
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

        full_text = " ".join([
            content.get("intro", ""),
            content.get("conclusion", ""),
        ])
        wc = count_words(full_text)

        page = PSEOPage(
            page_type="Comparison",
            primary_keyword=primary_keyword,
            url_path=url_path,
            template_id="comparison_v1",
            title=content.get("title", f"{tool_a.name} vs {tool_b.name}"),
            meta_description=content.get("meta_description", ""),
            h1=content.get("h1", primary_keyword),
            generated_content=content,
            schema_json=schema,
            word_count=wc,
            status="Draft",
            primary_tool_id=tool_a.id,
        )

        self.session.add(page)
        self.session.commit()
        self.session.refresh(page)
        print(f"[Assembler] Created page: {url_path} ({wc} words)")
        return page

    def assemble_listicle_page(self, category_slug: str, limit: int = 10) -> Optional[PSEOPage]:
        """
        Assemble a 'Best X tools' listicle page.
        e.g. /best/ai-image-generators
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

        full_text = " ".join([
            content.get("intro", ""),
            content.get("conclusion", ""),
        ])
        wc = count_words(full_text)

        page = PSEOPage(
            page_type="Listicle",
            primary_keyword=primary_keyword,
            url_path=url_path,
            template_id="listicle_v1",
            title=content.get("title", f"Best {category.name}"),
            meta_description=content.get("meta_description", ""),
            h1=content.get("h1", primary_keyword),
            generated_content=content,
            schema_json=schema,
            word_count=wc,
            status="Draft",
            category_id=category.id,
        )

        self.session.add(page)
        self.session.commit()
        self.session.refresh(page)
        print(f"[Assembler] Created page: {url_path} ({wc} words)")
        return page

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

    def publish_page(self, page_id: str) -> bool:
        """Mark a draft page as published."""
        page = self.session.query(PSEOPage).filter(PSEOPage.id == page_id).first()
        if not page:
            return False
        page.status = "Published"
        page.published_at = datetime.utcnow()
        self.session.commit()
        return True

    def close(self):
        self.session.close()
