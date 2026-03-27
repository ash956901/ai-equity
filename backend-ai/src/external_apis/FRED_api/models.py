"""
Pydantic models for FRED API responses
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date


# ==================== Series Models ====================

class SeriesObservation(BaseModel):
    """Single observation from a FRED series"""
    date: str = Field(..., description="Observation date")
    value: str = Field(..., description="Observation value (may be '.' for missing)")
    realtime_start: Optional[str] = Field(None, description="Real-time period start date")
    realtime_end: Optional[str] = Field(None, description="Real-time period end date")


class SeriesInfo(BaseModel):
    """Metadata about a FRED series"""
    id: str = Field(..., description="Series ID")
    title: str = Field(..., description="Series title")
    observation_start: str = Field(..., description="First observation date")
    observation_end: str = Field(..., description="Last observation date")
    frequency: str = Field(..., description="Data frequency")
    frequency_short: str = Field(..., description="Short frequency code")
    units: str = Field(..., description="Units of measurement")
    units_short: str = Field(..., description="Short units code")
    seasonal_adjustment: str = Field(..., description="Seasonal adjustment")
    seasonal_adjustment_short: str = Field(..., description="Short seasonal adjustment code")
    last_updated: str = Field(..., description="Last update timestamp")
    popularity: int = Field(..., description="Popularity ranking")
    notes: Optional[str] = Field(None, description="Series notes")


class SeriesSearchResult(BaseModel):
    """Search result for series"""
    id: str = Field(..., description="Series ID")
    title: str = Field(..., description="Series title")
    observation_start: str = Field(..., description="First observation date")
    observation_end: str = Field(..., description="Last observation date")
    frequency: str = Field(..., description="Data frequency")
    units: str = Field(..., description="Units of measurement")
    seasonal_adjustment: str = Field(..., description="Seasonal adjustment")
    popularity: int = Field(..., description="Popularity ranking")


# ==================== Category Models ====================

class Category(BaseModel):
    """FRED data category"""
    id: int = Field(..., description="Category ID")
    name: str = Field(..., description="Category name")
    parent_id: int = Field(..., description="Parent category ID")


# ==================== Tag Models ====================

class Tag(BaseModel):
    """FRED series tag"""
    name: str = Field(..., description="Tag name")
    group_id: str = Field(..., description="Tag group ID")
    notes: Optional[str] = Field(None, description="Tag notes")
    created: str = Field(..., description="Creation timestamp")
    popularity: int = Field(..., description="Tag popularity")
    series_count: int = Field(..., description="Number of series with this tag")


# ==================== Release Models ====================

class Release(BaseModel):
    """FRED data release"""
    id: int = Field(..., description="Release ID")
    realtime_start: str = Field(..., description="Real-time period start")
    realtime_end: str = Field(..., description="Real-time period end")
    name: str = Field(..., description="Release name")
    press_release: bool = Field(..., description="Has press release")
    link: Optional[str] = Field(None, description="Release link")


class ReleaseDate(BaseModel):
    """Release date information"""
    release_id: int = Field(..., description="Release ID")
    date: str = Field(..., description="Release date")


# ==================== Response Models ====================

class SeriesObservationsResponse(BaseModel):
    """Response containing series observations"""
    realtime_start: str
    realtime_end: str
    observation_start: str
    observation_end: str
    units: str
    output_type: int
    file_type: str
    order_by: str
    sort_order: str
    count: int
    offset: int
    limit: int
    observations: List[SeriesObservation]


class SeriesInfoResponse(BaseModel):
    """Response containing series information"""
    realtime_start: str
    realtime_end: str
    seriess: List[SeriesInfo]


class SeriesSearchResponse(BaseModel):
    """Response containing search results"""
    realtime_start: str
    realtime_end: str
    order_by: str
    sort_order: str
    count: int
    offset: int
    limit: int
    seriess: List[SeriesSearchResult]


class CategoryResponse(BaseModel):
    """Response containing category information"""
    categories: List[Category]


class TagsResponse(BaseModel):
    """Response containing tags"""
    realtime_start: str
    realtime_end: str
    order_by: str
    sort_order: str
    count: int
    offset: int
    limit: int
    tags: List[Tag]


class ReleasesResponse(BaseModel):
    """Response containing releases"""
    realtime_start: str
    realtime_end: str
    order_by: str
    sort_order: str
    count: int
    offset: int
    limit: int
    releases: List[Release]


# ==================== Convenience Response Models ====================

class EconomicDataPoint(BaseModel):
    """Simplified economic data point for API responses"""
    date: str = Field(..., description="Observation date")
    value: Optional[float] = Field(None, description="Numeric value")
    value_str: str = Field(..., description="String value (original)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "date": "2024-01-01",
                "value": 5.33,
                "value_str": "5.33"
            }
        }


class YieldCurvePoint(BaseModel):
    """Single point on the yield curve"""
    maturity: str = Field(..., description="Maturity (e.g., '10Y')")
    yield_value: Optional[float] = Field(None, description="Yield percentage")
    date: str = Field(..., description="Observation date")


class YieldCurveResponse(BaseModel):
    """Yield curve data"""
    date: str = Field(..., description="Yield curve date")
    curve_points: List[YieldCurvePoint] = Field(..., description="Yield curve points")
    
    class Config:
        json_schema_extra = {
            "example": {
                "date": "2024-01-01",
                "curve_points": [
                    {"maturity": "3M", "yield_value": 5.4, "date": "2024-01-01"},
                    {"maturity": "2Y", "yield_value": 4.8, "date": "2024-01-01"},
                    {"maturity": "10Y", "yield_value": 4.2, "date": "2024-01-01"}
                ]
            }
        }


class EconomicIndicatorSummary(BaseModel):
    """Summary of key economic indicators"""
    indicator_name: str = Field(..., description="Indicator name")
    series_id: str = Field(..., description="FRED series ID")
    latest_value: Optional[float] = Field(None, description="Most recent value")
    latest_date: str = Field(..., description="Date of latest value")
    previous_value: Optional[float] = Field(None, description="Previous value")
    previous_date: Optional[str] = Field(None, description="Date of previous value")
    change: Optional[float] = Field(None, description="Change from previous")
    change_percent: Optional[float] = Field(None, description="Percent change from previous")
    units: str = Field(..., description="Units of measurement")
    frequency: str = Field(..., description="Data frequency")
    
    class Config:
        json_schema_extra = {
            "example": {
                "indicator_name": "Unemployment Rate",
                "series_id": "UNRATE",
                "latest_value": 3.7,
                "latest_date": "2024-01-01",
                "previous_value": 3.8,
                "previous_date": "2023-12-01",
                "change": -0.1,
                "change_percent": -2.63,
                "units": "Percent",
                "frequency": "Monthly"
            }
        }
