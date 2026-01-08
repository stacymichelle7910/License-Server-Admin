import streamlit as st
import requests
import platform
import uuid
from datetime import datetime
import os

st.set_page_config(page_title="GhostShell Pro License Manager v1.0", layout="wide")

# Update this if you deploy to a new Render instance
API_URL = os.getenv("API_URL", "https://license-server-58kf.onrender.com")

def get_system_info():
    return {
        "machine_id": str(uuid.getnode()),
        "platform": platform.system(),
        "arch": platform.machine(),
        "ip": "unknown"
    }

def handle_error(response):
    try:
        error = response.json()
        detail = error.get("detail", str(error))
    except:
        detail = response.text
    st.error(f"Server Error {response.status_code}: {detail}")

# Activate (binds machine)
def activate_license():
    st.header("Activate License (Binds This Machine)")
    with st.form("activate_form"):
        license_key = st.text_input("License Key", placeholder="GHOST-XXXX-XXXX-XXXX")
        submit = st.form_submit_button("Activate License")

        if submit:
            if not license_key.strip():
                st.error("Please enter a license key")
                return

            payload = {
                "license_key": license_key.strip(),
                "fingerprint": get_system_info(),
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "version": "1.0.0"
            }

            with st.spinner("Activating license..."):
                try:
                    r = requests.post(f"{API_URL}/activate", json=payload, timeout=15)
                    if r.status_code == 200:
                        data = r.json()
                        if data.get("valid"):
                            st.success("License Activated Successfully!")
                            st.write(f"**Message:** {data['message']}")
                            if data.get("expires_at"):
                                exp = data["expires_at"].replace("Z", "+00:00")
                                st.write(f"**Expires:** {datetime.fromisoformat(exp).strftime('%Y-%m-%d %H:%M UTC')}")
                            st.info(f"Bound to Machine ID: `{get_system_info()['machine_id']}`")
                        else:
                            st.error(f"Failed: {data.get('message')}")
                    else:
                        handle_error(r)
                except requests.exceptions.RequestException as e:
                    st.error(f"Connection failed: {e}")

# Validate only (no binding)
def validate_license():
    st.header("Validate License (No Binding)")
    with st.form("validate_form"):
        license_key = st.text_input("License Key", placeholder="GHOST-SHELL-UNIVERSAL-2026")
        submit = st.form_submit_button("Validate Only")

        if submit:
            if not license_key.strip():
                st.error("Please enter a license key")
                return

            payload = {
                "license_key": license_key.strip(),
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "version": "1.0.0"
            }

            with st.spinner("Validating..."):
                try:
                    r = requests.post(f"{API_URL}/validate", json=payload, timeout=15)
                    if r.status_code == 200:
                        data = r.json()
                        if data.get("valid"):
                            st.success("License is Valid!")
                            st.write(f"**Message:** {data['message']}")
                            if data.get("expires_at"):
                                exp = data["expires_at"].replace("Z", "+00:00")
                                st.write(f"**Expires:** {datetime.fromisoformat(exp).strftime('%Y-%m-%d %H:%M UTC')}")
                        else:
                            st.error(f"Invalid: {data.get('message')}")
                    else:
                        handle_error(r)
                except requests.exceptions.RequestException as e:
                    st.error(f"Connection failed: {e}")

# Admin: Create License
def create_license():
    st.header("Admin • Create New License")
    with st.form("create_form"):
        admin_token = st.text_input("Admin Token", type="password")
        custom_key = st.text_input("Custom License Key (optional)", placeholder="Leave blank = auto-generate")
        days = st.number_input("Valid for (days)", min_value=1, value=365)
        instances = st.number_input("Max Machines", min_value=1, value=1)
        submit = st.form_submit_button("Create License")

        if submit:
            if not admin_token:
                st.error("Admin token required")
                return

            payload = {
                "license_key": custom_key.strip() or None,
                "expires_in_days": int(days),
                "max_instances": int(instances)
            }

            with st.spinner("Creating license..."):
                try:
                    r = requests.post(
                        f"{API_URL}/create",
                        json=payload,
                        headers={"Authorization": f"Bearer {admin_token}"},
                        timeout=15
                    )
                    if r.status_code == 200:
                        data = r.json()
                        st.success("License Created!")
                        st.code(data["license_key"], language="text")
                        st.write(f"Expires: {data['expires_at'][:10]}")
                        st.write(f"Max instances: {data['max_instances']}")
                    else:
                        handle_error(r)
                except requests.exceptions.RequestException as e:
                    st.error(f"Request failed: {e}")

def main():
    st.title("GhostShell License Manager")
    st.caption("Test instantly with universal key → `GHOST-SHELL-UNIVERSAL-2026`")

    tab1, tab2, tab3 = st.tabs([
        "Activate (Bind Machine)",
        "Validate Only",
        "Admin: Create License"
    ])

    with tab1:
        activate_license()
    with tab2:
        validate_license()
    with tab3:
        create_license()

    st.sidebar.success("""
    **Universal Key (Works Forever)**  
    GHOST-SHELL-UNIVERSAL-2026 
    Use it anywhere — no activation needed.
    """)

    st.sidebar.info(f"Server: `{API_URL}`")

if __name__ == "__main__":
    main()
