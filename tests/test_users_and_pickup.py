from fastapi.testclient import TestClient


def get_auth_token(client: TestClient, username: str, password: str) -> str:
    res = client.post("/api/auth/login", json={"username_or_email": username, "password": password})
    assert res.status_code == 200, f"Login failed for {username}: {res.text}"
    return res.json()["access_token"]


def test_admin_list_users(client: TestClient):
    token = get_auth_token(client, "admin", "Admin123!")
    res = client.get("/api/users", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    users = res.json()
    assert len(users) >= 5
    usernames = [u["username"] for u in users]
    assert "admin" in usernames
    assert "warehouse" in usernames
    assert "inspector" in usernames
    assert "retailer_tech" in usernames


def test_non_admin_cannot_list_or_manage_users(client: TestClient):
    token = get_auth_token(client, "warehouse", "Warehouse123!")

    # Attempt to list users
    res = client.get("/api/users", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 403

    # Attempt to create user
    res = client.post(
        "/api/users",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "username": "hacker_user",
            "email": "hacker@test.example",
            "password": "Password123!",
            "full_name": "Unauthorized Creator",
            "role": "ADMIN"
        }
    )
    assert res.status_code == 403


def test_admin_create_and_delete_user(client: TestClient):
    token = get_auth_token(client, "admin", "Admin123!")

    # Create new retailer user
    new_user_data = {
        "username": "new_retailer_bob",
        "email": "bob@techretail.example",
        "password": "SecurePassword123!",
        "full_name": "Bob Vance",
        "role": "RETAILER",
        "organization_id": 1
    }
    create_res = client.post("/api/users", headers={"Authorization": f"Bearer {token}"}, json=new_user_data)
    assert create_res.status_code == 201
    created_user = create_res.json()
    assert created_user["username"] == "new_retailer_bob"
    assert created_user["role"] == "RETAILER"
    assert created_user["organization_id"] == 1
    user_id = created_user["id"]

    # Verify newly created user can log in
    bob_token = get_auth_token(client, "new_retailer_bob", "SecurePassword123!")
    assert bob_token is not None

    # Attempt duplicate username creation -> 409 Conflict
    dup_res = client.post("/api/users", headers={"Authorization": f"Bearer {token}"}, json=new_user_data)
    assert dup_res.status_code == 409

    # Toggle active status
    toggle_res = client.patch(f"/api/users/{user_id}/toggle-active", headers={"Authorization": f"Bearer {token}"})
    assert toggle_res.status_code == 200
    assert toggle_res.json()["is_active"] is False

    # Deactivated user cannot log in (403 Forbidden)
    deact_login = client.post("/api/auth/login", json={"username_or_email": "new_retailer_bob", "password": "SecurePassword123!"})
    assert deact_login.status_code == 403

    # Reactivate
    client.patch(f"/api/users/{user_id}/toggle-active", headers={"Authorization": f"Bearer {token}"})

    # Delete the user
    del_res = client.delete(f"/api/users/{user_id}", headers={"Authorization": f"Bearer {token}"})
    assert del_res.status_code == 200

    # Verify user no longer exists
    get_res = client.get("/api/users", headers={"Authorization": f"Bearer {token}"})
    remaining_usernames = [u["username"] for u in get_res.json()]
    assert "new_retailer_bob" not in remaining_usernames


def test_admin_self_deletion_prevented(client: TestClient):
    token = get_auth_token(client, "admin", "Admin123!")

    # Get admin's own ID
    me_res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    admin_id = me_res.json()["id"]

    # Attempt to delete self
    del_res = client.delete(f"/api/users/{admin_id}", headers={"Authorization": f"Bearer {token}"})
    assert del_res.status_code == 400
    assert "cannot delete your own" in del_res.json()["detail"].lower()


def test_pickup_partner_lifecycle_and_assignment(client: TestClient):
    admin_token = get_auth_token(client, "admin", "Admin123!")
    wh_token = get_auth_token(client, "warehouse", "Warehouse123!")

    # 1. List existing seeded pickup partners
    list_res = client.get("/api/pickup-partners", headers={"Authorization": f"Bearer {wh_token}"})
    assert list_res.status_code == 200
    partners = list_res.json()
    assert len(partners) >= 2
    partner_names = [p["name"] for p in partners]
    assert "EcoLogix Express" in partner_names

    # 2. Admin registers a new pickup partner
    new_partner_payload = {
        "name": "VoltCity Courier",
        "contact_name": "Elena Rostova",
        "contact_email": "dispatch@voltcity.example",
        "contact_phone": "+1-800-VOLT-CITY",
        "service_regions": "Downtown Metro & Coastal Hubs",
        "fleet_type": "Electric Cargo Van (Zero-Emission)",
        "active": True
    }
    create_p_res = client.post("/api/pickup-partners", headers={"Authorization": f"Bearer {admin_token}"}, json=new_partner_payload)
    assert create_p_res.status_code == 201
    created_p = create_p_res.json()
    p_id = created_p["id"]
    assert created_p["name"] == "VoltCity Courier"

    # Duplicate creation rejected
    dup_p_res = client.post("/api/pickup-partners", headers={"Authorization": f"Bearer {admin_token}"}, json=new_partner_payload)
    assert dup_p_res.status_code == 409

    # Non-admin cannot delete partner
    unauth_del = client.delete(f"/api/pickup-partners/{p_id}", headers={"Authorization": f"Bearer {wh_token}"})
    assert unauth_del.status_code == 403

    # 3. Register a new return case without initial partner
    ret_res = client.post(
        "/api/returns",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "return_id": "RET-PICKUP-TEST-1",
            "order_ref": "ORD-PICKUP-99",
            "organization_id": 1,
            "product_category": "Smartphone",
            "product_name": "Pixel 8 Pro 256GB",
            "sku": "PXL-8P-BLU",
            "serial_expected": "SN-PXL8-00123",
            "customer_pincode": "94107",
            "return_reason": "Customer changed mind"
        }
    )
    assert ret_res.status_code == 201
    ret_data = ret_res.json()
    assert ret_data["pickup_status"] == "PENDING_ASSIGNMENT"

    # 4. Assign the new partner to this return
    assign_res = client.post(
        f"/api/returns/{ret_data['id']}/assign-pickup",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "pickup_partner_id": p_id,
            "notes": "Handle with care, express residential pickup"
        }
    )
    assert assign_res.status_code == 200
    assigned_ret = assign_res.json()
    assert assigned_ret["pickup_partner_id"] == p_id
    assert assigned_ret["pickup_partner_name"] == "VoltCity Courier"
    assert assigned_ret["pickup_status"] == "ASSIGNED"

    # 5. Confirm field pickup collection
    confirm_res = client.post(
        f"/api/returns/{ret_data['id']}/confirm-pickup",
        headers={"Authorization": f"Bearer {wh_token}"},
        json={"picked_up_notes": "Driver collected item in sealed tamper-evident bag."}
    )
    assert confirm_res.status_code == 200
    confirmed_ret = confirm_res.json()
    assert confirmed_ret["pickup_status"] == "IN_TRANSIT"

    # 6. Delete the test partner
    del_p_res = client.delete(f"/api/pickup-partners/{p_id}", headers={"Authorization": f"Bearer {admin_token}"})
    assert del_p_res.status_code == 200


def test_admin_delete_user_permanently_revokes_credentials_and_access(client: TestClient):
    admin_token = get_auth_token(client, "admin", "Admin123!")

    # 1. Create a user with credentials in the database
    user_payload = {
        "username": "user_for_perm_delete",
        "email": "perm_delete@logistics.example",
        "password": "Password123!",
        "full_name": "Temporary Operator",
        "role": "WAREHOUSE",
        "organization_id": 3
    }
    create_res = client.post("/api/users", headers={"Authorization": f"Bearer {admin_token}"}, json=user_payload)
    assert create_res.status_code == 201
    created_id = create_res.json()["id"]

    # 2. Verify login succeeds with newly added credentials
    login_res = client.post("/api/auth/login", json={"username_or_email": "user_for_perm_delete", "password": "Password123!"})
    assert login_res.status_code == 200
    assert "access_token" in login_res.json()

    # 3. Permanently remove the user from the database
    del_res = client.delete(f"/api/users/{created_id}", headers={"Authorization": f"Bearer {admin_token}"})
    assert del_res.status_code == 200
    assert "permanently removed from database" in del_res.json()["message"].lower()

    # 4. Verify login fails immediately (credentials & access wiped)
    failed_login = client.post("/api/auth/login", json={"username_or_email": "user_for_perm_delete", "password": "Password123!"})
    assert failed_login.status_code == 401

    # 5. Verify user record is completely gone from database
    users_list = client.get("/api/users", headers={"Authorization": f"Bearer {admin_token}"}).json()
    assert not any(u["id"] == created_id for u in users_list)
