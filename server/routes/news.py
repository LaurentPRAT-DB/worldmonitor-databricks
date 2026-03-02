"""
News API endpoints - RSS aggregation and AI summarization.
"""

from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Query
from pydantic import BaseModel
import httpx
import feedparser

from ..db import cache_get, cache_set
from ..llm import summarize_article

router = APIRouter()


class NewsArticle(BaseModel):
    id: str
    title: str
    link: str
    source: str
    published_at: int
    summary: Optional[str] = None
    image_url: Optional[str] = None
    categories: list[str] = []


class ListFeedDigestResponse(BaseModel):
    articles: list[NewsArticle]
    total: int
    updated_at: int


class SummarizeArticleResponse(BaseModel):
    title: str
    summary: str
    source: str
    tokens_used: int


# Sample RSS feeds by category
RSS_FEEDS = {
    "world": [
        ("Reuters World", "https://feeds.reuters.com/reuters/worldNews"),
        ("BBC World", "https://feeds.bbci.co.uk/news/world/rss.xml"),
        ("Al Jazeera", "https://www.aljazeera.com/xml/rss/all.xml"),
    ],
    "tech": [
        ("Hacker News", "https://news.ycombinator.com/rss"),
        ("TechCrunch", "https://techcrunch.com/feed/"),
        ("Ars Technica", "https://feeds.arstechnica.com/arstechnica/index"),
    ],
    "finance": [
        ("Reuters Business", "https://feeds.reuters.com/reuters/businessNews"),
        ("CNBC Top News", "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114"),
    ],
}

NEWS_CACHE_TTL = 900  # 15 minutes


@router.get("/list-feed-digest", response_model=ListFeedDigestResponse)
async def list_feed_digest(
    category: str = Query("world", description="Feed category: world, tech, finance"),
    limit: int = Query(50, le=200),
):
    """Get aggregated news feed digest from multiple RSS sources."""
    cache_key = f"news:digest:{category}"

    cached = await cache_get(cache_key)
    if cached:
        return ListFeedDigestResponse(**cached)

    articles = []
    feeds = RSS_FEEDS.get(category, RSS_FEEDS["world"])

    async with httpx.AsyncClient(timeout=30.0) as client:
        for source_name, feed_url in feeds:
            try:
                response = await client.get(feed_url)
                if response.status_code == 200:
                    feed = feedparser.parse(response.text)

                    for entry in feed.entries[:20]:  # Limit per feed
                        # Parse published date
                        published = entry.get("published_parsed") or entry.get("updated_parsed")
                        if published:
                            pub_ts = int(datetime(*published[:6]).timestamp() * 1000)
                        else:
                            pub_ts = int(datetime.utcnow().timestamp() * 1000)

                        # Extract image URL
                        image_url = None
                        if "media_content" in entry:
                            image_url = entry.media_content[0].get("url")
                        elif "enclosures" in entry and entry.enclosures:
                            image_url = entry.enclosures[0].get("url")

                        articles.append(NewsArticle(
                            id=entry.get("id", entry.get("link", "")),
                            title=entry.get("title", ""),
                            link=entry.get("link", ""),
                            source=source_name,
                            published_at=pub_ts,
                            summary=entry.get("summary", "")[:500] if entry.get("summary") else None,
                            image_url=image_url,
                            categories=entry.get("tags", []) if hasattr(entry, "tags") else [],
                        ))
            except Exception as e:
                print(f"[news] Error fetching {source_name}: {e}")

    # Sort by published date (newest first) and limit
    articles.sort(key=lambda a: a.published_at, reverse=True)
    articles = articles[:limit]

    result = {
        "articles": [a.model_dump() for a in articles],
        "total": len(articles),
        "updated_at": int(datetime.utcnow().timestamp() * 1000)
    }

    await cache_set(cache_key, result, NEWS_CACHE_TTL)
    return ListFeedDigestResponse(**result)


@router.post("/summarize-article", response_model=SummarizeArticleResponse)
async def summarize_article_endpoint(
    url: str = Query(..., description="Article URL to summarize"),
    title: Optional[str] = Query(None, description="Article title"),
):
    """Generate AI summary of a news article using Foundation Model."""
    cache_key = f"summary:{url}"

    cached = await cache_get(cache_key)
    if cached:
        return SummarizeArticleResponse(**cached)

    # Fetch article content
    content = ""
    article_title = title or "Unknown Article"

    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(url)
            if response.status_code == 200:
                # Simple content extraction (would use readability in production)
                html = response.text
                # Strip tags for simple text extraction
                import re
                text = re.sub(r'<[^>]+>', ' ', html)
                text = re.sub(r'\s+', ' ', text)
                content = text[:4000]

                # Try to extract title if not provided
                if not title:
                    title_match = re.search(r'<title[^>]*>([^<]+)</title>', html, re.IGNORECASE)
                    if title_match:
                        article_title = title_match.group(1).strip()
    except Exception as e:
        print(f"[news] Error fetching article: {e}")

    # Generate summary using LLM
    if content:
        try:
            summary = await summarize_article(article_title, content)
        except Exception as e:
            print(f"[news] LLM error: {e}")
            summary = content[:200] + "..."
    else:
        summary = "Unable to fetch article content."

    result = {
        "title": article_title,
        "summary": summary,
        "source": url,
        "tokens_used": len(content.split()) // 4  # Rough token estimate
    }

    await cache_set(cache_key, result, 3600)  # 1 hour cache
    return SummarizeArticleResponse(**result)
