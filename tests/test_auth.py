
DEMO_ACCOUNTS = [
    ("admin", "Admin123!", "ADMIN", 3),
    ("warehouse", "Warehouse123!", "WAREHOUSE", 3),
    ("inspector", "Inspector123!", "INSPECTOR", 3),
    ("retailer_tech", "Retailer123!", "RETAILER", 1),
    ("retailer_apex", "Retailer123!", "RETAILER", 2),
]

DEMO_EMAILS = [
    ("admin@logistics.example", "Admin123!", "ADMIN"),
    ("warehouse@logistics.example", "Warehouse123!", "WAREHOUSE"),
    ("inspector@logistics.example", "Inspector123!", "INSPECTOR"),
    ("retailer1@techretail.example", "Retailer123!", "RETAILER"),
    ("retailer2@apexmobile.example", "Retailer123!", "RETAILER"),
]

def test_login_every_documented_account(client):
    """Verify that every documented demo account can log in via username."""
    for username, password, expected_role, org_id in DEMO_ACCOUNTS:
        resp = client.post(
            "/api/auth/login",
            json={"username_or_email": username, "password": password}
        )
        assert resp.status_code == 200, f"Login failed for {username}: {resp.text}"
        data = resp.json()
        assert data["access_token"]
        assert data["token_type"] == "bearer"
        assert data["role"] == expected_role
        assert data["username"] == username
        if org_id:
            assert data["organization_id"] == org_id

def test_login_via_email(client):
    """Verify login works with email as well as username."""
    for email, password, expected_role in DEMO_EMAILS:
        resp = client.post(
            "/api/auth/login",
            json={"username_or_email": email, "password": password}
        )
        assert resp.status_code == 200, f"Login via email failed for {email}: {resp.text}"
        data = resp.json()
        assert data["role"] == expected_role

def test_login_invalid_password(client):
    """Verify rejection of invalid credentials."""
    resp = client.post(
        "/api/auth/login",
        json={"username_or_email": "admin", "password": "WrongPassword123!"}
    )
    assert resp.status_code == 401
    assert "Incorrect" in resp.json()["detail"]

def test_login_nonexistent_user(client):
    resp = client.post(
        "/api/auth/login",
        json={"username_or_email": "nonexistent_user", "password": "Password123!"}
    )
    assert resp.status_code == 401

def test_get_current_user_profile(client):
    # Login as admin
    resp = client.post("/api/auth/login", json={"username_or_email": "admin", "password": "Admin123!"})
    token = resp.json()["access_token"]

    me_resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 200
    me = me_resp.json()
    assert me["username"] == "admin"
    assert me["role"] == "ADMIN"
    assert me["is_active"] is True
