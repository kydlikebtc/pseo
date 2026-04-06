"""
Data collector for seeding the tool database.
Supports manual data entry and basic web scraping for tool metadata.
"""
import httpx
from bs4 import BeautifulSoup
from typing import Optional

from src.models import Tool, Category, ToolCategory, get_session
from src.utils.helpers import slugify


class DataCollector:
    """
    Seeds the database with AI tool data.
    Provides both manual seeding and basic scraping capabilities.
    """

    def __init__(self):
        self.session = get_session()

    def seed_sample_data(self):
        """
        Seed the database with sample AI tool data for testing and demonstration.
        In production, replace with real data from APIs or manual curation.
        """
        # --- Categories ---
        categories_data = [
            {
                "name": "AI Image Generator",
                "slug": "ai-image-generator",
                "description": "Tools that generate images from text prompts using AI",
                "primary_keyword": "ai image generator",
                "intent_type": "Commercial"
            },
            {
                "name": "AI Writing Assistant",
                "slug": "ai-writing-assistant",
                "description": "AI-powered tools for writing, editing, and content creation",
                "primary_keyword": "ai writing assistant",
                "intent_type": "Commercial"
            },
            {
                "name": "AI Video Generator",
                "slug": "ai-video-generator",
                "description": "Tools that generate or edit videos using AI",
                "primary_keyword": "ai video generator",
                "intent_type": "Commercial"
            },
        ]

        categories = {}
        for cat_data in categories_data:
            existing = self.session.query(Category).filter(Category.slug == cat_data["slug"]).first()
            if not existing:
                cat = Category(**cat_data)
                self.session.add(cat)
                self.session.flush()
                categories[cat_data["slug"]] = cat
                print(f"[Seeder] Created category: {cat_data['name']}")
            else:
                categories[cat_data["slug"]] = existing

        # --- AI Image Generator Tools ---
        image_tools = [
            {
                "name": "Midjourney",
                "slug": "midjourney",
                "description": "AI image generation tool known for high-quality artistic outputs, accessible via Discord.",
                "official_url": "https://midjourney.com",
                "pricing_model": "Paid",
                "starting_price": 10.0,
                "features": ["Text-to-image", "Image variations", "Upscaling", "Style tuning", "Discord integration"],
                "pros": ["Exceptional image quality", "Strong artistic style", "Active community", "Regular model updates"],
                "cons": ["No free tier", "Discord-only interface", "Limited control over composition", "Slow on basic plan"],
                "use_cases": ["Digital art", "Concept art", "Marketing visuals", "Book covers"],
                "rating": 4.7,
                "monthly_users": 15000000,
            },
            {
                "name": "DALL-E 3",
                "slug": "dall-e-3",
                "description": "OpenAI's image generation model integrated into ChatGPT, known for following prompts accurately.",
                "official_url": "https://openai.com/dall-e-3",
                "pricing_model": "Freemium",
                "starting_price": 0.0,
                "features": ["Text-to-image", "ChatGPT integration", "Prompt accuracy", "Safety filters", "API access"],
                "pros": ["Excellent prompt adherence", "Free via ChatGPT", "Easy to use", "API available"],
                "cons": ["Less artistic than Midjourney", "Limited style control", "Rate limits on free tier", "No image editing"],
                "use_cases": ["Content creation", "Presentations", "Social media", "Prototyping"],
                "rating": 4.5,
                "monthly_users": 20000000,
            },
            {
                "name": "Stable Diffusion",
                "slug": "stable-diffusion",
                "description": "Open-source AI image generation model that can be run locally or via cloud services.",
                "official_url": "https://stability.ai",
                "pricing_model": "Free",
                "starting_price": 0.0,
                "features": ["Text-to-image", "Image-to-image", "Inpainting", "ControlNet", "Local deployment", "Fine-tuning"],
                "pros": ["Completely free and open-source", "Full control over outputs", "No content restrictions", "Highly customizable"],
                "cons": ["Requires technical knowledge", "Hardware requirements for local use", "Inconsistent quality", "Complex setup"],
                "use_cases": ["Research", "Custom model training", "Unrestricted generation", "Local privacy"],
                "rating": 4.3,
                "monthly_users": 10000000,
            },
            {
                "name": "Adobe Firefly",
                "slug": "adobe-firefly",
                "description": "Adobe's AI image generation tool, commercially safe and integrated into Creative Cloud.",
                "official_url": "https://firefly.adobe.com",
                "pricing_model": "Freemium",
                "starting_price": 0.0,
                "features": ["Text-to-image", "Generative Fill", "Text effects", "Creative Cloud integration", "Commercial license"],
                "pros": ["Commercially safe content", "Adobe ecosystem integration", "Easy to use", "Free tier available"],
                "cons": ["Less creative than Midjourney", "Requires Adobe account", "Limited free credits", "Slower iteration"],
                "use_cases": ["Commercial projects", "Marketing", "Adobe workflow integration", "Safe content generation"],
                "rating": 4.2,
                "monthly_users": 8000000,
            },
            {
                "name": "Leonardo AI",
                "slug": "leonardo-ai",
                "description": "AI image generation platform with fine-tuned models for game assets and creative content.",
                "official_url": "https://leonardo.ai",
                "pricing_model": "Freemium",
                "starting_price": 0.0,
                "features": ["Text-to-image", "Fine-tuned models", "Canvas editor", "Motion generation", "API access"],
                "pros": ["Generous free tier", "Game asset specialization", "Multiple model options", "Good community"],
                "cons": ["Watermarks on free tier", "Inconsistent quality", "Limited video features", "Slower than competitors"],
                "use_cases": ["Game development", "Concept art", "Character design", "Asset creation"],
                "rating": 4.1,
                "monthly_users": 5000000,
            },
        ]

        # --- AI Writing Tools ---
        writing_tools = [
            {
                "name": "ChatGPT",
                "slug": "chatgpt",
                "description": "OpenAI's conversational AI assistant capable of writing, coding, analysis, and more.",
                "official_url": "https://chat.openai.com",
                "pricing_model": "Freemium",
                "starting_price": 0.0,
                "features": ["Long-form writing", "Code generation", "Analysis", "Summarization", "Translation", "Plugins"],
                "pros": ["Versatile", "Strong reasoning", "Free tier available", "Huge ecosystem", "Regular updates"],
                "cons": ["Knowledge cutoff", "Can hallucinate", "No real-time web access on free tier", "Generic outputs"],
                "use_cases": ["Content writing", "Coding assistance", "Research", "Customer support", "Education"],
                "rating": 4.7,
                "monthly_users": 100000000,
            },
            {
                "name": "Claude",
                "slug": "claude",
                "description": "Anthropic's AI assistant known for long context windows, safety, and nuanced writing.",
                "official_url": "https://claude.ai",
                "pricing_model": "Freemium",
                "starting_price": 0.0,
                "features": ["200K context window", "Long-form writing", "Document analysis", "Code review", "Safety focus"],
                "pros": ["Exceptional long context", "Nuanced writing style", "Strong safety", "Great for analysis"],
                "cons": ["No image generation", "Slower than GPT-4", "Limited integrations", "Less plugin ecosystem"],
                "use_cases": ["Long document analysis", "Academic writing", "Legal review", "Complex reasoning"],
                "rating": 4.6,
                "monthly_users": 30000000,
            },
            {
                "name": "Jasper",
                "slug": "jasper",
                "description": "AI writing platform designed for marketing teams with brand voice and templates.",
                "official_url": "https://jasper.ai",
                "pricing_model": "Paid",
                "starting_price": 39.0,
                "features": ["Brand voice", "Marketing templates", "SEO integration", "Team collaboration", "Plagiarism checker"],
                "pros": ["Marketing-focused templates", "Brand voice training", "Team features", "SEO tools integration"],
                "cons": ["Expensive", "No free tier", "Output quality varies", "Requires editing"],
                "use_cases": ["Marketing copy", "Blog posts", "Ad copy", "Email campaigns"],
                "rating": 4.2,
                "monthly_users": 1000000,
            },
        ]

        # --- AI Video Tools ---
        video_tools = [
            {
                "name": "Runway",
                "slug": "runway",
                "description": "AI video generation and editing platform with Gen-2 video model.",
                "official_url": "https://runwayml.com",
                "pricing_model": "Freemium",
                "starting_price": 0.0,
                "features": ["Text-to-video", "Image-to-video", "Video editing", "Green screen", "Motion tracking"],
                "pros": ["High quality video", "Multiple AI tools", "Professional features", "Regular updates"],
                "cons": ["Expensive for heavy use", "Short video clips", "Slow generation", "Learning curve"],
                "use_cases": ["Film production", "Marketing videos", "Social content", "Visual effects"],
                "rating": 4.5,
                "monthly_users": 3000000,
            },
            {
                "name": "Sora",
                "slug": "sora",
                "description": "OpenAI's text-to-video model capable of generating realistic and imaginative video content.",
                "official_url": "https://sora.com",
                "pricing_model": "Paid",
                "starting_price": 20.0,
                "features": ["Text-to-video", "High resolution", "Long videos", "Storyboarding", "ChatGPT Plus integration"],
                "pros": ["Exceptional realism", "Long video support", "Strong physics simulation", "OpenAI ecosystem"],
                "cons": ["Expensive", "Limited availability", "No free tier", "Usage limits"],
                "use_cases": ["Film prototyping", "Marketing", "Education", "Creative projects"],
                "rating": 4.6,
                "monthly_users": 2000000,
            },
        ]

        def seed_tools(tools_data: list, category_slug: str):
            cat = categories.get(category_slug)
            if not cat:
                return
            for tool_data in tools_data:
                existing = self.session.query(Tool).filter(Tool.slug == tool_data["slug"]).first()
                if not existing:
                    tool = Tool(**tool_data)
                    self.session.add(tool)
                    self.session.flush()
                    rel = ToolCategory(tool_id=tool.id, category_id=cat.id)
                    self.session.add(rel)
                    print(f"[Seeder] Created tool: {tool_data['name']}")

        seed_tools(image_tools, "ai-image-generator")
        seed_tools(writing_tools, "ai-writing-assistant")
        seed_tools(video_tools, "ai-video-generator")

        self.session.commit()
        print("[Seeder] Sample data seeded successfully!")

    def add_tool(self, tool_data: dict, category_slug: str) -> Optional[Tool]:
        """Add a single tool to the database."""
        existing = self.session.query(Tool).filter(Tool.slug == tool_data.get("slug")).first()
        if existing:
            return existing

        category = self.session.query(Category).filter(Category.slug == category_slug).first()
        if not category:
            print(f"[Collector] Category not found: {category_slug}")
            return None

        tool = Tool(**tool_data)
        self.session.add(tool)
        self.session.flush()

        rel = ToolCategory(tool_id=tool.id, category_id=category.id)
        self.session.add(rel)
        self.session.commit()
        return tool

    def close(self):
        self.session.close()
