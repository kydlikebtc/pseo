"""
LLM-based content generator for pSEO pages.

Uses the OpenAI-compatible API that is pre-configured in the Manus environment.
No LLM API key configuration is required from the user — the environment
variable OPENAI_API_KEY and base_url are already injected by the runtime.

Supported models: any model name accepted via LLM_MODEL env var.
Latest examples (as of Apr 2026):
  OpenAI   : gpt-5.4 | gpt-5.4-mini (default) | gpt-5.4-nano
  Anthropic: claude-opus-4-6 | claude-sonnet-4-6 | claude-haiku-4-5
  Google   : gemini-3.1-pro | gemini-2.5-pro | gemini-2.5-flash

To override the model, set LLM_MODEL in your .env file. Any model name is accepted.
"""
import json
import os
from openai import OpenAI


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
    Priority: LLM_MODEL env var → default gpt-5.4-mini
    Any model name is accepted — no restriction on model choice.
    Latest models (Apr 2026): gpt-5.4, gpt-5.4-mini, gpt-5.4-nano,
    claude-opus-4-6, claude-sonnet-4-6, gemini-3.1-pro, gemini-2.5-flash
    """
    return os.environ.get("LLM_MODEL", "gpt-5.4-mini")


class LLMContentGenerator:
    """
    Generates structured, information-rich SEO content using LLM.
    All content is grounded in real structured data to ensure Information Gain.

    No API key setup is required when running inside the Manus environment.
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
        return self._call(prompt)

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
        return self._call(prompt)

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
        return self._call(prompt)
