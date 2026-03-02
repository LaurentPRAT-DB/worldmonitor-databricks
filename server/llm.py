"""
Foundation Model API client for AI features.
Uses OpenAI-compatible interface with Databricks serving endpoints.
"""

import os
from typing import Optional
from openai import AsyncOpenAI

from .config import get_oauth_token, get_workspace_host, settings, IS_DATABRICKS_APP


def get_llm_client() -> AsyncOpenAI:
    """Get OpenAI-compatible client for Databricks Foundation Models.

    The client is configured to use Databricks serving endpoints
    with OAuth authentication.
    """
    host = get_workspace_host()

    if IS_DATABRICKS_APP:
        # Remote: Use service principal token or env token
        token = os.environ.get("DATABRICKS_TOKEN") or get_oauth_token()
    else:
        # Local: Use profile token
        token = get_oauth_token()

    return AsyncOpenAI(
        api_key=token,
        base_url=f"{host}/serving-endpoints"
    )


async def chat_completion(
    messages: list[dict],
    model: Optional[str] = None,
    max_tokens: int = 4096,
    temperature: float = 0.7,
) -> str:
    """Get chat completion from Foundation Model.

    Args:
        messages: List of message dicts with 'role' and 'content'
        model: Model endpoint name (defaults to SERVING_ENDPOINT setting)
        max_tokens: Maximum tokens in response
        temperature: Sampling temperature (0-1)

    Returns:
        Generated text response
    """
    client = get_llm_client()
    model = model or settings.SERVING_ENDPOINT

    response = await client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    return response.choices[0].message.content or ""


async def summarize_article(
    title: str,
    content: str,
    max_words: int = 100,
) -> str:
    """Generate AI summary of a news article.

    Args:
        title: Article title
        content: Article body text
        max_words: Target summary length

    Returns:
        Concise summary of the article
    """
    prompt = f"""Summarize the following news article in {max_words} words or less.
Focus on the key facts, who is involved, and why it matters.

Title: {title}

Content:
{content[:4000]}

Summary:"""

    return await chat_completion(
        messages=[{"role": "user", "content": prompt}],
        max_tokens=200,
        temperature=0.3,
    )


async def generate_country_brief(
    country_name: str,
    country_code: str,
    recent_events: list[dict],
    economic_data: Optional[dict] = None,
) -> str:
    """Generate intelligence brief for a country.

    Args:
        country_name: Full country name
        country_code: ISO 2-letter country code
        recent_events: List of recent events/news
        economic_data: Optional economic indicators

    Returns:
        Structured intelligence brief
    """
    events_text = "\n".join([
        f"- {e.get('title', 'Unknown')}: {e.get('summary', '')}"
        for e in recent_events[:10]
    ])

    econ_text = ""
    if economic_data:
        econ_text = f"""
Economic Indicators:
- GDP Growth: {economic_data.get('gdp_growth', 'N/A')}%
- Inflation: {economic_data.get('inflation', 'N/A')}%
- Unemployment: {economic_data.get('unemployment', 'N/A')}%
"""

    prompt = f"""Generate a concise intelligence brief for {country_name} ({country_code}).

Recent Events:
{events_text}
{econ_text}

Provide:
1. Current Situation (2-3 sentences)
2. Key Risks (bullet points)
3. Outlook (1-2 sentences)

Brief:"""

    return await chat_completion(
        messages=[{"role": "user", "content": prompt}],
        max_tokens=500,
        temperature=0.5,
    )


async def classify_event(
    title: str,
    description: str,
    location: Optional[str] = None,
) -> dict:
    """Classify an event by type and severity.

    Args:
        title: Event title
        description: Event description
        location: Optional location string

    Returns:
        Dict with 'category', 'severity', 'tags'
    """
    prompt = f"""Classify the following event:

Title: {title}
Description: {description}
Location: {location or 'Unknown'}

Respond in JSON format:
{{
    "category": "conflict|disaster|economic|political|cyber|other",
    "severity": "low|medium|high|critical",
    "tags": ["tag1", "tag2"],
    "affected_sectors": ["sector1", "sector2"]
}}

Classification:"""

    response = await chat_completion(
        messages=[{"role": "user", "content": prompt}],
        max_tokens=150,
        temperature=0.2,
    )

    # Parse JSON response
    import json
    try:
        # Extract JSON from response
        start = response.find("{")
        end = response.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(response[start:end])
    except json.JSONDecodeError:
        pass

    return {
        "category": "other",
        "severity": "medium",
        "tags": [],
        "affected_sectors": []
    }
