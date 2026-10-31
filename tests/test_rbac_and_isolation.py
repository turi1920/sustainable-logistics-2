
def get_token(client, username, password):
    resp = client.post("/api/auth/login", json={"username_or_email": username, "password": password})
    assert resp.status_code == 200
    return resp.json()["access_token"]

def test_unauthorized_actions_by_role(client):
    """Step 17: Verify unauthorized role actions are rejected with 403 Forbidden."""
    warehouse_token = get_token(client, "warehouse", "Warehouse123!")
    inspector_token = get_token(client, "inspector", "Inspector123!")
    retailer_token = get_token(client, "retailer_tech", "Retailer123!")

    # 1. Warehouse employee attempts to conduct inspection -> 403
    resp = client.post(
        "/api/returns/RET-1002/inspect",
        headers={"Authorization": f"Bearer {warehouse_token}"},
        json={"physical_condition": "GOOD"}
    )
    assert resp.status_code == 403
    assert "not authorized" in resp.json()["detail"]

    # 2. Warehouse employee attempts to approve retailer decision -> 403
    resp = client.post(
        "/api/returns/RET-1003/decide",
        headers={"Authorization": f"Bearer {warehouse_token}"},
        json={"decision": "APPROVED", "approved_option": "REFURBISH"}
    )
    assert resp.status_code == 403

    # 3. Inspector attempts to restock inventory -> 403
    resp = client.post(
        "/api/returns/RET-1003/restock",
        headers={"Authorization": f"Bearer {inspector_token}"},
        json={"disposition_type": "RESTOCKED"}
    )
    assert resp.status_code == 403

    # 4. Retailer attempts to confirm warehouse receipt -> 403
    resp = client.post(
        "/api/returns/RET-1001/receive",
        headers={"Authorization": f"Bearer {retailer_token}"},
        json={"serial_received": "SN-000", "storage_location": "Bin 1"}
    )
    assert resp.status_code == 403

def test_cross_retailer_tenant_isolation(client):
    """Step 18: Verify that one retailer cannot access another retailer's records."""
    retailer1_token = get_token(client, "retailer_tech", "Retailer123!")  # Org 1: TechRetail Direct
    retailer2_token = get_token(client, "retailer_apex", "Retailer123!")  # Org 2: Apex Mobile

    # RET-1001 belongs to TechRetail Direct (Org 1)
    # Retailer 1 CAN access RET-1001
    r1_resp = client.get("/api/returns/RET-1001", headers={"Authorization": f"Bearer {retailer1_token}"})
    assert r1_resp.status_code == 200
    assert r1_resp.json()["id"] == "RET-1001"

    # Retailer 2 CANNOT access RET-1001 -> 403 Forbidden!
    r2_resp = client.get("/api/returns/RET-1001", headers={"Authorization": f"Bearer {retailer2_token}"})
    assert r2_resp.status_code == 403
    assert "another retailer organization" in r2_resp.json()["detail"]

    # Retailer 2 CANNOT view journey of RET-1001 -> 403 Forbidden!
    r2_journey_resp = client.get("/api/returns/RET-1001/journey", headers={"Authorization": f"Bearer {retailer2_token}"})
    assert r2_journey_resp.status_code == 403

    # Retailer 2 CANNOT decide or approve RET-1003 (Org 1) -> 403 Forbidden!
    r2_decide_resp = client.post(
        "/api/returns/RET-1003/decide",
        headers={"Authorization": f"Bearer {retailer2_token}"},
        json={"decision": "APPROVED", "approved_option": "REFURBISH"}
    )
    assert r2_decide_resp.status_code == 403

    # Retailer 2 listing returns only sees Org 2 returns (never Org 1)
    list_resp = client.get("/api/returns", headers={"Authorization": f"Bearer {retailer2_token}"})
    assert list_resp.status_code == 200
    items = list_resp.json()
    for item in items:
        assert item["organization_id"] == 2
        assert item["id"] != "RET-1001"
        assert item["id"] != "RET-1003"
