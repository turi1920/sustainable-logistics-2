import time

from playwright.sync_api import sync_playwright

FRONTEND_URL = "http://localhost:8501"

ACCOUNTS = [
    ("admin", "Admin123!", "Platform Admin Dashboard"),
    ("warehouse", "Warehouse123!", "Warehouse Employee Dashboard"),
    ("inspector", "Inspector123!", "Electronics Inspection & Quality Dashboard"),
    ("retailer_tech", "Retailer123!", "Retailer Representative Portal"),
    ("retailer_apex", "Retailer123!", "Retailer Representative Portal"),
    ("driver_eco", "Pickup123!", "Pickup Partner Field Logistics Portal"),
    ("driver_green", "Pickup123!", "Pickup Partner Field Logistics Portal"),
]

def test_browser_login_all_accounts():
    """Verify that every documented demo account can log in through the real UI in Edge."""
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        context = browser.new_context()
        page = context.new_page()

        for username, password, expected_dashboard in ACCOUNTS:
            page.goto(FRONTEND_URL)
            page.wait_for_load_state("networkidle")
            time.sleep(1)

            # If logged in from previous test, log out
            logout_btn = page.query_selector("button:has-text('Logout')")
            if logout_btn:
                logout_btn.click()
                time.sleep(1)
                page.wait_for_load_state("networkidle")

            # Fill username and password
            page.fill("input[aria-label='Username or Email']", username)
            page.fill("input[aria-label='Password']", password)
            page.click("button:has-text('Sign In')")

            # Wait for dashboard to load
            time.sleep(2)
            page.wait_for_load_state("networkidle")

            # Check that expected dashboard is present
            body_text = page.inner_text("body")
            assert expected_dashboard in body_text, f"Failed: '{expected_dashboard}' not found for user '{username}'"

            # Check logout button exists
            logout_btn = page.query_selector("button:has-text('Logout')")
            assert logout_btn is not None, f"Logout button not found for '{username}'"
            logout_btn.click()
            time.sleep(1)

        browser.close()

if __name__ == "__main__":
    test_browser_login_all_accounts()
    print("All browser login checks passed successfully!")
