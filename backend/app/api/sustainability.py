from decimal import Decimal
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.app.core.dependencies import get_current_user
from backend.app.database import get_db
from backend.app.models.assessment import CostEstimate
from backend.app.models.execution import QualityCheck
from backend.app.models.return_request import ReturnRequest
from backend.app.models.user import User
from backend.app.services.environmental_service import (
    CATEGORY_BENCHMARKS,
    DEFAULT_BENCHMARK,
    calculate_environmental_impact,
)

router = APIRouter(prefix="/api/sustainability", tags=["Sustainability & Circularity Impact"])


@router.get("/summary")
def get_sustainability_summary(
    organization_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Calculate aggregated positive environmental impact, LCA metrics, and circular ledger."""
    query = db.query(ReturnRequest)
    if current_user.role == "RETAILER":
        query = query.filter(ReturnRequest.organization_id == current_user.organization_id)
    elif organization_id:
        query = query.filter(ReturnRequest.organization_id == organization_id)

    returns = query.order_by(ReturnRequest.created_at.desc()).all()

    total_returns = len(returns)
    total_co2_kg = Decimal("0.00")
    total_ewaste_kg = Decimal("0.00")
    total_minerals_g = Decimal("0.00")
    green_fleet_count = 0
    data_sanitized_count = 0

    strategy_counts = {
        "REFURBISH": 0,
        "REPAIR": 0,
        "RESALE_AS_IS": 0,
        "RECYCLE": 0,
        "RETURN_TO_RETAILER": 0
    }
    category_map: Dict[str, Dict[str, Any]] = {}
    ledger: List[Dict[str, Any]] = []

    for r in returns:
        benchmark = CATEGORY_BENCHMARKS.get(r.product_category, DEFAULT_BENCHMARK)
        device_weight = benchmark["weight_kg"]
        minerals_weight = benchmark["minerals_saved_grams"]

        # Check for recommended cost estimate or calculate benchmark
        rec_ce = (
            db.query(CostEstimate)
            .filter(CostEstimate.return_id == r.id, CostEstimate.is_recommended.is_(True))
            .first()
        )
        if rec_ce:
            co2_item = rec_ce.co2_saved_kg
            strategy = rec_ce.option_type
        else:
            # Estimate potential impact based on Refurbish policy
            env = calculate_environmental_impact(r.product_category, "REFURBISH")
            co2_item = env["co2_saved_kg"]
            strategy = "REFURBISH (Pending Inspection)"

        clean_strategy = strategy.split()[0]
        if clean_strategy in strategy_counts:
            strategy_counts[clean_strategy] += 1
        else:
            strategy_counts["REFURBISH"] += 1

        total_co2_kg += co2_item
        total_ewaste_kg += device_weight
        total_minerals_g += minerals_weight

        # Check green fleet pickup
        fleet_name = "Marketplace / Direct"
        if r.pickup_partner:
            fleet_name = f"{r.pickup_partner.name} ({r.pickup_partner.fleet_type})"
            ft_lower = (r.pickup_partner.fleet_type or "").lower()
            if any(k in ft_lower for k in ["electric", "zero", "cng", "hybrid", "bike", "cargo"]):
                green_fleet_count += 1
        elif r.assigned_driver:
            fleet_name = f"Driver @{r.assigned_driver.username}"

        # Check certified sanitization
        qc = db.query(QualityCheck).filter(QualityCheck.return_id == r.id).first()
        if qc and qc.sanitization_passed:
            data_sanitized_count += 1
            sanitized_status = "✅ Certified NIST 800-88"
        else:
            sanitized_status = "Pending Inspection/QC"

        # Category aggregation
        cat = r.product_category or "Other"
        if cat not in category_map:
            category_map[cat] = {
                "category": cat,
                "count": 0,
                "co2_saved_kg": Decimal("0.00"),
                "ewaste_diverted_kg": Decimal("0.00")
            }
        category_map[cat]["count"] += 1
        category_map[cat]["co2_saved_kg"] += co2_item
        category_map[cat]["ewaste_diverted_kg"] += device_weight

        ledger.append({
            "return_id": r.id,
            "order_ref": r.order_ref or "N/A",
            "product_name": r.product_name,
            "category": r.product_category,
            "status": r.status,
            "circular_strategy": strategy,
            "co2_saved_kg": float(co2_item),
            "ewaste_diverted_kg": float(device_weight),
            "minerals_saved_g": float(minerals_weight),
            "fleet_transit": fleet_name,
            "data_sanitization": sanitized_status
        })

    trees_eq = round(float(total_co2_kg) / 21.77, 1) if total_co2_kg > 0 else 0.0
    km_avoided = round(float(total_co2_kg) / 0.17, 1) if total_co2_kg > 0 else 0.0
    phone_charges_k = round((float(total_co2_kg) / 0.012) / 1000.0, 1) if total_co2_kg > 0 else 0.0

    return {
        "total_returns": total_returns,
        "total_co2_saved_kg": float(total_co2_kg),
        "total_ewaste_diverted_kg": float(total_ewaste_kg),
        "total_minerals_saved_grams": float(total_minerals_g),
        "circular_rate_pct": 100.0 if total_returns > 0 else 0.0,
        "green_fleet_pickups": green_fleet_count,
        "data_sanitized_count": data_sanitized_count,
        "trees_equivalent": trees_eq,
        "km_avoided": km_avoided,
        "phone_charges_thousand": phone_charges_k,
        "strategy_counts": strategy_counts,
        "category_breakdown": [
            {
                "category": v["category"],
                "count": v["count"],
                "co2_saved_kg": float(v["co2_saved_kg"]),
                "ewaste_diverted_kg": float(v["ewaste_diverted_kg"])
            }
            for v in category_map.values()
        ],
        "ledger": ledger
    }
