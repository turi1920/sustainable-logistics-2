from decimal import Decimal
from typing import Any, Dict, List

from backend.app.services.environmental_service import calculate_environmental_impact


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
    """
    options = []

    # 1. REFURBISH
    if physical_condition in ["GOOD", "LOW_DAMAGE", "MEDIUM_DAMAGE"]:
        repair_cost = Decimal("65.00") if physical_condition == "MEDIUM_DAMAGE" else Decimal("35.00") if physical_condition == "LOW_DAMAGE" else Decimal("20.00")
        packaging_cost = Decimal("8.00")
        transport_cost = Decimal("12.00")
        sanitization_cost = Decimal("10.00")
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
            "recommendation_reason": "Maximizes net financial recovery and product lifecycle extension through cosmetic & functional refurbishment."
        })

    # 2. REPAIR
    if physical_condition in ["LOW_DAMAGE", "MEDIUM_DAMAGE", "HIGH_DAMAGE"]:
        repair_cost = Decimal("85.00") if physical_condition == "HIGH_DAMAGE" else Decimal("50.00")
        packaging_cost = Decimal("8.00")
        transport_cost = Decimal("12.00")
        sanitization_cost = Decimal("10.00")
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

    # 3. RESALE_AS_IS
    if physical_condition in ["GOOD", "LOW_DAMAGE"] and functional_passed:
        repair_cost = Decimal("0.00")
        packaging_cost = Decimal("5.00")
        transport_cost = Decimal("12.00")
        sanitization_cost = Decimal("10.00")
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
            "recommendation_reason": "Immediate liquidation as Grade-B / open-box with zero repair expenditure."
        })

    # 4. RETURN_TO_RETAILER
    transport_cost = Decimal("18.00")
    handling_cost = Decimal("10.00")
    resale_val = Decimal("0.00")
    nrv = resale_val - (transport_cost + handling_cost)
    env = calculate_environmental_impact(product_category, "RETURN_TO_RETAILER")
    options.append({
        "option_type": "RETURN_TO_RETAILER",
        "estimated_resale_value": resale_val,
        "estimated_repair_cost": handling_cost,
        "estimated_packaging_cost": Decimal("0.00"),
        "estimated_transport_cost": transport_cost,
        "estimated_sanitization_cost": Decimal("0.00"),
        "estimated_nrv": nrv,
        "co2_saved_kg": env["co2_saved_kg"],
        "environmental_assumptions": env["assumptions"],
        "recommendation_reason": "Revert custody back to originating retailer/manufacturer per commercial agreement."
    })

    # 5. RECYCLE
    scrap_val = Decimal("8.00")
    recycle_fee = Decimal("15.00")
    transport_cost = Decimal("5.00")
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

    # Determine recommended option: highest NRV that is positive; if none positive, RECYCLE or RETURN
    viable_options = [opt for opt in options if opt["option_type"] in ["REFURBISH", "REPAIR", "RESALE_AS_IS"]]
    if viable_options:
        best_opt = max(viable_options, key=lambda x: x["estimated_nrv"])
    else:
        best_opt = options[0]

    for opt in options:
        opt["is_recommended"] = (opt["option_type"] == best_opt["option_type"])

    return options
