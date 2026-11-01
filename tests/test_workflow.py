
def get_token(client, username, password):
    resp = client.post("/api/auth/login", json={"username_or_email": username, "password": password})
    assert resp.status_code == 200
    return resp.json()["access_token"]

def test_full_smartphone_return_lifecycle(client):
    admin_token = get_token(client, "admin", "Admin123!")
    warehouse_token = get_token(client, "warehouse", "Warehouse123!")
    inspector_token = get_token(client, "inspector", "Inspector123!")
    retailer_token = get_token(client, "retailer_tech", "Retailer123!")
    driver_token = get_token(client, "driver_eco", "Pickup123!")

    # 1. Register a new smartphone return (Step 6)
    reg_payload = {
        "return_id": "RET-2026-SMP-FLOW1",
        "order_ref": "ORD-SMP-9912",
        "organization_id": 1,  # TechRetail Direct
        "product_category": "Smartphone",
        "product_name": "Samsung Galaxy S22 Ultra 256GB",
        "sku": "SM-S908B-BLK",
        "serial_expected": "SN-S22U-7721",
        "customer_pincode": "94103",
        "return_reason": "Screen flickering, minor edge scuffs",
        "pickup_partner_id": 1  # Assigned to EcoLogix Express
    }
    reg_resp = client.post(
        "/api/returns",
        headers={"Authorization": f"Bearer {admin_token}"},
        json=reg_payload
    )
    assert reg_resp.status_code == 201, f"Failed registration: {reg_resp.text}"
    ret_data = reg_resp.json()
    return_id = ret_data["id"]
    assert ret_data["status"] == "RETURN_REQUESTED"
    assert ret_data["product_category"] == "Smartphone"
    assert ret_data["pickup_status"] == "ASSIGNED"

    # Phase sequencing check: Attempting to receive before pickup must fail with 400
    early_recv = client.post(
        f"/api/returns/{return_id}/receive",
        headers={"Authorization": f"Bearer {warehouse_token}"},
        json={"serial_received": "SN-S22U-7721", "storage_location": "Aisle 3, Bin W-302"}
    )
    assert early_recv.status_code == 400
    assert "Phase Sequencing Violation" in early_recv.json()["detail"]

    # 1.5. Driver picks up device from customer doorstep and delivers to warehouse dock
    collect_resp = client.post(
        f"/api/returns/{return_id}/confirm-pickup",
        headers={"Authorization": f"Bearer {driver_token}"},
        json={"picked_up_notes": "Device received from customer in protective padded pouch."}
    )
    assert collect_resp.status_code == 200
    assert collect_resp.json()["pickup_status"] == "IN_TRANSIT"

    deliver_resp = client.post(
        f"/api/returns/{return_id}/deliver-warehouse",
        headers={"Authorization": f"Bearer {driver_token}"},
        json={"delivery_notes": "Delivered to warehouse intake bay 3."}
    )
    assert deliver_resp.status_code == 200
    assert deliver_resp.json()["pickup_status"] == "DELIVERED_TO_WAREHOUSE"

    # 2. Confirm warehouse receipt (Step 7)
    recv_payload = {
        "serial_received": "SN-S22U-7721",
        "storage_location": "Aisle 3, Bin W-302",
        "package_condition": "Original retail box, all cords present"
    }
    recv_resp = client.post(
        f"/api/returns/{return_id}/receive",
        headers={"Authorization": f"Bearer {warehouse_token}"},
        json=recv_payload
    )
    assert recv_resp.status_code == 200, f"Failed receipt: {recv_resp.text}"
    assert recv_resp.json()["status"] == "RECEIVED"
    assert recv_resp.json()["storage_location"] == "Aisle 3, Bin W-302"

    # 3. Complete inspection & generate recovery estimates (Steps 8 & 9)
    insp_payload = {
        "physical_condition": "LOW_DAMAGE",
        "screen_condition": "Micro-scratches on display glass",
        "battery_health_pct": 89,
        "functional_tests_passed": True,
        "damage_notes": "Cosmetic scuffs only. Core electronics 100% operational.",
        "safety_concerns": "None. Battery safe."
    }
    insp_resp = client.post(
        f"/api/returns/{return_id}/inspect",
        headers={"Authorization": f"Bearer {inspector_token}"},
        json=insp_payload
    )
    assert insp_resp.status_code == 200, f"Failed inspection: {insp_resp.text}"
    insp_data = insp_resp.json()
    assert insp_data["status"] == "AWAITING_APPROVAL"
    assert len(insp_data["cost_estimates"]) >= 3

    # Inspect estimated options & NRVs
    refurb_opt = next((opt for opt in insp_data["cost_estimates"] if opt["option_type"] == "REFURBISH"), None)
    assert refurb_opt is not None
    assert float(refurb_opt["estimated_nrv"]) > 0
    assert float(refurb_opt["co2_saved_kg"]) > 0
    assert "Assumptions:" in refurb_opt["environmental_assumptions"]

    # 4. Retailer approves eligible recovery option (Step 10)
    decision_payload = {
        "decision": "APPROVED",
        "approved_option": "REFURBISH",
        "remarks": "Approved by TechRetail for certified refurbishment."
    }
    dec_resp = client.post(
        f"/api/returns/{return_id}/decide",
        headers={"Authorization": f"Bearer {retailer_token}"},
        json=decision_payload
    )
    assert dec_resp.status_code == 200, f"Failed decision: {dec_resp.text}"
    assert dec_resp.json()["status"] == "APPROVED"

    # 5. Complete technical processing task and record ACTUAL costs in INR (Step 11 & Step 15)
    proc_payload = {
        "work_performed": "Replaced glass surface layer, recalibrated battery, flashed factory firmware.",
        "actual_repair_cost": 5000.00,
        "actual_packaging_cost": 600.00,
        "actual_labor_cost": 1600.00,
        "actual_transport_cost": 960.00
    }
    proc_resp = client.post(
        f"/api/returns/{return_id}/process",
        headers={"Authorization": f"Bearer {inspector_token}"},
        json=proc_payload
    )
    assert proc_resp.status_code == 200, f"Failed processing: {proc_resp.text}"
    proc_data = proc_resp.json()
    assert proc_data["status"] == "PROCESSING_COMPLETED"
    pt = proc_data["processing_task"]
    assert float(pt["actual_repair_cost"]) == 5000.00
    assert float(pt["total_actual_cost"]) == 8160.00  # 5000 + 600 + 1600 + 960

    # 6. Perform required Quality Check & verify Data Sanitization Gate (Step 12)
    qc_payload = {
        "functional_qc_passed": True,
        "cosmetic_grade": "GRADE_A",
        "sanitization_passed": True,
        "sanitization_certificate": "CERT-NIST-800-88-S22U",
        "sanitization_method": "NIST SP 800-88 Rev 1 Cryptographic Erase",
        "qc_notes": "All 12 diagnostic tests passed. Ready for Grade A resale."
    }
    qc_resp = client.post(
        f"/api/returns/{return_id}/qc",
        headers={"Authorization": f"Bearer {inspector_token}"},
        json=qc_payload
    )
    assert qc_resp.status_code == 200, f"Failed QC: {qc_resp.text}"
    assert qc_resp.json()["status"] == "QC_PASSED"

    # 7. Restock product to inventory (Step 13)
    restock_payload = {
        "disposition_type": "RESTOCKED",
        "inventory_location": "SHELF-RESALE-S22-01",
        "realized_resale_value": 30000.00,
        "notes": "Added to secondary resale catalog."
    }
    restock_resp = client.post(
        f"/api/returns/{return_id}/restock",
        headers={"Authorization": f"Bearer {warehouse_token}"},
        json=restock_payload
    )
    assert restock_resp.status_code == 200, f"Failed restock: {restock_resp.text}"
    assert restock_resp.json()["status"] == "COMPLETED"

    # 8. Search for return and verify complete journey audit trail (Step 14)
    journey_resp = client.get(
        f"/api/returns/{return_id}/journey",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert journey_resp.status_code == 200
    journey = journey_resp.json()
    assert len(journey) >= 6

    actions = [j["action"] for j in journey]
    assert "REGISTER_RETURN" in actions
    assert "CONFIRM_WAREHOUSE_RECEIPT" in actions
    assert "COMPLETE_INSPECTION" in actions
    assert "RECORD_RETAILER_DECISION" in actions
    assert "COMPLETE_PROCESSING" in actions
    assert "COMPLETE_QUALITY_CHECK" in actions
    assert "DISPOSITION_RESTOCKED" in actions

    # 9. Verify Estimated vs Actual costs recorded separately (Step 15)
    detail_resp = client.get(
        f"/api/returns/{return_id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert detail_resp.status_code == 200
    detail = detail_resp.json()

    # Has estimated costs
    assert len(detail["cost_estimates"]) > 0
    est = detail["cost_estimates"][0]
    assert float(est["estimated_repair_cost"]) > 0
    assert float(est["estimated_resale_value"]) > 0

    # Has separate actual costs
    actual = detail["processing_task"]
    assert float(actual["actual_repair_cost"]) == 5000.00
    assert float(actual["total_actual_cost"]) == 8160.00
    assert float(detail["disposition"]["realized_resale_value"]) == 30000.00
