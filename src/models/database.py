"""
SQLAlchemy ORM models for the pSEO system.
Implements the full data schema designed in the technical specification.
"""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Column, String, Text, Float, Integer, Boolean,
    DateTime, Enum, ForeignKey, JSON, create_engine
)
from sqlalchemy.orm import DeclarativeBase, relationship, Session
from sqlalchemy.dialects.sqlite import TEXT

from src.config import settings


class Base(DeclarativeBase):
    pass


def generate_uuid() -> str:
    return str(uuid.uuid4())


class Tool(Base):
    """Core AI tool entity with structured attributes for pSEO content generation."""
    __tablename__ = "tools"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(200), nullable=False, index=True)
    slug = Column(String(200), nullable=False, unique=True, index=True)
    description = Column(Text)
    official_url = Column(String(500))
    pricing_model = Column(
        Enum("Free", "Freemium", "Paid", "Enterprise", name="pricing_model_enum"),
        default="Freemium"
    )
    starting_price = Column(Float, default=0.0)
    features = Column(JSON, default=list)       # List[str]
    pros = Column(JSON, default=list)            # List[str]
    cons = Column(JSON, default=list)            # List[str]
    use_cases = Column(JSON, default=list)       # List[str]
    rating = Column(Float, default=0.0)
    monthly_users = Column(Integer, default=0)
    founded_year = Column(Integer)
    logo_url = Column(String(500))
    screenshot_url = Column(String(500))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    category_relations = relationship("ToolCategory", back_populates="tool", cascade="all, delete-orphan")
    pseo_pages = relationship("PSEOPage", back_populates="primary_tool")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "slug": self.slug,
            "description": self.description,
            "official_url": self.official_url,
            "pricing_model": self.pricing_model,
            "starting_price": self.starting_price,
            "features": self.features or [],
            "pros": self.pros or [],
            "cons": self.cons or [],
            "use_cases": self.use_cases or [],
            "rating": self.rating,
        }


class Category(Base):
    """Tool category with SEO intent classification."""
    __tablename__ = "categories"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(200), nullable=False)
    slug = Column(String(200), nullable=False, unique=True, index=True)
    description = Column(Text)
    primary_keyword = Column(String(300))
    intent_type = Column(
        Enum("Informational", "Commercial", "Transactional", name="intent_type_enum"),
        default="Commercial"
    )
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    tool_relations = relationship("ToolCategory", back_populates="category")
    keywords = relationship("KeywordMatrix", back_populates="category")
    pseo_pages = relationship("PSEOPage", back_populates="category")


class ToolCategory(Base):
    """Many-to-many relationship between tools and categories."""
    __tablename__ = "tool_categories"

    tool_id = Column(String(36), ForeignKey("tools.id"), primary_key=True)
    category_id = Column(String(36), ForeignKey("categories.id"), primary_key=True)

    tool = relationship("Tool", back_populates="category_relations")
    category = relationship("Category", back_populates="tool_relations")


class KeywordMatrix(Base):
    """Keyword research matrix for pSEO page generation planning."""
    __tablename__ = "keyword_matrix"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    keyword = Column(String(500), nullable=False, index=True)
    intent_type = Column(
        Enum("Informational", "Commercial", "Transactional", name="kw_intent_enum"),
        default="Commercial"
    )
    difficulty = Column(
        Enum("Low", "Medium", "High", name="difficulty_enum"),
        default="Medium"
    )
    search_volume = Column(Integer, default=0)
    page_type_suggestion = Column(
        Enum("Alternative", "Comparison", "Listicle", "Tutorial", "Landing", name="page_type_enum"),
        default="Alternative"
    )
    category_id = Column(String(36), ForeignKey("categories.id"))
    is_processed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    category = relationship("Category", back_populates="keywords")


class PSEOPage(Base):
    """Programmatically generated SEO page record."""
    __tablename__ = "pseo_pages"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    page_type = Column(
        Enum("Alternative", "Comparison", "Listicle", "Tutorial", "Landing", name="pseo_page_type_enum"),
        nullable=False
    )
    primary_keyword = Column(String(500), nullable=False)
    url_path = Column(String(500), nullable=False, unique=True, index=True)
    template_id = Column(String(100), default="default")
    title = Column(String(300))
    meta_description = Column(String(500))
    h1 = Column(String(300))
    generated_content = Column(JSON)   # Full structured content object
    schema_json = Column(JSON)         # JSON-LD structured data
    word_count = Column(Integer, default=0)
    status = Column(
        Enum("Draft", "Published", "Archived", name="page_status_enum"),
        default="Draft"
    )
    published_at = Column(DateTime)
    last_indexed_at = Column(DateTime)
    indexing_status = Column(String(50), default="pending")
    primary_tool_id = Column(String(36), ForeignKey("tools.id"))
    category_id = Column(String(36), ForeignKey("categories.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    primary_tool = relationship("Tool", back_populates="pseo_pages")
    category = relationship("Category", back_populates="pseo_pages")


class Competitor(Base):
    """Tracked competitor domain for SEO monitoring."""
    __tablename__ = "competitors"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    domain = Column(String(300), nullable=False, unique=True, index=True)
    domain_rating = Column(Integer, default=0)
    monthly_traffic = Column(Integer, default=0)
    seo_traffic_ratio = Column(Float, default=0.0)
    top_keywords = Column(JSON, default=list)
    last_checked_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

    backlink_opportunities = relationship("BacklinkOpportunity", back_populates="competitor")


class BacklinkOpportunity(Base):
    """Discovered backlink opportunity from competitor analysis."""
    __tablename__ = "backlink_opportunities"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    competitor_id = Column(String(36), ForeignKey("competitors.id"))
    source_url = Column(String(1000), nullable=False)
    source_domain = Column(String(300))
    domain_rating = Column(Integer, default=0)
    context_snippet = Column(Text)
    link_type = Column(
        Enum("DoFollow", "NoFollow", "Unknown", name="link_type_enum"),
        default="Unknown"
    )
    status = Column(
        Enum("New", "Contacted", "Acquired", "Rejected", name="bl_status_enum"),
        default="New"
    )
    is_notified = Column(Boolean, default=False)
    discovered_at = Column(DateTime, default=datetime.utcnow)

    competitor = relationship("Competitor", back_populates="backlink_opportunities")


class SEOAuditResult(Base):
    """SEO technical audit result for a page."""
    __tablename__ = "seo_audit_results"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    url = Column(String(1000), nullable=False)
    audit_type = Column(
        Enum("Performance", "BrokenLinks", "Structure", "Full", name="audit_type_enum"),
        default="Full"
    )
    lcp_score = Column(Float)        # Largest Contentful Paint (seconds)
    cls_score = Column(Float)        # Cumulative Layout Shift
    inp_score = Column(Float)        # Interaction to Next Paint (ms)
    performance_score = Column(Integer)  # 0-100
    has_h1 = Column(Boolean)
    h1_count = Column(Integer, default=0)
    missing_alt_count = Column(Integer, default=0)
    broken_links_count = Column(Integer, default=0)
    has_meta_description = Column(Boolean)
    has_schema = Column(Boolean)
    issues = Column(JSON, default=list)  # List of issue descriptions
    passed = Column(Boolean, default=False)
    audited_at = Column(DateTime, default=datetime.utcnow)


# Database engine and session factory
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {}
)


def init_db():
    """Create all tables."""
    Base.metadata.create_all(bind=engine)


def get_session() -> Session:
    """Get a new database session."""
    return Session(engine)
