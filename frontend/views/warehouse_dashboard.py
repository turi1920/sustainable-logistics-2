import streamlit as st

from frontend.api_client import api_client
from frontend.views.return_journey import render_return_journey


def render_warehouse_dashboard(token: str, user: dict):
    st.title("📦 Warehouse Employee Dashboard")
    st.caption(f"Logged in as **{user['full_name']}** (`{user['username']}`) | Role: **{user['role']}**")

    tabs = st.tabs(["📥 Warehouse Intake (Confirm Receipt)", "🏷️ Restock & Dispatch Queue", "🔍 Case Traceability"])

    with tabs[0]:
        st.subheader("Returns Awaiting Warehouse Receipt")
        try:
            pending_receipt = api_client.list_returns(token, status="RETURN_REQUESTED")
        except Exception as e:
            st.error(f"Failed to fetch returns: {e}")
            pending_receipt = []

        if not pending_receipt:
            st.success("🎉 No pending returns awaiting intake receipt.")
        else:
            return_options = {f"{r['id']} — {r['product_name']} (Order: {r.get('order_ref')})": r for r in pending_receipt}
            selected_label = st.selectbox("Select Return Case to Receive", list(return_options.keys()))
            selected_ret = return_options[selected_label]

            st.write(f"**Expected Serial:** `{selected_ret.get('serial_expected') or 'Not specified'}`")
            st.write(f"**Retailer:** {selected_ret.get('organization_name')}")
            st.write(f"**Return Reason:** {selected_ret.get('return_reason')}")

            with st.form("warehouse_receive_form"):
                serial_received = st.text_input(
                    "Serial Number Received on Physical Device",
                    value=selected_ret.get("serial_expected", "")
                )
                storage_loc = st.text_input("Assigned Warehouse Storage Location / Bin", value="Aisle 2, Bin W-105")
                package_cond = st.selectbox(
                    "Package Condition",
                    ["Intact box with original packaging", "Damaged outer box, device secure", "Unboxed / Bagged", "Missing accessories"]
                )
                receive_btn = st.form_submit_button("Confirm Warehouse Receipt", use_container_width=True)

                if receive_btn:
                    if not serial_received.strip():
                        st.error("Please record the received serial number.")
                    else:
                        payload = {
                            "serial_received": serial_received.strip(),
                            "storage_location": storage_loc.strip(),
                            "package_condition": package_cond
                        }
                        try:
                            res = api_client.receive_return(token, selected_ret["id"], payload)
                            st.success(f"✅ Warehouse receipt confirmed for **{res['id']}**! Status updated to `{res['status']}`.")
                            st.info("The return has been placed into inspection queue.")
                        except Exception as e:
                            st.error(f"Receipt failed: {e}")

    with tabs[1]:
        st.subheader("Restock into Inventory / Return to Retailer")
        st.write("Items that have successfully passed Quality Check and Data Sanitization.")

        try:
            ready_for_restock = api_client.list_returns(token, status="QC_PASSED")
        except Exception as e:
            st.error(f"Failed to fetch QC passed returns: {e}")
            ready_for_restock = []

        if not ready_for_restock:
            st.info("No items currently in `QC_PASSED` status waiting for restock.")
        else:
            options = {f"{r['id']} — {r['product_name']}": r for r in ready_for_restock}
            selected_label = st.selectbox("Select Return to Restock / Dispatch", list(options.keys()))
            selected_ret = options[selected_label]

            with st.form("warehouse_restock_form"):
                disposition_type = st.radio("Disposition Action", ["RESTOCKED", "RETURNED_TO_RETAILER"], index=0)
                inv_location = st.text_input("Final Resale Shelf / Shipping Bay", value="SHELF-REFURB-A1")
                resale_value = st.number_input("Realized Resale Price ($)", min_value=0.0, value=375.0, step=5.0)
                notes = st.text_area("Disposition & Restock Notes", value="Packaged in certified eco-box with warranty seal.")
                submit_restock = st.form_submit_button("Complete Restock / Return", use_container_width=True)

                if submit_restock:
                    payload = {
                        "disposition_type": disposition_type,
                        "inventory_location": inv_location,
                        "realized_resale_value": resale_value,
                        "notes": notes
                    }
                    try:
                        res = api_client.restock_return(token, selected_ret["id"], payload)
                        st.success(f"✅ Disposition successfully recorded for **{res['id']}**! Status: `{res['status']}`.")
                    except Exception as e:
                        st.error(f"Restock failed: {e}")

    with tabs[2]:
        render_return_journey(token)
