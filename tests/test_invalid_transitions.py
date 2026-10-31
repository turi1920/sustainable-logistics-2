
def get_token(client, username, password):
    resp = client.post("/api/auth/login", json={"username_or_email": username, "password": password})
    assert resp.status_code == 200
    return resp.json()["access_token"]

def test_invalid_workflow_transitions(client):
    admin_token = get_token(client, "admin", "Admin123!")

    # 1. RET-1001 is in RETURN_REQUESTED.
    # Attempting to inspect before receipt must fail with 400 Bad Request.
    insp_resp = client.post(
        "/api/returns/RET-1001/inspect",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"physical_condition": "GOOD"}
    )
    assert insp_resp.status_code == 400
    assert "Invalid workflow transition" in insp_resp.json()["detail"]

    # 2. Attempting to approve RET-1001 before inspection must fail with 400
    appr_resp = client.post(
        "/api/returns/RET-1001/decide",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"decision": "APPROVED", "approved_option": "REFURBISH"}
    )
    assert appr_resp.status_code == 400
    assert "Invalid workflow transition" in appr_resp.json()["detail"]

    # 3. Attempting to process RET-1001 before approval must fail with 400
    proc_resp = client.post(
        "/api/returns/RET-1001/process",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"work_performed": "Fixed screen"}
    )
    assert proc_resp.status_code == 400
    assert "Invalid workflow transition" in proc_resp.json()["detail"]

    # 4. Attempting to restock RET-1001 before QC must fail with 400
    restock_resp = client.post(
        "/api/returns/RET-1001/restock",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"disposition_type": "RESTOCKED"}
    )
    assert restock_resp.status_code == 400
    assert "Invalid workflow transition" in restock_resp.json()["detail"]

def test_data_sanitization_gate_rejection(client):
    """Requirement 11: Data sanitization gate must block QC if sanitization failed."""
    admin_token = get_token(client, "admin", "Admin123!")

    # Advance a test case to PROCESSING_COMPLETED
    # First register
    reg = client.post(
        "/api/returns",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "return_id": "RET-SAN-TEST",
            "organization_id": 1,
            "product_name": "Test Phone",
            "sku": "TP-01"
        }
    )
    assert reg.status_code == 201

    # Receive
    client.post("/api/returns/RET-SAN-TEST/receive", headers={"Authorization": f"Bearer {admin_token}"}, json={"serial_received": "SN-1", "storage_location": "B1"})
    # Inspect
    client.post("/api/returns/RET-SAN-TEST/inspect", headers={"Authorization": f"Bearer {admin_token}"}, json={"physical_condition": "GOOD"})
    # Approve
    client.post("/api/returns/RET-SAN-TEST/decide", headers={"Authorization": f"Bearer {admin_token}"}, json={"decision": "APPROVED", "approved_option": "REFURBISH"})
    # Process
    client.post("/api/returns/RET-SAN-TEST/process", headers={"Authorization": f"Bearer {admin_token}"}, json={"work_performed": "Cleaned"})

    # Now attempt QC with sanitization_passed = False
    qc_fail_resp = client.post(
        "/api/returns/RET-SAN-TEST/qc",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "functional_qc_passed": True,
            "cosmetic_grade": "GRADE_A",
            "sanitization_passed": False  # FAILED SANITIZATION
        }
    )
    assert qc_fail_resp.status_code == 400
    assert "Sanitization Gate Failed" in qc_fail_resp.json()["detail"]
