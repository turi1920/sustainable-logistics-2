from decimal import Decimal

from backend.app.services.environmental_service import calculate_environmental_impact


def test_smartphone_environmental_calculation():
    """Verify that smartphone environmental calculations display baseline assumptions."""
    impact = calculate_environmental_impact("Smartphone", "REFURBISH")

    # Baseline manufacturing (70.0 kg) - Refurbishment (1.5 kg) = 68.5 kg CO2e saved
    assert impact["co2_saved_kg"] == Decimal("68.50")
    assert impact["ewaste_diverted_kg"] == Decimal("0.19")
    assert impact["minerals_saved_grams"] == Decimal("180.00")

    # Verify assumptions are transparently stated
    assumptions = impact["assumptions"]
    assert "Baseline manufacturing footprint: 70.00 kg CO2 eq" in assumptions
    assert "Refurbishment/reprocessing footprint: 1.50 kg CO2 eq" in assumptions
    assert "Net avoided emissions = 68.50 kg CO2 eq" in assumptions
    assert "E-waste diverted: 0.19 kg" in assumptions

def test_recycling_environmental_calculation():
    impact = calculate_environmental_impact("Smartphone", "RECYCLE")
    # Recycling recovers material without full device reuse
    assert impact["co2_saved_kg"] == Decimal("70.00") * Decimal("0.45")
    assert "Circularity" in impact["status_note"]
