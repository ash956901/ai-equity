"""Seed initial causal chains and sector exposures for Indian market."""

import logging

from src.db.database import SessionLocal
from src.db.models import CausalChain, SectorExposure

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def seed_causal_chains(db):
    """Seed initial causal chains."""
    
    chains = [
        # Oil & Gas → Transportation → Aviation
        {
            "name": "Middle East Conflict → Oil → Aviation",
            "trigger_type": "geopolitical_event",
            "trigger_value": "middle_east_conflict",
            "hop1_type": "commodity",
            "hop1_target": "WTI_USD",
            "hop1_relationship": "causes_increase",
            "hop2_type": "commodity",
            "hop2_target": "JET_FUEL_USD",
            "hop2_relationship": "pass_through",
            "hop3_type": "sector",
            "hop3_target": "Aviation",
            "hop3_relationship": "margin_pressure",
            "confidence": 0.8,
        },
        # Russia/Ukraine → Natural Gas → Fertilizer
        {
            "name": "Russia/Ukraine → Natural Gas → Fertilizer",
            "trigger_type": "geopolitical_event",
            "trigger_value": "russia_ukraine_tension",
            "hop1_type": "commodity",
            "hop1_target": "NATURAL_GAS_USD",
            "hop1_relationship": "causes_increase",
            "hop2_type": "sector",
            "hop2_target": "Fertilizer",
            "hop2_relationship": "input_cost_increase",
            "hop3_type": "sector",
            "hop3_target": "Fertilizer",
            "hop3_relationship": "margin_pressure",
            "confidence": 0.75,
        },
        # Brazil drought → Sugar → Indian Sugar companies
        {
            "name": "Brazil Drought → Sugar → Indian Sugar",
            "trigger_type": "weather_event",
            "trigger_value": "brazil_drought",
            "hop1_type": "commodity",
            "hop1_target": "sugar_11",
            "hop1_relationship": "causes_increase",
            "hop2_type": "sector",
            "hop2_target": "Sugar",
            "hop2_relationship": "price_increase",
            "hop3_type": "sector",
            "hop3_target": "Sugar",
            "hop3_relationship": "export_benefit",
            "confidence": 0.7,
        },
        # US China tension → Copper → Metals/Mining
        {
            "name": "US China Tension → Copper → Metals",
            "trigger_type": "geopolitical_event",
            "trigger_value": "us_china_tension",
            "hop1_type": "commodity",
            "hop1_target": "copper",
            "hop1_relationship": "causes_decrease",
            "hop2_type": "sector",
            "hop2_target": "Metals & Mining",
            "hop2_relationship": "demand_impact",
            "hop3_type": "sector",
            "hop3_target": "Metals & Mining",
            "hop3_relationship": "revenue_impact",
            "confidence": 0.65,
        },
        # Gold → Jewellery → Titan
        {
            "name": "Gold Price ↑ → Jewellery → Titan",
            "trigger_type": "commodity_change",
            "trigger_value": "gold_price_increase",
            "hop1_type": "commodity",
            "hop1_target": "XAU",
            "hop1_relationship": "causes_increase",
            "hop2_type": "sector",
            "hop2_target": "Jewellery",
            "hop2_relationship": "input_cost_increase",
            "hop3_type": "sector",
            "hop3_target": "Jewellery",
            "hop3_relationship": "margin_pressure",
            "confidence": 0.75,
        },
        # USD/INR → IT Services
        {
            "name": "USD Strength → IT Exports → TCS/INFY",
            "trigger_type": "currency_change",
            "trigger_value": "usd_inr_increase",
            "hop1_type": "commodity",
            "hop1_target": "USDINR",
            "hop1_relationship": "causes_increase",
            "hop2_type": "sector",
            "hop2_target": "IT Services",
            "hop2_relationship": "revenue_benefit",
            "hop3_type": "sector",
            "hop3_target": "IT Services",
            "hop3_relationship": "earnings_upside",
            "confidence": 0.85,
        },
        # Coal → Steel → Tata Steel
        {
            "name": "Coal Price ↑ → Steel Costs → Tata Steel margins",
            "trigger_type": "commodity_change",
            "trigger_value": "coal_price_increase",
            "hop1_type": "commodity",
            "hop1_target": "COAL_USD",
            "hop1_relationship": "causes_increase",
            "hop2_type": "sector",
            "hop2_target": "Steel",
            "hop2_relationship": "input_cost_increase",
            "hop3_type": "sector",
            "hop3_target": "Steel",
            "hop3_relationship": "margin_pressure",
            "confidence": 0.8,
        },
        # Diesel → Logistics → AllCargo
        {
            "name": "Diesel ↑ → Logistics Costs → Transport sector",
            "trigger_type": "commodity_change",
            "trigger_value": "diesel_price_increase",
            "hop1_type": "commodity",
            "hop1_target": "DIESEL_USD",
            "hop1_relationship": "causes_increase",
            "hop2_type": "sector",
            "hop2_target": "Transportation",
            "hop2_relationship": "input_cost_increase",
            "hop3_type": "sector",
            "hop3_target": "Transportation",
            "hop3_relationship": "margin_pressure",
            "confidence": 0.8,
        },
        # Oil → FMCG input costs → HUL
        {
            "name": "Oil ↑ → Input Costs → FMCG margins",
            "trigger_type": "commodity_change",
            "trigger_value": "oil_price_increase",
            "hop1_type": "commodity",
            "hop1_target": "WTI_USD",
            "hop1_relationship": "causes_increase",
            "hop2_type": "sector",
            "hop2_target": "FMCG",
            "hop2_relationship": "input_cost_increase",
            "hop3_type": "sector",
            "hop3_target": "FMCG",
            "hop3_relationship": "margin_pressure",
            "confidence": 0.7,
        },
        # Gas → Fertilizer → NFL/RCF
        {
            "name": "Gas ↑ → Fertilizer Costs → Agri sector",
            "trigger_type": "commodity_change",
            "trigger_value": "gas_price_increase",
            "hop1_type": "commodity",
            "hop1_target": "NATURAL_GAS_USD",
            "hop1_relationship": "causes_increase",
            "hop2_type": "sector",
            "hop2_target": "Fertilizer",
            "hop2_relationship": "input_cost_increase",
            "hop3_type": "sector",
            "hop3_target": "Fertilizer",
            "hop3_relationship": "margin_pressure",
            "confidence": 0.8,
        },
        # Gold → Jewellery → Titan etc
        {
            "name": "Global Uncertainty → Gold → Jewellery",
            "trigger_type": "macro_event",
            "trigger_value": "global_uncertainty",
            "hop1_type": "commodity",
            "hop1_target": "XAU",
            "hop1_relationship": "causes_increase",
            "hop2_type": "sector",
            "hop2_target": "Jewellery",
            "hop2_relationship": "demand_increase",
            "hop3_type": "sector",
            "hop3_target": "Jewellery",
            "hop3_relationship": "revenue_benefit",
            "confidence": 0.75,
        },
    ]

    for chain_data in chains:
        existing = (
            db.query(CausalChain)
            .filter(
                CausalChain.trigger_value == chain_data["trigger_value"],
                CausalChain.name == chain_data["name"],
            )
            .first()
        )
        
        if not existing:
            chain = CausalChain(**chain_data)
            db.add(chain)
            logger.info(f"Added causal chain: {chain_data['name']}")

    db.commit()
    logger.info("Causal chains seeding complete")


def seed_sector_exposures(db):
    """Seed sector to commodity exposure mappings."""
    
    exposures = [
        # Oil & Gas
        {
            "sector": "Oil & Gas",
            "industry": "Exploration & Production",
            "commodity": "WTI_USD",
            "dependency_type": "revenue",
            "impact_direction": "positive",
            "impact_magnitude": "high",
            "affected_companies": ["RELIANCE", "ONGC", "OIL", "GAIL"],
        },
        {
            "sector": "Oil & Gas",
            "industry": "Refining & Marketing",
            "commodity": "WTI_USD",
            "dependency_type": "input_cost",
            "impact_direction": "negative",
            "impact_magnitude": "high",
            "affected_companies": ["RELIANCE", "HPCL", "BPCL", "IOC"],
        },
        # Power
        {
            "sector": "Power",
            "industry": "Thermal Power",
            "commodity": "COAL_USD",
            "dependency_type": "input_cost",
            "impact_direction": "negative",
            "impact_magnitude": "high",
            "affected_companies": ["NTPC", "TATA_POWER", "JSW_ENERGY", "ADANI_POWER"],
        },
        {
            "sector": "Power",
            "industry": "Thermal Power",
            "commodity": "NATURAL_GAS_USD",
            "dependency_type": "input_cost",
            "impact_direction": "negative",
            "impact_magnitude": "medium",
            "affected_companies": ["NTPC", "RIL"],
        },
        # Aviation
        {
            "sector": "Aviation",
            "industry": "Airlines",
            "commodity": "JET_FUEL_USD",
            "dependency_type": "input_cost",
            "impact_direction": "negative",
            "impact_magnitude": "high",
            "affected_companies": ["INDIGO", "SPICEJET", "AIRINDIA", "GOAIR"],
        },
        # Sugar
        {
            "sector": "Sugar",
            "industry": "Sugar Manufacturing",
            "commodity": "sugar_11",
            "dependency_type": "revenue",
            "impact_direction": "positive",
            "impact_magnitude": "high",
            "affected_companies": ["BKW", "DWARIKESH", "MAHARASHTRA_SUGAR", "TRIVENI"],
        },
        # Jewellery
        {
            "sector": "Jewellery",
            "industry": "Retail",
            "commodity": "XAU",
            "dependency_type": "input_cost",
            "impact_direction": "negative",
            "impact_magnitude": "medium",
            "affected_companies": ["TITAN", "KALYAN", "MALABAR", "PANDORA"],
        },
        # Metals & Mining
        {
            "sector": "Metals & Mining",
            "industry": "Copper",
            "commodity": "copper",
            "dependency_type": "revenue",
            "impact_direction": "positive",
            "impact_magnitude": "high",
            "affected_companies": ["HINDALCO", "VEDANTA", "HINDUSTAN_COPPER"],
        },
        {
            "sector": "Metals & Mining",
            "industry": "Aluminum",
            "commodity": "aluminum",
            "dependency_type": "revenue",
            "impact_direction": "positive",
            "impact_magnitude": "medium",
            "affected_companies": ["HINDALCO", "VEDANTA", "NATIONAL_ALUM"],
        },
        # Fertilizer
        {
            "sector": "Fertilizer",
            "industry": "Nitrogenous",
            "commodity": "NATURAL_GAS_USD",
            "dependency_type": "input_cost",
            "impact_direction": "negative",
            "impact_magnitude": "high",
            "affected_companies": ["NFL", "RCF", "FACT", "GSFC"],
        },
        # Automobile
        {
            "sector": "Automobile",
            "industry": "Four Wheeler",
            "commodity": "WTI_USD",
            "dependency_type": "input_cost",
            "impact_direction": "negative",
            "impact_magnitude": "medium",
            "affected_companies": ["MARUTI", "HYUNDAI", "TATA_MOTORS", "M&M"],
        },
        # Transportation/Logistics
        {
            "sector": "Transportation",
            "industry": "Logistics",
            "commodity": "DIESEL_USD",
            "dependency_type": "input_cost",
            "impact_direction": "negative",
            "impact_magnitude": "high",
            "affected_companies": ["ALLCARGO", "GATEWAY", "ACEMO", "VRL_LOG"],
        },
        # IT Services (USD/INR impact)
        {
            "sector": "IT Services",
            "industry": "Software Services",
            "commodity": "USDINR",
            "dependency_type": "revenue",
            "impact_direction": "positive",
            "impact_magnitude": "high",
            "affected_companies": ["TCS", "INFY", "WIPRO", "HCLTECH"],
        },
        # Pharmaceuticals (API costs)
        {
            "sector": "Pharmaceuticals",
            "industry": "Generic Drugs",
            "commodity": "NATURAL_GAS_USD",
            "dependency_type": "input_cost",
            "impact_direction": "negative",
            "impact_magnitude": "medium",
            "affected_companies": ["SUNPHARMA", "DRREDDY", "CIPLA", "APPM"],
        },
        # Real Estate (interest rates proxy via oil)
        {
            "sector": "Real Estate",
            "industry": "Residential",
            "commodity": "WTI_USD",
            "dependency_type": "macro_proxy",
            "impact_direction": "negative",
            "impact_magnitude": "medium",
            "affected_companies": ["DLF", "GODREJ", "PRESTIGE", "OBEROI"],
        },
        # FMCG (commodity input costs)
        {
            "sector": "FMCG",
            "industry": "Consumer Staples",
            "commodity": "WTI_USD",
            "dependency_type": "input_cost",
            "impact_direction": "negative",
            "impact_magnitude": "medium",
            "affected_companies": ["HUL", "NESTLE", "BRITANNIA", "ITC"],
        },
        # Steel (coal + iron ore proxy)
        {
            "sector": "Steel",
            "industry": "Flat Steel",
            "commodity": "COAL_USD",
            "dependency_type": "input_cost",
            "impact_direction": "negative",
            "impact_magnitude": "high",
            "affected_companies": ["TATA_STEEL", "JSW_STEEL", "SAIL", "NMDC"],
        },
        # Cement (coal + logistics)
        {
            "sector": "Cement",
            "industry": "Portland Cement",
            "commodity": "COAL_USD",
            "dependency_type": "input_cost",
            "impact_direction": "negative",
            "impact_magnitude": "high",
            "affected_companies": ["ACC", "AMBUJACEM", "ULTRACEM", "SHREE_CEM"],
        },
        # Textile (cotton proxy via gas/fertilizer)
        {
            "sector": "Textiles",
            "industry": "Cotton textiles",
            "commodity": "NATURAL_GAS_USD",
            "dependency_type": "input_cost",
            "impact_direction": "negative",
            "impact_magnitude": "medium",
            "affected_companies": ["Raymond", "Trident", "Welspun", "Arvind"],
        },
    ]

    for exp_data in exposures:
        existing = (
            db.query(SectorExposure)
            .filter(
                SectorExposure.sector == exp_data["sector"],
                SectorExposure.commodity == exp_data["commodity"],
            )
            .first()
        )
        
        if not existing:
            exposure = SectorExposure(**exp_data)
            db.add(exposure)
            logger.info(f"Added sector exposure: {exp_data['sector']} -> {exp_data['commodity']}")

    db.commit()
    logger.info("Sector exposures seeding complete")


def main():
    db = SessionLocal()
    try:
        logger.info("Starting seed data for causal intelligence...")
        
        seed_causal_chains(db)
        seed_sector_exposures(db)
        
        logger.info("Seed data complete!")
        
    except Exception as e:
        logger.error(f"Seed failed: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()