import streamlit as st

from frontend.api_client import api_client
from frontend.views.return_journey import render_return_journey


def render_inspector_dashboard(token: str, user: dict):
    st.title("🔬 Electronics Inspection & Quality Dashboard")
    st.caption(f"Logged in as **{user['full_name']}** (`{user['username']}`) | Role: **{user['role']}**")

    if "inspector_flash_msg" in st.session_state:
        st.success(st.session_state.pop("inspector_flash_msg"))

    tabs = st.tabs([
        "1️⃣ Inspection & Estimates",
        "2️⃣ Processing Task Execution",
        "3️⃣ Quality Check & Sanitization",
        "🔍 Case Search"
    ])

    # Tab 1: Inspection & Estimates
    with tabs[0]:
        st.subheader("1. Detailed Physical & Functional Inspection")
        try:
            received_returns = api_client.list_returns(token, status="RECEIVED")
        except Exception as e:
            st.error(f"Failed to fetch returns: {e}")
            received_returns = []

        if not received_returns:
            st.info("No received products currently awaiting inspection.")
        else:
            options = {f"{r['id']} — {r['product_name']} (Bin: {r.get('storage_location')})": r for r in received_returns}
            selected_label = st.selectbox("Select Return to Inspect", list(options.keys()))
            selected_ret = options[selected_label]

            with st.form("inspection_form"):
                st.write(f"**Serial Verified:** `{selected_ret.get('serial_received')}` | **Category:** `{selected_ret.get('product_category')}`")

                col1, col2 = st.columns(2)
                with col1:
                    condition = st.selectbox("Overall Physical Condition", ["LOW_DAMAGE", "GOOD", "MEDIUM_DAMAGE", "HIGH_DAMAGE"])
                    screen_cond = st.text_input("Screen / Display Condition", value="Minor surface scratches, touch responsive")
                    battery_health = st.slider("Battery Health (%)", min_value=10, max_value=100, value=88)

                with col2:
                    func_pass = st.checkbox("Functional Diagnostic Checks Passed (Touch, Camera, Wi-Fi, Audio)", value=True)
                    safety = st.text_input("Safety Concerns / Thermal Assessment", value="None. Normal operating temperature, battery unswollen.")
                    damage_notes = st.text_area("Detailed Damage Notes", value="Bezel scuffs, slight screen wear. High recovery potential with panel restoration.")

                submit_insp = st.form_submit_button(
                    "Complete Inspection & Generate Recovery Estimates",
                    use_container_width=True
                )

                if submit_insp:
                    payload = {
                        "physical_condition": condition,
                        "screen_condition": screen_cond,
                        "battery_health_pct": battery_health,
                        "functional_tests_passed": func_pass,
                        "damage_notes": damage_notes,
                        "safety_concerns": safety
                    }
                    try:
                        res = api_client.inspect_return(token, selected_ret["id"], payload)
                        st.session_state["inspector_flash_msg"] = (
                            f"✅ Inspection completed for **{res['id']}**! Generated {len(res.get('cost_estimates', []))} recovery options. "
                            "The return is now in `AWAITING_APPROVAL` for retailer review."
                        )
                        st.rerun()
                    except Exception as e:
                        st.error(f"Inspection failed: {e}")

    # Tab 2: Processing Task Execution
    with tabs[1]:
        st.subheader("2. Execute Recovery Processing Task (Refurbishment / Repair)")
        try:
            approved_returns = api_client.list_returns(token, status="APPROVED")
        except Exception as e:
            st.error(f"Failed to fetch approved returns: {e}")
            approved_returns = []

        if not approved_returns:
            st.info("No approved returns currently waiting for physical processing.")
        else:
            options = {f"{r['id']} — {r['product_name']}": r for r in approved_returns}
            selected_label = st.selectbox("Select Return to Process", list(options.keys()))
            selected_ret = options[selected_label]

            with st.form("processing_task_form"):
                st.write(f"**Executing Return Case:** `{selected_ret['id']}`")
                work_performed = st.text_area("Technical Work Performed", value="Screen replaced with OEM refurbished panel, contacts cleaned, battery cycle calibrated.")

                col1, col2 = st.columns(2)
                with col1:
                    actual_repair = st.number_input("Actual Parts & Repair Cost (₹)", min_value=0.0, value=5000.0, step=100.0)
                    actual_pack = st.number_input("Actual Packaging Cost (₹)", min_value=0.0, value=600.0, step=50.0)
                with col2:
                    actual_labor = st.number_input("Actual Labor / Sanitization Labor (₹)", min_value=0.0, value=1600.0, step=100.0)
                    actual_trans = st.number_input("Actual Transport Cost (₹)", min_value=0.0, value=960.0, step=50.0)

                total_cost = actual_repair + actual_pack + actual_labor + actual_trans
                st.markdown(f"**Total Actual Cost to Record:** `₹{total_cost:.2f}`")

                submit_proc = st.form_submit_button(
                    "Complete Processing Task",
                    use_container_width=True
                )

                if submit_proc:
                    payload = {
                        "work_performed": work_performed,
                        "actual_repair_cost": actual_repair,
                        "actual_packaging_cost": actual_pack,
                        "actual_labor_cost": actual_labor,
                        "actual_transport_cost": actual_trans
                    }
                    try:
                        res = api_client.process_return(token, selected_ret["id"], payload)
                        st.session_state["inspector_flash_msg"] = (
                            f"✅ Processing task recorded for **{res['id']}**! Status: `{res['status']}`. "
                            "Item is now ready for final QC & Sanitization."
                        )
                        st.rerun()
                    except Exception as e:
                        st.error(f"Processing failed: {e}")

    # Tab 3: Quality Check & Sanitization
    with tabs[2]:
        st.subheader("3. Quality Check & Data Sanitization Gate")
        try:
            proc_returns = api_client.list_returns(token, status="PROCESSING_COMPLETED")
        except Exception as e:
            st.error(f"Failed to fetch returns: {e}")
            proc_returns = []

        if not proc_returns:
            st.info("No items currently waiting for final QC.")
        else:
            options = {f"{r['id']} — {r['product_name']}": r for r in proc_returns}
            selected_label = st.selectbox("Select Return for QC Verification", list(options.keys()))
            selected_ret = options[selected_label]

            with st.form("qc_form"):
                st.markdown("##### 🔒 Mandatory Data Sanitization Gate")
                sanit_pass = st.checkbox("Certified Cryptographic Data Wipe PASSED (Zero data remanence)", value=True)
                sanit_cert = st.text_input("Sanitization Certificate Reference", value=f"CERT-WIPE-NIST-{selected_ret['id']}")
                sanit_method = st.text_input("Sanitization Method Used", value="NIST SP 800-88 Rev 1 Cryptographic Erase")

                st.markdown("##### 🔬 Quality & Cosmetic Grading")
                qc_pass = st.checkbox("12-Point Functional Diagnostic Verification Passed", value=True)
                cosmetic_grade = st.selectbox("Cosmetic Grade Assigned", ["GRADE_A", "GRADE_B", "GRADE_C"])
                qc_notes = st.text_area("Quality Inspector Certification Notes", value="Passed all optical and functional tests. Battery capacity >85%. Resale ready.")

                submit_qc = st.form_submit_button(
                    "Certify Quality Check",
                    use_container_width=True
                )

                if submit_qc:
                    payload = {
                        "functional_qc_passed": qc_pass,
                        "cosmetic_grade": cosmetic_grade,
                        "sanitization_passed": sanit_pass,
                        "sanitization_certificate": sanit_cert,
                        "sanitization_method": sanit_method,
                        "qc_notes": qc_notes
                    }
                    try:
                        res = api_client.qc_return(token, selected_ret["id"], payload)
                        st.session_state["inspector_flash_msg"] = (
                            f"✅ Quality Check Certified for **{res['id']}**! Status: `{res['status']}`. "
                            "Product is now cleared for restocking."
                        )
                        st.rerun()
                    except Exception as e:
                        st.error(f"QC Certification failed: {e}")

    # Tab 4: Search
    with tabs[3]:
        render_return_journey(token)
