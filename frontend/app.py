import streamlit as st

from frontend.api_client import api_client
from frontend.views.admin_dashboard import render_admin_dashboard
from frontend.views.inspector_dashboard import render_inspector_dashboard
from frontend.views.pickup_dashboard import render_pickup_dashboard
from frontend.views.retailer_dashboard import render_retailer_dashboard
from frontend.views.warehouse_dashboard import render_warehouse_dashboard

st.set_page_config(
    page_title="Sustainable Reverse Logistics Platform",
    page_icon="♻️",
    layout="wide"
)

# Initialize Session State
if "token" not in st.session_state:
    st.session_state.token = None
if "user" not in st.session_state:
    st.session_state.user = None
if "current_view" not in st.session_state:
    st.session_state.current_view = None

def handle_logout():
    st.session_state.token = None
    st.session_state.user = None
    st.session_state.current_view = None
    st.rerun()

# ----------------- LOGIN SCREEN -----------------
if not st.session_state.token or not st.session_state.user:
    st.title("♻️ Sustainable Reverse Logistics System")
    st.markdown("#### Enterprise Circular Returns & Lifecycle Recovery Platform")

    col_login, col_info = st.columns([1, 1])

    with col_login:
        st.subheader("Sign In")
        with st.form("login_form"):
            username_or_email = st.text_input("Username or Email")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Sign In", use_container_width=True)

            if submit:
                if not username_or_email.strip() or not password.strip():
                    st.error("Please enter both username/email and password.")
                else:
                    try:
                        login_res = api_client.login(username_or_email.strip(), password.strip())
                        token = login_res["access_token"]
                        user_profile = api_client.get_me(token)

                        st.session_state.token = token
                        st.session_state.user = user_profile

                        # Role-based redirection
                        role = user_profile["role"]
                        if role == "ADMIN":
                            st.session_state.current_view = "Admin Dashboard"
                        elif role == "WAREHOUSE":
                            st.session_state.current_view = "Warehouse Dashboard"
                        elif role == "INSPECTOR":
                            st.session_state.current_view = "Inspector Dashboard"
                        elif role == "RETAILER":
                            st.session_state.current_view = "Retailer Portal"
                        elif role == "PICKUP_PARTNER":
                            st.session_state.current_view = "Pickup Partner Portal"

                        st.success(f"Welcome, {user_profile['full_name']}!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Authentication failed: {e}")

    with col_info:
        st.subheader("🔑 Documented Demo Accounts")
        st.info(
            """
            | Role | Username | Password | Organization / Carrier | Scope |
            | :--- | :--- | :--- | :--- | :--- |
            | **Admin** | `admin` | `Admin123!` | Logistics Central | Full Platform Admin |
            | **Warehouse** | `warehouse` | `Warehouse123!` | Logistics Central | Intake & Restock |
            | **Inspector** | `inspector` | `Inspector123!` | Logistics Central | Inspect, Estimate, QC |
            | **Retailer 1** | `retailer_tech` | `Retailer123!` | TechRetail Direct | Org 1 Returns Only |
            | **Retailer 2** | `retailer_apex` | `Retailer123!` | Apex Mobile | Org 2 Returns Only |
            | **Pickup Driver 1** | `driver_eco` | `Pickup123!` | EcoLogix Express | Doorstep Pickup & Transit |
            | **Pickup Driver 2** | `driver_green` | `Pickup123!` | GreenRoute 3PL | Doorstep Pickup & Transit |
            """
        )
        st.caption("All accounts use secure bcrypt password hashing and RBAC authorization.")

# ----------------- AUTHENTICATED PORTAL -----------------
else:
    user = st.session_state.user
    role = user["role"]
    token = st.session_state.token

    with st.sidebar:
        st.title("♻️ Reverse Logistics")
        st.markdown(f"**User:** {user['full_name']}")
        st.markdown(f"**Username:** `{user['username']}`")
        st.markdown(f"**Role:** `{role}`")
        if user.get("organization_name"):
            st.markdown(f"**Organization:** {user['organization_name']}")
        if user.get("pickup_partner_name"):
            st.markdown(f"**Carrier:** {user['pickup_partner_name']}")

        st.markdown("---")

        # Navigation with Strict RBAC Route Protection
        available_views = []
        if role == "ADMIN":
            available_views = [
                "Admin Dashboard",
                "Warehouse Dashboard",
                "Inspector Dashboard",
                "Retailer Portal",
                "Pickup Partner Portal"
            ]
        elif role == "WAREHOUSE":
            available_views = ["Warehouse Dashboard"]
        elif role == "INSPECTOR":
            available_views = ["Inspector Dashboard"]
        elif role == "RETAILER":
            available_views = ["Retailer Portal"]
        elif role == "PICKUP_PARTNER":
            available_views = ["Pickup Partner Portal"]

        # Ensure current view matches allowed role
        if st.session_state.current_view not in available_views:
            st.session_state.current_view = available_views[0]

        if len(available_views) > 1:
            st.session_state.current_view = st.selectbox(
                "Navigation",
                options=available_views,
                index=available_views.index(st.session_state.current_view)
            )

        st.markdown("---")
        if st.button("🚪 Logout", use_container_width=True):
            handle_logout()

    # Route Enforcement & View Dispatch
    current_view = st.session_state.current_view

    if current_view == "Admin Dashboard":
        if role != "ADMIN":
            st.error("⛔ Access Denied: Admin role required.")
        else:
            render_admin_dashboard(token, user)

    elif current_view == "Warehouse Dashboard":
        if role not in ["WAREHOUSE", "ADMIN"]:
            st.error("⛔ Access Denied: Warehouse role required.")
        else:
            render_warehouse_dashboard(token, user)

    elif current_view == "Inspector Dashboard":
        if role not in ["INSPECTOR", "ADMIN"]:
            st.error("⛔ Access Denied: Inspector role required.")
        else:
            render_inspector_dashboard(token, user)

    elif current_view == "Retailer Portal":
        if role not in ["RETAILER", "ADMIN"]:
            st.error("⛔ Access Denied: Retailer role required.")
        else:
            render_retailer_dashboard(token, user)

    elif current_view == "Pickup Partner Portal":
        if role not in ["PICKUP_PARTNER", "ADMIN"]:
            st.error("⛔ Access Denied: Pickup Partner role required.")
        else:
            render_pickup_dashboard(token, user)
