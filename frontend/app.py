import streamlit as st
import requests
import json
import platform
import uuid
from datetime import datetime
import os

# Enable Streamlit config for full-screen and clean UI
st.set_page_config(page_title="Ghost Shell Pro License Manager v1.0", layout="wide")

# API Base URL from environment variable
API_URL = os.getenv("API_URL", "https://license-server-58kf.onrender.com")

# Helper function to get system info
def get_system_info():
    return {
        "machine_id": str(uuid.getnode()),  # Use MAC address as machine ID
        "platform": platform.system(),
        "arch": platform.machine(),
        "ip": "unknown"  # Placeholder for client IP (Streamlit can't access request headers directly)
    }

def activate_license():
    st.header("Activate License")
    with st.form(key='activate_form'):
        license_key = st.text_input("Enter License Key", placeholder="Enter license key")
        submit_button = st.form_submit_button("Activate License")

        if submit_button:
            if not license_key:
                st.error("License Key is required")
                return
            system_info = get_system_info()
            payload = {
                "license_key": license_key,
                "fingerprint": {
                    "machine_id": system_info["machine_id"],
                    "platform": system_info["platform"],
                    "arch": system_info["arch"],
                    "ip": system_info["ip"]
                },
                "timestamp": datetime.now().isoformat(),
                "version": "1.0.0"
            }
            with st.spinner("Activating..."):
                try:
                    response = requests.post(f"{API_URL}/activate",
                                          headers={"Content-Type": "application/json"},
                                          data=json.dumps(payload))
                    response.raise_for_status()
                    data = response.json()
                    if data.get("valid"):
                        st.success(f"Status: Valid\nMessage: {data.get('message')}\nMachine ID: {system_info['machine_id']}")
                        if data.get("expires_at"):
                            st.write(f"Expires: {datetime.fromisoformat(data['expires_at']).strftime('%Y-%m-%d %H:%M:%S')}")
                        if data.get("remaining_validations") is not None:
                            st.write(f"Remaining Validations: {data['remaining_validations']}")
                    else:
                        st.error(f"Status: Invalid\nMessage: {data.get('message')}")
                except requests.RequestException as e:
                    st.error(f"Failed to activate license: {str(e)}")

def validate_license():
    st.header("Validate License")
    with st.form(key='validate_form'):
        license_key = st.text_input("Enter License Key", placeholder="Enter license key")
        submit_button = st.form_submit_button("Validate License")

        if submit_button:
            if not license_key:
                st.error("License Key is required")
                return
            payload = {
                "license_key": license_key,
                "timestamp": datetime.now().isoformat(),
                "version": "1.0.0"
            }
            with st.spinner("Validating..."):
                try:
                    response = requests.post(f"{API_URL}/validate",
                                          headers={"Content-Type": "application/json"},
                                          data=json.dumps(payload))
                    response.raise_for_status()
                    data = response.json()
                    if data.get("valid"):
                        st.success(f"Status: Valid\nMessage: {data.get('message')}")
                        if data.get("expires_at"):
                            st.write(f"Expires: {datetime.fromisoformat(data['expires_at']).strftime('%Y-%m-%d %H:%M:%S')}")
                        if data.get("remaining_validations") is not None:
                            st.write(f"Remaining Validations: {data['remaining_validations']}")
                    else:
                        st.error(f"Status: Invalid\nMessage: {data.get('message')}")
                except requests.RequestException as e:
                    st.error(f"Failed to validate license: {str(e)}")

def create_license():
    st.header("Create License")
    with st.form(key='create_form'):
        admin_token = st.text_input("Enter Admin Token", placeholder="Enter admin token", type="password")
        license_key = st.text_input("Enter License Key (optional)", placeholder="Leave blank to auto-generate")
        expires_in_days = st.number_input("Expires In Days", min_value=1, value=365)
        max_instances = st.number_input("Max Instances", min_value=1, value=1)
        submit_button = st.form_submit_button("Create License")

        if submit_button:
            if not admin_token:
                st.error("Admin Token is required")
                return
            payload = {
                "licenseKey": license_key,
                "expiresInDays": expires_in_days,
                "maxInstances": max_instances
            }
            with st.spinner("Creating..."):
                try:
                    response = requests.post(f"{API_URL}/create",
                                          headers={
                                              "Content-Type": "application/json",
                                              "Authorization": f"Bearer {admin_token}"
                                          },
                                          data=json.dumps(payload))
                    response.raise_for_status()
                    data = response.json()
                    st.success(f"License Key: {data.get('license_key')}\n"
                              f"Expires: {datetime.fromisoformat(data['expires_at']).strftime('%Y-%m-%d %H:%M:%S')}\n"
                              f"Max Instances: {data.get('max_instances')}\n"
                              f"Message: {data.get('message')}")
                except requests.RequestException as e:
                    st.error(f"Failed to create license: {str(e)}")

def manage_license():
    st.header("Manage License")
    
    # Update License Form
    st.subheader("Update License")
    with st.form(key='update_form'):
        admin_token_update = st.text_input("Enter Admin Token (Update)", placeholder="Enter admin token", type="password")
        license_key_update = st.text_input("Enter License Key (Update)", placeholder="Enter license key")
        expires_in_days = st.number_input("Expires In Days", min_value=1, value=365)
        max_instances = st.number_input("Max Instances", min_value=1, value=1)
        submit_button_update = st.form_submit_button("Update License")

        if submit_button_update:
            if not admin_token_update or not license_key_update:
                st.error("Admin Token and License Key are required")
                return
            payload = {
                "license_key": license_key_update,
                "expires_in_days": expires_in_days,
                "max_instances": max_instances
            }
            with st.spinner("Updating..."):
                try:
                    response = requests.put(f"{API_URL}/update",
                                          headers={
                                              "Content-Type": "application/json",
                                              "Authorization": f"Bearer {admin_token_update}"
                                          },
                                          data=json.dumps(payload))
                    response.raise_for_status()
                    data = response.json()
                    st.success(f"License Key: {data.get('license_key')}\n"
                              f"Expires: {datetime.fromisoformat(data['expires_at']).strftime('%Y-%m-%d %H:%M:%S')}\n"
                              f"Max Instances: {data.get('max_instances')}\n"
                              f"Message: {data.get('message')}")
                except requests.RequestException as e:
                    st.error(f"Failed to update license: {str(e)}")

    # Delete License Form
    st.subheader("Delete License")
    with st.form(key='delete_form'):
        admin_token_delete = st.text_input("Enter Admin Token (Delete)", placeholder="Enter admin token", type="password")
        license_key_delete = st.text_input("Enter License Key (Delete)", placeholder="Enter license key")
        submit_button_delete = st.form_submit_button("Delete License")

        if submit_button_delete:
            if not admin_token_delete or not license_key_delete:
                st.error("Admin Token and License Key are required")
                return
            payload = {
                "license_key": license_key_delete
            }
            with st.spinner("Deleting..."):
                try:
                    response = requests.delete(f"{API_URL}/delete",
                                            headers={
                                                "Content-Type": "application/json",
                                                "Authorization": f"Bearer {admin_token_delete}"
                                            },
                                            data=json.dumps(payload))
                    response.raise_for_status()
                    data = response.json()
                    st.success(f"Message: {data.get('message', 'License deleted successfully')}")
                except requests.RequestException as e:
                    st.error(f"Failed to delete license: {str(e)}")

def stats():
    st.header("Statistics")
    with st.form(key='stats_form'):
        admin_token = st.text_input("Enter Admin Token", placeholder="Enter admin token", type="password")
        submit_button = st.form_submit_button("Fetch Statistics")

        if submit_button:
            if not admin_token:
                st.error("Admin Token is required")
                return
            with st.spinner("Loading..."):
                try:
                    response = requests.get(f"{API_URL}/stats",
                                      headers={"Authorization": f"Bearer {admin_token}"})
                    response.raise_for_status()
                    data = response.json()
                    st.success(f"Total Licenses: {data.get('total_licenses')}\n"
                              f"Active Licenses: {data.get('active_licenses')}\n"
                              f"Expired Licenses: {data.get('expired_licenses')}\n"
                              f"Recent Validations (7 days): {data.get('recent_validations')}\n"
                              f"Universal License Active: {'Yes' if data.get('universal_license_active') else 'No'}")
                except requests.RequestException as e:
                    st.error(f"Failed to fetch stats: {str(e)}")

def main():
    st.title("AlgoTrader License Manager")
    tabs = st.tabs(["Activate License", "Validate License", "Create License", "Manage License", "Statistics"])
    
    with tabs[0]:
        activate_license()
    with tabs[1]:
        validate_license()
    with tabs[2]:
        create_license()
    with tabs[3]:
        manage_license()
    with tabs[4]:
        stats()

if __name__ == "__main__":
    main()
