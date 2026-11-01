import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.scripts.seed import seed_demo_data

client = TestClient(app)

@pytest.fixture(scope="module", autouse=True)
def setup_database():
    seed_demo_data(reset=True)
    yield

def get_auth_token(username: str, password: str) -> str:
    response = client.post(
        "/api/auth/login",
        json={"username_or_email": username, "password": password}
    )
    assert response.status_code == 200, f"Login failed for {username}: {response.text}"
    return response.json()["access_token"]

def test_pickup_partner_driver_login():
    """Verify demo pickup drivers can authenticate and receive correct claims."""
    # Test EcoLogix Driver
    res_eco = client.post(
        "/api/auth/login",
        json={"username_or_email": "driver_eco", "password": "Pickup123!"}
    )
    assert res_eco.status_code == 200
    data_eco = res_eco.json()
    assert data_eco["role"] == "PICKUP_PARTNER"
    assert data_eco["pickup_partner_id"] is not None
    assert data_eco["pickup_partner_name"] == "EcoLogix Express"

    # Profile check /me
    token_eco = data_eco["access_token"]
    me_res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token_eco}"})
    assert me_res.status_code == 200
    assert me_res.json()["role"] == "PICKUP_PARTNER"
    assert me_res.json()["pickup_partner_name"] == "EcoLogix Express"

    # Test GreenRoute Driver
    res_green = client.post(
        "/api/auth/login",
        json={"username_or_email": "driver_green", "password": "Pickup123!"}
    )
    assert res_green.status_code == 200
    data_green = res_green.json()
    assert data_green["role"] == "PICKUP_PARTNER"
    assert data_green["pickup_partner_id"] is not None
    assert data_green["pickup_partner_name"] == "GreenRoute 3PL"
    assert data_eco["pickup_partner_id"] != data_green["pickup_partner_id"]

def test_carrier_multi_tenant_isolation():
    """Verify that a driver for Carrier A can ONLY view shipments assigned to Carrier A."""
    token_eco = get_auth_token("driver_eco", "Pickup123!")
    token_green = get_auth_token("driver_green", "Pickup123!")

    # EcoLogix Driver lists returns
    res_eco = client.get("/api/returns", headers={"Authorization": f"Bearer {token_eco}"})
    assert res_eco.status_code == 200
    eco_returns = res_eco.json()
    eco_return_ids = [r["id"] for r in eco_returns]

    assert "RET-1001" in eco_return_ids
    assert "RET-1004" not in eco_return_ids  # Belonging to GreenRoute 3PL

    # GreenRoute Driver lists returns
    res_green = client.get("/api/returns", headers={"Authorization": f"Bearer {token_green}"})
    assert res_green.status_code == 200
    green_returns = res_green.json()
    green_return_ids = [r["id"] for r in green_returns]

    assert "RET-1004" in green_return_ids
    assert "RET-1001" not in green_return_ids  # Belonging to EcoLogix Express

    # EcoLogix Driver attempts direct GET /api/returns/RET-1004 (Forbidden)
    forbidden_get = client.get("/api/returns/RET-1004", headers={"Authorization": f"Bearer {token_eco}"})
    assert forbidden_get.status_code == 403
    assert "Access denied" in forbidden_get.json()["detail"]

    # EcoLogix Driver attempts direct GET /api/returns/RET-1004/journey (Forbidden)
    forbidden_journey = client.get("/api/returns/RET-1004/journey", headers={"Authorization": f"Bearer {token_eco}"})
    assert forbidden_journey.status_code == 403
    assert "Access denied" in forbidden_journey.json()["detail"]

def test_driver_confirm_pickup_and_deliver_warehouse():
    """Verify pickup driver transitions return to IN_TRANSIT and DELIVERED_TO_WAREHOUSE."""
    token_eco = get_auth_token("driver_eco", "Pickup123!")

    # Confirm Doorstep Collection
    collect_payload = {"picked_up_notes": "Smartphone picked up from customer door. Serial verified."}
    res_collect = client.post(
        "/api/returns/RET-1001/confirm-pickup",
        headers={"Authorization": f"Bearer {token_eco}"},
        json=collect_payload
    )
    assert res_collect.status_code == 200
    assert res_collect.json()["pickup_status"] == "IN_TRANSIT"

    # Confirm Delivery to Warehouse Dock
    deliver_payload = {"delivery_notes": "Delivered to Central Warehouse intake dock bay 1."}
    res_deliver = client.post(
        "/api/returns/RET-1001/deliver-warehouse",
        headers={"Authorization": f"Bearer {token_eco}"},
        json=deliver_payload
    )
    assert res_deliver.status_code == 200
    assert res_deliver.json()["pickup_status"] == "DELIVERED_TO_WAREHOUSE"

    # Check journey audit trail
    journey_res = client.get("/api/returns/RET-1001/journey", headers={"Authorization": f"Bearer {token_eco}"})
    assert journey_res.status_code == 200
    actions = [h["action"] for h in journey_res.json()]
    assert "CONFIRM_PICKUP_COLLECTION" in actions
    assert "DELIVER_TO_WAREHOUSE_DOCK" in actions

def test_cross_carrier_unauthorized_rejections():
    """Verify that a driver cannot confirm collection or delivery for another carrier's shipment."""
    token_eco = get_auth_token("driver_eco", "Pickup123!")

    # Attempt to collect GreenRoute's shipment
    bad_collect = client.post(
        "/api/returns/RET-1004/confirm-pickup",
        headers={"Authorization": f"Bearer {token_eco}"},
        json={"picked_up_notes": "Unauthorized attempt"}
    )
    assert bad_collect.status_code == 403
    assert "Access denied" in bad_collect.json()["detail"]

    # Attempt to deliver GreenRoute's shipment
    bad_deliver = client.post(
        "/api/returns/RET-1004/deliver-warehouse",
        headers={"Authorization": f"Bearer {token_eco}"},
        json={"delivery_notes": "Unauthorized attempt"}
    )
    assert bad_deliver.status_code == 403
    assert "Access denied" in bad_deliver.json()["detail"]

def test_unauthorized_role_rejections():
    """Verify that unauthorized roles (e.g. Retailer) cannot call pickup endpoints."""
    token_ret = get_auth_token("retailer_tech", "Retailer123!")

    res = client.post(
        "/api/returns/RET-1001/confirm-pickup",
        headers={"Authorization": f"Bearer {token_ret}"},
        json={"picked_up_notes": "Retailer trying to collect"}
    )
    assert res.status_code == 403
    assert "Access denied" in res.json()["detail"]

    # Pickup driver cannot call warehouse intake receive
    token_eco = get_auth_token("driver_eco", "Pickup123!")
    bad_receive = client.post(
        "/api/returns/RET-1001/receive",
        headers={"Authorization": f"Bearer {token_eco}"},
        json={"serial_received": "SN-PXL-78901", "storage_location": "Bin W-1", "package_condition": "Good"}
    )
    assert bad_receive.status_code == 403
    assert "Access denied" in bad_receive.json()["detail"]

def test_driver_report_pickup_failure_and_warehouse_blocking():
    """Verify that a driver can report a failed pickup attempt, and warehouse intake is strictly blocked."""
    admin_token = get_auth_token("admin", "Admin123!")
    driver_token = get_auth_token("driver_eco", "Pickup123!")
    wh_token = get_auth_token("warehouse", "Warehouse123!")

    # 1. Register a new return assigned to EcoLogix (id: 1)
    reg_res = client.post(
        "/api/returns",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "return_id": "RET-FAIL-01",
            "organization_id": 1,
            "product_name": "Galaxy Fold Exception Test",
            "sku": "GF-TEST-01",
            "pickup_partner_id": 1,
            "customer_pincode": "560001"
        }
    )
    assert reg_res.status_code == 201
    assert reg_res.json()["pickup_status"] == "ASSIGNED"

    # 2. Driver reports doorstep collection failure
    fail_payload = {
        "failure_reason": "Customer Unavailable / Door Locked / Unreachable",
        "failure_notes": "Door locked, customer phone unreachable after 3 contact attempts."
    }
    fail_res = client.post(
        "/api/returns/RET-FAIL-01/fail-pickup",
        headers={"Authorization": f"Bearer {driver_token}"},
        json=fail_payload
    )
    assert fail_res.status_code == 200
    ret_data = fail_res.json()
    assert ret_data["pickup_status"] == "PICKUP_FAILED"
    assert "Pickup attempt failed" in ret_data["pickup_notes"]

    # Verify status history audit
    hist_actions = [h["action"] for h in ret_data["status_history"]]
    assert "RECORD_PICKUP_FAILURE" in hist_actions

    # 3. Warehouse intake MUST be strictly blocked with HTTP 400
    wh_attempt = client.post(
        "/api/returns/RET-FAIL-01/receive",
        headers={"Authorization": f"Bearer {wh_token}"},
        json={"serial_received": "GF-TEST-01", "storage_location": "Dock-1", "package_condition": "Boxed"}
    )
    assert wh_attempt.status_code == 400
    detail = wh_attempt.json()["detail"]
    assert "Phase Sequencing Violation" in detail
    assert "Pickup Attempt Failed" in detail

def test_driver_reschedule_failed_pickup_and_warehouse_blocking():
    """Verify that a driver can reschedule a failed pickup, warehouse intake remains blocked until collected."""
    wh_token = get_auth_token("warehouse", "Warehouse123!")
    driver_token = get_auth_token("driver_eco", "Pickup123!")

    # 1. Driver reschedules the failed pickup
    resched_payload = {
        "reschedule_date": "2026-11-05T11:00:00",
        "reschedule_notes": "Spoke with customer; agreed on re-attempt Thursday morning."
    }
    resched_res = client.post(
        "/api/returns/RET-FAIL-01/reschedule-pickup",
        headers={"Authorization": f"Bearer {driver_token}"},
        json=resched_payload
    )
    assert resched_res.status_code == 200
    assert resched_res.json()["pickup_status"] == "RESCHEDULED"
    assert "Rescheduled for 2026-11-05" in resched_res.json()["pickup_notes"]

    # 2. Warehouse intake MUST STILL be blocked while rescheduled
    wh_attempt = client.post(
        "/api/returns/RET-FAIL-01/receive",
        headers={"Authorization": f"Bearer {wh_token}"},
        json={"serial_received": "GF-TEST-01", "storage_location": "Dock-1", "package_condition": "Boxed"}
    )
    assert wh_attempt.status_code == 400
    detail = wh_attempt.json()["detail"]
    assert "Phase Sequencing Violation" in detail
    assert "Pickup Rescheduled" in detail

def test_successful_pickup_and_warehouse_intake_after_reschedule():
    """Verify that after rescheduling, once driver confirms collection, warehouse intake succeeds."""
    wh_token = get_auth_token("warehouse", "Warehouse123!")
    driver_token = get_auth_token("driver_eco", "Pickup123!")

    # 1. Driver arrives on rescheduled date and successfully collects
    collect_payload = {"picked_up_notes": "Customer handed over device in original packaging on re-attempt."}
    collect_res = client.post(
        "/api/returns/RET-FAIL-01/confirm-pickup",
        headers={"Authorization": f"Bearer {driver_token}"},
        json=collect_payload
    )
    assert collect_res.status_code == 200
    assert collect_res.json()["pickup_status"] == "IN_TRANSIT"

    # 2. Warehouse receipt can now be successfully confirmed
    receive_res = client.post(
        "/api/returns/RET-FAIL-01/receive",
        headers={"Authorization": f"Bearer {wh_token}"},
        json={"serial_received": "GF-TEST-01", "storage_location": "Bin W-202", "package_condition": "Intact box"}
    )
    assert receive_res.status_code == 200
    assert receive_res.json()["status"] == "RECEIVED"
    assert receive_res.json()["pickup_status"] == "DELIVERED_TO_WAREHOUSE"

def test_fail_pickup_with_immediate_reschedule_flag():
    """Verify fail-pickup endpoint accepts optional reschedule_date to immediately transition to RESCHEDULED."""
    admin_token = get_auth_token("admin", "Admin123!")
    driver_token = get_auth_token("driver_eco", "Pickup123!")

    reg_res = client.post(
        "/api/returns",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "return_id": "RET-FAIL-IMMEDIATE",
            "organization_id": 1,
            "product_name": "OnePlus Return",
            "sku": "OP-99",
            "pickup_partner_id": 1,
            "customer_pincode": "560002"
        }
    )
    assert reg_res.status_code == 201

    fail_payload = {
        "failure_reason": "Customer Refused Handover / Cancelled Return",
        "failure_notes": "Customer requested collection tomorrow instead.",
        "reschedule_date": "2026-11-06T15:00:00"
    }
    fail_res = client.post(
        "/api/returns/RET-FAIL-IMMEDIATE/fail-pickup",
        headers={"Authorization": f"Bearer {driver_token}"},
        json=fail_payload
    )
    assert fail_res.status_code == 200
    assert fail_res.json()["pickup_status"] == "RESCHEDULED"
    assert "Rescheduled for 2026-11-06 15:00" in fail_res.json()["pickup_notes"]

def test_cross_carrier_fail_and_reschedule_forbidden():
    """Verify carrier security: driver for Carrier A cannot fail or reschedule Carrier B shipments."""
    driver_eco = get_auth_token("driver_eco", "Pickup123!")

    # RET-1004 is assigned to GreenRoute (id: 2)
    bad_fail = client.post(
        "/api/returns/RET-1004/fail-pickup",
        headers={"Authorization": f"Bearer {driver_eco}"},
        json={"failure_reason": "Customer Unavailable"}
    )
    assert bad_fail.status_code == 403
    assert "Access denied" in bad_fail.json()["detail"]

    bad_resched = client.post(
        "/api/returns/RET-1004/reschedule-pickup",
        headers={"Authorization": f"Bearer {driver_eco}"},
        json={"reschedule_date": "2026-11-08T10:00:00"}
    )
    assert bad_resched.status_code == 403
    assert "Access denied" in bad_resched.json()["detail"]
