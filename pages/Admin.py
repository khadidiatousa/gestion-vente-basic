import streamlit as st
import pandas as pd
from auth import create_user
from database import conn
from security import require_admin

require_admin()
user = st.session_state.user

st.title("👨‍💼 Admin Panel")

# Ajouter utilisateur
st.subheader("➕ Ajouter utilisateur")
username = st.text_input("Identifiant")
password = st.text_input("Mot de passe initial", type="password")
is_admin = st.checkbox("Admin", value=False)

if st.button("Créer utilisateur"):
    if create_user(username, password, int(is_admin)):
        st.success("Utilisateur créé ✅")
    else:
        st.error("Erreur ❌")

# Liste utilisateurs
st.subheader("📋 Utilisateurs")
df = pd.read_sql("SELECT id, username, is_admin FROM users", conn)
st.dataframe(df)