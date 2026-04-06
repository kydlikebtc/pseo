"""
LLM-based content generator for pSEO pages.
Uses structured prompts to generate information-gain content based on real tool data.
Avoids content-farm patterns by requiring factual grounding.
"""
import json
import os
from typing import Optional
from openai import OpenAI

from src.config import settings


class LLMContentGenerator:
    """
    Generates structured, information-rich SEO content using LLM.
    All content is grounded in real structured data to ensure Information Gain.
    """

    def __init__(self):
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_model

    def generate_alternatives_page(
        self,
        target_tool: dict,
        alternatives: list[dict],
        primary_keyword: str
    ) -> dict:
        """
        Generate content for an 'X alternatives' page.
        Returns a structured JSON content object.
        """
        prompt = f"""You are a senior SEO content strategist and AI software reviewer.
Your task: Write a comprehensive '{primary_keyword}' page.

TARGET TOOL DATA (the tool being replaced):
{json.dumps(target_tool, indent=2, ensure_ascii=False)}

ALTERNATIVE TOOLS DATA:
{json.dumps(alternatives, indent=2, ensure_ascii=False)}

CRITICAL RULES:
1. Base ALL claims strictly on the provided data. Do NOT invent features or prices.
2. Focus on Information Gain: explain WHY someone would switch, not just list features.
3. Be specific: mention actual price differences, specific missing features, real use cases.
4. Output must be valid JSON matching the schema below exactly.

OUTPUT SCHEMA:
{{
  "title": "Top X {primary_keyword} in 2025 [Free & Paid]",
  "meta_description": "150-160 char meta description",
  "h1": "H1 heading for the page",
  "intro": "2-3 paragraph introduction explaining why users look for alternatives and what to expect",
  "why_look_for_alternatives": "1-2 paragraphs on specific pain points with the target tool based on its cons",
  "alternatives": [
    {{
      "tool_name": "...",
      "slug": "...",
      "why_choose": "2-3 sentences: specific reason to choose this over target tool",
      "best_for": "One sentence describing the ideal user",
      "key_differentiator": "The single most important difference",
      "pricing_note": "Specific pricing comparison"
    }}
  ],
  "comparison_table_note": "A paragraph summarizing the comparison table",
  "conclusion": "2 paragraphs wrapping up with a recommendation framework",
  "faqs": [
    {{"question": "...", "answer": "..."}}
  ]
}}"""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are an expert SEO content writer. Always output valid JSON."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.7
        )

        return json.loads(response.choices[0].message.content)

    def generate_comparison_page(
        self,
        tool_a: dict,
        tool_b: dict,
        primary_keyword: str
    ) -> dict:
        """
        Generate content for a 'Tool A vs Tool B' comparison page.
        """
        prompt = f"""You are a senior SEO content strategist and AI software reviewer.
Your task: Write a comprehensive '{primary_keyword}' comparison page.

TOOL A DATA:
{json.dumps(tool_a, indent=2, ensure_ascii=False)}

TOOL B DATA:
{json.dumps(tool_b, indent=2, ensure_ascii=False)}

CRITICAL RULES:
1. Base ALL claims strictly on the provided data.
2. Be balanced and objective. Acknowledge strengths and weaknesses of both.
3. Give a clear verdict for different user types.
4. Output must be valid JSON matching the schema below.

OUTPUT SCHEMA:
{{
  "title": "...",
  "meta_description": "...",
  "h1": "...",
  "intro": "...",
  "quick_verdict": {{
    "choose_tool_a_if": "...",
    "choose_tool_b_if": "..."
  }},
  "detailed_comparison": {{
    "features": "paragraph comparing features",
    "pricing": "paragraph comparing pricing with specific numbers",
    "ease_of_use": "paragraph comparing UX",
    "use_cases": "paragraph on different use cases"
  }},
  "conclusion": "...",
  "faqs": [
    {{"question": "...", "answer": "..."}}
  ]
}}"""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are an expert SEO content writer. Always output valid JSON."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.7
        )

        return json.loads(response.choices[0].message.content)

    def generate_listicle_page(
        self,
        tools: list[dict],
        category_name: str,
        primary_keyword: str
    ) -> dict:
        """
        Generate content for a 'Best X tools' listicle page.
        """
        prompt = f"""You are a senior SEO content strategist and AI software reviewer.
Your task: Write a comprehensive '{primary_keyword}' listicle page.

TOOLS DATA:
{json.dumps(tools, indent=2, ensure_ascii=False)}

CRITICAL RULES:
1. Base ALL claims strictly on the provided data.
2. Each tool entry must have a specific "best for" designation to differentiate.
3. Include honest pros/cons from the data.
4. Output must be valid JSON.

OUTPUT SCHEMA:
{{
  "title": "...",
  "meta_description": "...",
  "h1": "...",
  "intro": "...",
  "selection_criteria": "How we evaluated these tools",
  "tools": [
    {{
      "tool_name": "...",
      "slug": "...",
      "badge": "Best Overall / Best Free / Best for Teams / etc.",
      "summary": "2-3 sentence summary",
      "pros": ["...", "..."],
      "cons": ["...", "..."],
      "pricing": "...",
      "best_for": "..."
    }}
  ],
  "conclusion": "...",
  "faqs": [
    {{"question": "...", "answer": "..."}}
  ]
}}"""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are an expert SEO content writer. Always output valid JSON."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.7
        )

        return json.loads(response.choices[0].message.content)
