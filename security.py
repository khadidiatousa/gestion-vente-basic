import streamlit as st

def require_login():
    if "user" not in st.session_state or st.session_state.user is None:
        st.warning("🔐 Veuillez vous connecter")
        st.stop()

def require_admin():
    require_login()
    if st.session_state.user[3] == 0:
        st.error("⛔ Accès refusé (Admin uniquement)")
        st.stop()