"""Pydantic contract for structured analyst output.

The orchestrator and each subagent are instructed to emit responses
matching this skeleton (Markdown-rendered). The contract is also used
server-side to lightly validate (presence of required sections) before
returning to the client; missing required sections trigger a single
auto-retry with a sharper instruction.

The structure follows the chatgpt.txt master spec section
"LLM REASONING STRUCTURE OUTPUT" plus the discovery extensions
introduced in the Hidden Insights & Industries plan.
"""

from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class ImpactDirection(str, Enum):
    POSITIVE = "+"
    NEGATIVE = "-"
    NEUTRAL = "neutral"


class ImpactHorizon(str, Enum):
    SHORT = "short"
    MEDIUM = "medium"
    LONG = "long"


class Citation(BaseModel):
    """Inline evidence reference for a claim."""

    label: str = Field(..., description="Theme code, filing id, or edge tag")
    quote: Optional[str] = Field(
        None, description="Verbatim excerpt that supports the claim"
    )
    url: Optional[str] = None


class ThemeExposure(BaseModel):
    code: str
    label: Optional[str] = None
    exposure_type: str
    impact_direction: ImpactDirection = ImpactDirection.POSITIVE
    impact_horizon: ImpactHorizon = ImpactHorizon.MEDIUM
    impact_score: float = 0.0
    confidence: float = 0.0
    is_asymmetric: bool = False
    evidence_quotes: List[str] = Field(default_factory=list)


class RiskFlag(BaseModel):
    code: str
    severity: str
    description: str
    metric: Optional[str] = None
    value: Optional[float] = None
    evidence: Optional[Citation] = None


class SecondOrderEffect(BaseModel):
    seed_theme: str
    derived_theme: str
    propagation_weight: float
    direction: ImpactDirection = ImpactDirection.POSITIVE
    top_companies: List[str] = Field(
        default_factory=list, description="company_id or ticker shortlist"
    )


class StructuredAnalysis(BaseModel):
    """Authoritative shape of an analyst response.

    Subagents need not return this object directly — they emit Markdown
    that follows the same section ordering. The Markdown is parsed
    optimistically; this Pydantic model is the contract for downstream
    consumers (frontend, exports, regression tests).
    """

    business_overview: str
    domain_exposure: List[ThemeExposure] = Field(default_factory=list)
    asymmetric_exposure: List[ThemeExposure] = Field(default_factory=list)
    growth_drivers: List[str] = Field(default_factory=list)
    cost_drivers: List[str] = Field(default_factory=list)
    financial_health: Optional[str] = None
    risk_flags: List[RiskFlag] = Field(default_factory=list)
    macro_sensitivity: Optional[str] = None
    second_order_effects: List[SecondOrderEffect] = Field(default_factory=list)
    valuation_commentary: Optional[str] = None
    bull_case: Optional[str] = None
    bear_case: Optional[str] = None
    explained_simply: str = Field(
        ..., description="Always populated, expertise-adapted layman summary"
    )
    sources: List[Citation] = Field(default_factory=list)
    suggested_followups: List[str] = Field(
        default_factory=list,
        description="3 specific questions to deepen the research journey",
    )


# ---------------------------------------------------------------------- #
# Section headers used both as Markdown anchors AND for validation.
# Order matters — synthesis prompts reference the same list.
# ---------------------------------------------------------------------- #

SECTION_ORDER: list[tuple[str, bool]] = [
    # (heading, required)
    ("Business Overview", True),
    ("Domain & Subdomain Exposure", False),
    ("Hidden / Asymmetric Exposure", False),
    ("Growth Drivers", False),
    ("Cost Drivers", False),
    ("Financial Health", False),
    ("Risk Flags", False),
    ("Macro Sensitivity", False),
    ("Second-Order Effects", False),
    ("Valuation Commentary", False),
    ("Bull vs Bear", False),
    ("Explained Simply", True),
    ("Sources", False),
    ("Suggested follow-ups", True),
]


def required_sections() -> list[str]:
    return [name for name, required in SECTION_ORDER if required]


def validate_markdown_skeleton(markdown: str) -> list[str]:
    """Return the list of required sections that are missing from
    ``markdown``. Empty list means the response is structurally valid.

    Lightweight check — looks for the heading text anywhere in the
    response (case-insensitive). Section content is not validated.
    """
    if not markdown:
        return required_sections()
    lowered = markdown.lower()
    missing: list[str] = []
    for name in required_sections():
        if name.lower() not in lowered:
            missing.append(name)
    return missing
