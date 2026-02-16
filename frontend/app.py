import streamlit as st
import requests
import json
from datetime import datetime
import os
import platform
import uuid

st.set_page_config(page_title="Ghost Shell Pro • License Manager", page_icon="🔐", layout="wide")

# ─── CSS ────────────────────────────────────────────────────────────────
st.markdown("""<style>
    .stApp { background: #0e1117; color: #e0e0e0; }
    h1, h2, h3 { color: #00ff9d !important; }
    .section-card {
        background: #161b22;
        border: 1px solid #30363d;
        border-radius: 12px;
        padding: 1.8rem;
        margin: 1.2rem 0;
        box-shadow: 0 6px 20px rgba(0,0,0,0.45);
    }
    .stButton>button { border-radius: 8px; font-weight: 600; }
    .st-success { background: #1a3a2a; border-left: 5px solid #00ff9d; }
    .st-error   { background: #3a1a1f; border-left: 5px solid #ff4d4f; }
    div[data-testid="stMetricValue"] { color: #00ff9d; }
    .license-row { border-bottom: 1px solid #30363d; padding: 0.8rem 0; }
    .delete-btn  { background: #ff4d4f !important; color: white !important; }
</style>""", unsafe_allow_html=True)

# ─── CONFIG ─────────────────────────────────────────────────────────────
API_URL = os.getenv("API_URL", "http://localhost:8000").rstrip("/")
ADMIN_TOKEN_KEY = "admin_token_ghostshell"

# ─── HELPERS ────────────────────────────────────────────────────────────
def api_headers(token=None):
    if token:
        return {"Authorization": f"Bearer {token}"}
    return {}

def get_system_fingerprint():
    return {
        "machine_id": str(uuid.getnode()),
        "platform": platform.system(),
        "arch": platform.machine(),
        "ip": "unknown"
    }

# ─── PAGES / TABS ───────────────────────────────────────────────────────
def tab_activate():
    with st.container():
        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        st.subheader("Activate License")
        with st.form("activate"):
            key = st.text_input("License Key", placeholder="GSH-PRO-XXXX-XXXX-XXXX")
            if st.form_submit_button("Activate"):
                if not key.strip():
                    st.error("License key required")
                    st.stop()
                payload = {
                    "license_key": key.strip(),
                    "fingerprint": get_system_fingerprint(),
                    "timestamp": datetime.now().isoformat(),
                    "version": "1.0"
                }
                try:
                    r = requests.post(f"{API_URL}/activate", json=payload, timeout=15)
                    r.raise_for_status()
                    data = r.json()
                    if data["valid"]:
                        st.success("License activated!")
                        st.write(f"**Expires:** {data.get('expires_at', 'Never')}")
                        st.write(f"**Remaining validations:** {data.get('remaining_validations', '?')}")
                    else:
                        st.error(data.get("message", "Activation failed"))
                except Exception as e:
                    st.error(f"Connection error: {str(e)}")
        st.markdown("</div>", unsafe_allow_html=True)

def tab_validate():
    with st.container():
        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        st.subheader("Validate License")
        with st.form("validate"):
            key = st.text_input("License Key")
            if st.form_submit_button("Check"):
                if not key.strip():
                    st.error("Enter license key")
                    st.stop()
                payload = {
                    "license_key": key.strip(),
                    "timestamp": datetime.now().isoformat(),
                    "version": "1.0"
                }
                try:
                    r = requests.post(f"{API_URL}/validate", json=payload, timeout=12)
                    r.raise_for_status()
                    data = r.json()
                    if data["valid"]:
                        st.success("License is **VALID**")
                        st.write(f"Expires: {data.get('expires_at', 'No expiry')}")
                    else:
                        st.error(data.get("message", "Invalid / expired"))
                except Exception as e:
                    st.error(f"Error: {str(e)}")
        st.markdown("</div>", unsafe_allow_html=True)

def tab_licenses():
    with st.container():
        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        st.subheader("All Licenses (Admin)")

        token = st.session_state.get(ADMIN_TOKEN_KEY, "")
        if not token:
            token = st.text_input("Admin Token", type="password", key="list_token")
            if st.button("Authenticate"):
                st.session_state[ADMIN_TOKEN_KEY] = token
                st.rerun()
            st.stop()

        try:
            r = requests.get(f"{API_URL}/licenses", headers=api_headers(token), timeout=10)
            r.raise_for_status()
            data = r.json()
            licenses = data.get("licenses", [])

            if not licenses:
                st.info("No licenses found.")
                return

            for lic in licenses:
                with st.expander(f"{lic['license_key']}  •  {'Active' if lic['is_active'] else 'Inactive'}"):
                    col1, col2 = st.columns([2,1])
                    with col1:
                        st.write(f"**Created:** {lic.get('created_at','—')}")
                        st.write(f"**Expires:** {lic.get('expires_at','Never')}")
                        st.write(f"**Max activations:** {lic['max_instances']}")
                        st.write(f"**Used validations:** {lic['validation_count']}")
                        if lic.get('machine_fingerprint'):
                            st.caption(f"Bound machine: {lic['machine_fingerprint'][:16]}…")
                    with col2:
                        if st.button("🗑 Delete", key=f"del_{lic['license_key']}", help="Permanently deactivate"):
                            if st.session_state.get(f"confirm_del_{lic['license_key']}", False):
                                try:
                                    resp = requests.delete(
                                        f"{API_URL}/delete",
                                        json={"license_key": lic["license_key"]},
                                        headers=api_headers(token)
                                    )
                                    resp.raise_for_status()
                                    st.success("License deactivated")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Delete failed: {e}")
                            else:
                                st.session_state[f"confirm_del_{lic['license_key']}"] = True
                                st.warning("Click again to confirm deletion")
                                st.rerun()

        except requests.exceptions.RequestException as e:
            st.error(f"Cannot load licenses: {str(e)}")
            if "401" in str(e):
                del st.session_state[ADMIN_TOKEN_KEY]
                st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)

def tab_create():
    with st.container():
        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        st.subheader("Create New License (Admin)")
        token = st.text_input("Admin Token", type="password", key="create_token")
        if not token:
            st.stop()

        with st.form("create"):
            custom_key = st.text_input("Custom key (optional)")
            days = st.slider("Days valid", 7, 1095, 365)
            max_act = st.slider("Max activations", 1, 20, 2)
            if st.form_submit_button("Generate License"):
                payload = {
                    "license_key": custom_key.strip() or None,
                    "expires_in_days": days,
                    "max_instances": max_act
                }
                try:
                    r = requests.post(f"{API_URL}/create", json=payload, headers=api_headers(token))
                    r.raise_for_status()
                    data = r.json()
                    st.success("License created!")
                    st.code(data["license_key"])
                    st.write(f"Expires: {data['expires_at']}")
                    st.write(f"Max activations: {data['max_instances']}")
                except Exception as e:
                    st.error(f"Create failed: {str(e)}")
        st.markdown("</div>", unsafe_allow_html=True)

# ─── MAIN LAYOUT ────────────────────────────────────────────────────────
st.title("🔐 Ghost Shell Pro License Manager")

tabs = st.tabs(["Activate", "Validate", "Licenses", "Create"])

with tabs[0]: tab_activate()
with tabs[1]: tab_validate()
with tabs[2]: tab_licenses()
with tabs[3]: tab_create()

st.markdown("---")
st.caption("Ghost Shell Pro • License Server v1.1 • 2025–2026")
