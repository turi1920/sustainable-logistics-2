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


def test_browser_sustainability_tab_admin_and_retailer():
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

        # 2. Click Sustainability Impact Tab
        sust_tab = page.get_by_role("tab", name="🌱 Sustainability Impact")
        assert sust_tab.is_visible()
        sust_tab.click()
        time.sleep(2)
        page.wait_for_load_state("networkidle")

        body = page.inner_text("body")
        assert "Sustainability & Circular Economy Impact" in body
        assert "Headline Environmental Savings" in body
        assert "Net Avoided Carbon Emissions" in body
        assert "E-Waste Diverted from Landfills" in body
        assert "Critical Minerals Conserved" in body
        assert "Circular Recovery Distribution" in body
        assert "Positive Steps Towards Sustainability" in body
        assert "Returns Circularity & Environmental Ledger" in body
        assert "ISO 14040/44 LCA Certified" in body
        print("PASSED: Admin Sustainability Impact tab verified!")

        # 3. Log out and log in as Retailer
        page.click("button:has-text('Logout')")
        time.sleep(1)
        page.wait_for_load_state("networkidle")

        page.fill("input[aria-label='Username or Email']", "retailer_tech")
        page.fill("input[aria-label='Password']", "Retailer123!")
        page.click("button:has-text('Sign In')")
        time.sleep(2)
        page.wait_for_load_state("networkidle")

        body = page.inner_text("body")
        assert "Retailer Representative Portal" in body

        # Click Retailer Sustainability Impact Tab
        retailer_sust_tab = page.get_by_role("tab", name="🌱 Sustainability Impact")
        assert retailer_sust_tab.is_visible()
        retailer_sust_tab.click()
        time.sleep(2)
        page.wait_for_load_state("networkidle")

        body = page.inner_text("body")
        assert "Sustainability & Circular Economy Impact" in body
        assert "Net Avoided Carbon Emissions" in body
        assert "Positive Steps Towards Sustainability" in body
        print("PASSED: Retailer Sustainability Impact tab verified!")

        browser.close()


if __name__ == "__main__":
    test_browser_sustainability_tab_admin_and_retailer()
    print("ALL SUSTAINABILITY BROWSER CHECKS PASSED!")
