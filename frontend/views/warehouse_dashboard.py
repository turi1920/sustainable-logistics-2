import streamlit as st

from frontend.api_client import api_client
from frontend.views.return_journey import render_return_journey


def render_warehouse_dashboard(token: str, user: dict):
    st.title("📦 Warehouse Employee Dashboard")
    st.caption(f"Logged in as **{user['full_name']}** (`{user['username']}`) | Role: **{user['role']}**")

    if "warehouse_flash_msg" in st.session_state:
        st.success(st.session_state.pop("warehouse_flash_msg"))

    tab_labels = ["📥 Warehouse Intake (Confirm Receipt)", "🏷️ Restock & Dispatch Queue", "🔍 Case Traceability"]
    default_tab = tab_labels[0]
    if st.session_state.get("journey_search_input"):
        default_tab = "🔍 Case Traceability"
    tabs = st.tabs(tab_labels, default=default_tab)

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
            # Prioritize shipments ready for intake at the top of the intake queue, newest first
            ready_items = [r for r in pending_receipt if r.get("pickup_status") in ["IN_TRANSIT", "DELIVERED_TO_WAREHOUSE"]]
            waiting_items = [r for r in pending_receipt if r.get("pickup_status") not in ["IN_TRANSIT", "DELIVERED_TO_WAREHOUSE"]]
            ready_items.sort(key=lambda r: str(r.get("created_at") or r.get("id") or ""), reverse=True)
            waiting_items.sort(key=lambda r: str(r.get("created_at") or r.get("id") or ""), reverse=True)
            sorted_pending = ready_items + waiting_items

            return_options = {}
            for r in sorted_pending:
                pst = r.get("pickup_status") or "PENDING_ASSIGNMENT"
                if pst in ["IN_TRANSIT", "DELIVERED_TO_WAREHOUSE"]:
                    tag = "🟢 Ready"
                elif pst == "PICKUP_FAILED":
                    tag = "❌ Pickup Failed"
                elif pst == "RESCHEDULED":
                    tag = "📅 Rescheduled"
                else:
                    tag = "⏳ Awaiting Pickup"
                label = f"[{tag}] {r['id']} — {r['product_name']} (Order: {r.get('order_ref')})"
                return_options[label] = r

            selected_label = st.selectbox("Select Return Case to Receive", list(return_options.keys()))
            selected_ret = return_options[selected_label]

            pickup_status = selected_ret.get("pickup_status") or "PENDING_ASSIGNMENT"
            partner_name = selected_ret.get("pickup_partner_name") or "Unassigned Carrier"
            is_picked_up = pickup_status in ["IN_TRANSIT", "DELIVERED_TO_WAREHOUSE"]

            col_a, col_b = st.columns(2)
            with col_a:
                st.write(f"**Expected Serial:** `{selected_ret.get('serial_expected') or 'Not specified'}`")
                st.write(f"**Retailer:** {selected_ret.get('organization_name') or 'N/A'}")
                st.write(f"**Return Reason:** {selected_ret.get('return_reason') or 'N/A'}")
            with col_b:
                st.write(f"**Pickup Partner:** {partner_name}")
                if is_picked_up:
                    st.markdown(f"**Logistics Status:** 🟢 `{pickup_status}` (Picked Up)")
                elif pickup_status == "PICKUP_FAILED":
                    st.markdown(f"**Logistics Status:** ❌ `{pickup_status}` (Exception)")
                elif pickup_status == "RESCHEDULED":
                    st.markdown(f"**Logistics Status:** 📅 `{pickup_status}` (Rescheduled)")
                else:
                    st.markdown(f"**Logistics Status:** ⏳ `{pickup_status}` (Awaiting Pickup)")

            if pickup_status == "PICKUP_FAILED":
                st.error(
                    f"⛔ **Pickup Attempt Failed**: The logistics carrier (**{partner_name}**) reported a doorstep collection failure for this return.\n\n"
                    f"- **Current Pickup Status**: `{pickup_status}`\n"
                    f"- **Exception Log**: {selected_ret.get('pickup_notes') or 'Failed collection attempt logged'}\n\n"
                    f"**Intake Blocked**: The carrier or dispatcher must resolve the exception and reschedule pickup before warehouse intake can occur."
                )
            elif not is_picked_up:
                st.warning(
                    f"⚠️ **Phase Sequencing Requirement**: This return cannot be received yet because it has not been picked up from the customer.\n\n"
                    f"- **Carrier**: {partner_name}\n"
                    f"- **Current Pickup Status**: `{pickup_status}`\n"
                    f"- **Action Required**: The carrier driver must collect the product from the customer doorstep first (`IN_TRANSIT`)."
                )
            else:
                st.success(
                    f"✅ **Ready for Intake Receipt**: Product was picked up by **{partner_name}** (`{pickup_status}`) and is available for intake verification."
                )

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
                receive_btn = st.form_submit_button(
                    "Confirm Warehouse Receipt",
                    use_container_width=True,
                    disabled=not is_picked_up
                )

                if receive_btn:
                    if not is_picked_up:
                        st.error("⛔ Phase Sequencing Error: The product has to be picked up first before warehouse intake can confirm receipt.")
                    elif not serial_received.strip():
                        st.error("Please record the received serial number.")
                    else:
                        payload = {
                            "serial_received": serial_received.strip(),
                            "storage_location": storage_loc.strip(),
                            "package_condition": package_cond
                        }
                        try:
                            res = api_client.receive_return(token, selected_ret["id"], payload)
                            st.session_state["warehouse_flash_msg"] = f"✅ Warehouse receipt confirmed for **{res['id']}**! Status updated to `{res['status']}`."
                            st.rerun()
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
                resale_value = st.number_input("Realized Resale Price (₹)", min_value=0.0, value=30000.0, step=500.0)
                notes = st.text_area("Disposition & Restock Notes", value="Packaged in certified eco-box with warranty seal.")
                submit_restock = st.form_submit_button(
                    "Complete Restock / Return",
                    use_container_width=True
                )

                if submit_restock:
                    payload = {
                        "disposition_type": disposition_type,
                        "inventory_location": inv_location,
                        "realized_resale_value": resale_value,
                        "notes": notes
                    }
                    try:
                        res = api_client.restock_return(token, selected_ret["id"], payload)
                        st.session_state["warehouse_flash_msg"] = (
                            f"✅ Disposition successfully recorded for **{res['id']}**! "
                            f"Action: `{disposition_type}`. Status updated to `{res['status']}`."
                        )
                        st.rerun()
                    except Exception as e:
                        st.error(f"Restock failed: {e}")

    with tabs[2]:
        render_return_journey(token)
