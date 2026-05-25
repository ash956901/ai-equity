"""GDELT Cloud client for geopolitical event detection."""

import logging
from datetime import datetime
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)


class GDELTClient:
    """Client for GDELT Cloud - structured geopolitical events.
    
    Docs: https://docs.gdeltcloud.com/
    Free tier available.
    """

    BASE_URL = "https://gdeltcloud.com/api/v2"

    # Relevant event categories for financial impact
    RELEVANT_CATEGORIES = [
        "conflict",
        "political",
        "economic",
        "infrastructure",
    ]

    # High-priority regions for Indian market
    PRIORITY_REGIONS = [
        "Middle East",
        "Europe",
        "USA",
        "China",
        "Russia",
        "India",
    ]

    def __init__(self, api_key: str):
        self.api_key = api_key

    def _get_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def get_events(
        self,
        country: Optional[str] = None,
        category: str = "conflict",
        hours: int = 24,
        min_confidence: float = 0.75,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Get recent significant events.
        
        Args:
            country: Filter by country code (e.g., 'US', 'RU', 'IL')
            category: Event family ('conflict' or 'cameoplus')
            hours: Look back window (default 24)
            min_confidence: Minimum confidence threshold
            limit: Max events to return
            
        Returns:
            List of event dicts
        """
        try:
            params = {
                "event_family": category,
                "hours": hours,
                "min_confidence": min_confidence,
                "limit": limit,
                "sort": "significance",
            }
            
            if country:
                params["country"] = country

            response = httpx.get(
                f"{self.BASE_URL}/events",
                params=params,
                headers=self._get_headers(),
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()

            events = data.get("events", [])
            return [self._transform_event(e) for e in events]

        except httpx.HTTPStatusError as e:
            logger.error(f"GDELT HTTP error: {e.response.status_code}")
        except Exception as e:
            logger.error(f"GDELT error: {str(e)}")
        
        return []

    def _transform_event(self, event: dict) -> dict:
        """Transform GDELT event to our schema."""
        return {
            "event_id": event.get("id"),
            "title": event.get("title", ""),
            "summary": event.get("summary", ""),
            "event_date": event.get("event_date"),
            "country": event.get("geo", {}).get("country"),
            "region": event.get("geo", {}).get("admin1"),
            "category": event.get("category"),
            "subcategory": event.get("subcategory"),
            "goldstein_scale": event.get("metrics", {}).get("goldstein_scale"),
            "confidence": event.get("metrics", {}).get("confidence"),
            "fatalities": event.get("metrics", {}).get("fatalities"),
            "source": "gdelt",
            "raw_data": event,
        }

    def get_events_by_countries(
        self,
        countries: list[str],
        hours: int = 24,
    ) -> list[dict[str, Any]]:
        """Get events for multiple countries.
        
        Args:
            countries: List of country codes
            hours: Look back window
            
        Returns:
            Combined list of events from all countries
        """
        all_events = []
        
        for country in countries:
            events = self.get_events(
                country=country,
                hours=hours,
                min_confidence=0.7,
            )
            all_events.extend(events)
        
        # Sort by significance/confidence
        all_events.sort(key=lambda x: x.get("confidence", 0), reverse=True)
        
        return all_events[:50]  # Limit to top 50

    def search_events(
        self,
        query: str,
        hours: int = 72,
    ) -> list[dict[str, Any]]:
        """Semantic search for events.
        
        Args:
            query: Search text
            hours: Look back window
            
        Returns:
            List of matching events
        """
        try:
            params = {
                "search": query,
                "hours": hours,
                "limit": 20,
            }

            response = httpx.get(
                f"{self.BASE_URL}/events",
                params=params,
                headers=self._get_headers(),
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()

            events = data.get("events", [])
            return [self._transform_event(e) for e in events]

        except Exception as e:
            logger.error(f"GDELT search error: {str(e)}")
            return []

    def get_middle_east_events(self, hours: int = 48) -> list[dict[str, Any]]:
        """Get Middle East conflict events (highest priority for oil prices)."""
        middle_east_countries = ["IL", "IR", "SA", "AE", "IQ", "SY", "YE", "PS"]
        return self.get_events_by_countries(middle_east_countries, hours)

    def get_europe_events(self, hours: int = 48) -> list[dict[str, Any]]:
        """Get Europe-related events."""
        europe_countries = ["RU", "UA", "GB", "DE", "FR", "IT", "PL"]
        return self.get_events_by_countries(europe_countries, hours)


# Alternative: Free GDELT raw API (no auth required for basic queries)
class GDELTFreeClient:
    """Free GDELT API without authentication.
    
    Use for basic event detection when API key unavailable.
    """

    BASE_URL = "https://api.gdeltproject.org/api/v2"

    def search_mentions(
        self,
        query: str,
        max_results: int = 25,
    ) -> list[dict[str, Any]]:
        """Search GDELT for mentions matching query."""
        try:
            url = f"{self.BASE_URL}/doc/doc"
            params = {
                "query": query,
                "format": "json",
                "maxresults": max_results,
                "mode": "artlist",
            }

            response = httpx.get(url, params=params, timeout=30.0, follow_redirects=True)
            response.raise_for_status()
            data = response.json()

            articles = data.get("articles", [])
            return [
                {
                    "title": a.get("title", ""),
                    "url": a.get("url", ""),
                    "domain": a.get("domain", ""),
                    "seendate": a.get("seendate", ""),
                    "source": "gdelt_free",
                }
                for a in articles
            ]

        except Exception as e:
            logger.error(f"GDELT free API error: {str(e)}")
            return []