"""
LLM-based content generator for pSEO pages.

Uses the OpenAI-compatible API that is pre-configured in the Manus environment.
No LLM API key configuration is required from the user — the environment
variable OPENAI_API_KEY and base_url are already injected by the runtime.

Supported models: any model name accepted via LLM_MODEL env var.
Latest examples (as of Apr 2026):
  OpenAI   : gpt-4.1 | gpt-4.1-mini (default) | gpt-4.1-nano
  Anthropic: claude-opus-4-5 | claude-sonnet-4-5 | claude-haiku-4-5
  Google   : gemini-2.5-pro | gemini-2.5-flash

To override the model, set LLM_MODEL in your .env file. Any model name is accepted.
"""
import json
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()  # Load .env file so LLM_MODEL and other vars are available


# ---------------------------------------------------------------------------
# Client initialization
# ---------------------------------------------------------------------------
# OPENAI_API_KEY and base_url are pre-injected by the Manus runtime.
# If running outside Manus (e.g. local dev), set OPENAI_API_KEY manually.
# ---------------------------------------------------------------------------

def _build_client() -> OpenAI:
    """
    Build an OpenAI client.
    - Inside Manus: OPENAI_API_KEY + base_url are pre-configured in env.
    - Outside Manus: reads OPENAI_API_KEY from .env; uses default OpenAI endpoint.
    """
    api_key = os.environ.get("OPENAI_API_KEY", "")
    base_url = os.environ.get("OPENAI_BASE_URL", None)  # Manus injects this

    if base_url:
        return OpenAI(api_key=api_key, base_url=base_url)
    return OpenAI(api_key=api_key)


def _get_model() -> str:
    """
    Resolve the LLM model to use.
    Priority: LLM_MODEL env var → default gpt-4.1-mini
    Any model name is accepted — no restriction on model choice.
    Latest models (Apr 2026): gpt-4.1, gpt-4.1-mini, gpt-4.1-nano,
    claude-opus-4-5, claude-sonnet-4-5, gemini-2.5-pro, gemini-2.5-flash
    """
    return os.environ.get("LLM_MODEL", "gpt-4.1-mini")


class LLMContentGenerator:
    """
    Generates structured, information-rich SEO content using LLM.
    All content is grounded in real structured data to ensure Information Gain.

    No API key setup is required when running inside the Manus environment.

    Supported page types:
    - Alternative pages  : generate_alternatives_page()
    - Comparison pages   : generate_comparison_page()
    - Listicle pages     : generate_listicle_page()
    - Tutorial pages     : generate_tutorial_page()  [NEW]
    - Landing pages      : generate_landing_page()   [NEW]
    - Internal link map  : generate_internal_link_map() [NEW]
    """

    def __init__(self):
        self.client = _build_client()
        self.model = _get_model()

    def _call(self, prompt: str) -> dict:
        """Shared LLM call with JSON output enforcement."""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert SEO content writer. Always output valid JSON."
                },
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.7
        )
        return json.loads(response.choices[0].message.content)

    def generate_alternatives_page(
        self,
        target_tool: dict,
        alternatives: list[dict],
        primary_keyword: str
    ) -> dict:
        """
        Generate content for an 'X alternatives' page.
        Targets Commercial intent searchers (buyers evaluating options).
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
4. Target COMMERCIAL intent: readers are evaluating whether to switch tools.
5. Output must be valid JSON matching the schema below exactly.

OUTPUT SCHEMA:
{{
  "title": "Top X {primary_keyword} in 2025 [Free & Paid]",
  "meta_description": "150-160 char meta description with primary keyword",
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
        return self._call(prompt)

    def generate_comparison_page(
        self,
        tool_a: dict,
        tool_b: dict,
        primary_keyword: str
    ) -> dict:
        """
        Generate content for a 'Tool A vs Tool B' comparison page.
        Targets Commercial intent searchers making a final purchase decision.
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
3. Give a clear verdict for different user types (ICP segmentation).
4. Target COMMERCIAL intent: readers are making a final purchase decision.
5. Output must be valid JSON matching the schema below.

OUTPUT SCHEMA:
{{
  "title": "...",
  "meta_description": "150-160 char meta description",
  "h1": "...",
  "intro": "2 paragraphs introducing both tools and what this comparison covers",
  "quick_verdict": {{
    "choose_tool_a_if": "Specific user profile and use case",
    "choose_tool_b_if": "Specific user profile and use case"
  }},
  "detailed_comparison": {{
    "features": "paragraph comparing features with specific examples",
    "pricing": "paragraph comparing pricing with specific numbers from data",
    "ease_of_use": "paragraph comparing UX and learning curve",
    "use_cases": "paragraph on different ideal use cases for each tool",
    "integrations": "paragraph on ecosystem and integration differences"
  }},
  "winner_by_category": [
    {{"category": "Best Value", "winner": "...", "reason": "..."}}
  ],
  "conclusion": "2 paragraphs with final recommendation",
  "faqs": [
    {{"question": "...", "answer": "..."}}
  ]
}}"""
        return self._call(prompt)

    def generate_listicle_page(
        self,
        tools: list[dict],
        category_name: str,
        primary_keyword: str
    ) -> dict:
        """
        Generate content for a 'Best X tools' listicle page.
        Targets Informational intent searchers discovering options.
        """
        prompt = f"""You are a senior SEO content strategist and AI software reviewer.
Your task: Write a comprehensive '{primary_keyword}' listicle page.

TOOLS DATA:
{json.dumps(tools, indent=2, ensure_ascii=False)}

CRITICAL RULES:
1. Base ALL claims strictly on the provided data.
2. Each tool entry must have a specific "best for" designation to differentiate.
3. Include honest pros/cons from the data.
4. Target INFORMATIONAL intent: readers are discovering options for the first time.
5. Output must be valid JSON.

OUTPUT SCHEMA:
{{
  "title": "...",
  "meta_description": "150-160 char meta description",
  "h1": "...",
  "intro": "2 paragraphs introducing the category and what readers will learn",
  "selection_criteria": "How we evaluated these tools (methodology paragraph)",
  "tools": [
    {{
      "tool_name": "...",
      "slug": "...",
      "badge": "Best Overall / Best Free / Best for Teams / Best for Beginners / etc.",
      "summary": "2-3 sentence summary with specific differentiator",
      "pros": ["...", "..."],
      "cons": ["...", "..."],
      "pricing": "Specific pricing from data",
      "best_for": "One sentence ideal user profile",
      "information_gain": "One unique insight not obvious from the tool name"
    }}
  ],
  "comparison_summary": "A paragraph summarizing key differences across all tools",
  "conclusion": "2 paragraphs with guidance on how to choose",
  "faqs": [
    {{"question": "...", "answer": "..."}}
  ]
}}"""
        return self._call(prompt)

    def generate_tutorial_page(
        self,
        tool: dict,
        task: str,
        primary_keyword: str,
        target_audience: str = "beginners"
    ) -> dict:
        """
        Generate content for a 'How to use X for Y' tutorial page.
        Targets Informational intent searchers (Learners in ICP model).
        Provides step-by-step instructions grounded in real tool features.
        """
        prompt = f"""You are a senior SEO content strategist and expert technical writer.
Your task: Write a comprehensive '{primary_keyword}' tutorial page.

TOOL DATA:
{json.dumps(tool, indent=2, ensure_ascii=False)}

TASK TO ACCOMPLISH: {task}
TARGET AUDIENCE: {target_audience}

CRITICAL RULES:
1. Base ALL steps and features strictly on the provided tool data.
2. Focus on Information Gain: provide specific, actionable steps — not generic advice.
3. Target INFORMATIONAL intent: readers want to learn how to do something specific.
4. Include real feature names from the tool data in the steps.
5. Output must be valid JSON matching the schema below.

OUTPUT SCHEMA:
{{
  "title": "How to {task} with {tool.get('name', 'this tool')}: Step-by-Step Guide",
  "meta_description": "150-160 char meta description with primary keyword",
  "h1": "...",
  "intro": "2 paragraphs: what this tutorial covers and what the reader will achieve",
  "prerequisites": ["List of things needed before starting"],
  "steps": [
    {{
      "step_number": 1,
      "heading": "Step heading",
      "description": "Detailed explanation of this step",
      "tip": "Optional pro tip for this step"
    }}
  ],
  "common_mistakes": [
    {{"mistake": "...", "solution": "..."}}
  ],
  "advanced_tips": "2 paragraphs with advanced techniques using the tool's features",
  "conclusion": "1-2 paragraphs summarizing what was learned and next steps",
  "faqs": [
    {{"question": "...", "answer": "..."}}
  ]
}}"""
        return self._call(prompt)

    def generate_landing_page(
        self,
        tool: dict,
        primary_keyword: str,
        cta_action: str = "Start Free Trial"
    ) -> dict:
        """
        Generate content for a tool landing/feature page.
        Targets Transactional intent searchers ready to sign up or buy.
        """
        prompt = f"""You are a senior SEO content strategist and conversion copywriter.
Your task: Write a comprehensive landing page for '{primary_keyword}'.

TOOL DATA:
{json.dumps(tool, indent=2, ensure_ascii=False)}

CTA ACTION: {cta_action}

CRITICAL RULES:
1. Base ALL claims strictly on the provided tool data.
2. Target TRANSACTIONAL intent: readers are ready to sign up or buy.
3. Lead with the strongest value proposition from the tool's pros.
4. Address objections using the tool's cons as known concerns to pre-empt.
5. Output must be valid JSON matching the schema below.

OUTPUT SCHEMA:
{{
  "title": "...",
  "meta_description": "150-160 char meta description",
  "h1": "...",
  "hero_headline": "Compelling headline (max 10 words)",
  "hero_subheadline": "Supporting sentence (max 20 words)",
  "value_propositions": [
    {{"headline": "...", "description": "2 sentences explaining this benefit"}}
  ],
  "feature_highlights": [
    {{"feature": "...", "benefit": "What this means for the user"}}
  ],
  "pricing_section": "Clear pricing explanation from the data",
  "objection_handling": [
    {{"objection": "Common concern", "response": "How the tool addresses this"}}
  ],
  "cta_text": "{cta_action}",
  "faqs": [
    {{"question": "...", "answer": "..."}}
  ]
}}"""
        return self._call(prompt)

    def generate_internal_link_map(
        self,
        pages: list[dict],
        site_name: str
    ) -> dict:
        """
        Generate an internal linking strategy for a set of pSEO pages.
        Implements the 'internal links as weight guidance system' from the playbook.
        Returns a map of which pages should link to which, with anchor text suggestions.
        """
        prompt = f"""You are an SEO architect specializing in internal link strategy.
Your task: Design an internal linking map for {site_name}.

PAGES TO LINK:
{json.dumps(pages, indent=2, ensure_ascii=False)}

CRITICAL RULES:
1. Hub pages (listicles) should link to spoke pages (alternatives, comparisons).
2. Spoke pages should link back to the hub and to related spokes.
3. Use keyword-rich anchor text that matches the target page's primary keyword.
4. Prioritize links that help users navigate logically through the content.
5. Output must be valid JSON.

OUTPUT SCHEMA:
{{
  "strategy_summary": "2 paragraphs explaining the internal link architecture",
  "hub_pages": ["url_paths of listicle/category pages that are hubs"],
  "link_map": [
    {{
      "source_page": "url_path",
      "source_type": "Alternative/Comparison/Listicle/Tutorial",
      "links_to": [
        {{
          "target_page": "url_path",
          "anchor_text": "Suggested anchor text",
          "placement": "intro/body/conclusion/sidebar",
          "reason": "Why this link makes sense"
        }}
      ]
    }}
  ],
  "priority_links": [
    {{
      "source": "url_path",
      "target": "url_path",
      "anchor_text": "...",
      "priority": "High/Medium/Low"
    }}
  ]
}}"""
        return self._call(prompt)
