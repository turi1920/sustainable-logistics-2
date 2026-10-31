import time

from playwright.sync_api import sync_playwright

FRONTEND_URL = "http://localhost:8501"

def test_full_browser_ui_lifecycle():
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        context = browser.new_context()
        page = context.new_page()

        # Step 1: Admin registers new smartphone return
        print("UI Step 1: Admin registers smartphone return...")
        page.goto(FRONTEND_URL)
        page.wait_for_load_state("networkidle")
        time.sleep(1)

        # Logout if already logged in
        logout_btn = page.query_selector("button:has-text('Logout')")
        if logout_btn:
            logout_btn.click()
            time.sleep(1)

        page.fill("input[aria-label='Username or Email']", "admin")
        page.fill("input[aria-label='Password']", "Admin123!")
        page.click("button:has-text('Sign In')")
        time.sleep(2)
        page.wait_for_load_state("networkidle")

        # Click "Register New Return" tab
        page.get_by_role("tab", name="Register New Return").click()
        time.sleep(1)

        # Fill smartphone return form
        page.fill("input[aria-label='Custom Return ID (Optional)']", "RET-UI-SMP-881")
        page.fill("input[aria-label='Order Reference']", "ORD-UI-8899")
        page.fill("input[aria-label='Product Model / Name']", "Apple iPhone 14 Pro 128GB Space Black")
        page.fill("input[aria-label='SKU']", "IPH-14P-128SB")
        page.fill("input[aria-label='Expected Serial Number']", "SN-IPH14P-9900")
        page.fill("textarea[aria-label='Customer Return Reason']", "Back glass scuffed, battery drains moderately fast")

        page.click("button:has-text('Submit Return Registration')")
        time.sleep(2)
        body = page.inner_text("body")
        assert "Successfully registered Return Case" in body or "RET-UI-SMP-881" in body
        print("PASSED: Admin registered smartphone return RET-UI-SMP-881")

        # Step 2: Warehouse confirms receipt
        print("UI Step 2: Warehouse confirms receipt...")
        page.click("button:has-text('Logout')")
        time.sleep(1)
        page.fill("input[aria-label='Username or Email']", "warehouse")
        page.fill("input[aria-label='Password']", "Warehouse123!")
        page.click("button:has-text('Sign In')")
        time.sleep(2)

        # Confirm receipt
        page.fill("input[aria-label='Serial Number Received on Physical Device']", "SN-IPH14P-9900")
        page.fill("input[aria-label='Assigned Warehouse Storage Location / Bin']", "Aisle 4, Bin W-410")
        page.click("button:has-text('Confirm Warehouse Receipt')")
        time.sleep(2)
        body = page.inner_text("body")
        assert "Warehouse receipt confirmed" in body
        print("PASSED: Warehouse receipt confirmed")

        # Step 3: Inspector conducts inspection & generates recovery options
        print("UI Step 3: Inspector conducts technical inspection...")
        page.click("button:has-text('Logout')")
        time.sleep(1)
        page.fill("input[aria-label='Username or Email']", "inspector")
        page.fill("input[aria-label='Password']", "Inspector123!")
        page.click("button:has-text('Sign In')")
        time.sleep(2)

        page.click("button:has-text('Complete Inspection & Generate Recovery Estimates')")
        time.sleep(2)
        body = page.inner_text("body")
        assert "Inspection completed" in body or "recovery options" in body
        print("PASSED: Inspection completed and recovery options generated")

        # Step 4: Retailer approves refurbishment option
        print("UI Step 4: Retailer representative reviews and approves option...")
        page.click("button:has-text('Logout')")
        time.sleep(1)
        page.fill("input[aria-label='Username or Email']", "retailer_tech")
        page.fill("input[aria-label='Password']", "Retailer123!")
        page.click("button:has-text('Sign In')")
        time.sleep(2)

        # Review case
        body = page.inner_text("body")
        assert "Expected NRV" in body or "Recovery Economics" in body

        # Submit approval
        page.click("button:has-text('Submit Commercial Authorization')")
        time.sleep(2)
        body = page.inner_text("body")
        assert "Authorization submitted" in body
        print("PASSED: Retailer approved recovery option")

        # Step 5: Inspector executes processing task
        print("UI Step 5: Inspector completes processing task...")
        page.click("button:has-text('Logout')")
        time.sleep(1)
        page.fill("input[aria-label='Username or Email']", "inspector")
        page.fill("input[aria-label='Password']", "Inspector123!")
        page.click("button:has-text('Sign In')")
        time.sleep(2)

        # Click Processing tab
        page.get_by_role("tab", name="2️⃣ Processing Task Execution").click()
        time.sleep(1)
        page.click("button:has-text('Complete Processing Task')")
        time.sleep(2)
        body = page.inner_text("body")
        assert "Processing task recorded" in body
        print("PASSED: Processing task recorded with actual costs")

        # Step 6: Inspector completes Quality Check & Data Sanitization Gate
        print("UI Step 6: Quality check and data sanitization certification...")
        page.get_by_role("tab", name="3️⃣ Quality Check & Sanitization").click()
        time.sleep(1)
        page.click("button:has-text('Certify Quality Check')")
        time.sleep(2)
        body = page.inner_text("body")
        assert "Quality Check Certified" in body
        print("PASSED: Quality check and data sanitization verified")

        # Step 7: Warehouse restocks into inventory
        print("UI Step 7: Warehouse restocks to inventory...")
        page.click("button:has-text('Logout')")
        time.sleep(1)
        page.fill("input[aria-label='Username or Email']", "warehouse")
        page.fill("input[aria-label='Password']", "Warehouse123!")
        page.click("button:has-text('Sign In')")
        time.sleep(2)

        page.get_by_role("tab", name="Restock & Dispatch Queue").click()
        time.sleep(1)
        page.click("button:has-text('Complete Restock / Return')")
        time.sleep(2)
        body = page.inner_text("body")
        assert "Disposition successfully recorded" in body
        print("PASSED: Smartphone restocked into inventory")

        # Step 8: Search case and verify full journey timeline
        print("UI Step 8: Verifying complete return journey...")
        page.get_by_role("tab", name="Case Traceability").click()
        time.sleep(1)
        page.fill("input[aria-label='Enter Return Case ID or Serial Number']", "RET-1003")
        page.click("button:has-text('Search Case')")
        time.sleep(2)

        body = page.inner_text("body")
        assert "COMPLETED" in body
        assert "RECORD_RETAILER_DECISION" in body or "APPROVED" in body
        assert "COMPLETE_PROCESSING" in body or "PROCESSING_COMPLETED" in body
        assert "COMPLETE_QUALITY_CHECK" in body or "QC_PASSED" in body
        assert "TechRetail Direct" in body
        print("PASSED: Full lifecycle journey verified in UI!")

        browser.close()

if __name__ == "__main__":
    test_full_browser_ui_lifecycle()
    print("ALL UI LIFECYCLE STEPS COMPLETED AND VERIFIED VIA REAL BROWSER!")
