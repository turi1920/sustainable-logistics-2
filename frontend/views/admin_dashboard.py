import pandas as pd
import streamlit as st

from frontend.api_client import api_client
from frontend.views.return_journey import render_return_journey


def render_admin_dashboard(token: str, user: dict):
    st.title("🛡️ Platform Admin Dashboard")
    st.caption(f"Logged in as **{user['full_name']}** (`{user['username']}`) | Role: **{user['role']}**")

    tabs = st.tabs(["📊 Overview & Returns", "➕ Register New Return", "🔍 Traceability & Audit"])

    with tabs[0]:
        st.subheader("All Returns & System Health")
        try:
            returns = api_client.list_returns(token)
            orgs = api_client.list_organizations(token)
        except Exception as e:
            st.error(f"Failed to load returns: {e}")
            return

        # Metrics
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("Total Returns", len(returns))
        with c2:
            awaiting = sum(1 for r in returns if r["status"] == "AWAITING_APPROVAL")
            st.metric("Awaiting Retailer Decision", awaiting)
        with c3:
            in_prog = sum(1 for r in returns if r["status"] in ["RECEIVED", "APPROVED", "PROCESSING_COMPLETED"])
            st.metric("In Progress", in_prog)
        with c4:
            completed = sum(1 for r in returns if r["status"] in ["RESTOCKED", "COMPLETED"])
            st.metric("Completed / Restocked", completed)

        st.markdown("---")
        st.markdown("#### Returns Inventory")
        if returns:
            df = pd.DataFrame([{
                "Return ID": r["id"],
                "Order Ref": r.get("order_ref", ""),
                "Retailer": r.get("organization_name", ""),
                "Category": r.get("product_category", ""),
                "Product": r.get("product_name", ""),
                "Status": r["status"],
                "Created At": r["created_at"][:19]
            } for r in returns])
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No returns registered.")

    with tabs[1]:
        st.subheader("Register a New Smartphone Return")
        st.write("Manual return registration for customer reverse-logistics cases.")

        try:
            orgs = api_client.list_organizations(token)
            retailer_orgs = [o for o in orgs if o["org_type"] == "RETAILER"]
        except Exception as e:
            st.error(f"Failed to fetch retailers: {e}")
            retailer_orgs = []

        with st.form("admin_register_return_form"):
            col1, col2 = st.columns(2)
            with col1:
                return_id = st.text_input("Custom Return ID (Optional)", placeholder="e.g. RET-2026-SMP1")
                order_ref = st.text_input("Order Reference", value="ORD-SMP-8821")
                retailer_choice = st.selectbox(
                    "Retailer / Product Owner",
                    options=retailer_orgs,
                    format_func=lambda o: f"{o['name']} (ID: {o['id']})"
                )
                product_cat = st.selectbox("Product Category", ["Smartphone", "Headphones", "Smartwatch", "Laptop"], index=0)
                product_name = st.text_input("Product Model / Name", value="Samsung Galaxy S22 5G 128GB")

            with col2:
                sku = st.text_input("SKU", value="SM-S901B-BLK")
                serial_expected = st.text_input("Expected Serial Number", value="SN-SMART-98421")
                customer_pincode = st.text_input("Customer Pincode", value="94103")
                return_reason = st.text_area("Customer Return Reason", value="Touchscreen occasional stutter, minor back scratch")

            submitted = st.form_submit_button("Submit Return Registration", use_container_width=True)

            if submitted:
                if not retailer_choice:
                    st.error("Please select a valid retailer organization.")
                else:
                    payload = {
                        "return_id": return_id.strip() if return_id.strip() else None,
                        "order_ref": order_ref.strip(),
                        "organization_id": retailer_choice["id"],
                        "product_category": product_cat,
                        "product_name": product_name.strip(),
                        "sku": sku.strip(),
                        "serial_expected": serial_expected.strip(),
                        "customer_pincode": customer_pincode.strip(),
                        "return_reason": return_reason.strip()
                    }
                    try:
                        res = api_client.create_return(token, payload)
                        st.success(f"✅ Successfully registered Return Case: **{res['id']}**!")
                        st.info("The return is now in status `RETURN_REQUESTED` and queued for warehouse receipt.")
                    except Exception as e:
                        st.error(f"Registration failed: {e}")

    with tabs[2]:
        render_return_journey(token)
