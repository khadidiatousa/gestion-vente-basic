import streamlit as st
import pandas as pd
from database import conn, c
from security import require_login

require_login()
user = st.session_state.user

st.title("💰 Ventes")

df = pd.read_sql(f"SELECT * FROM products WHERE user_id={user[0]}", conn)
if not df.empty:
    prod = st.selectbox("Produit", df["name"])
    qte = st.number_input("Quantité", min_value=1)
    prix = df[df["name"] == prod]["price"].values[0]
    total = prix * qte
    st.metric("Total", f"{total} FCFA")
    if st.button("Vendre"):
        c.execute(
            "INSERT INTO sales (user_id, product, quantity, total) VALUES (?, ?, ?, ?)",
            (user[0], prod, qte, total)
        )
        conn.commit()
        st.success("Vente enregistrée")

sales = pd.read_sql(f"SELECT * FROM sales WHERE user_id={user[0]}", conn)
st.dataframe(sales)
st.metric("Chiffre d'affaires", f"{sales['total'].sum()} FCFA")