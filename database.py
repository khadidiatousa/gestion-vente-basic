import streamlit as st
import sqlite3
import os
import hashlib
from fpdf import FPDF
from datetime import datetime

# --- CONFIGURATION PAGE ---
st.set_page_config(page_title="Gestion des vente", page_icon="✨")

# --- DATABASE ---
conn = sqlite3.connect("vendeur.db", check_same_thread=False)
conn.row_factory = sqlite3.Row
c = conn.cursor()

# --- TABLES ---
# USERS
c.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    password TEXT,
    is_admin INTEGER DEFAULT 0,
    must_change_password INTEGER DEFAULT 1
)
""")

# PRODUCTS
c.execute("""
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    name TEXT,
    description TEXT,
    price INTEGER,
    stock INTEGER,
    image TEXT
)
""")

# SALES
c.execute("""
CREATE TABLE IF NOT EXISTS sales (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    product_id INTEGER,
    product_name TEXT,
    quantity INTEGER,
    total INTEGER,
    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")
conn.commit()

# --- PASSWORD HASH ---
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# --- CREATE DEFAULT ADMIN ---
def create_default_admin():
    c.execute("SELECT * FROM users WHERE is_admin=1")
    admin = c.fetchone()
    if not admin:
        c.execute("INSERT INTO users (username, password, is_admin, must_change_password) VALUES (?,?,?,0)",
                  ("admin", hash_password("admin123"), 1))
        conn.commit()
create_default_admin()

# --- SESSION STATE ---
if "user" not in st.session_state: st.session_state.user = None
if "page" not in st.session_state: st.session_state.page = "Dashboard"

# --- LOGIN FUNCTION ---
def login_user(username, password):
    c.execute("SELECT * FROM users WHERE username=? AND password=?", (username, hash_password(password)))
    row = c.fetchone()
    return dict(row) if row else None


if not st.session_state.user:
    st.markdown("<h1 style='text-align:center;'>Gestion de Vente Simple </h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center;'>Votre solution bde gestion eauté </p>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        with st.container():
            st.subheader("🔐 Connexion")
            username = st.text_input("Identifiant", placeholder="Entrez votre identifiant")
            password = st.text_input("Mot de passe", type="password", placeholder="Entrez votre mot de passe")

            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                if st.button("Se connecter", use_container_width=True):
                    user = login_user(username, password)
                    if user:
                        st.session_state.user = user
                        st.rerun()
                    else:
                        st.error("❌ Identifiants incorrects")
            with col_btn2:
                if st.button("Mot de passe oublié ?", use_container_width=True):
                    st.info("Contactez l'administrateur pour réinitialiser votre mot de passe")

    st.stop()


# --- NAVIGATION HORIZONTALE ---
user = st.session_state.user
nav_items = ["Dashboard", "Catalogue", "Ventes", "Rapports"]
if user['is_admin']:
    nav_items.insert(1, "Utilisateurs")


# Navigation via selectbox pour state

page = st.session_state.page

# --- PAGE DASHBOARD ---
if page == "Dashboard":
    st.header("🏠 Tableau de bord")
    if user['is_admin']:
        st.info("Vous êtes admin, vous pouvez gérer utilisateurs, produits et ventes.")
    else:
        st.info("Vous êtes vendeur, vous pouvez gérer vos produits et ventes.")

# --- PAGE ADMIN UTILISATEURS ---
elif page == "Utilisateurs" and user['is_admin']:
    st.header("👥 Gestion des utilisateurs")
    with st.expander("➕ Créer un compte"):
        new_un = st.text_input("Nom d'utilisateur", key="new_un")
        new_pw = st.text_input("Mot de passe", type="password", key="new_pw")
        is_adm = st.checkbox("Admin", key="new_adm")
        if st.button("Enregistrer", key="create_user"):
            try:
                c.execute("INSERT INTO users (username, password, is_admin, must_change_password) VALUES (?,?,?,0)",
                          (new_un, hash_password(new_pw), int(is_adm)))
                conn.commit()
                st.success("Utilisateur créé !")
                st.experimental_rerun()
            except:
                st.error("Nom déjà utilisé")

    c.execute("SELECT * FROM users")
    for u in [dict(r) for r in c.fetchall()]:
        with st.container():
            st.markdown(f"<div class='card'>👤 {u['username']} | {'Admin' if u['is_admin'] else 'Vendeur'}", unsafe_allow_html=True)
            if u['username'] != "admin":
                if st.button("Supprimer", key=f"del_u_{u['id']}"):
                    c.execute("DELETE FROM users WHERE id=?", (u['id'],))
                    conn.commit()
                    st.experimental_rerun()

# --- PAGE CATALOGUE ---
elif page == "Catalogue":
    st.header("📦 Catalogue")
    with st.expander("➕ Ajouter produit"):
        n = st.text_input("Nom", key="prod_name")
        d = st.text_area("Description", key="prod_desc")
        pr = st.number_input("Prix", min_value=0, key="prod_price")
        stk = st.number_input("Stock", min_value=0, key="prod_stock")
        img = st.file_uploader("Image", type=["jpg","png","jpeg"], key="prod_img")
        if st.button("Ajouter produit", key="add_prod"):
            if n and img:
                if not os.path.exists("images"): os.makedirs("images")
                path = f"images/{img.name}"
                with open(path, "wb") as f: f.write(img.getbuffer())
                c.execute("INSERT INTO products (user_id, name, description, price, stock, image) VALUES (?,?,?,?,?,?)",
                          (user['id'], n, d, pr, stk, path))
                conn.commit()
                st.success("Produit ajouté !")
                st.experimental_rerun()

    c.execute("SELECT * FROM products WHERE user_id=?", (user['id'],))
    prods = [dict(r) for r in c.fetchall()]
    cols = st.columns(3)
    for i, p in enumerate(prods):
        with cols[i%3]:
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            st.image(p['image'], width=180)
            st.subheader(p['name'])
            st.write(f"{p['price']} FCFA | Stock: {p['stock']}")
            st.write(p['description'][:100] if p['description'] else "")
            if st.button("🗑️ Supprimer", key=f"del_p_{p['id']}"):
                c.execute("DELETE FROM products WHERE id=?", (p['id'],))
                conn.commit()
                st.experimental_rerun()
            st.markdown("</div>", unsafe_allow_html=True)

# --- PAGE VENTES ---
elif page == "Ventes":
    st.header("🛒 Ventes")
    c.execute("SELECT * FROM products WHERE user_id=? AND stock>0", (user['id'],))
    available = [dict(r) for r in c.fetchall()]
    if available:
        p_sel = st.selectbox("Produit", available, format_func=lambda x: f"{x['name']} ({x['stock']} dispo)")
        qty = st.number_input("Quantité", min_value=1, max_value=p_sel['stock'])
        if st.button("Valider vente", key="sale_btn"):
            total = p_sel['price'] * qty
            c.execute("INSERT INTO sales (user_id, product_id, product_name, quantity, total) VALUES (?,?,?,?,?)",
                      (user['id'], p_sel['id'], p_sel['name'], qty, total))
            c.execute("UPDATE products SET stock = stock - ? WHERE id=?", (qty, p_sel['id']))
            conn.commit()
            st.success("Vente enregistrée !")
            st.experimental_rerun()

    st.subheader("📋 Historique des ventes")
    c.execute("SELECT * FROM sales WHERE user_id=? ORDER BY date DESC", (user['id'],))
    for s in [dict(r) for r in c.fetchall()]:
        with st.container():
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            st.write(f"{s['product_name']} x{s['quantity']} = {s['total']} FCFA")
            st.write(f"Date: {s['date']}")
            if st.button("Annuler", key=f"rev_{s['id']}"):
                c.execute("UPDATE products SET stock = stock + ? WHERE id=?", (s['quantity'], s['product_id']))
                c.execute("DELETE FROM sales WHERE id=?", (s['id'],))
                conn.commit()
                st.experimental_rerun()
            st.markdown("</div>", unsafe_allow_html=True)

# --- PAGE RAPPORTS ---
elif page == "Rapports":
    st.header("📊 Rapports")
    c.execute("SELECT SUM(total) as ca, COUNT(*) as nb FROM sales WHERE user_id=?", (user['id'],))
    data = c.fetchone()
    st.metric("Chiffre d'Affaires Total", f"{data['ca'] or 0} FCFA")
    c.execute("SELECT product_name, quantity, total, date FROM sales WHERE user_id=?", (user['id'],))
    sales_list = [dict(r) for r in c.fetchall()]
    st.table(sales_list)