"""
Utility helper functions for the pSEO system.
"""
import re
import httpx
from typing import Optional
from src.config import settings


def slugify(text: str) -> str:
    """Convert a string to a URL-friendly slug."""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_-]+', '-', text)
    text = re.sub(r'^-+|-+$', '', text)
    return text


def count_words(text: str) -> int:
    """Count the number of words in a text string."""
    if not text:
        return 0
    return len(re.findall(r'\b\w+\b', text))


def send_feishu_notification(title: str, content: str) -> bool:
    """
    Send a notification to Feishu/Lark via webhook.
    Returns True on success, False on failure.
    """
    webhook_url = settings.feishu_webhook_url
    if not webhook_url:
        print(f"[Feishu] Webhook not configured. Message: {title}")
        return False

    payload = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {"tag": "plain_text", "content": title},
                "template": "blue"
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {"tag": "lark_md", "content": content}
                }
            ]
        }
    }

    try:
        response = httpx.post(webhook_url, json=payload, timeout=10)
        return response.status_code == 200
    except Exception as e:
        print(f"[Feishu] Failed to send notification: {e}")
        return False


def build_json_ld_software(tool_data: dict) -> dict:
    """Build JSON-LD SoftwareApplication schema for a tool page."""
    return {
        "@context": "https://schema.org",
        "@type": "SoftwareApplication",
        "name": tool_data.get("name", ""),
        "description": tool_data.get("description", ""),
        "url": tool_data.get("official_url", ""),
        "applicationCategory": "WebApplication",
        "offers": {
            "@type": "Offer",
            "price": str(tool_data.get("starting_price", 0)),
            "priceCurrency": "USD"
        },
        "aggregateRating": {
            "@type": "AggregateRating",
            "ratingValue": str(tool_data.get("rating", 0)),
            "bestRating": "5",
            "worstRating": "1"
        }
    }


def build_json_ld_faq(faqs: list[dict]) -> dict:
    """Build JSON-LD FAQPage schema from a list of Q&A pairs."""
    return {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": faq.get("question", ""),
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": faq.get("answer", "")
                }
            }
            for faq in faqs
        ]
    }
