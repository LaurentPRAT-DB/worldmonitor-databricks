"""
Intelligence API endpoints - Risk scores and AI analysis.
"""

from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Query
from pydantic import BaseModel

from ..db import cache_get, cache_set
from ..llm import generate_country_brief, classify_event, chat_completion

router = APIRouter()


class RiskScore(BaseModel):
    country_code: str
    country_name: str
    overall_risk: float  # 0-100
    political_risk: float
    economic_risk: float
    security_risk: float
    climate_risk: float
    last_updated: str


class GetRiskScoresResponse(BaseModel):
    scores: list[RiskScore]
    updated_at: int


class CountryBrief(BaseModel):
    country_code: str
    country_name: str
    current_situation: str
    key_risks: list[str]
    outlook: str
    generated_at: str
    data_sources: list[str]


class EventClassification(BaseModel):
    category: str
    severity: str
    tags: list[str]
    affected_sectors: list[str]


class AskRequest(BaseModel):
    question: str
    context: Optional[str] = None  # Optional context about what's on screen


class AskResponse(BaseModel):
    answer: str
    sources: list[str]
    generated_at: str


# Placeholder risk data (would be calculated from multiple data sources)
RISK_DATA = {
    "US": {"name": "United States", "overall": 25, "political": 30, "economic": 20, "security": 20, "climate": 30},
    "CN": {"name": "China", "overall": 45, "political": 50, "economic": 40, "security": 45, "climate": 50},
    "RU": {"name": "Russia", "overall": 75, "political": 80, "economic": 75, "security": 80, "climate": 40},
    "UA": {"name": "Ukraine", "overall": 90, "political": 85, "economic": 90, "security": 95, "climate": 50},
    "DE": {"name": "Germany", "overall": 30, "political": 25, "economic": 35, "security": 20, "climate": 35},
    "GB": {"name": "United Kingdom", "overall": 30, "political": 30, "economic": 35, "security": 25, "climate": 30},
    "FR": {"name": "France", "overall": 35, "political": 40, "economic": 35, "security": 30, "climate": 35},
    "JP": {"name": "Japan", "overall": 30, "political": 25, "economic": 35, "security": 25, "climate": 45},
    "IN": {"name": "India", "overall": 50, "political": 45, "economic": 50, "security": 55, "climate": 60},
    "BR": {"name": "Brazil", "overall": 50, "political": 55, "economic": 50, "security": 50, "climate": 55},
    "IL": {"name": "Israel", "overall": 70, "political": 60, "economic": 50, "security": 85, "climate": 45},
    "IR": {"name": "Iran", "overall": 80, "political": 85, "economic": 85, "security": 75, "climate": 55},
    "SA": {"name": "Saudi Arabia", "overall": 45, "political": 50, "economic": 40, "security": 45, "climate": 50},
    "TW": {"name": "Taiwan", "overall": 55, "political": 65, "economic": 40, "security": 60, "climate": 45},
}

RISK_CACHE_TTL = 3600  # 1 hour


@router.get("/risk-scores", response_model=GetRiskScoresResponse)
async def get_risk_scores(
    countries: Optional[str] = Query(None, description="Comma-separated country codes"),
):
    """Get risk scores for countries."""
    cache_key = f"risk:{countries or 'all'}"

    cached = await cache_get(cache_key)
    if cached:
        return GetRiskScoresResponse(**cached)

    # Filter countries if specified
    codes = [c.strip().upper() for c in countries.split(",")] if countries else list(RISK_DATA.keys())

    scores = []
    now = datetime.utcnow().isoformat()

    for code in codes:
        if code in RISK_DATA:
            data = RISK_DATA[code]
            scores.append(RiskScore(
                country_code=code,
                country_name=data["name"],
                overall_risk=data["overall"],
                political_risk=data["political"],
                economic_risk=data["economic"],
                security_risk=data["security"],
                climate_risk=data["climate"],
                last_updated=now,
            ))

    result = {
        "scores": [s.model_dump() for s in scores],
        "updated_at": int(datetime.utcnow().timestamp() * 1000)
    }
    await cache_set(cache_key, result, RISK_CACHE_TTL)
    return GetRiskScoresResponse(**result)


@router.get("/country-brief/{country_code}", response_model=CountryBrief)
async def get_country_brief(
    country_code: str,
    refresh: bool = Query(False, description="Force refresh from AI"),
):
    """Get AI-generated intelligence brief for a country."""
    cache_key = f"brief:{country_code.upper()}"

    if not refresh:
        cached = await cache_get(cache_key)
        if cached:
            return CountryBrief(**cached)

    code = country_code.upper()
    country_name = RISK_DATA.get(code, {}).get("name", country_code)

    # Generate brief using LLM
    try:
        # Get recent events (would come from database in production)
        recent_events = [
            {"title": "Economic Update", "summary": "Recent economic indicators..."},
            {"title": "Political Development", "summary": "Latest political news..."},
        ]

        # Get economic data (would come from database)
        economic_data = {
            "gdp_growth": 2.5,
            "inflation": 3.2,
            "unemployment": 4.1,
        }

        brief_text = await generate_country_brief(
            country_name=country_name,
            country_code=code,
            recent_events=recent_events,
            economic_data=economic_data,
        )

        # Parse the structured response
        lines = brief_text.split("\n")
        situation = ""
        risks = []
        outlook = ""

        section = ""
        for line in lines:
            line = line.strip()
            if "Current Situation" in line or "situation" in line.lower():
                section = "situation"
            elif "Key Risks" in line or "risks" in line.lower():
                section = "risks"
            elif "Outlook" in line or "outlook" in line.lower():
                section = "outlook"
            elif line.startswith("-") or line.startswith("•"):
                if section == "risks":
                    risks.append(line.lstrip("-•").strip())
            elif line:
                if section == "situation":
                    situation += line + " "
                elif section == "outlook":
                    outlook += line + " "

        brief = CountryBrief(
            country_code=code,
            country_name=country_name,
            current_situation=situation.strip() or "Analysis in progress.",
            key_risks=risks if risks else ["Analysis pending"],
            outlook=outlook.strip() or "Assessment ongoing.",
            generated_at=datetime.utcnow().isoformat(),
            data_sources=["ACLED", "UCDP", "World Bank", "News Feeds"],
        )
    except Exception as e:
        print(f"[intelligence] LLM error: {e}")
        brief = CountryBrief(
            country_code=code,
            country_name=country_name,
            current_situation="Brief generation temporarily unavailable.",
            key_risks=["Data analysis pending"],
            outlook="Check back later for updated assessment.",
            generated_at=datetime.utcnow().isoformat(),
            data_sources=[],
        )

    await cache_set(cache_key, brief.model_dump(), 3600)  # 1 hour cache
    return brief


@router.post("/classify-event", response_model=EventClassification)
async def classify_event_endpoint(
    title: str = Query(..., description="Event title"),
    description: str = Query(..., description="Event description"),
    location: Optional[str] = Query(None, description="Event location"),
):
    """Classify an event using AI."""
    try:
        result = await classify_event(title, description, location)
        return EventClassification(**result)
    except Exception as e:
        print(f"[intelligence] Classification error: {e}")
        return EventClassification(
            category="other",
            severity="medium",
            tags=[],
            affected_sectors=[],
        )


# System prompt for the Ask AI feature
ASK_SYSTEM_PROMPT = """You are World Monitor AI, an expert geopolitical intelligence analyst.
You help users understand global events, conflicts, risks, economic trends, and security situations.

Your knowledge includes:
- Armed conflicts and military activities (ACLED, UCDP data)
- Natural disasters (earthquakes from USGS, wildfires from NASA FIRMS)
- Maritime tracking and shipping routes
- Financial markets and economic indicators
- Cyber threats and infrastructure status
- Country risk assessments

Guidelines:
- Be concise and factual
- Cite data sources when possible
- Provide actionable insights
- Flag high-risk situations
- Use professional, analytical tone
- If you don't know something, say so

Current date: {current_date}
"""


@router.post("/ask", response_model=AskResponse)
async def ask_ai(request: AskRequest):
    """Ask the AI about global events, risks, and analysis."""
    try:
        # Build system prompt with current date
        system_prompt = ASK_SYSTEM_PROMPT.format(
            current_date=datetime.utcnow().strftime("%Y-%m-%d")
        )

        # Add context if provided
        user_message = request.question
        if request.context:
            user_message = f"Context: {request.context}\n\nQuestion: {request.question}"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]

        # Get response from LLM
        answer = await chat_completion(
            messages=messages,
            max_tokens=1000,
            temperature=0.7,
        )

        return AskResponse(
            answer=answer,
            sources=["ACLED", "UCDP", "USGS", "NASA FIRMS", "Finnhub", "World Monitor Analysis"],
            generated_at=datetime.utcnow().isoformat(),
        )

    except Exception as e:
        print(f"[intelligence] Ask AI error: {e}")
        return AskResponse(
            answer="I apologize, but I'm temporarily unable to process your question. Please try again in a moment.",
            sources=[],
            generated_at=datetime.utcnow().isoformat(),
        )
