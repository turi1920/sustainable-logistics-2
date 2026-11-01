import random
from datetime import datetime

import pandas as pd
import streamlit as st

from frontend.api_client import api_client
from frontend.views.return_journey import render_return_journey
from frontend.views.sustainability_dashboard import render_sustainability_tab


def render_admin_dashboard(token: str, user: dict):
    st.title("🛡️ Platform Admin Dashboard")
    st.caption(f"Logged in as **{user['full_name']}** (`{user['username']}`) | Role: **{user['role']}**")

    if "admin_flash_msg" in st.session_state:
        st.success(st.session_state.pop("admin_flash_msg"))

    tab_labels = [
        "📊 Overview & Returns",
        "➕ Register New Return",
        "👥 User Management",
        "🚚 Pickup Partners & Dispatch",
        "🌱 Sustainability Impact",
        "🔍 Traceability & Audit",
    ]
    saved_tab = st.query_params.get("tab")
    default_tab = tab_labels[0]
    if saved_tab:
        for lbl in tab_labels:
            if saved_tab == lbl or saved_tab.lower() in lbl.lower() or lbl.lower() in saved_tab.lower():
                default_tab = lbl
                break
    elif st.session_state.get("journey_search_input"):
        default_tab = "🔍 Traceability & Audit"

    tabs = st.tabs(tab_labels, default=default_tab)

    # ==========================================
    # TAB 1: OVERVIEW & RETURNS
    # ==========================================
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
                "Assigned Driver": r.get("assigned_driver_name") or r.get("pickup_partner_name") or "🌐 Marketplace Pool",
                "Pickup Status": r.get("pickup_status") or "PENDING",
                "Category": r.get("product_category", ""),
                "Product": r.get("product_name", ""),
                "Status": r["status"],
                "Created At": r["created_at"][:19]
            } for r in returns])
            st.dataframe(df, width="stretch")
        else:
            st.info("No returns registered.")

    # ==========================================
    # TAB 2: REGISTER NEW RETURN
    # ==========================================
    with tabs[1]:
        st.subheader("Register a New Smartphone Return")
        st.write("Manual return registration for customer reverse-logistics cases.")

        try:
            orgs = api_client.list_organizations(token)
            retailer_orgs = [o for o in orgs if o["org_type"] == "RETAILER"]
            users_all = api_client.list_users(token)
            pickup_drivers = [u for u in users_all if u.get("role") == "PICKUP_PARTNER"]
        except Exception as e:
            st.error(f"Failed to fetch organizations or pickup drivers: {e}")
            retailer_orgs = []
            pickup_drivers = []

        # Auto-generate Primary Key Return ID if not in session state
        if "auto_generated_return_id" not in st.session_state:
            try:
                gen_data = api_client.generate_return_id(token)
                st.session_state["auto_generated_return_id"] = gen_data["return_id"]
            except Exception:
                st.session_state["auto_generated_return_id"] = f"RET-{datetime.utcnow().year}-{random.randint(1000, 9999)}"

        current_return_id = st.session_state["auto_generated_return_id"]

        with st.form("admin_register_return_form"):
            col1, col2 = st.columns(2)
            with col1:
                st.text_input(
                    "Return Case ID (Auto-Generated)",
                    value=current_return_id,
                    disabled=True,
                    help="System-generated unique primary key. Non-editable to preserve database integrity."
                )
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

                # Pickup driver selection (default to first active driver if available)
                driver_options = [{"id": None, "name": "🌐 Public Tasks Marketplace (Available to all drivers)", "pickup_partner_id": None}] + [
                    {"id": d["id"], "name": f"{d['full_name']} (@{d['username']})", "pickup_partner_id": d.get("pickup_partner_id")}
                    for d in pickup_drivers
                ]
                driver_choice = st.selectbox(
                    "Assign Logistics / Pickup Partner",
                    options=driver_options,
                    index=1 if len(pickup_drivers) > 0 else 0,
                    format_func=lambda d: d["name"]
                )

            submitted = st.form_submit_button("Submit Return Registration", use_container_width=True)

            if submitted:
                if not retailer_choice:
                    st.error("Please select a valid retailer organization.")
                else:
                    payload = {
                        "return_id": current_return_id,
                        "order_ref": order_ref.strip(),
                        "organization_id": retailer_choice["id"],
                        "product_category": product_cat,
                        "product_name": product_name.strip(),
                        "sku": sku.strip(),
                        "serial_expected": serial_expected.strip(),
                        "customer_pincode": customer_pincode.strip(),
                        "return_reason": return_reason.strip(),
                        "pickup_partner_id": driver_choice.get("pickup_partner_id"),
                        "assigned_driver_id": driver_choice.get("id")
                    }
                    try:
                        res = api_client.create_return(token, payload)
                        st.session_state.pop("auto_generated_return_id", None)
                        driver_info = f" Assigned Driver: {res['assigned_driver_name']}." if res.get("assigned_driver_name") else (" Assigned Partner: " + res['pickup_partner_name'] if res.get('pickup_partner_name') else " Open in Public Marketplace.")
                        st.session_state["admin_flash_msg"] = f"✅ Successfully registered Return Case: **{res['id']}**!{driver_info}"
                        st.rerun()
                    except Exception as e:
                        st.error(f"Registration failed: {e}")

    # ==========================================
    # TAB 3: USER MANAGEMENT (ADD / REMOVE USER)
    # ==========================================
    with tabs[2]:
        st.subheader("👥 User Management")
        st.caption("Manage platform staff and retailer accounts with Role-Based Access Control.")

        if "user_flash_msg" in st.session_state:
            st.success(st.session_state.pop("user_flash_msg"))

        try:
            users_list = api_client.list_users(token)
            all_orgs = api_client.list_organizations(token)
            partners = api_client.list_pickup_partners(token)
        except Exception as e:
            st.error(f"Failed to fetch users or carriers: {e}")
            users_list = []
            all_orgs = []
            partners = []

        # Current Users Directory Table
        st.markdown("#### Registered System Users")
        if users_list:
            users_df = pd.DataFrame([{
                "User ID": u["id"],
                "Username": u["username"],
                "Full Name": u["full_name"],
                "Email": u["email"],
                "Role": u["role"],
                "Organization / Carrier": u.get("pickup_partner_name") or u.get("organization_name") or "Platform Internal",
                "Status": "🟢 Active" if u.get("is_active") else "🔴 Inactive",
                "Created At": u["created_at"][:10] if u.get("created_at") else ""
            } for u in users_list])
            st.dataframe(users_df, width="stretch")
        else:
            st.info("No users found.")

        st.markdown("---")

        u_col1, u_col2 = st.columns(2)

        # ADD NEW USER FORM
        with u_col1:
            st.markdown("#### ➕ Add New User")
            with st.form("add_new_user_form"):
                new_username = st.text_input("Username", placeholder="e.g. john_doe")
                new_email = st.text_input("Email Address", placeholder="e.g. john@retailer.example")
                new_password = st.text_input("Password", type="password", placeholder="Min 6 characters")
                new_fullname = st.text_input("Full Name", placeholder="e.g. John Doe")
                new_role = st.selectbox("Assigned Role", ["WAREHOUSE", "INSPECTOR", "RETAILER", "PICKUP_PARTNER", "ADMIN"], index=0)

                # Organization selection
                org_options = [{"id": None, "name": "None (Platform Staff)"}] + all_orgs
                new_org = st.selectbox(
                    "Organization (Mandatory for RETAILER)",
                    options=org_options,
                    format_func=lambda o: o["name"]
                )

                # Carrier selection
                carrier_options = [{"id": None, "name": "None / Independent"}] + partners
                new_carrier = st.selectbox(
                    "Logistics Carrier (Optional for PICKUP_PARTNER)",
                    options=carrier_options,
                    format_func=lambda p: p["name"]
                )

                add_user_btn = st.form_submit_button("Create User Account", use_container_width=True)

                if add_user_btn:
                    if not new_username.strip() or not new_email.strip() or not new_password.strip() or not new_fullname.strip():
                        st.error("Please fill in all required fields (username, email, password, full name).")
                    elif new_role == "RETAILER" and (not new_org or new_org["id"] is None):
                        st.error("A Retailer user must be assigned to a specific retailer organization.")
                    else:
                        payload = {
                            "username": new_username.strip(),
                            "email": new_email.strip().lower(),
                            "password": new_password,
                            "full_name": new_fullname.strip(),
                            "role": new_role,
                            "organization_id": new_org["id"] if new_org else None,
                            "pickup_partner_id": new_carrier["id"] if new_carrier and new_carrier.get("id") else None
                        }
                        try:
                            created = api_client.create_user(token, payload)
                            st.session_state["user_flash_msg"] = f"✅ User **{created['username']}** created successfully with role `{created['role']}`!"
                            st.query_params["tab"] = "👥 User Management"
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to create user: {e}")

        # REMOVE EXISTING USER FORM
        with u_col2:
            st.markdown("#### 🗑️ Remove User from Database")
            st.warning("⚠️ Permanently removes the user account, login credentials, and platform access from PostgreSQL. Audit logs remain intact.")

            # Filter out current logged-in user to prevent accidental self-lockout
            deletable_users = [u for u in users_list if u["id"] != user["id"]]

            if not deletable_users:
                st.info("No other users available in the database to delete.")
            else:
                with st.form("delete_user_form"):
                    user_options = {
                        f"{u['username']} ({u['full_name']} — Role: {u['role']}) [ID: {u['id']}]": u
                        for u in deletable_users
                    }
                    user_label = st.selectbox(
                        "Select User to Delete",
                        options=list(user_options.keys()),
                        index=len(deletable_users) - 1
                    )
                    user_to_delete = user_options[user_label]

                    confirm_delete = st.checkbox("Confirm permanent deletion of this user and their login credentials")
                    delete_btn = st.form_submit_button("🗑️ Delete User & Revoke Access", type="primary", use_container_width=True)

                    if delete_btn:
                        if not confirm_delete:
                            st.error("Please check the confirmation box before deleting.")
                        else:
                            try:
                                res = api_client.delete_user(token, user_to_delete["id"])
                                st.session_state["user_flash_msg"] = f"✅ {res.get('message', 'User deleted successfully!')}"
                                st.query_params["tab"] = "👥 User Management"
                                st.rerun()
                            except Exception as e:
                                st.error(f"Failed to delete user: {e}")

            st.markdown("---")
            st.markdown("#### 🔄 Toggle Active / Inactive Status")
            if users_list:
                user_to_toggle = st.selectbox(
                    "Select User to Activate / Deactivate",
                    options=users_list,
                    key="toggle_user_select",
                    format_func=lambda u: f"{u['username']} ({'Active' if u.get('is_active') else 'Inactive'})"
                )
                if st.button("Toggle Status", use_container_width=True):
                    try:
                        res = api_client.toggle_user_active(token, user_to_toggle["id"])
                        st.session_state["user_flash_msg"] = f"✅ {res.get('message', 'Status updated!')}"
                        st.query_params["tab"] = "👥 User Management"
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to toggle status: {e}")

    # ==========================================
    # TAB 4: PICKUP PERSONNEL & DISPATCH
    # ==========================================
    with tabs[3]:
        st.subheader("🚚 Pickup Personnel & Field Dispatch")
        st.caption("Manage doorstep pickup drivers, carrier affiliations, and direct task dispatching.")

        if "partner_flash_msg" in st.session_state:
            st.success(st.session_state.pop("partner_flash_msg"))

        try:
            users_all = api_client.list_users(token)
            pickup_drivers = [u for u in users_all if u.get("role") == "PICKUP_PARTNER"]
            partners = api_client.list_pickup_partners(token)
            returns_all = api_client.list_returns(token)
        except Exception as e:
            st.error(f"Failed to fetch pickup personnel or returns: {e}")
            users_all = []
            pickup_drivers = []
            partners = []
            returns_all = []

        # Current Pickup Personnel Table
        st.markdown("#### Registered Pickup Personnel & Field Drivers")
        if pickup_drivers:
            driver_task_counts = {
                d["id"]: sum(
                    1 for r in returns_all
                    if r.get("assigned_driver_id") == d["id"]
                    and r.get("pickup_status") in ["ASSIGNED", "RESCHEDULED", "IN_TRANSIT"]
                )
                for d in pickup_drivers
            }
            drivers_df = pd.DataFrame([{
                "Driver ID": d["id"],
                "Username": d["username"],
                "Full Name": d["full_name"],
                "Email": d["email"],
                "Role": d["role"],
                "Logistics Carrier": d.get("pickup_partner_name") or "Independent / Direct",
                "Status": "🟢 Active" if d.get("is_active") else "🔴 Inactive",
                "Active Tasks": f"{driver_task_counts.get(d['id'], 0)} assigned",
                "Date Added": d["created_at"][:10] if d.get("created_at") else ""
            } for d in pickup_drivers])
            st.dataframe(drivers_df, width="stretch")
        else:
            st.info("No pickup drivers registered in the system.")

        st.markdown("---")

        p_col1, p_col2 = st.columns(2)

        # ADD NEW PICKUP DRIVER
        with p_col1:
            st.markdown("#### ➕ Add Pickup Driver / Personnel")
            with st.form("add_pickup_driver_form"):
                d_username = st.text_input("Driver Username", placeholder="e.g. driver_sam")
                d_fullname = st.text_input("Driver Full Name", placeholder="e.g. Sam Rivera (Courier)")
                d_email = st.text_input("Driver Email Address", placeholder="e.g. sam@ecologix.example")
                d_password = st.text_input("Initial Password", type="password", value="Pickup123!")

                carrier_options = [{"id": None, "name": "Independent Courier (Direct)"}] + partners
                d_carrier = st.selectbox(
                    "Logistics Carrier Affiliation",
                    options=carrier_options,
                    format_func=lambda c: c["name"]
                )

                add_driver_btn = st.form_submit_button("Create Driver Account", use_container_width=True)

                if add_driver_btn:
                    if not d_username.strip() or not d_fullname.strip() or not d_email.strip() or not d_password.strip():
                        st.error("Please fill in all required driver account fields.")
                    else:
                        payload = {
                            "username": d_username.strip(),
                            "email": d_email.strip().lower(),
                            "password": d_password,
                            "full_name": d_fullname.strip(),
                            "role": "PICKUP_PARTNER",
                            "pickup_partner_id": d_carrier["id"] if d_carrier and d_carrier.get("id") else None
                        }
                        try:
                            created_d = api_client.create_user(token, payload)
                            st.session_state["partner_flash_msg"] = f"✅ Pickup Driver **{created_d['username']}** ({created_d['full_name']}) added successfully!"
                            st.query_params["tab"] = "🚚 Pickup Partners & Dispatch"
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to create driver: {e}")

        # DISPATCH RETURN CASE & REMOVE DRIVER
        with p_col2:
            st.markdown("#### 🚚 Dispatch / Assign Return Case to Driver")
            assignable_returns = [r for r in returns_all if r["status"] == "RETURN_REQUESTED"]

            if not assignable_returns:
                st.info("No active returns in `RETURN_REQUESTED` state awaiting pickup assignment.")
            elif not pickup_drivers:
                st.warning("Please add at least one pickup driver first.")
            else:
                with st.form("assign_pickup_form"):
                    target_return = st.selectbox(
                        "Select Return Case",
                        options=assignable_returns,
                        format_func=lambda r: f"{r['id']} — {r['product_name']} [Pickup: {r.get('pickup_status', 'PENDING')}] (Driver: {r.get('assigned_driver_username') or 'Marketplace Pool'})"
                    )
                    dispatch_destinations = [
                        {"id": None, "name": "🌐 Public Tasks Marketplace (Available to all drivers)", "pickup_partner_id": None}
                    ] + [
                        {"id": d["id"], "name": f"{d['full_name']} (@{d['username']}) — {d.get('pickup_partner_name') or 'Direct'}", "pickup_partner_id": d.get("pickup_partner_id")}
                        for d in pickup_drivers
                    ]
                    chosen_dest = st.selectbox(
                        "Assign to Pickup Driver / Route",
                        options=dispatch_destinations,
                        format_func=lambda d: d["name"]
                    )
                    pickup_notes = st.text_area("Pickup Instructions / Notes", value="Fragile electronics, customer requires 1-hour pre-arrival call.")

                    assign_btn = st.form_submit_button("Assign Driver & Dispatch", use_container_width=True)

                    if assign_btn:
                        payload = {
                            "assigned_driver_id": chosen_dest["id"],
                            "pickup_partner_id": chosen_dest.get("pickup_partner_id"),
                            "notes": pickup_notes.strip()
                        }
                        try:
                            res = api_client.assign_pickup_partner(token, target_return["id"], payload)
                            dest_name = chosen_dest["name"]
                            st.session_state["partner_flash_msg"] = f"✅ Return **{res['id']}** dispatched to **{dest_name}**!"
                            st.query_params["tab"] = "🚚 Pickup Partners & Dispatch"
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to dispatch return: {e}")

            st.markdown("---")
            st.markdown("#### 🗑️ Remove Pickup Driver from Platform")
            if pickup_drivers:
                with st.form("delete_pickup_driver_form"):
                    driver_options = {
                        f"{d['username']} ({d['full_name']}) [ID: {d['id']}]": d
                        for d in pickup_drivers
                    }
                    driver_label = st.selectbox(
                        "Select Driver to Delete",
                        options=list(driver_options.keys()),
                        index=len(pickup_drivers) - 1
                    )
                    driver_to_delete = driver_options[driver_label]
                    confirm_del = st.checkbox("Confirm permanent removal of this driver account")
                    del_d_btn = st.form_submit_button("🗑️ Delete Driver from Platform", type="primary", use_container_width=True)

                    if del_d_btn:
                        if not confirm_del:
                            st.error("Please check the confirmation box before deleting.")
                        else:
                            try:
                                res = api_client.delete_user(token, driver_to_delete["id"])
                                st.session_state["partner_flash_msg"] = f"✅ {res.get('message', 'Driver removed successfully!')}"
                                st.query_params["tab"] = "🚚 Pickup Partners & Dispatch"
                                st.rerun()
                            except Exception as e:
                                st.error(f"Failed to delete driver: {e}")
            else:
                st.info("No pickup drivers available to delete.")

    # ==========================================
    # TAB 5: SUSTAINABILITY & CIRCULARITY
    # ==========================================
    with tabs[4]:
        render_sustainability_tab(token, user)

    # ==========================================
    # TAB 6: TRACEABILITY & AUDIT
    # ==========================================
    with tabs[5]:
        render_return_journey(token)
