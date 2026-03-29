import streamlit as st
import pandas as pd
from database import conn, c
from security import require_login

require_login()
user = st.session_state.user

st.title("📦 Catalogue")

with st.form("add_product"):
    name = st.text_input("Nom")
    price = st.number_input("Prix (FCFA)", min_value=0)
    stock = st.number_input("Stock", min_value=0)
    image = st.file_uploader("Image")

    if st.form_submit_button("Ajouter"):
        path = ""
        if image:
            path = f"images/{image.name}"
            with open(path, "wb") as f:
                f.write(image.getbuffer())
        c.execute(
            "INSERT INTO products (user_id, name, price, stock, image) VALUES (?, ?, ?, ?, ?)",
            (user[0], name, price, stock, path)
        )
        conn.commit()
        st.success("Produit ajouté ✅")

df = pd.read_sql(f"SELECT * FROM products WHERE user_id={user[0]}", conn)
st.dataframe(df)