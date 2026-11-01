
import pandas as pd
import streamlit as st

from frontend.api_client import api_client


def render_return_journey(token: str, default_return_id: str = ""):
    st.subheader("🔍 Return Case Journey & Audit Timeline")

    with st.form("journey_search_form"):
        col1, col2 = st.columns([3, 1])
        with col1:
            search_query = st.text_input(
                "Enter Return Case ID or Serial Number",
                value=default_return_id,
                key="journey_search_input",
            )
        with col2:
            st.form_submit_button("Search Case", use_container_width=True)

    if not search_query:
        st.info("Enter a return case ID (e.g. `RET-1001`, `RET-1003`) to view its end-to-end lifecycle.")
        return

    try:
        ret = api_client.get_return(token, search_query.strip())
        journey = api_client.get_return_journey(token, search_query.strip())
    except Exception as e:
        st.error(f"Search failed: {e}")
        return

    st.markdown("---")
    st.markdown(f"### Return Case: **{ret['id']}** — *{ret['product_name']}*")

    # Metadata Overview
    mcol1, mcol2, mcol3, mcol4, mcol5 = st.columns(5)
    with mcol1:
        st.metric("Status", ret["status"])
    with mcol2:
        st.metric("Retailer Organization", ret.get("organization_name", "N/A"))
    with mcol3:
        st.metric("Pickup Partner", ret.get("pickup_partner_name") or "Unassigned")
    with mcol4:
        st.metric("Storage Location", ret.get("storage_location") or "Not yet assigned")
    with mcol5:
        st.metric("Order Reference", ret.get("order_ref") or "N/A")

    if ret.get("pickup_partner_name"):
        pickup_info_text = f"🚚 **Assigned Logistics Partner:** **{ret['pickup_partner_name']}** | **Status:** `{ret.get('pickup_status', 'ASSIGNED')}`"
        if ret.get("pickup_scheduled_date"):
            pickup_info_text += f" | **Scheduled Date:** {ret['pickup_scheduled_date'][:10]}"
        if ret.get("pickup_notes"):
            pickup_info_text += f" | **Instructions:** *{ret['pickup_notes']}*"
        st.info(pickup_info_text)

    tab_timeline, tab_costs, tab_env, tab_assessment, tab_execution = st.tabs([
        "📜 Audit Timeline",
        "💰 Estimated vs Actual Costs",
        "🌱 Environmental Impact",
        "🔬 Inspection & Condition",
        "⚙️ Execution & QC"
    ])

    with tab_timeline:
        st.markdown("#### Chronological Chain of Custody & Transitions")
        if journey:
            for item in journey:
                with st.expander(f"📍 {item['action']} — {item['new_status']} ({item['created_at'][:19]})", expanded=True):
                    st.write(f"**Actor:** `{item['actor_username']}` (Role: `{item['actor_role']}`)")
                    st.write(f"**Transition:** `{item.get('old_status') or 'INIT'}` ➡️ `{item['new_status']}`")
                    if item.get("details"):
                        st.write(f"**Details:** {item['details']}")
        else:
            st.info("No status history found.")

    with tab_costs:
        st.markdown("#### Financial Analysis: Estimated vs Actual Cost Breakdown")

        c_col1, c_col2 = st.columns(2)
        with c_col1:
            st.markdown("##### 📋 Estimated Options & Net Recovery Value (NRV)")
            if ret.get("cost_estimates"):
                est_data = []
                for ce in ret["cost_estimates"]:
                    est_data.append({
                        "Option": ce["option_type"] + (" ⭐ Recommended" if ce["is_recommended"] else ""),
                        "Est. Resale": f"₹{float(ce['estimated_resale_value']):.2f}",
                        "Repair": f"₹{float(ce['estimated_repair_cost']):.2f}",
                        "Transport": f"₹{float(ce['estimated_transport_cost']):.2f}",
                        "Sanitization": f"₹{float(ce['estimated_sanitization_cost']):.2f}",
                        "NRV": f"₹{float(ce['estimated_nrv']):.2f}"
                    })
                st.table(pd.DataFrame(est_data))
            else:
                st.info("No estimates generated yet (pending inspection).")

        with c_col2:
            st.markdown("##### 🛠️ Actual Recorded Costs")
            pt = ret.get("processing_task")
            disp = ret.get("disposition")
            if pt:
                actual_data = [
                    {"Cost Element": "Actual Repair & Parts", "Amount": f"₹{float(pt['actual_repair_cost']):.2f}"},
                    {"Cost Element": "Actual Packaging", "Amount": f"₹{float(pt['actual_packaging_cost']):.2f}"},
                    {"Cost Element": "Actual Labor / Sanitization", "Amount": f"₹{float(pt['actual_labor_cost']):.2f}"},
                    {"Cost Element": "Actual Transport", "Amount": f"₹{float(pt['actual_transport_cost']):.2f}"},
                    {"Cost Element": "TOTAL ACTUAL COST", "Amount": f"₹{float(pt['total_actual_cost']):.2f}"},
                ]
                if disp:
                    actual_data.append({"Cost Element": "Realized Resale Value", "Amount": f"₹{float(disp['realized_resale_value']):.2f}"})
                    net_actual = float(disp['realized_resale_value']) - float(pt['total_actual_cost'])
                    actual_data.append({"Cost Element": "REALIZED NET RECOVERY", "Amount": f"₹{net_actual:.2f}"})
                st.table(pd.DataFrame(actual_data))
            else:
                st.info("No processing task completed yet; actual costs will be logged upon execution.")

    with tab_env:
        st.markdown("#### 🌍 Environmental Footprint & Circularity Savings")
        ce_rec = next((c for c in ret.get("cost_estimates", []) if c.get("is_recommended")), None)
        if ce_rec:
            e1, e2, e3 = st.columns(3)
            with e1:
                st.metric("Net Avoided Carbon Emissions", f"{float(ce_rec['co2_saved_kg']):.1f} kg CO2e")
            with e2:
                st.metric("E-Waste Diverted from Landfill", "100% of product mass")
            with e3:
                st.metric("Circularity Strategy", "Product Life Extension")

            st.info(f"**Transparent Methodology & Assumptions:**\n\n{ce_rec.get('environmental_assumptions')}")
        else:
            st.info("Environmental savings will be calculated upon inspection.")

    with tab_assessment:
        st.markdown("#### 🔍 Detailed Inspection Results")
        ass = ret.get("assessment")
        if ass:
            st.write(f"**Physical Condition:** `{ass['physical_condition']}`")
            st.write(f"**Screen Condition:** {ass.get('screen_condition') or 'N/A'}")
            st.write(f"**Battery Health:** {ass.get('battery_health_pct')}%")
            st.write(f"**Functional Tests Passed:** {'✅ YES' if ass['functional_tests_passed'] else '❌ NO'}")
            st.write(f"**Damage Notes:** {ass.get('damage_notes') or 'None'}")
            st.write(f"**Safety Concerns:** {ass.get('safety_concerns') or 'None detected'}")
        else:
            st.info("Product has not yet been inspected.")

    with tab_execution:
        st.markdown("#### ⚙️ Processing, Quality Check & Disposition")
        qc = ret.get("quality_check")
        disp = ret.get("disposition")
        if qc:
            st.success(f"**Quality Check Certified:** Passed (Cosmetic Grade: `{qc['cosmetic_grade']}`)")
            st.write(f"**Data Sanitization:** {'✅ VERIFIED PASSED' if qc['sanitization_passed'] else '❌ FAILED'}")
            st.write(f"**Sanitization Certificate:** `{qc.get('sanitization_certificate')}`")
            st.write(f"**Method:** `{qc.get('sanitization_method')}`")
        else:
            st.info("Quality check not yet performed.")

        if disp:
            st.success(f"**Final Disposition:** `{disp['disposition_type']}` at `{disp.get('inventory_location')}`")
            st.write(f"**Realized Resale Value:** ₹{float(disp['realized_resale_value']):.2f}")
