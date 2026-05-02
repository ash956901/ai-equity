"""Enrichment step to extract structured metrics, timeline summary, and red flags from filings."""
import logging
import json
from typing import Dict, Any

from src.llm import get_llm
from langchain_core.messages import HumanMessage

logger = logging.getLogger(__name__)

class FilingEnricher:
    """Uses LLM to enrich raw filing text with summaries and structured metrics."""
    
    def __init__(self):
        self.llm = get_llm(temperature=0.0)
        
    def enrich_filing(self, text: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Generate timeline summary, extract red flags, and key metrics."""
        safe_text = text[:8000] # LLM context window safety
        
        prompt = f"""
You are an expert financial analyst. Analyze the following excerpts from a company filing.
Extract the following information in strict JSON format:
1. "timeline_summary": A concise (<50 words) actionable summary of the filing (e.g. 'Capex guidance raised 30%...').
2. "red_flags": A list of strings identifying any governance, accounting, or risk warnings. Leave empty if none.
3. "metrics": A dictionary of extracted financial metrics (e.g., "revenue_cr": number, "pat_cr": number). Only include if clearly stated.

Filing Text:
{safe_text}

Return ONLY a valid JSON object, without any markdown code blocks or explanations.
"""
        try:
            response = self.llm.invoke([HumanMessage(content=prompt)])
            
            content = response.content.strip()
            if content.startswith("```json"):
                content = content[7:-3].strip()
            elif content.startswith("```"):
                content = content[3:-3].strip()
                
            enrichment_data = json.loads(content)
            return enrichment_data
        except Exception as e:
            logger.error(f"Error enriching filing: {e}")
            return {
                "timeline_summary": "Automated summary could not be generated.",
                "red_flags": [],
                "metrics": {}
            }
