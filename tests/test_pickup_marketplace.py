import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.scripts.seed import seed_demo_data

client = TestClient(app)

@pytest.fixture(scope="module", autouse=True)
def setup_database():
    seed_demo_data(reset=True)
    yield


def get_token(username: str, password: str = "Pickup123!") -> str:
    res = client.post(
        "/api/auth/login",
        json={"username_or_email": username, "password": password}
    )
    assert res.status_code == 200, f"Failed login for {username}: {res.text}"
    return res.json()["access_token"]


def create_marketplace_return(admin_token: str, return_id: str, pincode: str = "94103") -> str:
    """Helper to create an unassigned return available for marketplace."""
    res = client.post(
        "/api/returns",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "return_id": return_id,
            "order_ref": f"ORD-MKT-{return_id}",
            "organization_id": 1,
            "product_category": "Smartphone",
            "product_name": "OnePlus 11 5G 256GB",
            "sku": "1PLUS-11-256",
            "serial_expected": f"SN-OP-{return_id}",
            "customer_pincode": pincode,
            "return_reason": "Customer changed mind, unopened box",
            "pickup_partner_id": None  # Unassigned, open to all
        }
    )
    assert res.status_code == 201, f"Failed creating return: {res.text}"
    return res.json()["id"]


def test_public_marketplace_feed_visibility():
    """Verify that any pickup driver across carriers can see unassigned marketplace tasks."""
    admin_token = get_token("admin", "Admin123!")
    eco_token = get_token("driver_eco")
    green_token = get_token("driver_green")

    ret_id = create_marketplace_return(admin_token, "RET-MKT-FEED-01")

    # Driver Eco (EcoLogix) views marketplace
    res_eco = client.get("/api/returns/marketplace", headers={"Authorization": f"Bearer {eco_token}"})
    assert res_eco.status_code == 200
    eco_ids = [r["id"] for r in res_eco.json()]
    assert ret_id in eco_ids

    # Driver Green (GreenRoute) views marketplace
    res_green = client.get("/api/returns/marketplace", headers={"Authorization": f"Bearer {green_token}"})
    assert res_green.status_code == 200
    green_ids = [r["id"] for r in res_green.json()]
    assert ret_id in green_ids


def test_atomic_accept_and_concurrency_lockout():
    """Verify that when Driver A accepts a task, Driver B is locked out with 409 Conflict."""
    admin_token = get_token("admin", "Admin123!")
    eco_token = get_token("driver_eco")
    green_token = get_token("driver_green")

    ret_id = create_marketplace_return(admin_token, "RET-MKT-CONCURRENCY-01")

    # Driver Eco accepts first
    res_accept = client.post(f"/api/returns/{ret_id}/accept", headers={"Authorization": f"Bearer {eco_token}"})
    assert res_accept.status_code == 200
    data = res_accept.json()
    assert data["assigned_driver_username"] == "driver_eco"
    assert data["pickup_partner_name"] == "EcoLogix Express"

    # Driver Green attempts to accept the exact same task -> must fail with HTTP 409
    res_conflict = client.post(f"/api/returns/{ret_id}/accept", headers={"Authorization": f"Bearer {green_token}"})
    assert res_conflict.status_code == 409
    assert "already been accepted by another driver" in res_conflict.json()["detail"]

    # Verify task is no longer in marketplace for ANY driver
    res_mkt_eco = client.get("/api/returns/marketplace", headers={"Authorization": f"Bearer {eco_token}"})
    assert ret_id not in [r["id"] for r in res_mkt_eco.json()]

    res_mkt_green = client.get("/api/returns/marketplace", headers={"Authorization": f"Bearer {green_token}"})
    assert ret_id not in [r["id"] for r in res_mkt_green.json()]


def test_driver_reject_hides_for_caller_only():
    """Verify that rejecting a task hides it for the rejecting driver while leaving it available for others."""
    admin_token = get_token("admin", "Admin123!")
    eco_token = get_token("driver_eco")
    green_token = get_token("driver_green")

    ret_id = create_marketplace_return(admin_token, "RET-MKT-REJECT-01")

    # Driver Eco rejects task
    res_rej = client.post(
        f"/api/returns/{ret_id}/reject",
        headers={"Authorization": f"Bearer {eco_token}"},
        json={"reason": "Outside my daily delivery sector"}
    )
    assert res_rej.status_code == 200
    assert res_rej.json()["action"] == "REJECTED"

    # Task must NOT appear in Driver Eco's marketplace
    res_eco_feed = client.get("/api/returns/marketplace", headers={"Authorization": f"Bearer {eco_token}"})
    assert ret_id not in [r["id"] for r in res_eco_feed.json()]

    # Task MUST still appear in Driver Green's marketplace
    res_green_feed = client.get("/api/returns/marketplace", headers={"Authorization": f"Bearer {green_token}"})
    assert ret_id in [r["id"] for r in res_green_feed.json()]

    # Driver Green accepts it successfully
    res_accept = client.post(f"/api/returns/{ret_id}/accept", headers={"Authorization": f"Bearer {green_token}"})
    assert res_accept.status_code == 200
    assert res_accept.json()["assigned_driver_username"] == "driver_green"


def test_driver_release_task_back_to_marketplace_with_self_exclusion():
    """Verify that releasing a task puts it back in the marketplace for others, but excludes releasing driver."""
    admin_token = get_token("admin", "Admin123!")
    eco_token = get_token("driver_eco")
    green_token = get_token("driver_green")

    ret_id = create_marketplace_return(admin_token, "RET-MKT-RELEASE-01")

    # Driver Eco accepts the task
    res_acc = client.post(f"/api/returns/{ret_id}/accept", headers={"Authorization": f"Bearer {eco_token}"})
    assert res_acc.status_code == 200

    # Unauthorized driver cannot release another driver's task (403)
    res_unauth_rel = client.post(
        f"/api/returns/{ret_id}/release",
        headers={"Authorization": f"Bearer {green_token}"},
        json={"reason": "I want to release it"}
    )
    assert res_unauth_rel.status_code == 403

    # Driver Eco releases the task
    res_rel = client.post(
        f"/api/returns/{ret_id}/release",
        headers={"Authorization": f"Bearer {eco_token}"},
        json={"reason": "Shift ended, unable to finish route"}
    )
    assert res_rel.status_code == 200
    assert res_rel.json()["action"] == "RELEASED"

    # Task must NOT appear back in Driver Eco's marketplace
    res_eco_feed = client.get("/api/returns/marketplace", headers={"Authorization": f"Bearer {eco_token}"})
    assert ret_id not in [r["id"] for r in res_eco_feed.json()]

    # Task MUST appear in Driver Green's marketplace
    res_green_feed = client.get("/api/returns/marketplace", headers={"Authorization": f"Bearer {green_token}"})
    assert ret_id in [r["id"] for r in res_green_feed.json()]

    # Driver Green can now claim and accept the released task
    res_green_accept = client.post(f"/api/returns/{ret_id}/accept", headers={"Authorization": f"Bearer {green_token}"})
    assert res_green_accept.status_code == 200
    assert res_green_accept.json()["assigned_driver_username"] == "driver_green"


def test_cannot_release_in_transit_task():
    """Verify that once doorstep pickup is confirmed (IN_TRANSIT), task cannot be released."""
    admin_token = get_token("admin", "Admin123!")
    eco_token = get_token("driver_eco")

    ret_id = create_marketplace_return(admin_token, "RET-MKT-INTRANSIT-01")

    # Driver Eco accepts
    client.post(f"/api/returns/{ret_id}/accept", headers={"Authorization": f"Bearer {eco_token}"})

    # Driver Eco confirms doorstep pickup -> transitions to IN_TRANSIT
    res_collect = client.post(
        f"/api/returns/{ret_id}/confirm-pickup",
        headers={"Authorization": f"Bearer {eco_token}"},
        json={"picked_up_notes": "Collected at doorstep"}
    )
    assert res_collect.status_code == 200
    assert res_collect.json()["pickup_status"] == "IN_TRANSIT"

    # Driver Eco attempts to release task -> 400 Bad Request
    res_fail_rel = client.post(
        f"/api/returns/{ret_id}/release",
        headers={"Authorization": f"Bearer {eco_token}"},
        json={"reason": "Cannot complete"}
    )
    assert res_fail_rel.status_code == 400
    assert "already been collected" in res_fail_rel.json()["detail"]


def test_carrier_driver_can_release_carrier_assigned_task():
    """Verify that a driver can release a task assigned to their carrier even if assigned_driver_id was None."""
    admin_token = get_token("admin", "Admin123!")
    eco_token = get_token("driver_eco")
    green_token = get_token("driver_green")

    # Create return assigned to EcoLogix carrier (id: 1) without specific driver
    res_create = client.post(
        "/api/returns",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "return_id": "RET-MKT-CARRIER-01",
            "order_ref": "ORD-MKT-C01",
            "organization_id": 1,
            "product_category": "Smartphone",
            "product_name": "Google Pixel 8 Pro",
            "sku": "PXL-8P-128",
            "serial_expected": "SN-PXL8P-001",
            "customer_pincode": "94103",
            "return_reason": "Screen defect",
            "pickup_partner_id": 1,  # EcoLogix
        }
    )
    assert res_create.status_code == 201

    # Driver Eco (EcoLogix) can release it back to the marketplace pool
    res_rel = client.post(
        "/api/returns/RET-MKT-CARRIER-01/release",
        headers={"Authorization": f"Bearer {eco_token}"},
        json={"reason": "Dont have time"}
    )
    assert res_rel.status_code == 200
    assert res_rel.json()["action"] == "RELEASED"

    # Must disappear from Driver Eco's returns and marketplace
    res_eco_returns = client.get("/api/returns", headers={"Authorization": f"Bearer {eco_token}"})
    assert "RET-MKT-CARRIER-01" not in [r["id"] for r in res_eco_returns.json()]

    res_eco_mkt = client.get("/api/returns/marketplace", headers={"Authorization": f"Bearer {eco_token}"})
    assert "RET-MKT-CARRIER-01" not in [r["id"] for r in res_eco_mkt.json()]

    # Must appear in Driver Green's marketplace
    res_green_mkt = client.get("/api/returns/marketplace", headers={"Authorization": f"Bearer {green_token}"})
    assert "RET-MKT-CARRIER-01" in [r["id"] for r in res_green_mkt.json()]

    # Driver Green accepts it
    res_acc = client.post("/api/returns/RET-MKT-CARRIER-01/accept", headers={"Authorization": f"Bearer {green_token}"})
    assert res_acc.status_code == 200
    assert res_acc.json()["assigned_driver_username"] == "driver_green"

