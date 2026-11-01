from decimal import Decimal
from typing import Any, Dict, List

from backend.app.services.environmental_service import calculate_environmental_impact


def is_data_bearing(product_category: str) -> bool:
    """Check if the product category contains digital storage requiring customer privacy sanitization."""
    cat = (product_category or "").strip().upper()
    data_bearing_tokens = ["PHONE", "LAPTOP", "TABLET", "SMARTWATCH", "STORAGE", "DRIVE", "ELECTRONIC", "COMPUTER"]
    return any(token in cat for token in data_bearing_tokens)


def generate_recovery_options(
    product_category: str,
    base_resale_value: Decimal,
    physical_condition: str,
    battery_health: int,
    functional_passed: bool
) -> List[Dict[str, Any]]:
    """
    Computes recovery options and Net Recovery Value (NRV).
    NRV = Resale Value - (Repair + Packaging + Transport + Sanitization)

    Business Policies Enforced:
    1. Products are never restocked without restoring them to their best condition (REFURBISH).
    2. Data-bearing devices with digital storage always require certified data sanitization for customer privacy (₹800.00).
    3. Units with physical/cosmetic damage cannot be resold as-is without reconditioning to best condition.
    4. Returning to retailer incurs ₹0.00 repair cost (returned in received condition).
    """
    options = []
    has_storage = is_data_bearing(product_category)
    sanitization_cost = Decimal("800.00") if has_storage else Decimal("0.00")

    # 1. REFURBISH (Restores device to its best like-new condition)
    if physical_condition in ["GOOD", "LOW_DAMAGE", "MEDIUM_DAMAGE"]:
        repair_cost = Decimal("5200.00") if physical_condition == "MEDIUM_DAMAGE" else Decimal("2800.00") if physical_condition == "LOW_DAMAGE" else Decimal("1600.00")
        packaging_cost = Decimal("640.00")
        transport_cost = Decimal("960.00")
        resale_val = base_resale_value * Decimal("0.85")
        nrv = resale_val - (repair_cost + packaging_cost + transport_cost + sanitization_cost)
        env = calculate_environmental_impact(product_category, "REFURBISH")
        options.append({
            "option_type": "REFURBISH",
            "estimated_resale_value": resale_val,
            "estimated_repair_cost": repair_cost,
            "estimated_packaging_cost": packaging_cost,
            "estimated_transport_cost": transport_cost,
            "estimated_sanitization_cost": sanitization_cost,
            "estimated_nrv": nrv,
            "co2_saved_kg": env["co2_saved_kg"],
            "environmental_assumptions": env["assumptions"],
            "recommendation_reason": "Restores product to best certified like-new condition with mandatory customer privacy data sanitization prior to restocking."
        })

    # 2. REPAIR (Functional component repair)
    if physical_condition in ["LOW_DAMAGE", "MEDIUM_DAMAGE", "HIGH_DAMAGE"]:
        repair_cost = Decimal("6800.00") if physical_condition == "HIGH_DAMAGE" else Decimal("4000.00")
        packaging_cost = Decimal("640.00")
        transport_cost = Decimal("960.00")
        resale_val = base_resale_value * Decimal("0.70")
        nrv = resale_val - (repair_cost + packaging_cost + transport_cost + sanitization_cost)
        env = calculate_environmental_impact(product_category, "REPAIR")
        options.append({
            "option_type": "REPAIR",
            "estimated_resale_value": resale_val,
            "estimated_repair_cost": repair_cost,
            "estimated_packaging_cost": packaging_cost,
            "estimated_transport_cost": transport_cost,
            "estimated_sanitization_cost": sanitization_cost,
            "estimated_nrv": nrv,
            "co2_saved_kg": env["co2_saved_kg"],
            "environmental_assumptions": env["assumptions"],
            "recommendation_reason": "Functional component fix to restore operation without complete cosmetic overhaul."
        })

    # 3. RESALE_AS_IS (Only allowed if ALREADY in best pristine condition; damaged units cannot be restocked as-is)
    if physical_condition == "GOOD" and functional_passed:
        repair_cost = Decimal("0.00")
        packaging_cost = Decimal("400.00")
        transport_cost = Decimal("960.00")
        resale_val = base_resale_value * Decimal("0.60")
        nrv = resale_val - (repair_cost + packaging_cost + transport_cost + sanitization_cost)
        env = calculate_environmental_impact(product_category, "RESALE_AS_IS")
        options.append({
            "option_type": "RESALE_AS_IS",
            "estimated_resale_value": resale_val,
            "estimated_repair_cost": repair_cost,
            "estimated_packaging_cost": packaging_cost,
            "estimated_transport_cost": transport_cost,
            "estimated_sanitization_cost": sanitization_cost,
            "estimated_nrv": nrv,
            "co2_saved_kg": env["co2_saved_kg"],
            "environmental_assumptions": env["assumptions"],
            "recommendation_reason": "Direct restocking for pristine unopened/mint units with mandatory data sanitization."
        })

    # 4. RETURN_TO_RETAILER (Returned as-is, zero repair performed)
    transport_cost = Decimal("1440.00")
    repair_cost = Decimal("0.00")
    resale_val = Decimal("0.00")
    nrv = resale_val - transport_cost
    env = calculate_environmental_impact(product_category, "RETURN_TO_RETAILER")
    options.append({
        "option_type": "RETURN_TO_RETAILER",
        "estimated_resale_value": resale_val,
        "estimated_repair_cost": repair_cost,
        "estimated_packaging_cost": Decimal("0.00"),
        "estimated_transport_cost": transport_cost,
        "estimated_sanitization_cost": Decimal("0.00"),
        "estimated_nrv": nrv,
        "co2_saved_kg": env["co2_saved_kg"],
        "environmental_assumptions": env["assumptions"],
        "recommendation_reason": "Revert custody back to originating retailer/manufacturer as received with zero technical repairs."
    })

    # 5. RECYCLE (Certified e-waste breakdown)
    scrap_val = Decimal("640.00")
    recycle_fee = Decimal("1200.00")
    transport_cost = Decimal("400.00")
    nrv = scrap_val - (recycle_fee + transport_cost)
    env = calculate_environmental_impact(product_category, "RECYCLE")
    options.append({
        "option_type": "RECYCLE",
        "estimated_resale_value": scrap_val,
        "estimated_repair_cost": recycle_fee,
        "estimated_packaging_cost": Decimal("0.00"),
        "estimated_transport_cost": transport_cost,
        "estimated_sanitization_cost": Decimal("0.00"),
        "estimated_nrv": nrv,
        "co2_saved_kg": env["co2_saved_kg"],
        "environmental_assumptions": env["assumptions"],
        "recommendation_reason": "Safe material breakdown and certified electronic waste recycling."
    })

    # Best-Condition Recommendation Policy:
    # 1. Prioritize REFURBISH whenever viable, as it restores the product to best condition for certified restocking.
    # 2. If REFURBISH is not viable (e.g. HIGH_DAMAGE), pick best viable positive NRV (REPAIR), else RECYCLE.
    refurb_opt = next((o for o in options if o["option_type"] == "REFURBISH"), None)
    if refurb_opt and refurb_opt["estimated_nrv"] > Decimal("0.00"):
        best_opt = refurb_opt
    else:
        viable_options = [opt for opt in options if opt["option_type"] in ["REFURBISH", "REPAIR", "RESALE_AS_IS"]]
        if viable_options:
            best_opt = max(viable_options, key=lambda x: x["estimated_nrv"])
        else:
            best_opt = options[0]

    for opt in options:
        opt["is_recommended"] = (opt["option_type"] == best_opt["option_type"])

    return options
