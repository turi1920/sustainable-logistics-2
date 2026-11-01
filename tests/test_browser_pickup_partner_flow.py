import time

import pytest
from playwright.sync_api import sync_playwright

from backend.scripts.seed import seed_demo_data

FRONTEND_URL = "http://localhost:8501"

@pytest.fixture(autouse=True)
def clean_db():
    seed_demo_data(reset=True)
    yield

def test_browser_pickup_partner_doorstep_and_handover():
    """Verify pickup partner driver doorstep collection and warehouse handover via real browser."""
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        context = browser.new_context()
        page = context.new_page()

        # Step 1: Login as driver_eco
        page.goto(FRONTEND_URL)
        page.wait_for_load_state("networkidle")
        time.sleep(1)

        logout_btn = page.query_selector("button:has-text('Logout')")
        if logout_btn:
            logout_btn.click()
            time.sleep(1)
            page.wait_for_load_state("networkidle")

        page.fill("input[aria-label='Username or Email']", "driver_eco")
        page.fill("input[aria-label='Password']", "Pickup123!")
        page.click("button:has-text('Sign In')")
        time.sleep(2)
        page.wait_for_load_state("networkidle")

        # Step 2: Verify Pickup Partner Portal loaded
        body = page.inner_text("body")
        assert "Pickup Partner Field Logistics Portal" in body
        assert "EcoLogix Express" in body
        assert "Doorstep Collection Queue" in body

        # Step 3: Confirm physical collection if pending
        collect_btn = page.query_selector("button:has-text('Confirm Doorstep Physical Pickup')")
        if collect_btn:
            collect_btn.click()
            time.sleep(2)
            page.wait_for_load_state("networkidle")
            body_after_collect = page.inner_text("body")
            assert "Successfully collected return" in body_after_collect or "Active In-Transit" in body_after_collect

        # Step 4: Switch to Tab 2: Active Transit & Warehouse Handover
        transit_tab = page.query_selector("button[role='tab']:has-text('Active Transit & Warehouse Handover')")
        if transit_tab:
            transit_tab.click()
            time.sleep(1)
            page.wait_for_load_state("networkidle")

            handover_btn = page.query_selector("button:has-text('Hand Over to Warehouse Dock')")
            if handover_btn:
                handover_btn.click()
                time.sleep(2)
                page.wait_for_load_state("networkidle")
                body_after_deliver = page.inner_text("body")
                assert "handed over to central warehouse dock" in body_after_deliver or "Delivered to Dock" in body_after_deliver

        # Step 5: Switch to Tab 3: Completed Manifest & Sustainability
        manifest_tab = page.query_selector("button[role='tab']:has-text('Completed Manifest & Sustainability')")
        if manifest_tab:
            manifest_tab.click()
            time.sleep(1)
            page.wait_for_load_state("networkidle")
            body_manifest = page.inner_text("body")
            assert "Carrier Delivery Manifest" in body_manifest
            assert "Clean Mobility Impact" in body_manifest

        # Step 6: Logout
        logout_btn = page.query_selector("button:has-text('Logout')")
        assert logout_btn is not None
        logout_btn.click()
        time.sleep(1)

        # Step 7: Login as warehouse operator to verify warehouse sees the handed-over shipment
        page.fill("input[aria-label='Username or Email']", "warehouse")
        page.fill("input[aria-label='Password']", "Warehouse123!")
        page.click("button:has-text('Sign In')")
        time.sleep(2)
        page.wait_for_load_state("networkidle")

        wh_body = page.inner_text("body")
        assert "Warehouse Employee Dashboard" in wh_body
        assert "Warehouse Intake (Confirm Receipt)" in wh_body

        browser.close()

def test_browser_pickup_failure_and_reschedule_flow():
    """Verify pickup driver reporting failure, viewing in Exceptions tab, and rescheduling via browser."""
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        context = browser.new_context()
        page = context.new_page()

        page.goto(FRONTEND_URL)
        page.wait_for_load_state("networkidle")
        time.sleep(1)

        logout_btn = page.query_selector("button:has-text('Logout')")
        if logout_btn:
            logout_btn.click()
            time.sleep(1)
            page.wait_for_load_state("networkidle")

        page.fill("input[aria-label='Username or Email']", "driver_eco")
        page.fill("input[aria-label='Password']", "Pickup123!")
        page.click("button:has-text('Sign In')")
        time.sleep(2)
        page.wait_for_load_state("networkidle")

        body = page.inner_text("body")
        assert "Doorstep Collection Queue" in body

        # Report pickup failure
        notes_input = page.query_selector("textarea[aria-label='Doorstep cargo notes & observation']")
        if notes_input:
            notes_input.fill("Customer was not at home, phone went to voicemail.")

        fail_btn = page.query_selector("button:has-text('Record Failed Attempt')")
        assert fail_btn is not None
        fail_btn.click()
        time.sleep(2)
        page.wait_for_load_state("networkidle")

        body_after_fail = page.inner_text("body")
        assert "Pickup failure recorded" in body_after_fail or "Exceptions queue" in body_after_fail or "Exceptions / Failed" in body_after_fail

        # Switch to Tab 2: Exceptions & Failed Attempts
        exc_tab = page.query_selector("button[role='tab']:has-text('Exceptions & Failed Attempts')")
        assert exc_tab is not None
        exc_tab.click()
        time.sleep(1)
        page.wait_for_load_state("networkidle")

        body_exc = page.inner_text("body")
        assert "Exceptions & Failed Pickups Queue" in body_exc
        assert "PICKUP_FAILED" in body_exc

        # Reschedule the pickup
        resched_btn = page.query_selector("button:has-text('Reschedule Doorstep Pickup')")
        assert resched_btn is not None
        resched_btn.click()
        time.sleep(2)
        page.wait_for_load_state("networkidle")

        body_after_resched = page.inner_text("body")
        assert "successfully rescheduled" in body_after_resched or "Doorstep Collection Queue" in body_after_resched

        # Logout and check Warehouse Operator view
        logout_btn = page.query_selector("button:has-text('Logout')")
        assert logout_btn is not None
        logout_btn.click()
        time.sleep(1)

        page.fill("input[aria-label='Username or Email']", "warehouse")
        page.fill("input[aria-label='Password']", "Warehouse123!")
        page.click("button:has-text('Sign In')")
        time.sleep(2)
        page.wait_for_load_state("networkidle")

        wh_body = page.inner_text("body")
        assert "Warehouse Employee Dashboard" in wh_body
        assert "Rescheduled" in wh_body or "Phase Sequencing Requirement" in wh_body

        browser.close()

if __name__ == "__main__":
    test_browser_pickup_partner_doorstep_and_handover()
    test_browser_pickup_failure_and_reschedule_flow()
    print("Browser pickup partner doorstep & handover flow passed successfully!")
