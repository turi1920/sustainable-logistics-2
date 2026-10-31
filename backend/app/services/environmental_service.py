from decimal import Decimal
from typing import Any, Dict

# Standard LCA benchmarks for consumer electronics (based on ISO 14040/44 LCA studies)
CATEGORY_BENCHMARKS = {
    "Smartphone": {
        "manufacturing_co2_kg": Decimal("70.00"),
        "weight_kg": Decimal("0.19"),
        "transport_co2_per_km_kg": Decimal("0.00015"),
        "avg_transit_km": 150,
        "refurb_co2_kg": Decimal("1.50"),
        "minerals_saved_grams": Decimal("180.00"),
    },
    "Headphones": {
        "manufacturing_co2_kg": Decimal("25.00"),
        "weight_kg": Decimal("0.25"),
        "transport_co2_per_km_kg": Decimal("0.00015"),
        "avg_transit_km": 150,
        "refurb_co2_kg": Decimal("0.80"),
        "minerals_saved_grams": Decimal("80.00"),
    },
    "Smartwatch": {
        "manufacturing_co2_kg": Decimal("35.00"),
        "weight_kg": Decimal("0.06"),
        "transport_co2_per_km_kg": Decimal("0.00015"),
        "avg_transit_km": 150,
        "refurb_co2_kg": Decimal("0.90"),
        "minerals_saved_grams": Decimal("60.00"),
    },
    "Laptop": {
        "manufacturing_co2_kg": Decimal("280.00"),
        "weight_kg": Decimal("1.80"),
        "transport_co2_per_km_kg": Decimal("0.00015"),
        "avg_transit_km": 150,
        "refurb_co2_kg": Decimal("4.50"),
        "minerals_saved_grams": Decimal("950.00"),
    }
}

DEFAULT_BENCHMARK = CATEGORY_BENCHMARKS["Smartphone"]

def calculate_environmental_impact(category: str, option_type: str) -> Dict[str, Any]:
    benchmark = CATEGORY_BENCHMARKS.get(category, DEFAULT_BENCHMARK)
    mfg_co2 = benchmark["manufacturing_co2_kg"]
    refurb_co2 = benchmark["refurb_co2_kg"]
    device_weight = benchmark["weight_kg"]
    minerals = benchmark["minerals_saved_grams"]

    if option_type in ["REFURBISH", "REPAIR", "RESALE_AS_IS"]:
        net_saved_co2 = mfg_co2 - refurb_co2
        ewaste_diverted = device_weight
        minerals_saved = minerals
        status_note = "High Circularity (Reuse / Life Extension)"
    elif option_type == "RECYCLE":
        # Recycling recovers materials (~60% emissions savings vs virgin mining), avoids landfill
        net_saved_co2 = mfg_co2 * Decimal("0.45")
        ewaste_diverted = device_weight * Decimal("0.85")
        minerals_saved = minerals * Decimal("0.70")
        status_note = "Moderate Circularity (Material Recovery & Landfill Diversion)"
    else:  # RETURN_TO_RETAILER
        net_saved_co2 = Decimal("0.00")
        ewaste_diverted = Decimal("0.00")
        minerals_saved = Decimal("0.00")
        status_note = "Custody Reverted to Retailer / Manufacturer"

    assumptions_text = (
        f"Assumptions: (1) Baseline manufacturing footprint: {mfg_co2} kg CO2 eq "
        f"(standard LCA for {category}); (2) Refurbishment/reprocessing footprint: {refurb_co2} kg CO2 eq; "
        f"(3) Net avoided emissions = {net_saved_co2} kg CO2 eq; "
        f"(4) E-waste diverted: {ewaste_diverted} kg (100% of product mass kept out of municipal landfills); "
        f"(5) Avoided virgin mineral extraction: {minerals_saved} g."
    )

    return {
        "co2_saved_kg": net_saved_co2,
        "ewaste_diverted_kg": ewaste_diverted,
        "minerals_saved_grams": minerals_saved,
        "status_note": status_note,
        "assumptions": assumptions_text
    }
