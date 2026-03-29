
import streamlit as st
import sqlite3
import os
import hashlib
from datetime import datetime

# --- CONFIG ---
st.set_page_config(page_title="Gestion des ventes", page_icon="✨")

# --- DB ---
conn = sqlite3.connect("vendeur.db", check_same_thread=False)
conn.row_factory = sqlite3.Row
c = conn.cursor()

# --- TABLES ---
c.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    password TEXT,
    is_admin INTEGER DEFAULT 0,
    must_change_password INTEGER DEFAULT 1
)
""")

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

# --- HASH ---
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# --- ADMIN PAR DEFAUT ---
def create_default_admin():
    c.execute("SELECT * FROM users WHERE is_admin=1")
    if not c.fetchone():
        c.execute(
            "INSERT INTO users (username, password, is_admin, must_change_password) VALUES (?,?,?,0)",
            ("admin", hash_password("admin123"), 1)
        )
        conn.commit()

create_default_admin()

# --- SESSION ---
if "user" not in st.session_state:
    st.session_state.user = None

if "force_password_change" not in st.session_state:
    st.session_state.force_password_change = False

if "page" not in st.session_state:
    st.session_state.page = "Dashboard"

# --- LOGIN ---
def login_user(username, password):
    c.execute("SELECT * FROM users WHERE username=?", (username,))
    user = c.fetchone()

    if user and user["password"] == hash_password(password):
        return dict(user)
    return None


# --- LOGIN PAGE ---
if not st.session_state.user:
    st.title("🔐 Connexion")

    username = st.text_input("Identifiant")
    password = st.text_input("Mot de passe", type="password")

    if st.button("Se connecter"):
        user = login_user(username, password)

        if user:
            st.session_state.user = user
            st.session_state.force_password_change = user["must_change_password"]
            st.rerun()
        else:
            st.error("❌ Identifiants incorrects")

    st.stop()

# --- FORCE PASSWORD CHANGE ---
if st.session_state.force_password_change:
    st.title("🔐 Changement obligatoire du mot de passe")

    new_pw = st.text_input("Nouveau mot de passe", type="password")
    confirm_pw = st.text_input("Confirmer le mot de passe", type="password")

    if st.button("Changer mot de passe"):
        if len(new_pw) < 8:
            st.error("❌ Minimum 8 caractères")
        elif new_pw != confirm_pw:
            st.error("❌ Les mots de passe ne correspondent pas")
        else:
            c.execute(
                "UPDATE users SET password=?, must_change_password=0 WHERE id=?",
                (hash_password(new_pw), st.session_state.user["id"])
            )
            conn.commit()

            st.success("✅ Mot de passe changé")

            st.session_state.user["must_change_password"] = 0
            st.session_state.force_password_change = False
            st.rerun()

    st.stop()

# --- USER ---
user = st.session_state.user

# --- NAVIGATION ---
menu = ["Dashboard", "Catalogue", "Ventes", "Rapports","Parametres"]
if user["is_admin"]:
    menu.insert(1, "Utilisateurs")

page = st.sidebar.selectbox("Menu", menu)

# --- DASHBOARD ---
if page == "Dashboard":
    st.header("🏠 Tableau de bord")

    if user["is_admin"]:
        st.success("Admin connecté")
    else:
        st.info("Vendeur connecté")

# --- UTILISATEURS ---
elif page == "Utilisateurs" and user["is_admin"]:
    st.header("👥 Utilisateurs")

    with st.expander("➕ Créer utilisateur"):
        new_un = st.text_input("Username")
        new_pw = st.text_input("Mot de passe", type="password")
        is_admin = st.checkbox("Admin")

        if st.button("Créer"):
            if len(new_pw) < 8:
                st.error("❌ Mot de passe ≥ 8 caractères")
            else:
                try:
                    c.execute(
                        "INSERT INTO users (username, password, is_admin, must_change_password) VALUES (?,?,?,1)",
                        (new_un, hash_password(new_pw), int(is_admin))
                    )
                    conn.commit()
                    st.success("Utilisateur créé")
                    st.rerun()
                except:
                    st.error("Nom déjà utilisé")

    c.execute("SELECT * FROM users")
    for u in c.fetchall():
        st.write(f"{u['username']} - {'Admin' if u['is_admin'] else 'Vendeur'}")

        if u["username"] != "admin":
            if st.button("Supprimer", key=f"del_{u['id']}"):
                c.execute("DELETE FROM users WHERE id=?", (u["id"],))
                conn.commit()
                st.rerun()

# --- CATALOGUE ---
elif page == "Catalogue":
    st.header("📦 Catalogue")

    with st.expander("➕ Ajouter produit"):
        name = st.text_input("Nom")
        desc = st.text_area("Description")
        price = st.number_input("Prix", min_value=0)
        stock = st.number_input("Stock", min_value=0)
        img = st.file_uploader("Image", type=["jpg", "png"])

        if st.button("Ajouter"):
            if name and img:
                os.makedirs("images", exist_ok=True)
                path = f"images/{img.name}"

                with open(path, "wb") as f:
                    f.write(img.getbuffer())

                c.execute(
                    "INSERT INTO products (user_id, name, description, price, stock, image) VALUES (?,?,?,?,?,?)",
                    (user["id"], name, desc, price, stock, path)
                )
                conn.commit()
                st.success("Produit ajouté")
                st.rerun()

    c.execute("SELECT * FROM products WHERE user_id=?", (user["id"],))
    for p in c.fetchall():
        st.image(p["image"], width=150)
        st.write(f"{p['name']} - {p['price']} FCFA (Stock: {p['stock']})")

        if st.button("Supprimer", key=f"prod_{p['id']}"):
            c.execute("DELETE FROM products WHERE id=?", (p["id"],))
            conn.commit()
            st.rerun()

# --- VENTES ---
elif page == "Ventes":
    st.header("🛒 Vente")

    c.execute("SELECT * FROM products WHERE user_id=? AND stock>0", (user["id"],))
    prods = c.fetchall()

    if prods:
        prod = st.selectbox("Produit", prods, format_func=lambda x: x["name"])
        qty = st.number_input("Quantité", min_value=1, max_value=prod["stock"])

        if st.button("Valider"):
            total = prod["price"] * qty

            c.execute(
                "INSERT INTO sales (user_id, product_id, product_name, quantity, total) VALUES (?,?,?,?,?)",
                (user["id"], prod["id"], prod["name"], qty, total)
            )

            c.execute(
                "UPDATE products SET stock=stock-? WHERE id=?",
                (qty, prod["id"])
            )

            conn.commit()
            st.success("Vente enregistrée")
            st.rerun()

# --- RAPPORTS ---
elif page == "Rapports":
    st.header("📊 Rapports")

    c.execute("SELECT SUM(total) as ca FROM sales WHERE user_id=?", (user["id"],))
    ca = c.fetchone()["ca"] or 0

    st.metric("Chiffre d'affaires", f"{ca} FCFA")

    c.execute("SELECT * FROM sales WHERE user_id=?", (user["id"],))
    st.dataframe(c.fetchall())

# --- PAGE PARAMÈTRES ---
if page == "Paramètres":
    st.header("⚙️ Paramètres")

    conn = get_db_connection()
    c = conn.cursor()

    # 🔐 Changement de mot de passe
    st.subheader("🔐 Changer le mot de passe")
    with st.form("change_password_form"):
        old_pwd = st.text_input("Mot de passe actuel", type="password")
        new_pwd = st.text_input("Nouveau mot de passe", type="password")
        confirm_pwd = st.text_input("Confirmer le nouveau mot de passe", type="password")
        submit_pwd = st.form_submit_button("Mettre à jour le mot de passe")

        if submit_pwd:
            if len(new_pwd) < 8:
                st.error("❌ Le mot de passe doit contenir au moins 8 caractères")
            elif new_pwd != confirm_pwd:
                st.error("❌ Les mots de passe ne correspondent pas")
            else:
                c.execute("SELECT password FROM users WHERE id=?", (user['id'],))
                current_hashed = c.fetchone()["password"]
                if hash_password(old_pwd) == current_hashed:
                    c.execute("UPDATE users SET password=?, must_change_password=0 WHERE id=?",
                              (hash_password(new_pwd), user['id']))
                    conn.commit()
                    st.success("✅ Mot de passe mis à jour avec succès")
                    st.session_state.user["must_change_password"] = 0
                else:
                    st.error("❌ Mot de passe actuel incorrect")

    # 🏢 Nom de l'entreprise / SaaS
    st.subheader("🏢 Informations de l'entreprise")
    entreprise = st.text_input("Nom de l'entreprise", value=user.get("entreprise", ""))

    if st.button("Sauvegarder les informations de l'entreprise"):
        c.execute("UPDATE users SET entreprise=? WHERE id=?", (entreprise, user['id']))
        conn.commit()
        st.success("✅ Informations de l'entreprise mises à jour")
        st.session_state.user["entreprise"] = entreprise

    # 🔹 Logo
    st.subheader("Logo de l'entreprise")
    logo_file = st.file_uploader("Importer un logo (jpg/png)", type=["jpg", "jpeg", "png"])
    if logo_file:
        os.makedirs("logos", exist_ok=True)
        logo_path = f"logos/{user['id']}_{logo_file.name}"
        with open(logo_path, "wb") as f:
            f.write(logo_file.getbuffer())

        c.execute("UPDATE users SET logo=? WHERE id=?", (logo_path, user['id']))
        conn.commit()
        st.success("✅ Logo mis à jour")
        st.session_state.user["logo"] = logo_path

    conn.close()