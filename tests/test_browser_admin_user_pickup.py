import time

import pytest
from playwright.sync_api import sync_playwright

from backend.scripts.seed import seed_demo_data

BASE_URL = "http://localhost:8501"

@pytest.fixture(autouse=True)
def clean_db():
    seed_demo_data(reset=True)
    yield
    seed_demo_data(reset=True)

def test_browser_admin_user_and_pickup_management():
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        context = browser.new_context()
        page = context.new_page()
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        time.sleep(1)

        # Logout if logged in
        logout_btn = page.query_selector("button:has-text('Logout')")
        if logout_btn:
            logout_btn.click()
            time.sleep(1)
            page.wait_for_load_state("networkidle")

        # 1. Login as Admin
        page.fill("input[aria-label='Username or Email']", "admin")
        page.fill("input[aria-label='Password']", "Admin123!")
        page.click("button:has-text('Sign In')")
        time.sleep(2)
        page.wait_for_load_state("networkidle")

        body_text = page.inner_text("body")
        assert "Platform Admin Dashboard" in body_text

        # 2. Test User Management Tab
        user_mgmt_tab = page.get_by_role("tab", name="👥 User Management")
        user_mgmt_tab.click()
        time.sleep(1)

        body_text = page.inner_text("body")
        assert "Registered System Users" in body_text
        assert "Add New User" in body_text

        # Fill Add New User form
        page.fill("input[aria-label='Username']", "ui_test_bob")
        page.fill("input[aria-label='Email Address']", "bob_ui@techretail.example")
        page.fill("input[aria-label='Password']", "TestPass123!")
        page.fill("input[aria-label='Full Name']", "Bob UI Tester")

        page.click("button:has-text('Create User Account')")
        time.sleep(2)
        page.wait_for_load_state("networkidle")

        body_text = page.inner_text("body")
        assert "created successfully" in body_text or "ui_test_bob" in body_text

        # Delete user via remove section (newly created user ui_test_bob is pre-selected)
        page.locator("label:has-text('Confirm permanent deletion')").click()
        page.click("button:has-text('Delete User & Revoke Access')")
        time.sleep(2)
        page.wait_for_load_state("networkidle")

        body_text = page.inner_text("body")
        assert "deleted successfully" in body_text or "removed" in body_text

        # 3. Test Pickup Personnel & Dispatch Tab
        pickup_tab = page.get_by_role("tab", name="🚚 Pickup Partners & Dispatch")
        pickup_tab.click()
        time.sleep(1)

        body_text = page.inner_text("body")
        assert "Registered Pickup Personnel & Field Drivers" in body_text
        assert "Add Pickup Driver / Personnel" in body_text

        # Register a new pickup driver
        page.fill("input[aria-label='Driver Username']", "driver_aerovolt")
        page.fill("input[aria-label='Driver Full Name']", "David Tennant (AeroVolt Driver)")
        page.fill("input[aria-label='Driver Email Address']", "david@aerovolt.example")

        page.click("button:has-text('Create Driver Account')")
        time.sleep(2)
        page.wait_for_load_state("networkidle")

        body_text = page.inner_text("body")
        assert "added successfully" in body_text or "driver_aerovolt" in body_text

        # Dispatch return case to driver
        assert "Dispatch / Assign Return Case to Driver" in body_text
        page.click("button:has-text('Assign Driver & Dispatch')")
        time.sleep(2)
        page.wait_for_load_state("networkidle")

        body_text = page.inner_text("body")
        assert "dispatched to" in body_text or "RET-1001" in body_text

        # Delete the test driver (newly registered driver_aerovolt is pre-selected)
        page.locator("label:has-text('Confirm permanent removal of this driver account')").click()
        page.click("button:has-text('Delete Driver from Platform')")
        time.sleep(2)
        page.wait_for_load_state("networkidle")

        body_text = page.inner_text("body")
        assert "removed from database" in body_text or "permanently removed" in body_text or "successfully" in body_text

        browser.close()
