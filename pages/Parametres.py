import streamlit as st
from security import require_login

require_login()
st.title("⚙️ Paramètres")
st.write("Paramètres utilisateur (à étendre)")