"""
Keyword Planner — Keyword matrix planning and search intent classification.

Implements the playbook requirement:
  "搜索词的竞争难度决定了切入策略，而搜索意图则决定了页面的形态和优先级。"
  "ICP 细分：使用者（功能/模板）、购买者（对比/价格）、学习者（教程/最佳实践）"

This module:
1. Generates keyword matrices from tool and category data.
2. Classifies keywords by search intent (Informational/Commercial/Transactional).
3. Maps keywords to page types (Alternative/Comparison/Listicle/Tutorial/Landing).
4. Prioritizes keywords by difficulty and search volume for pSEO page generation.
"""
import json
from typing import Optional

from src.models import Tool, Category, KeywordMatrix, get_session
from src.engine.llm_generator import LLMContentGenerator
from src.utils.helpers import slugify


class KeywordPlanner:
    """
    Plans and manages the keyword matrix for pSEO page generation.

    ICP Segmentation (from the playbook):
    - Buyers   (Commercial intent)     → Alternative + Comparison pages
    - Learners (Informational intent)  → Tutorial + Listicle pages
    - Converters (Transactional intent) → Landing pages
    """

    # Keyword templates by page type and intent
    KEYWORD_TEMPLATES = {
        "Alternative": [
            "{tool} alternatives",
            "best {tool} alternatives",
            "{tool} alternatives free",
            "tools like {tool}",
            "{tool} competitors",
            "replace {tool}",
        ],
        "Comparison": [
            "{tool_a} vs {tool_b}",
            "{tool_a} vs {tool_b} comparison",
            "{tool_a} or {tool_b}",
            "difference between {tool_a} and {tool_b}",
            "{tool_a} vs {tool_b} which is better",
        ],
        "Listicle": [
            "best {category}",
            "top {category} tools",
            "best {category} 2025",
            "best free {category}",
            "{category} tools list",
        ],
        "Tutorial": [
            "how to use {tool}",
            "how to use {tool} for {task}",
            "{tool} tutorial",
            "{tool} guide for beginners",
            "getting started with {tool}",
        ],
        "Landing": [
            "{tool}",
            "{tool} pricing",
            "{tool} review",
            "{tool} features",
            "{tool} free trial",
        ],
    }

    INTENT_MAP = {
        "Alternative": "Commercial",
        "Comparison": "Commercial",
        "Listicle": "Informational",
        "Tutorial": "Informational",
        "Landing": "Transactional",
    }

    DIFFICULTY_MAP = {
        # High-volume head terms are harder
        "best {category}": "High",
        "{tool}": "High",
        "{tool} alternatives": "Medium",
        "{tool_a} vs {tool_b}": "Medium",
        "how to use {tool} for {task}": "Low",
        "{tool} tutorial": "Low",
        "tools like {tool}": "Low",
    }

    def __init__(self):
        self.session = get_session()
        self.llm = LLMContentGenerator()

    def generate_keyword_matrix(
        self,
        category_slug: str,
        tasks: list[str] = None
    ) -> list[KeywordMatrix]:
        """
        Generate a full keyword matrix for a category.
        Creates keywords for all page types: Alternative, Comparison, Listicle, Tutorial, Landing.

        Args:
            category_slug: The category to generate keywords for.
            tasks: Optional list of tasks for Tutorial keyword generation.
        """
        category = self.session.query(Category).filter(Category.slug == category_slug).first()
        if not category:
            print(f"[Planner] Category not found: {category_slug}")
            return []

        tools = (
            self.session.query(Tool)
            .join(Tool.category_relations)
            .join(Category, Category.id == Tool.category_relations.property.mapper.class_.category_id)
            .filter(Category.slug == category_slug, Tool.is_active == True)
            .all()
        )

        created = []
        tasks = tasks or ["generate content", "improve productivity", "automate tasks"]

        # --- Listicle keywords (one per category) ---
        for template in self.KEYWORD_TEMPLATES["Listicle"]:
            kw = template.format(category=category.name.lower())
            created.append(self._create_keyword(
                keyword=kw,
                page_type="Listicle",
                category=category,
                difficulty=self._estimate_difficulty(template)
            ))

        # --- Per-tool keywords ---
        for tool in tools:
            # Alternative keywords
            for template in self.KEYWORD_TEMPLATES["Alternative"]:
                kw = template.format(tool=tool.name)
                created.append(self._create_keyword(
                    keyword=kw,
                    page_type="Alternative",
                    category=category,
                    difficulty=self._estimate_difficulty(template)
                ))

            # Tutorial keywords
            for task in tasks:
                for template in self.KEYWORD_TEMPLATES["Tutorial"]:
                    kw = template.format(tool=tool.name, task=task)
                    created.append(self._create_keyword(
                        keyword=kw,
                        page_type="Tutorial",
                        category=category,
                        difficulty=self._estimate_difficulty(template)
                    ))

            # Landing keywords
            for template in self.KEYWORD_TEMPLATES["Landing"]:
                kw = template.format(tool=tool.name)
                created.append(self._create_keyword(
                    keyword=kw,
                    page_type="Landing",
                    category=category,
                    difficulty=self._estimate_difficulty(template)
                ))

        # --- Pairwise comparison keywords ---
        for i, tool_a in enumerate(tools):
            for tool_b in tools[i + 1:]:
                for template in self.KEYWORD_TEMPLATES["Comparison"]:
                    kw = template.format(tool_a=tool_a.name, tool_b=tool_b.name)
                    created.append(self._create_keyword(
                        keyword=kw,
                        page_type="Comparison",
                        category=category,
                        difficulty=self._estimate_difficulty(template)
                    ))

        self.session.commit()
        print(f"[Planner] Generated {len(created)} keywords for category: {category.name}")
        return created

    def _create_keyword(
        self,
        keyword: str,
        page_type: str,
        category: Category,
        difficulty: str = "Medium"
    ) -> KeywordMatrix:
        """Create or retrieve a keyword matrix entry."""
        existing = self.session.query(KeywordMatrix).filter(
            KeywordMatrix.keyword == keyword
        ).first()
        if existing:
            return existing

        kw = KeywordMatrix(
            keyword=keyword,
            intent_type=self.INTENT_MAP.get(page_type, "Informational"),
            difficulty=difficulty,
            page_type_suggestion=page_type,
            category_id=category.id,
            is_processed=False,
        )
        self.session.add(kw)
        return kw

    def _estimate_difficulty(self, template: str) -> str:
        """Estimate keyword difficulty based on template pattern."""
        for pattern, difficulty in self.DIFFICULTY_MAP.items():
            # Simple pattern matching
            if pattern.split("{")[0].strip() in template:
                return difficulty
        return "Medium"

    def get_priority_keywords(
        self,
        category_slug: str = None,
        page_type: str = None,
        difficulty: str = "Low",
        limit: int = 20
    ) -> list[KeywordMatrix]:
        """
        Get unprocessed keywords prioritized by difficulty (Low first = quick wins).
        This implements the playbook's 'low-difficulty first' entry strategy.
        """
        query = self.session.query(KeywordMatrix).filter(
            KeywordMatrix.is_processed == False
        )

        if category_slug:
            category = self.session.query(Category).filter(Category.slug == category_slug).first()
            if category:
                query = query.filter(KeywordMatrix.category_id == category.id)

        if page_type:
            query = query.filter(KeywordMatrix.page_type_suggestion == page_type)

        if difficulty:
            # Priority order: Low → Medium → High
            difficulty_order = {"Low": 0, "Medium": 1, "High": 2}
            all_kws = query.all()
            all_kws.sort(key=lambda k: difficulty_order.get(k.difficulty, 1))
            return all_kws[:limit]

        return query.limit(limit).all()

    def mark_processed(self, keyword_id: str):
        """Mark a keyword as processed (page generated)."""
        kw = self.session.query(KeywordMatrix).filter(KeywordMatrix.id == keyword_id).first()
        if kw:
            kw.is_processed = True
            self.session.commit()

    def get_keyword_stats(self) -> dict:
        """Get keyword matrix statistics."""
        all_kws = self.session.query(KeywordMatrix).all()
        stats = {
            "total": len(all_kws),
            "processed": len([k for k in all_kws if k.is_processed]),
            "pending": len([k for k in all_kws if not k.is_processed]),
            "by_intent": {},
            "by_page_type": {},
            "by_difficulty": {},
        }
        for kw in all_kws:
            stats["by_intent"][kw.intent_type] = stats["by_intent"].get(kw.intent_type, 0) + 1
            stats["by_page_type"][kw.page_type_suggestion] = stats["by_page_type"].get(kw.page_type_suggestion, 0) + 1
            stats["by_difficulty"][kw.difficulty] = stats["by_difficulty"].get(kw.difficulty, 0) + 1
        return stats

    def close(self):
        self.session.close()
