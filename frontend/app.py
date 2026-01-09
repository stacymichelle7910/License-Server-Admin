import streamlit as st
import requests
import json
import platform
import uuid
from datetime import datetime
import os

# ========================= PAGE CONFIG & CUSTOM CSS =========================
st.set_page_config(
    page_title="Ghost Shell Pro License Manager v1.0",
    page_icon="🔒",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    .main {
        background: linear-gradient(135deg, #2d333b 0%, #363c44 100%);
        padding: 2rem 0;
    }
    h1, h2, h3 {
        color: #00ff9d !important;
        font-family: 'Segoe UI', sans-serif;
        font-weight: 600;
    }
    .stApp {
        background: linear-gradient(135deg, #0e1117 0%, #1a1f2e 100%);
        color: #e0e0e0;
    }
    .section-card {
        background-color: #161b22;
        border-radius: 16px;
        padding: 2rem;
        margin-bottom: 2rem;
        border: 1px solid #30363d;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
    }
    .stTextInput > div > div > input {
        background-color: #21262d;
        color: #e0e0e0;
        border: 1px solid #30363d;
        border-radius: 10px;
        padding: 0.8rem;
    }
    .stButton > button {
        border-radius: 10px;
        padding: 0.7rem 1.5rem;
        height: auto;
        width: 100%;
        font-weight: bold;
        transition: all 0.3s;
    }
    .stButton > button:hover {
        transform: translateY(-3px);
        box-shadow: 0 6px 16px rgba(255, 255, 255, 0.1);
    }
    /* Custom red delete button */
    button[kind="delete"] {
        background-color: #ff3b5a !important;
        color: white !important;
    }
    button[kind="delete"]:hover {
        background-color: #ff1e40 !important;
        box-shadow: 0 6px 16px rgba(255, 59, 90, 0.4) !important;
    }
    .stSuccess {
        background-color: #1a3a2a;
        border-left: 6px solid #00ff9d;
        border-radius: 8px;
    }
    .stError {
        background-color: #3a1a1f;
        border-left: 6px solid #ff3b5a;
        border-radius: 8px;
    }
    .stInfo {
        background-color: #1a2a3a;
        border-left: 6px solid #3399ff;
        border-radius: 8px;
    }
    .stTabs [data-baseweb="tab-list"] {
        background-color: #161b22;
        border-radius: 12px;
        padding: 8px;
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        color: #8b949e;
        font-size: 16px;
        font-weight: 600;
        padding: 12px 28px;
        border-radius: 10px;
    }
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        color: #00ff9d;
        background-color: #21262d;
        box-shadow: 0 4px 12px rgba(0, 255, 157, 0.2);
    }
    .footer {
        text-align: center;
        color: #555;
        margin-top: 4rem;
        padding: 1.5rem;
        font-size: 0.9rem;
    }
</style>
""", unsafe_allow_html=True)

# ========================= CONFIG =========================
API_URL = os.getenv("API_URL", "https://license-server-58kf.onrender.com")

def get_system_info():
    return {
        "machine_id": str(uuid.getnode()),
        "platform": platform.system(),
        "arch": platform.machine(),
        "ip": "unknown"
    }

# ========================= SECTIONS =========================
def activate_license():
    with st.container():
        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        st.header("🔑 Activate License")
        with st.form(key='activate_form', clear_on_submit=False):
            st.markdown("### Enter your license key to activate on this machine")
            license_key = st.text_input("License Key", placeholder="GSH-PRO-XXXX-XXXX-XXXX", label_visibility="collapsed")
            col1, col2 = st.columns([1, 5])
            with col1:
                submit = st.form_submit_button("Activate Now")
            if submit:
                if not license_key.strip():
                    st.error("⚠️ License key is required!")
                    return
                system_info = get_system_info()
                payload = {
                    "license_key": license_key.strip(),
                    "fingerprint": system_info,
                    "timestamp": datetime.now().isoformat(),
                    "version": "1.0.0"
                }
                with st.spinner("🔄 Activating license..."):
                    try:
                        response = requests.post(f"{API_URL}/activate", json=payload, timeout=20)
                        response.raise_for_status()
                        data = response.json()
                        if data.get("valid"):
                            st.success("✅ **License Activated Successfully!**")
                            st.info(f"**Message:** {data.get('message', 'Activated')}")
                            st.code(f"Machine ID: {system_info['machine_id']}", language=None)
                            if data.get("expires_at"):
                                exp = datetime.fromisoformat(data["expires_at"])
                                st.write(f"**Expires:** {exp.strftime('%B %d, %Y at %I:%M %p')}")
                            if data.get("remaining_validations") is not None:
                                st.write(f"**Remaining Activations:** {data['remaining_validations']}")
                        else:
                            st.error(f"❌ **Activation Failed**\n\n{data.get('message', 'Invalid license')}")
                    except requests.RequestException as e:
                        st.error(f"🌐 Connection error: {str(e)}")
        st.markdown("</div>", unsafe_allow_html=True)

def validate_license():
    with st.container():
        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        st.header("✅ Validate License")
        with st.form(key='validate_form'):
            st.markdown("### Check if your license is still valid")
            license_key = st.text_input("License Key", placeholder="Enter your license key", label_visibility="collapsed")
            col1, col2 = st.columns([1, 5])
            with col1:
                submit = st.form_submit_button("Validate Now")
            if submit:
                if not license_key.strip():
                    st.error("⚠️ License key is required!")
                    return
                payload = {
                    "license_key": license_key.strip(),
                    "timestamp": datetime.now().isoformat(),
                    "version": "1.0.0"
                }
                with st.spinner("🔄 Validating..."):
                    try:
                        response = requests.post(f"{API_URL}/validate", json=payload, timeout=20)
                        response.raise_for_status()
                        data = response.json()
                        if data.get("valid"):
                            st.success("✅ **License is Valid and Active!**")
                            st.info(data.get("message", "All good"))
                            if data.get("expires_at"):
                                exp = datetime.fromisoformat(data["expires_at"])
                                st.write(f"**Expires:** {exp.strftime('%B %d, %Y at %I:%M %p')}")
                            if data.get("remaining_validations") is not None:
                                st.write(f"**Remaining Validations:** {data['remaining_validations']}")
                        else:
                            st.error(f"❌ **License Invalid or Expired**\n\n{data.get('message')}")
                    except requests.RequestException as e:
                        st.error(f"🌐 Request failed: {str(e)}")
        st.markdown("</div>", unsafe_allow_html=True)

def create_license():
    with st.container():
        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        st.header("🆕 Create New License")
        with st.form(key='create_form'):
            st.markdown("### Admin-only: Generate a new license key")
            admin_token = st.text_input("Admin Token", type="password", placeholder="Required for creation")
            license_key = st.text_input("Custom License Key (optional)", placeholder="Leave blank for auto-generation")
            expires_in_days = st.slider("Validity Period (days)", min_value=1, max_value=1095, value=365, step=30)
            max_instances = st.slider("Maximum Allowed Activations", min_value=1, max_value=50, value=1)
            submit = st.form_submit_button("Create License")
            if submit:
                if not admin_token.strip():
                    st.error("🔑 Admin token is required!")
                    return
                payload = {
                    "licenseKey": license_key.strip() or None,
                    "expiresInDays": int(expires_in_days),
                    "maxInstances": int(max_instances)
                }
                with st.spinner("🔄 Creating new license..."):
                    try:
                        response = requests.post(f"{API_URL}/create", json=payload, headers={"Authorization": f"Bearer {admin_token.strip()}"})
                        response.raise_for_status()
                        data = response.json()
                        st.success("🎉 **License Created Successfully!**")
                        st.code(data.get('license_key'), language=None)
                        exp = datetime.fromisoformat(data['expires_at'])
                        st.write(f"**Expires:** {exp.strftime('%B %d, %Y')}")
                        st.write(f"**Max Instances:** {data.get('max_instances')}")
                        st.info(data.get('message', 'License ready for distribution'))
                    except requests.RequestException as e:
                        st.error(f"❌ Failed to create: {str(e)}")
        st.markdown("</div>", unsafe_allow_html=True)

def manage_license():
    with st.container():
        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        st.header("⚙️ Manage License")

        # Update Section
        st.subheader("🔄 Update Existing License")
        with st.form(key='update_form'):
            admin_token_update = st.text_input("Admin Token (Update)", type="password", placeholder="Required")
            license_key_update = st.text_input("License Key to Update", placeholder="Enter existing key")
            expires_in_days = st.slider("New Validity Period (days)", 1, 1095, 365, key="update_days")
            max_instances = st.slider("New Max Activations", 1, 50, 1, key="update_instances")
            submit_update = st.form_submit_button("Update License")
            if submit_update:
                if not admin_token_update.strip() or not license_key_update.strip():
                    st.error("🔑 Both admin token and license key are required!")
                    return
                payload = {
                    "license_key": license_key_update.strip(),
                    "expires_in_days": int(expires_in_days),
                    "max_instances": int(max_instances)
                }
                with st.spinner("🔄 Updating license..."):
                    try:
                        response = requests.put(f"{API_URL}/update", json=payload, headers={"Authorization": f"Bearer {admin_token_update.strip()}"})
                        response.raise_for_status()
                        data = response.json()
                        st.success("✅ **License Updated Successfully!**")
                        st.code(data.get('license_key'))
                        exp = datetime.fromisoformat(data['expires_at'])
                        st.write(f"**New Expiry:** {exp.strftime('%B %d, %Y')}")
                        st.write(f"**New Max Instances:** {data.get('max_instances')}")
                    except requests.RequestException as e:
                        st.error(f"❌ Update failed: {str(e)}")

        st.markdown("---")

        # Delete Section - FIXED: No type="danger" on form_submit_button
        st.subheader("🗑️ Delete License")
        with st.form(key='delete_form'):
            admin_token_delete = st.text_input("Admin Token (Delete)", type="password", placeholder="Required")
            license_key_delete = st.text_input("License Key to Delete", placeholder="Enter key to permanently remove")
            
            st.markdown("**⚠️ This action is permanent and cannot be undone.**")
            confirm = st.checkbox("I understand this will permanently delete the license")

            # Use regular st.button with custom CSS for red color
            delete_clicked = st.form_submit_button("Delete Permanently")

            if delete_clicked:
                if not confirm:
                    st.error("⚠️ You must confirm the deletion to proceed.")
                    return
                if not admin_token_delete.strip() or not license_key_delete.strip():
                    st.error("🔑 Both fields are required!")
                    return
                
                payload = {"license_key": license_key_delete.strip()}
                with st.spinner("🗑️ Deleting license..."):
                    try:
                        response = requests.delete(f"{API_URL}/delete", json=payload, headers={"Authorization": f"Bearer {admin_token_delete.strip()}"})
                        response.raise_for_status()
                        data = response.json()
                        st.success(f"🗑️ **License Deleted Permanently**\n\n{data.get('message', 'Successfully removed')}")
                    except requests.RequestException as e:
                        st.error(f"❌ Deletion failed: {str(e)}")
        
        # Apply red styling via custom button kind (via CSS)
        st.markdown('<button kind="delete">Delete Permanently</button>', unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

def stats():
    with st.container():
        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        st.header("📊 System Statistics")
        with st.form(key='stats_form'):
            st.markdown("### Admin-only: View license system overview")
            admin_token = st.text_input("Admin Token", type="password", placeholder="Required for stats access")
            submit = st.form_submit_button("Fetch Statistics")
            if submit:
                if not admin_token.strip():
                    st.error("🔑 Admin token required!")
                    return
                with st.spinner("📈 Loading statistics..."):
                    try:
                        response = requests.get(f"{API_URL}/stats", headers={"Authorization": f"Bearer {admin_token.strip()}"})
                        response.raise_for_status()
                        data = response.json()
                        st.success("📊 **License System Overview**")
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Total Licenses", data.get('total_licenses', 'N/A'))
                            st.metric("Active Licenses", data.get('active_licenses', 'N/A'))
                        with col2:
                            st.metric("Expired Licenses", data.get('expired_licenses', 'N/A'))
                            st.metric("Recent Validations (7d)", data.get('recent_validations', 'N/A'))
                        with col3:
                            universal = data.get('universal_license_active', False)
                            st.metric("Universal License", "🟢 Active" if universal else "🔴 Inactive")
                    except requests.RequestException as e:
                        st.error(f"❌ Failed to load stats: {str(e)}")
        st.markdown("</div>", unsafe_allow_html=True)

# ========================= MAIN =========================
def main():
    st.markdown("""
        <h1 style='text-align: center; margin-bottom: 0.5rem;'>🔒 Ghost Shell Pro</h1>
        <p style='text-align: center; color: #8b949e; font-size: 1.2rem; margin-bottom: 3rem;'>
            Professional License Management System • v1.0
        </p>
    """, unsafe_allow_html=True)
    
    tabs = st.tabs(["🔑 Activate", "✅ Validate", "🆕 Create", "⚙️ Manage", "📊 Statistics"])
    
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
    
    st.markdown("---")
    st.markdown("""
        <div class='footer'>
            Ghost Shell Pro License Manager v1.0<br>
            Secure • Reliable • Modern License Activation System
        </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
