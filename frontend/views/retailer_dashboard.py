import pandas as pd
import streamlit as st

from frontend.api_client import api_client
from frontend.views.return_journey import render_return_journey
from frontend.views.sustainability_dashboard import render_sustainability_tab


def render_retailer_dashboard(token: str, user: dict):
    st.title("🏬 Retailer Representative Portal")
    org_name = user.get("organization_name") or "Retailer Partner"
    st.caption(f"Organization: **{org_name}** | User: **{user['full_name']}** (`{user['username']}`)")

    if "retailer_flash_msg" in st.session_state:
        st.success(st.session_state.pop("retailer_flash_msg"))

    st.info(f"🔒 Tenant Isolation Active: Viewing records exclusively for **{org_name}**.")

    tabs = st.tabs(["⏳ Pending Recovery Approvals", "📋 All Retailer Returns", "🌱 Sustainability Impact", "🔍 Return Case Journey"])

    # Tab 1: Pending Approvals
    with tabs[0]:
        st.subheader("Items Awaiting Authorization")
        try:
            pending = api_client.list_returns(token, status="AWAITING_APPROVAL")
        except Exception as e:
            st.error(f"Failed to load returns: {e}")
            pending = []

        if not pending:
            st.success("🎉 No returns currently awaiting your authorization.")
        else:
            options = {f"{r['id']} — {r['product_name']} (Order: {r.get('order_ref')})": r for r in pending}
            selected_label = st.selectbox("Select Case to Review", list(options.keys()))
            selected_ret = options[selected_label]

            # Fetch detailed return
            try:
                ret_detail = api_client.get_return(token, selected_ret["id"])
            except Exception as e:
                st.error(f"Failed to fetch return details: {e}")
                return

            st.markdown("---")
            st.markdown(f"#### Case Review: **{ret_detail['id']}** — {ret_detail['product_name']}")

            # Inspection summary
            ass = ret_detail.get("assessment")
            if ass:
                st.markdown("##### 🔬 Technical Inspection Findings")
                st.write(f"- **Physical Condition:** `{ass['physical_condition']}`")
                st.write(f"- **Screen Condition:** {ass.get('screen_condition')}")
                st.write(f"- **Battery Capacity:** {ass.get('battery_health_pct')}%")
                st.write(f"- **Inspection Notes:** {ass.get('damage_notes')}")

            # Cost estimates & NRV comparison
            st.markdown("##### 📊 Recovery Economics & Net Recovery Value (NRV)")
            estimates = ret_detail.get("cost_estimates", [])
            if estimates:
                table_rows = []
                for ce in estimates:
                    rec_badge = " ⭐ (System Recommended)" if ce["is_recommended"] else ""
                    table_rows.append({
                        "Option": ce["option_type"] + rec_badge,
                        "Est. Resale": f"₹{float(ce['estimated_resale_value']):.2f}",
                        "Repair / Work": f"₹{float(ce['estimated_repair_cost']):.2f}",
                        "Transport": f"₹{float(ce['estimated_transport_cost']):.2f}",
                        "Packaging": f"₹{float(ce['estimated_packaging_cost']):.2f}",
                        "Sanitization": f"₹{float(ce['estimated_sanitization_cost']):.2f}",
                        "Expected NRV": f"₹{float(ce['estimated_nrv']):.2f}",
                        "CO2 Saved": f"{float(ce['co2_saved_kg']):.1f} kg"
                    })
                st.table(pd.DataFrame(table_rows))

                rec_ce = next((c for c in estimates if c["is_recommended"]), None)
                if rec_ce:
                    st.info(f"**Circularity Assumptions:** {rec_ce.get('environmental_assumptions')}")

            # Approval Form
            with st.form("retailer_approval_form"):
                st.markdown("##### ✍️ Authorization Decision")
                eligible_options = [c["option_type"] for c in estimates] if estimates else ["REFURBISH", "REPAIR", "RESALE_AS_IS", "RETURN_TO_RETAILER", "RECYCLE"]

                selected_opt = st.selectbox("Approved Recovery Route", eligible_options, index=0)
                remarks = st.text_input("Decision Notes / Authorization Reference", value="Approved for high-yield refurbishment and local certified resale.")

                submit_dec = st.form_submit_button("Submit Commercial Authorization", use_container_width=True)

                if submit_dec:
                    payload = {
                        "decision": "APPROVED",
                        "approved_option": selected_opt,
                        "remarks": remarks
                    }
                    try:
                        res = api_client.decide_return(token, ret_detail["id"], payload)
                        st.session_state["retailer_flash_msg"] = (
                            f"✅ Authorization submitted for **{res['id']}**! "
                            f"Approved route: `{selected_opt}`. Status updated to `{res['status']}`."
                        )
                        st.rerun()
                    except Exception as e:
                        st.error(f"Decision submission failed: {e}")

    # Tab 2: All Retailer Returns
    with tabs[1]:
        st.subheader(f"All Returns for {org_name}")
        try:
            my_returns = api_client.list_returns(token)
            if my_returns:
                df = pd.DataFrame([{
                    "Return ID": r["id"],
                    "Order Ref": r.get("order_ref", ""),
                    "Product": r.get("product_name", ""),
                    "Serial": r.get("serial_received") or r.get("serial_expected", ""),
                    "Status": r["status"],
                    "Created At": r["created_at"][:19]
                } for r in my_returns])
                st.dataframe(df, width="stretch")
            else:
                st.info("No returns logged for this retailer.")
        except Exception as e:
            st.error(f"Failed to load returns: {e}")

    # Tab 3: Sustainability Impact
    with tabs[2]:
        render_sustainability_tab(token, user, organization_id=user.get("organization_id"))

    # Tab 4: Case Search
    with tabs[3]:
        render_return_journey(token)
