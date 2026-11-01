import pandas as pd
import streamlit as st

from frontend.api_client import api_client
from frontend.views.return_journey import render_return_journey


def render_pickup_dashboard(token: str, user: dict):
    carrier_name = user.get("pickup_partner_name") or "Logistics Carrier"
    partner_id = user.get("pickup_partner_id")

    st.title("🚚 Pickup Partner Field Logistics Portal")
    st.caption(
        f"Carrier: **{carrier_name}** | Driver: **{user['full_name']}** (`{user['username']}`) | Role: **{user['role']}**"
    )

    if not partner_id and user.get("role") == "PICKUP_PARTNER":
        st.error("⚠️ No logistics carrier account is linked to your driver profile. Please contact Platform Admin.")
        return

    if "pickup_flash_msg" in st.session_state:
        st.success(st.session_state.pop("pickup_flash_msg"))

    # Fetch carrier's assigned returns and open marketplace pool
    try:
        all_returns = api_client.list_returns(token)
        marketplace_returns = api_client.list_marketplace_returns(token)
    except Exception as e:
        st.error(f"Failed to fetch return shipments: {e}")
        all_returns = []
        marketplace_returns = []

    # Filter to this carrier's shipments if driver
    if partner_id:
        carrier_returns = [r for r in all_returns if r.get("pickup_partner_id") == partner_id]
    else:
        carrier_returns = all_returns

    assigned_queue = [r for r in carrier_returns if r.get("pickup_status") in ["ASSIGNED", "RESCHEDULED"]]
    failed_queue = [r for r in carrier_returns if r.get("pickup_status") == "PICKUP_FAILED"]
    transit_queue = [r for r in carrier_returns if r.get("pickup_status") == "IN_TRANSIT"]
    delivered_queue = [
        r for r in carrier_returns
        if r.get("pickup_status") == "DELIVERED_TO_WAREHOUSE" or r.get("status") not in ["RETURN_REQUESTED"]
    ]

    # Sort queues newest first
    assigned_queue.sort(key=lambda r: str(r.get("created_at") or r.get("id") or ""), reverse=True)
    failed_queue.sort(key=lambda r: str(r.get("created_at") or r.get("id") or ""), reverse=True)
    transit_queue.sort(key=lambda r: str(r.get("created_at") or r.get("id") or ""), reverse=True)

    # Top KPI Metrics Banner
    m_col1, m_col2, m_col3, m_col4, m_col5 = st.columns(5)
    with m_col1:
        st.metric("🌐 Marketplace Pool", len(marketplace_returns))
    with m_col2:
        st.metric("📋 My Active Pickups", len(assigned_queue))
    with m_col3:
        st.metric("⚠️ Exceptions / Failed", len(failed_queue))
    with m_col4:
        st.metric("🚛 Active In-Transit", len(transit_queue))
    with m_col5:
        st.metric("🏭 Delivered to Dock", len(delivered_queue))

    st.markdown("---")

    tabs = st.tabs([
        "📍 Doorstep Collection Queue",
        "🌐 Tasks Marketplace (Available Pool)",
        "⚠️ Exceptions & Failed Attempts",
        "🚛 Active Transit & Warehouse Handover",
        "📜 Completed Manifest & Sustainability",
        "🔍 Shipment Traceability",
    ])

    # ==========================================
    # TAB 1: ASSIGNED PICKUPS QUEUE (DOORSTEP)
    # ==========================================
    with tabs[0]:
        st.subheader("📍 Doorstep Collection Queue")
        st.caption("Pickups assigned or rescheduled for your carrier awaiting physical collection from customer premises.")

        if not assigned_queue:
            st.success("🎉 No pending doorstep pickups assigned to your carrier at this time.")
        else:
            options = {}
            for r in assigned_queue:
                tag = "📅 Rescheduled" if r.get("pickup_status") == "RESCHEDULED" else "📋 Assigned"
                label = f"[{tag}] {r['id']} — {r['product_name']} (Pincode: {r.get('customer_pincode') or 'N/A'})"
                options[label] = r

            selected_label = st.selectbox("Select Return to Collect", list(options.keys()))
            selected_ret = options[selected_label]

            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**Return ID:** `{selected_ret['id']}`")
                st.markdown(f"**Product Model:** {selected_ret['product_name']}")
                st.markdown(f"**Category:** `{selected_ret['product_category']}`")
                st.markdown(f"**SKU:** `{selected_ret['sku']}`")
                st.markdown(f"**Expected Serial:** `{selected_ret.get('serial_expected') or 'N/A'}`")
            with col2:
                st.markdown(f"**Customer Pincode / Zone:** `{selected_ret.get('customer_pincode') or 'N/A'}`")
                st.markdown(f"**Order Reference:** `{selected_ret.get('order_ref') or 'N/A'}`")
                st.markdown(f"**Retailer:** {selected_ret.get('organization_name') or 'N/A'}")
                st.markdown(f"**Customer Return Reason:** *{selected_ret.get('return_reason') or 'None listed'}*")
                st.markdown(f"**Current Status:** `{selected_ret.get('status')}` (Pickup: `{selected_ret.get('pickup_status')}`)")

            if selected_ret.get("pickup_notes"):
                st.info(f"📝 **Previous Driver / Dispatch Notes:** {selected_ret.get('pickup_notes')}")

            st.markdown("---")
            act_col1, act_col2 = st.columns(2)

            with act_col1:
                st.markdown("#### ✅ Confirm Doorstep Collection")
                st.caption("Record successful handover from customer to driver.")
                with st.form(f"collect_form_{selected_ret['id']}"):
                    pickup_notes = st.text_area(
                        "Doorstep Verification & Cargo Notes",
                        value="Customer identity and product physical condition verified. Packaged in reusable shock-absorbent tote."
                    )
                    submit_collect = st.form_submit_button("✅ Confirm Doorstep Physical Pickup", type="primary", use_container_width=True)

                    if submit_collect:
                        payload = {"picked_up_notes": pickup_notes.strip()}
                        try:
                            res = api_client.confirm_pickup_collection(token, selected_ret["id"], payload)
                            st.session_state["pickup_flash_msg"] = f"✅ Successfully collected return {res['id']}! Shipment is now IN_TRANSIT to warehouse dock."
                            st.rerun()
                        except Exception as e:
                            st.error(f"Collection failed: {e}")

            with act_col2:
                st.markdown("#### ❌ Report Failed Pickup Attempt")
                st.caption("Record customer absence, refused handover, or cargo mismatch.")
                with st.form(f"fail_form_{selected_ret['id']}"):
                    failure_reasons = {
                        "CUSTOMER_UNAVAILABLE": "Customer Unavailable / Door Locked / Unreachable",
                        "CUSTOMER_REFUSED": "Customer Refused Handover / Cancelled Return",
                        "SERIAL_MISMATCH": "Serial Number or Device Model Mismatch at Doorstep",
                        "DAMAGED_SAFETY_HAZARD": "Severe Damage / Swollen Battery / Safety Hazard",
                        "ADDRESS_INCORRECT": "Incorrect Customer Address / Inaccessible Location",
                        "OTHER": "Other Field Exception"
                    }
                    reason_key = st.selectbox(
                        "Reason for Failed Pickup",
                        options=list(failure_reasons.keys()),
                        format_func=lambda k: failure_reasons[k]
                    )
                    fail_notes = st.text_area(
                        "Doorstep cargo notes & observation",
                        value="",
                        placeholder="Provide details on why pickup could not be completed..."
                    )
                    resched_now = st.checkbox("Schedule retry date now?", value=False)
                    resched_date = None
                    if resched_now:
                        resched_date = st.date_input("Retry Pickup Date")

                    submit_fail = st.form_submit_button("❌ Record Failed Attempt", type="secondary", use_container_width=True)

                    if submit_fail:
                        if not fail_notes.strip():
                            st.error("Please provide cargo notes explaining the failed pickup attempt.")
                        else:
                            payload = {
                                "failure_reason": failure_reasons[reason_key],
                                "failure_notes": fail_notes.strip(),
                                "reschedule_date": f"{resched_date}T10:00:00" if resched_now and resched_date else None
                            }
                            try:
                                res = api_client.fail_pickup_collection(token, selected_ret["id"], payload)
                                new_st = res.get("pickup_status")
                                if new_st == "RESCHEDULED":
                                    st.session_state["pickup_flash_msg"] = f"⚠️ Pickup marked failed and rescheduled for return {res['id']} on {resched_date}."
                                else:
                                    st.session_state["pickup_flash_msg"] = f"❌ Pickup failure recorded for return {res['id']}. Shipment moved to Exceptions queue."
                                st.rerun()
                            except Exception as e:
                                st.error(f"Failed to record exception: {e}")

            st.markdown("---")
            with st.expander("↩️ Release Task back to Marketplace", expanded=False):
                st.caption(
                    "Release this shipment back to the public marketplace pool. "
                    "Once released, it will disappear from your queue and become available for other drivers."
                )
                rel_col1, rel_col2 = st.columns([3, 1])
                with rel_col1:
                    rel_reason = st.text_input(
                        "Reason (Optional)",
                        placeholder="e.g. Shift ended, vehicle full, outside daily route zone",
                        key=f"rel_reason_{selected_ret['id']}",
                    )
                with rel_col2:
                    st.write("")
                    btn_release = st.button("↩️ Release Task", key=f"btn_rel_{selected_ret['id']}", type="secondary", use_container_width=True)

                if btn_release:
                    try:
                        api_client.release_driver_task(token, selected_ret["id"], reason=rel_reason)
                        st.session_state["pickup_flash_msg"] = f"✅ Task **{selected_ret['id']}** released back to the public marketplace pool."
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to release task: {e}")

    # ==========================================
    # TAB 2: TASKS MARKETPLACE (AVAILABLE POOL)
    # ==========================================
    with tabs[1]:
        st.subheader("🌐 Tasks Marketplace (Available Pool)")
        st.caption("Public feed of customer returns across all carriers awaiting doorstep collection. Accept a task to lock it exclusively into your run-sheet.")

        if not marketplace_returns:
            st.info("🎉 There are no open pickup tasks in the marketplace at this moment. Check back soon!")
        else:
            st.markdown(f"**Available Pickup Opportunities ({len(marketplace_returns)})**")
            for ret in marketplace_returns:
                with st.container(border=True):
                    c_left, c_mid, c_right = st.columns([3, 3, 2])
                    with c_left:
                        st.markdown(f"#### `{ret['id']}`")
                        st.markdown(f"**{ret['product_name']}**")
                        st.caption(f"Category: `{ret['product_category']}` | SKU: `{ret['sku']}`")
                        st.caption(f"Retailer: **{ret.get('organization_name') or 'N/A'}**")
                    with c_mid:
                        st.markdown(f"📍 **Customer Pincode:** `{ret.get('customer_pincode') or 'N/A'}`")
                        st.markdown(f"📝 **Return Reason:** *{ret.get('return_reason') or 'Standard Return'}*")
                        if ret.get("order_ref"):
                            st.caption(f"Order: `{ret['order_ref']}`")
                    with c_right:
                        st.write("")
                        if st.button("✅ Accept", key=f"mkt_accept_{ret['id']}", use_container_width=True, type="primary"):
                            try:
                                api_client.accept_marketplace_task(token, ret["id"])
                                st.session_state["pickup_flash_msg"] = f"🎉 Successfully accepted task **{ret['id']}**! Added to your Doorstep Collection Queue."
                                st.rerun()
                            except Exception as e:
                                st.error(f"Could not accept task: {e}")

                        if st.button("❌ Reject", key=f"btn_rej_{ret['id']}", use_container_width=True):
                            try:
                                api_client.reject_marketplace_task(token, ret["id"])
                                st.session_state["pickup_flash_msg"] = f"Task **{ret['id']}** rejected and dismissed from your feed."
                                st.rerun()
                            except Exception as e:
                                st.error(f"Failed to reject: {e}")

    # ==========================================
    # TAB 3: EXCEPTIONS & FAILED PICKUPS QUEUE
    # ==========================================
    with tabs[2]:
        st.subheader("⚠️ Exceptions & Failed Pickups Queue")
        st.caption("Returns where doorstep collection failed. Review driver cargo notes and reschedule collection attempts.")

        if not failed_queue:
            st.success("🎉 No active pickup failures or field exceptions reported for your carrier.")
        else:
            fail_options = {
                f"{r['id']} — {r['product_name']} ({r.get('pickup_notes') or 'Failed attempt'})": r
                for r in failed_queue
            }
            selected_fail_label = st.selectbox("Select Failed Return to Review & Reschedule", list(fail_options.keys()))
            selected_failed_ret = fail_options[selected_fail_label]

            f_col1, f_col2 = st.columns(2)
            with f_col1:
                st.markdown(f"**Return ID:** `{selected_failed_ret['id']}`")
                st.markdown(f"**Product:** {selected_failed_ret['product_name']}")
                st.markdown(f"**Customer Pincode:** `{selected_failed_ret.get('customer_pincode') or 'N/A'}`")
                st.markdown(f"**Retailer:** {selected_failed_ret.get('organization_name') or 'N/A'}")
            with f_col2:
                st.markdown(f"**Current Status:** ❌ `{selected_failed_ret.get('pickup_status')}`")
                st.markdown(f"**Exception Log:** {selected_failed_ret.get('pickup_notes') or 'None logged'}")

            st.markdown("#### 🔄 Reschedule Pickup Attempt")
            with st.form(f"reschedule_form_{selected_failed_ret['id']}"):
                new_date = st.date_input("New Scheduled Collection Date")
                resched_notes = st.text_area(
                    "Reschedule Instructions / Customer Contact Notes",
                    value="Contacted customer via telephone; confirmed availability for new collection window."
                )
                submit_resched = st.form_submit_button("📅 Reschedule Doorstep Pickup", type="primary", use_container_width=True)

                if submit_resched:
                    payload = {
                        "reschedule_date": f"{new_date}T10:00:00",
                        "reschedule_notes": resched_notes.strip()
                    }
                    try:
                        res = api_client.reschedule_pickup(token, selected_failed_ret["id"], payload)
                        st.session_state["pickup_flash_msg"] = f"✅ Return {res['id']} successfully rescheduled for {new_date}! Moved back to Doorstep Collection Queue."
                        st.rerun()
                    except Exception as e:
                        st.error(f"Rescheduling failed: {e}")

    # ==========================================
    # TAB 4: ACTIVE TRANSIT & WAREHOUSE HANDOVER
    # ==========================================
    with tabs[3]:
        st.subheader("🚛 Active Transit & Warehouse Intake Handover")
        st.caption("Packages collected by your driver, currently on the vehicle en route to the central warehouse.")

        if not transit_queue:
            st.info("No shipments are currently in transit. Complete a doorstep pickup in Tab 1 to start transit.")
        else:
            options_transit = {
                f"{r['id']} — {r['product_name']} (From Pincode: {r.get('customer_pincode')})": r
                for r in transit_queue
            }
            selected_transit_label = st.selectbox("Select Shipment for Warehouse Handover", list(options_transit.keys()))
            selected_transit_ret = options_transit[selected_transit_label]

            t_col1, t_col2 = st.columns(2)
            with t_col1:
                st.markdown(f"**Return ID:** `{selected_transit_ret['id']}`")
                st.markdown(f"**Product:** {selected_transit_ret['product_name']}")
                st.markdown(f"**Expected Serial:** `{selected_transit_ret.get('serial_expected') or 'N/A'}`")
            with t_col2:
                st.markdown(f"**Carrier Fleet:** {carrier_name}")
                st.markdown(f"**Origin Pincode:** `{selected_transit_ret.get('customer_pincode') or 'N/A'}`")
                st.markdown(f"**Logistics Status:** `{selected_transit_ret.get('pickup_status')}`")

            st.markdown("#### 🏭 Handover to Warehouse Dock")
            with st.form(f"deliver_form_{selected_transit_ret['id']}"):
                dock_notes = st.text_area(
                    "Warehouse Dock Delivery Notes",
                    value="Arrived at central reverse logistics receiving bay. Handed package to intake receiving personnel."
                )
                submit_deliver = st.form_submit_button("🚚 Hand Over to Warehouse Dock", type="primary", use_container_width=True)

                if submit_deliver:
                    payload = {"delivery_notes": dock_notes.strip()}
                    try:
                        res = api_client.deliver_pickup_to_warehouse(token, selected_transit_ret["id"], payload)
                        st.session_state["pickup_flash_msg"] = f"✅ Return {res['id']} successfully handed over to central warehouse dock (DELIVERED_TO_WAREHOUSE)!"
                        st.rerun()
                    except Exception as e:
                        st.error(f"Handover failed: {e}")

    # ==========================================
    # TAB 5: COMPLETED MANIFEST & SUSTAINABILITY
    # ==========================================
    with tabs[4]:
        st.subheader("📜 Carrier Delivery Manifest & Environmental Metrics")
        st.caption("Consolidated log of shipments processed by your carrier fleet.")

        # Eco-Logistics Metrics Card
        st.markdown(
            """
            > **🌱 Clean Mobility Impact:**
            > Returns transported via optimized EV routes reduce doorstep logistics emissions by up to **68%**
            > compared to conventional diesel courier networks. Electric van regenerative braking and route clustering
            > ensure minimal carbon footprint per unit collected.
            """
        )

        if carrier_returns:
            manifest_data = []
            for r in carrier_returns:
                manifest_data.append({
                    "Return ID": r["id"],
                    "Order Ref": r.get("order_ref"),
                    "Product": r["product_name"],
                    "Category": r["product_category"],
                    "Pincode": r.get("customer_pincode") or "N/A",
                    "Pickup Status": r.get("pickup_status") or "PENDING",
                    "Lifecycle Status": r.get("status"),
                    "Retailer": r.get("organization_name")
                })
            st.dataframe(pd.DataFrame(manifest_data), width="stretch")
        else:
            st.info("No shipments assigned to your carrier yet.")

    # ==========================================
    # TAB 6: CASE TRACEABILITY
    # ==========================================
    with tabs[5]:
        render_return_journey(token)
