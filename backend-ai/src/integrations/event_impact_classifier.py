"""Event impact classifier - maps geopolitical events to commodity impacts."""

import logging
from dataclasses import dataclass
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class EventImpact:
    """Represents the impact of an event on commodities/sectors."""
    commodity: Optional[str] = None
    direction: str = "neutral"  # increase, decrease, neutral
    magnitude: str = "low"  # high, medium, low
    affected_sectors: list[str] = None
    confidence: float = 0.5
    trigger_keywords: list[str] = None

    def __post_init__(self):
        if self.affected_sectors is None:
            self.affected_sectors = []
        if self.trigger_keywords is None:
            self.trigger_keywords = []


class EventImpactClassifier:
    """Classifies geopolitical events by financial/commodity impact."""

    # Event patterns mapped to commodity impacts
    IMPACT_MAPPINGS = {
        # Middle East conflicts → Oil
        "middle_east": {
            "keywords": ["israel", "iran", "saudi", "iraq", "syria", "yemen", "gulf", "opec", "crude oil", "oil price"],
            "commodities": ["WTI_USD", "BRENT_CRUDE_USD"],
            "direction": "increase",
            "magnitude": "high",
            "sectors": ["Oil & Gas", "Aviation", "Transportation"],
            "description": "Middle East conflicts typically increase oil prices due to supply disruption fears",
        },
        # Russia/Ukraine → Natural Gas + Wheat
        "russia_ukraine": {
            "keywords": ["russia", "ukraine", "war", "putin", "kyiv", "kremlin", "natural gas", "gas supply", "wheat", "grain"],
            "commodities": ["NATURAL_GAS_USD", "wheat", "corn"],
            "direction": "increase",
            "magnitude": "high",
            "sectors": ["Power", "Fertilizer", "Sugar"],
            "description": "Russia/Europe tension disrupts natural gas supply, affects global wheat trade",
        },
        # US/China tensions → Copper, Tech metals
        "us_china": {
            "keywords": ["china", "us", "tariff", "trade war", "sanctions", "taiwan", "beijing", "wto"],
            "commodities": ["copper", "aluminum"],
            "direction": "uncertain",
            "magnitude": "medium",
            "sectors": ["Metals & Mining", "Automobile"],
            "description": "US-China tensions affect commodity demand and trade flows",
        },
        # India-related → Rupee, local sectors
        "india": {
            "keywords": ["india", "indian", "modi", "mumbai", "delhi", "rbi", "rupee"],
            "commodities": [],
            "direction": "neutral",
            "magnitude": "medium",
            "sectors": ["Banking", "Financial Services"],
            "description": "India-specific events affect local markets",
        },
        # Brazil weather → Agriculture (sugar, coffee)
        "brazil_weather": {
            "keywords": ["brazil", "drought", "flood", "rain", "harvest", "sugar", "coffee", "soybeans", "safrinha"],
            "commodities": ["sugar_11", "coffee", "corn", "soybeans"],
            "direction": "increase",
            "magnitude": "medium",
            "sectors": ["Sugar"],
            "description": "Brazil weather disruptions affect global agricultural commodity prices",
        },
        # US Fed → Gold, Interest rates
        "fed_rates": {
            "keywords": ["federal reserve", "fed", "interest rate", "inflation", " Jerome Powell", "fomc"],
            "commodities": ["XAU"],  # Gold
            "direction": "uncertain",
            "magnitude": "medium",
            "sectors": ["Jewellery", "Banking"],
            "description": "Fed policy changes affect gold as safe haven and interest-rate sensitive sectors",
        },
        # Europe energy crisis
        "europe_energy": {
            "keywords": ["europe", "energy crisis", "electricity", "power shortage", "coal", "nuclear"],
            "commodities": ["NATURAL_GAS_USD", "COAL_USD", "electricity"],
            "direction": "increase",
            "magnitude": "high",
            "sectors": ["Power", "Fertilizer"],
            "description": "Europe energy crises increase demand for alternative energy sources",
        },
        # Shipping/Ports → Commodities logistics
        "shipping": {
            "keywords": ["suez", "panama", "shipping", "port", "logistics", "container", "freight"],
            "commodities": ["WTI_USD", "BRENT_CRUDE_USD"],
            "direction": "increase",
            "magnitude": "medium",
            "sectors": ["Transportation", "Logistics"],
            "description": "Shipping disruptions affect commodity transport costs",
        },
    }

    def classify(self, event: dict[str, Any]) -> Optional[EventImpact]:
        """Classify an event and determine its commodity impact.
        
        Args:
            event: Event dict with title, summary, country, category
            
        Returns:
            EventImpact with commodity/sector implications, or None if no impact
        """
        title = (event.get("title") or "").lower()
        summary = (event.get("summary") or "").lower()
        country = (event.get("country") or "").lower()
        category = (event.get("category") or "").lower()
        
        text_to_analyze = f"{title} {summary} {country} {category}"
        
        # Find matching pattern
        best_match = None
        best_confidence = 0
        
        for pattern_name, mapping in self.IMPACT_MAPPINGS.items():
            keywords = mapping.get("keywords", [])
            matches = sum(1 for kw in keywords if kw in text_to_analyze)
            
            if matches > 0:
                confidence = min(0.9, matches / len(keywords) * 2)  # Normalize confidence
                
                # Boost confidence for country-specific events
                if country in keywords:
                    confidence += 0.1
                
                if confidence > best_confidence:
                    best_match = mapping
                    best_confidence = confidence
                    best_pattern = pattern_name
        
        if best_match and best_confidence >= 0.2:
            return EventImpact(
                commodity=best_match.get("commodities", [None])[0] if best_match.get("commodities") else None,
                direction=best_match.get("direction", "neutral"),
                magnitude=best_match.get("magnitude", "low"),
                affected_sectors=best_match.get("sectors", []),
                confidence=min(0.9, best_confidence),
                trigger_keywords=best_match.get("keywords", [])[:5],
            )
        
        return None

    def classify_batch(self, events: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Classify multiple events and return those with significant impact.
        
        Args:
            events: List of event dicts
            
        Returns:
            List of events with impact classification added
        """
        significant_events = []
        
        for event in events:
            impact = self.classify(event)
            
            if impact and impact.confidence >= 0.3:
                event["impact"] = {
                    "commodity": impact.commodity,
                    "direction": impact.direction,
                    "magnitude": impact.magnitude,
                    "affected_sectors": impact.affected_sectors,
                    "confidence": impact.confidence,
                }
                significant_events.append(event)
        
        return significant_events

    def get_commodity_alert(
        self,
        events: list[dict[str, Any]],
        current_commodities: dict[str, float],
    ) -> list[dict[str, Any]]:
        """Generate commodity alerts based on events + current prices.
        
        Args:
            events: List of classified events
            current_commodities: Dict of symbol -> price change percentage
            
        Returns:
            List of alerts with recommendations
        """
        alerts = []
        
        classified = self.classify_batch(events)
        
        for event in classified:
            impact = event.get("impact", {})
            commodity = impact.get("commodity")
            
            if commodity and commodity in current_commodities:
                price_change = current_commodities.get(commodity, 0)
                
                # Generate alert if price already moving in expected direction
                if (impact["direction"] == "increase" and price_change > 2) or \
                   (impact["direction"] == "decrease" and price_change < -2):
                    
                    alerts.append({
                        "event_title": event.get("title"),
                        "event_country": event.get("country"),
                        "commodity": commodity,
                        "price_change": price_change,
                        "direction": impact["direction"],
                        "magnitude": impact["magnitude"],
                        "sectors_affected": impact.get("affected_sectors", []),
                        "confidence": impact.get("confidence"),
                        "summary": event.get("summary", "")[:200],
                    })
        
        return alerts


# Singleton instance for reuse
_classifier = None


def get_event_classifier() -> EventImpactClassifier:
    """Get singleton instance of EventImpactClassifier."""
    global _classifier
    if _classifier is None:
        _classifier = EventImpactClassifier()
    return _classifier