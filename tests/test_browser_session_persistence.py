import time

from playwright.sync_api import sync_playwright

FRONTEND_URL = "http://localhost:8501"


def test_browser_session_persistence_on_reload():
    """Verify that after login, refreshing or reloading the browser page maintains authentication state."""
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        context = browser.new_context()
        page = context.new_page()

        # Step 1: Navigate to fresh login page
        page.goto(FRONTEND_URL)
        page.wait_for_load_state("networkidle")
        time.sleep(1)

        # Ensure logout if already logged in
        logout_btn = page.query_selector("button:has-text('Logout')")
        if logout_btn:
            logout_btn.click()
            time.sleep(1)
            page.wait_for_load_state("networkidle")

        # Step 2: Fill credentials and Sign In
        page.fill("input[aria-label='Username or Email']", "admin")
        page.fill("input[aria-label='Password']", "Admin123!")
        page.click("button:has-text('Sign In')")

        # Wait for dashboard to render
        time.sleep(2)
        page.wait_for_load_state("networkidle")

        assert "Platform Admin Dashboard" in page.inner_text("body"), "Admin dashboard should load after login"
        assert "Sign In" not in page.inner_text("body"), "Login form should disappear after login"

        # Step 3: RELOAD / REFRESH THE PAGE (simulate user pressing F5 or browser reload)
        page.reload()
        page.wait_for_load_state("networkidle")
        time.sleep(2)

        # Step 4: Verify authentication is preserved across reload
        body_text_after_reload = page.inner_text("body")
        assert "Platform Admin Dashboard" in body_text_after_reload, (
            "User should remain logged in and see Platform Admin Dashboard after page reload"
        )
        assert "Sign In" not in body_text_after_reload, (
            "Sign In form should NOT reappear on page reload when session is active"
        )

        # Step 5: Test driver account reload
        logout_btn = page.query_selector("button:has-text('Logout')")
        assert logout_btn is not None, "Logout button must be present"
        logout_btn.click()
        time.sleep(1)
        page.wait_for_load_state("networkidle")

        # Login as driver_eco
        page.fill("input[aria-label='Username or Email']", "driver_eco")
        page.fill("input[aria-label='Password']", "Pickup123!")
        page.click("button:has-text('Sign In')")
        time.sleep(2)
        page.wait_for_load_state("networkidle")

        assert "Pickup Partner Field Logistics Portal" in page.inner_text("body")

        # Reload as driver
        page.reload()
        page.wait_for_load_state("networkidle")
        time.sleep(2)

        assert "Pickup Partner Field Logistics Portal" in page.inner_text("body"), (
            "Driver should remain logged in after reload"
        )

        # Logout cleanly
        logout_btn = page.query_selector("button:has-text('Logout')")
        if logout_btn:
            logout_btn.click()
            time.sleep(1)
            page.wait_for_load_state("networkidle")

        browser.close()


def test_browser_tab_persistence_on_reload():
    """Verify that clicking a sub-tab (e.g. User Management) persists across page reloads instead of resetting to Overview."""
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        context = browser.new_context()
        page = context.new_page()

        page.goto(FRONTEND_URL)
        page.wait_for_load_state("networkidle")
        time.sleep(1)

        # Login as admin if not logged in
        logout_btn = page.query_selector("button:has-text('Logout')")
        if not logout_btn:
            page.fill("input[aria-label='Username or Email']", "admin")
            page.fill("input[aria-label='Password']", "Admin123!")
            page.click("button:has-text('Sign In')")
            time.sleep(2)
            page.wait_for_load_state("networkidle")

        # Click on User Management tab
        page.click("button[role='tab']:has-text('User Management')")
        time.sleep(1)

        # Confirm User Management elements are visible
        body_before_reload = page.inner_text("body")
        assert "Add New User" in body_before_reload
        assert "Remove User from Database" in body_before_reload

        # Reload the page (simulate user pressing F5 or refresh)
        page.reload()
        page.wait_for_load_state("networkidle")
        time.sleep(2)

        # Confirm that after reload, user is STILL on User Management, not Overview!
        body_after_reload = page.inner_text("body")
        assert "Add New User" in body_after_reload, (
            "User Management tab should remain active after page reload"
        )
        assert "Remove User from Database" in body_after_reload, (
            "User Management controls must remain visible after page reload"
        )

        active_tab = page.query_selector("button[role='tab'][aria-selected='true']")
        assert active_tab is not None
        assert "User Management" in active_tab.inner_text(), (
            f"Expected User Management tab to be active, got {active_tab.inner_text()}"
        )

        browser.close()
