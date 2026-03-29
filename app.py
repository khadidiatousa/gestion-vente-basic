# app.py
import io
import os
import hashlib
from datetime import datetime

import streamlit as st
import pandas as pd
import plotly.express as px
from PIL import Image
from fpdf import FPDF
import psycopg2
from psycopg2.extras import RealDictCursor

from database import login_user  # Assurez-vous que database.py existe avec login_user()


# --- CONFIGURATION PAGE ---
st.set_page_config(
    page_title="Glow Essentials - Admin",
    layout="wide",
    page_icon="✨",
    initial_sidebar_state="collapsed"
)


# 🔹 Fonction de nettoyage texte
def safe_text(text):
    if not text:
        return ""
    return (
        str(text)
        .replace("•", "-")
        .replace("–", "-")
        .replace("’", "'")
        .replace("à", "a")
        .replace("é", "e")
        .replace("è", "e")
        .replace("ê", "e")
        .replace("ô", "o")
        .encode("latin-1", "replace")
        .decode("latin-1")
    )


from fpdf import FPDF
import os

# --- FONCTION DE SÉCURISATION DU TEXTE ---


def safe_text(text):
    return str(text) if text else ""

class PDF(FPDF):
    def __init__(self, entreprise_name):
        super().__init__()
        self.entreprise_name = entreprise_name

    def header(self):
        self.set_font('Arial', 'B', 16)
        self.cell(0, 10, "GLOW ESSENTIALS", 0, 1, 'C')
        self.set_font('Arial', 'I', 12)
        self.cell(0, 8, f"Entreprise: {self.entreprise_name}", 0, 1, 'C')
        self.set_font('Arial', 'I', 10)
        self.cell(0, 5, "Catalogue de produits", 0, 1, 'C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f"Page {self.page_no()}", 0, 0, 'C')


def generate_catalog_pdf(products, user_name, entreprise_name):
    pdf = PDF(entreprise_name)
    pdf.add_page()
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(0, 10, f"Vendeur: {user_name}", 0, 1)
    pdf.ln(5)

    for product in products:
        y_before = pdf.get_y()

        # Construction du chemin absolu et remplacement des espaces
        image_file = product.get('image', '')
        image_path = os.path.join(os.getcwd(), image_file) if image_file else ""
        if image_path and os.path.exists(image_path):
            try:
                # Remplacer les espaces pour Windows
                pdf.image(image_path.replace("\\", "/"), x=10, y=y_before, w=35)
                pdf.set_xy(50, y_before)
            except Exception as e:
                print("Erreur image:", e)
                pdf.set_x(10)
        else:
            pdf.set_x(10)

        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 6, safe_text(product['name']), 0, 1)
        pdf.set_x(50 if image_path and os.path.exists(image_path) else 10)
        pdf.set_font('Arial', '', 11)
        pdf.cell(0, 5, f"Prix: {product['price']} FCFA", 0, 1)
        pdf.set_x(50 if image_path and os.path.exists(image_path) else 10)
        pdf.cell(0, 5, f"Stock: {product['stock']}", 0, 1)
        if product.get("description"):
            pdf.set_x(50 if image_path and os.path.exists(image_path) else 10)
            pdf.multi_cell(0, 5, safe_text(product["description"]))

        y_after = pdf.get_y()
        pdf.set_y(max(y_after, y_before + 40))
        pdf.ln(3)
        pdf.set_draw_color(200, 200, 200)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(5)

        if pdf.get_y() > 260:
            pdf.add_page()

    return pdf

# --- BASE DE DONNÉES ---
DB_URL = "postgresql://postgres.tukybtlafsdgvyemawlv:12345Khadidiatou@aws-1-eu-central-1.pooler.supabase.com:6543/postgres"


def get_db_connection():
    conn = psycopg2.connect(DB_URL)
    return conn, conn.cursor(cursor_factory=RealDictCursor)


def init_database():
    conn, c = get_db_connection()

    # Table users
    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        username TEXT UNIQUE,
        password TEXT,
        is_admin INTEGER DEFAULT 0,
        must_change_password INTEGER DEFAULT 1,
        entreprise TEXT,
        logo TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Table products
    c.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES users(id),
        name TEXT,
        description TEXT,
        price INTEGER,
        stock INTEGER,
        image TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Table sales
    c.execute("""
    CREATE TABLE IF NOT EXISTS sales (
        id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES users(id),
        product_id INTEGER REFERENCES products(id),
        product_name TEXT,
        quantity INTEGER,
        total INTEGER,
        date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Création admin par défaut si pas existant
    c.execute("SELECT * FROM users WHERE is_admin=1")
    if not c.fetchone():
        c.execute(
            "INSERT INTO users (username, password, is_admin, must_change_password) VALUES (%s,%s,%s,%s)",
            ("admin", hash_password("admin123"), 1, 0)
        )

    conn.commit()
    c.close()
    conn.close()


# --- HASH PASSWORD ---
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


# --- UTILITAIRES ---
def logout():
    st.session_state.clear()
    st.rerun()


def format_price(price):
    return f"{price:,.0f} FCFA"


# --- SESSION STATE ---
if "user" not in st.session_state:
    st.session_state.user = None
if "page" not in st.session_state:
    st.session_state.page = "Dashboard"
if "notifications" not in st.session_state:
    st.session_state.notifications = []

# Init DB
init_database()


# --- LOGIN SCREEN ---
if not st.session_state.user:
    st.markdown("<h1 style='text-align:center;'>Gestion de Vente Simple </h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center;'>Votre solution de gestion complète</p>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.subheader("🔐 Connexion")
        username = st.text_input("Identifiant")
        password = st.text_input("Mot de passe", type="password")
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("Se connecter"):
                user = login_user(username, password)
                if user:
                    st.session_state.user = user
                    st.session_state.notifications.append({"type": "success", "message": f"Bienvenue {user['username']} !"})
                    st.rerun()
                else:
                    st.error("❌ Identifiants incorrects")
        with col_btn2:
            if st.button("Mot de passe oublié ?"):
                st.info("Contactez l'administrateur pour réinitialiser votre mot de passe")
    st.stop()


# --- UTILISATEUR CONNECTÉ ---
user = st.session_state.user

# --- HEADER ---
col_logo, col_user, col_logout = st.columns([2, 1, 1])
with col_logo:
    st.markdown("<h1 style='margin:0;'>Gestion de Vente</h1>", unsafe_allow_html=True)
with col_user:
    st.markdown(f"<div style='text-align:right;'>👤 {user['username']}<br><span style='font-size:12px;'>{'Administrateur' if user['is_admin'] else 'Vendeur'}</span></div>", unsafe_allow_html=True)
with col_logout:
    if st.button("🚪 Déconnexion"):
        logout()
st.markdown("---")


# --- NAVIGATION ---
nav_items = [
    {"name": "Dashboard", "icon": "📊", "admin_only": False},
    {"name": "Catalogue", "icon": "📦", "admin_only": False},
    {"name": "Ventes", "icon": "🛒", "admin_only": False},
    {"name": "Rapports", "icon": "📈", "admin_only": False},
    {"name": "Paramètres", "icon": "⚙️", "admin_only": False}
]
if user['is_admin']:
    nav_items.insert(1, {"name": "Utilisateurs", "icon": "👥", "admin_only": True})

st.markdown('<div style="margin:20px 0;">', unsafe_allow_html=True)
nav_cols = st.columns(len(nav_items))
for idx, item in enumerate(nav_items):
    with nav_cols[idx]:
        if st.button(f"{item['icon']} {item['name']}", use_container_width=True):
            st.session_state.page = item['name']
            st.rerun()
st.markdown('</div>', unsafe_allow_html=True)

page = st.session_state.page

# ================== PAGES ==================
# --- DASHBOARD ---
if page == "Dashboard":
    st.header("📊 Tableau de bord")

    conn, c = get_db_connection()

    # Statistiques
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        c.execute("SELECT COUNT(*) as count FROM products WHERE user_id=%s", (user['id'],))
        products_count = c.fetchone()['count']
        st.metric("Produits en stock", products_count)

    with col2:
        c.execute("SELECT SUM(stock) as total_stock FROM products WHERE user_id=%s", (user['id'],))
        total_stock = c.fetchone()['total_stock'] or 0
        st.metric("Unités totales", total_stock)

    with col3:
        c.execute("SELECT SUM(total) as ca FROM sales WHERE user_id=%s", (user['id'],))
        total_ca = c.fetchone()['ca'] or 0
        st.metric("Chiffre d'affaires", format_price(total_ca))

    with col4:
        c.execute("SELECT COUNT(*) as count FROM sales WHERE user_id=%s", (user['id'],))
        sales_count = c.fetchone()['count'] or 0
        st.metric("Ventes réalisées", sales_count)

    # Dernières ventes
    st.markdown("---")
    st.subheader("🕒 Dernières ventes")
    c.execute("""
        SELECT * FROM sales 
        WHERE user_id=%s 
        ORDER BY date DESC 
        LIMIT 5
    """, (user['id'],))

    recent_sales = [dict(r) for r in c.fetchall()]
    if recent_sales:
        for sale in recent_sales:
            with st.container():
                col1, col2, col3 = st.columns([2, 1, 1])
                with col1:
                    st.write(f"**{sale['product_name']}**")
                with col2:
                    st.write(f"x{sale['quantity']} unités")
                with col3:
                    st.write(format_price(sale['total']))
                st.markdown("<hr style='margin: 5px 0;'>", unsafe_allow_html=True)
    else:
        st.info("Aucune vente récente")

    conn.close()

# --- UTILISATEURS (ADMIN) ---
elif page == "Utilisateurs":
    st.header("👥 Gestion des utilisateurs")
    conn, c = get_db_connection()

    # Formulaire pour ajouter un utilisateur
    with st.expander("➕ Ajouter un utilisateur"):
        new_username = st.text_input("Nom d'utilisateur")
        new_password = st.text_input("Mot de passe", type="password")
        new_role = st.selectbox("Rôle", ["Vendeur", "Admin"])
        if st.button("Ajouter utilisateur"):
            if new_username and new_password:
                c.execute(
                    "INSERT INTO users (username, password, is_admin) VALUES (%s, %s, %s)",
                    (new_username, hash_password(new_password), int(new_role == "Admin"))
                )
                conn.commit()
                st.success(f"Utilisateur {new_username} ajouté.")
            else:
                st.error("Tous les champs sont obligatoires.")

    # Liste des utilisateurs existants
    c.execute("SELECT * FROM users ORDER BY id DESC")
    users = c.fetchall()
    for u in users:
        cols = st.columns([4, 2, 2])
        with cols[0]:
            st.write(f"{u['id']}. {u['username']} | {'Admin' if u['is_admin'] else 'Vendeur'}")
        with cols[1]:
            if st.button(f"Modifier {u['id']}", key=f"edit_user_{u['id']}"):
                new_name = st.text_input("Nouveau nom", value=u['username'], key=f"name_{u['id']}")
                new_pass = st.text_input("Nouveau mot de passe", type="password", key=f"pass_{u['id']}")
                new_is_admin = st.checkbox("Admin ?", value=u['is_admin'], key=f"role_{u['id']}")
                if st.button(f"Enregistrer {u['id']}", key=f"save_{u['id']}"):
                    update_query = "UPDATE users SET username=%s, is_admin=%s"
                    params = [new_name, new_is_admin]
                    if new_pass:
                        update_query += ", password=%s"
                        params.append(hash_password(new_pass))
                    update_query += " WHERE id=%s"
                    params.append(u['id'])
                    c.execute(update_query, tuple(params))
                    conn.commit()
                    st.success("Utilisateur mis à jour")
        with cols[2]:
            if st.button(f"Supprimer {u['id']}", key=f"del_user_{u['id']}"):
                c.execute("DELETE FROM users WHERE id=%s", (u['id'],))
                conn.commit()
                st.warning(f"Utilisateur {u['username']} supprimé")

    conn.close()

# --- CATALOGUE ---
elif page == "Catalogue":
    st.header("📦 Catalogue de produits")
    conn, c = get_db_connection()

    # --- AJOUTER UN PRODUIT ---
    with st.expander("➕ Ajouter un produit"):
        name = st.text_input("Nom du produit", key="add_name")
        desc = st.text_area("Description", key="add_desc")
        price = st.number_input("Prix", min_value=0.0, step=0.01, key="add_price")
        stock = st.number_input("Stock", min_value=0, step=1, key="add_stock")
        img_file = st.file_uploader("Image", type=["png", "jpg", "jpeg"], key="add_img")

        if st.button("Ajouter produit"):
            img_path = None
            if img_file:
                os.makedirs("images", exist_ok=True)
                img_path = f"images/{name}_{img_file.name}"
                with open(img_path, "wb") as f:
                    f.write(img_file.getbuffer())
            c.execute(
                "INSERT INTO products (user_id, name, description, price, stock, image) VALUES (%s,%s,%s,%s,%s,%s)",
                (user['id'], name, desc, price, stock, img_path)
            )
            conn.commit()
            st.success(f"Produit {name} ajouté.")

    # --- AFFICHAGE DES PRODUITS ---
    c.execute("SELECT * FROM products WHERE user_id=%s ORDER BY id DESC", (user['id'],))
    products = c.fetchall()

    # --- GÉNÉRER PDF DU CATALOGUE ---
    if st.button("📄 Générer PDF du catalogue"):
        from fpdf import FPDF

        class PDF(FPDF):
            def header(self):
                self.set_font("Arial", "B", 16)
                self.cell(0, 10, f"Catalogue - {user['username']}", 0, 1, "C")
                entreprise = user.get('entreprise', '')
                if entreprise:
                    self.set_font("Arial", "I", 12)
                    self.cell(0, 8, f"Entreprise: {entreprise}", 0, 1, "C")
                self.ln(5)

            def footer(self):
                self.set_y(-15)
                self.set_font("Arial", "I", 8)
                self.cell(0, 10, f"Page {self.page_no()}", 0, 0, "C")

        pdf = PDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)

        for p in products:
            y_before = pdf.get_y()
            img_path = p.get('image', '')
            if img_path and os.path.exists(img_path):
                try:
                    pdf.image(img_path.replace("\\", "/"), x=10, y=y_before, w=40)
                    pdf.set_xy(55, y_before)
                except Exception as e:
                    pdf.set_x(10)
            else:
                pdf.set_x(10)

            pdf.set_font("Arial", "B", 12)
            pdf.cell(0, 6, p['name'], ln=True)
            pdf.set_x(55 if img_path and os.path.exists(img_path) else 10)
            pdf.set_font("Arial", "", 10)
            pdf.cell(0, 5, f"Prix: {p['price']} FCFA", ln=True)
            pdf.set_x(55 if img_path and os.path.exists(img_path) else 10)
            pdf.cell(0, 5, f"Stock: {p['stock']}", ln=True)
            if p.get("description"):
                pdf.set_x(55 if img_path and os.path.exists(img_path) else 10)
                pdf.multi_cell(0, 5, p.get("description", ""))

            y_after = pdf.get_y()
            pdf.set_y(max(y_after, y_before + 45))
            pdf.ln(3)
            pdf.set_draw_color(200, 200, 200)
            pdf.line(10, pdf.get_y(), 200, pdf.get_y())
            pdf.ln(5)

            if pdf.get_y() > 260:
                pdf.add_page()

        pdf_path = f"catalogue_{user['username']}.pdf"
        pdf.output(pdf_path)
        with open(pdf_path, "rb") as f:
            st.download_button("Télécharger PDF", f, file_name=pdf_path)
        os.remove(pdf_path)

    # --- LISTE DES PRODUITS EXISTANTS ---
    for p in products:
        cols = st.columns([1, 3, 2])
        with cols[0]:
            if p.get('image') and os.path.exists(p['image']):
                st.image(p['image'], width=80)
        with cols[1]:
            st.subheader(p['name'])
            st.write(p.get('description', ''))
            st.write(f"Prix: {p['price']} | Stock: {p['stock']}")
        with cols[2]:
            # Modifier un produit
            if st.button(f"Modifier {p['id']}", key=f"edit_{p['id']}"):
                new_name = st.text_input("Nom", value=p['name'], key=f"name_{p['id']}")
                new_desc = st.text_area("Description", value=p.get('description', ''), key=f"desc_{p['id']}")
                new_price = st.number_input("Prix", min_value=0.0, value=p['price'], step=0.01, key=f"price_{p['id']}")
                new_stock = st.number_input("Stock", min_value=0, value=p['stock'], step=1, key=f"stock_{p['id']}")
                new_img_file = st.file_uploader("Nouvelle image", type=["png", "jpg", "jpeg"], key=f"img_{p['id']}")
                if st.button(f"Enregistrer {p['id']}", key=f"save_{p['id']}"):
                    img_path = p.get('image')
                    if new_img_file:
                        os.makedirs("images", exist_ok=True)
                        img_path = f"images/{new_name}_{new_img_file.name}"
                        with open(img_path, "wb") as f:
                            f.write(new_img_file.getbuffer())
                    c.execute(
                        "UPDATE products SET name=%s, description=%s, price=%s, stock=%s, image=%s WHERE id=%s",
                        (new_name, new_desc, new_price, new_stock, img_path, p['id'])
                    )
                    conn.commit()
                    st.success("Produit mis à jour")

            # Supprimer un produit
            if st.button(f"Supprimer {p['id']}", key=f"del_{p['id']}"):
                if p.get('image') and os.path.exists(p['image']):
                    os.remove(p['image'])
                c.execute("DELETE FROM products WHERE id=%s", (p['id'],))
                conn.commit()
                st.warning(f"Produit {p['name']} supprimé")

    conn.close()

# --- VENTES ---
elif page == "Ventes":
    st.header("🛒 Enregistrement des ventes")

    conn, c = get_db_connection()

    tab1, tab2 = st.tabs(["💳 Nouvelle vente", "📜 Historique"])

    # --- Nouvelle vente ---
    with tab1:
        c.execute("SELECT * FROM products WHERE user_id=%s AND stock>0", (user['id'],))
        available_products = [dict(r) for r in c.fetchall()]

        if available_products:
            with st.form("sale_form"):
                col1, col2 = st.columns(2)
                with col1:
                    selected_product = st.selectbox(
                        "Produit à vendre",
                        available_products,
                        format_func=lambda x: f"{x['name']} - {format_price(x['price'])} (Stock: {x['stock']})"
                    )

                with col2:
                    quantity = st.number_input(
                        "Quantité",
                        min_value=1,
                        max_value=selected_product['stock'],
                        value=1
                    )

                total_price = selected_product['price'] * quantity
                st.info(f"💰 Montant total: {format_price(total_price)}")

                if st.form_submit_button("Valider la vente", use_container_width=True):
                    try:
                        # Insertion dans sales
                        c.execute("""
                            INSERT INTO sales (user_id, product_id, product_name, quantity, total) 
                            VALUES (%s, %s, %s, %s, %s)
                        """, (
                            user['id'],
                            selected_product['id'],
                            selected_product['name'],
                            quantity,
                            total_price
                        ))

                        # Mise à jour stock
                        c.execute("UPDATE products SET stock = stock - %s WHERE id = %s", (quantity, selected_product['id']))

                        conn.commit()

                        st.success(f"✅ Vente de {quantity} {selected_product['name']} enregistrée !")
                        st.balloons()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erreur lors de l'enregistrement de la vente : {e}")
        else:
            st.warning("⚠️ Aucun produit en stock disponible pour la vente")

    # --- Historique des ventes ---
    with tab2:
        c.execute("SELECT * FROM sales WHERE user_id=%s ORDER BY date DESC", (user['id'],))
        sales = [dict(r) for r in c.fetchall()]

        if sales:
            for sale in sales:
                with st.container():
                    col1, col2, col3, col4 = st.columns([2, 1, 1, 0.5])
                    with col1:
                        st.write(f"**{sale['product_name']}**")
                        sale_date = sale.get('date', '')
                        if sale_date:
                            st.caption(f"{sale_date.strftime('%Y-%m-%d') if sale_date else 'Date inconnue'}")
                    with col2:
                        st.write(f"Quantité: {sale['quantity']}")
                    with col3:
                        st.write(format_price(sale['total']))
                    with col4:
                        if st.button("↩️", key=f"undo_{sale['id']}"):
                            try:
                                # Restitution du stock
                                c.execute("UPDATE products SET stock = stock + %s WHERE id = %s", (sale['quantity'], sale['product_id']))
                                # Suppression de la vente
                                c.execute("DELETE FROM sales WHERE id=%s", (sale['id'],))
                                conn.commit()
                                st.success("Vente annulée")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erreur lors de l'annulation : {e}")
                    st.markdown("<hr>", unsafe_allow_html=True)
        else:
            st.info("Aucune vente enregistrée pour le moment")

    conn.close()
# --- PARAMÈTRES ---
elif page == "Paramètres":
    st.header("⚙️ Paramètres du compte")

    conn, c = get_db_connection()

    # Affichage des informations de l'utilisateur
    st.write(f"Utilisateur: {user['username']}")
    st.write(f"Entreprise: {user.get('entreprise', '-')}")
    st.write(f"Rôle: {'Administrateur' if user['is_admin'] else 'Vendeur'}")

    # --- Changer le mot de passe ---
    st.subheader("🔑 Changer le mot de passe")
    new_pass = st.text_input("Nouveau mot de passe", type="password")
    if st.button("💾 Enregistrer le mot de passe"):
        if new_pass:
            c.execute("UPDATE users SET password=%s WHERE id=%s", (hash_password(new_pass), user['id']))
            conn.commit()
            st.success("Mot de passe mis à jour avec succès")
        else:
            st.error("Veuillez saisir un mot de passe valide")

    # --- Modifier le nom et l'entreprise ---
    st.subheader("📝 Modifier les informations")
    new_username = st.text_input("Nom d'utilisateur", value=user['username'])
    new_entreprise = st.text_input("Nom de l'entreprise", value=user.get('entreprise', ''))
    if st.button("💾 Enregistrer les informations"):
        if new_username.strip():
            c.execute("UPDATE users SET username=%s, entreprise=%s WHERE id=%s",
                      (new_username, new_entreprise, user['id']))
            conn.commit()
            st.success("Informations mises à jour")
        else:
            st.error("Le nom d'utilisateur ne peut pas être vide")

    # --- Gestion du logo ---
    st.subheader("🏢 Logo de l'entreprise")
    if user.get('logo') and os.path.exists(user['logo']):
        st.image(user['logo'], width=150)

    uploaded_logo = st.file_uploader("Téléverser un nouveau logo", type=["png", "jpg", "jpeg"])
    if uploaded_logo:
        logo_path = f"logos/logo_user_{user['id']}.png"
        os.makedirs(os.path.dirname(logo_path), exist_ok=True)
        with open(logo_path, "wb") as f:
            f.write(uploaded_logo.getbuffer())
        c.execute("UPDATE users SET logo=%s WHERE id=%s", (logo_path, user['id']))
        conn.commit()
        st.success("Logo mis à jour avec succès")
        st.image(logo_path, width=150)

    conn.close()

# --- RAPPORTS ---
elif page == "Rapports":
    st.header("📊 Rapports et Analyses")

    conn, c = get_db_connection()

    # --- Filtres de date et type ---
    col1, col2, col3 = st.columns(3)
    with col1:
        start_date = st.date_input("Date début", value=datetime.now().replace(day=1))
    with col2:
        end_date = st.date_input("Date fin", value=datetime.now())
    with col3:
        report_type = st.selectbox("Type de rapport", ["Ventes", "Produits", "Chiffre d'affaires"])

    # --- Rapport Ventes ---
    if report_type == "Ventes":
        st.subheader("📊 Détail des ventes")
        try:
            c.execute("""
                SELECT * FROM sales 
                WHERE user_id=%s AND date(date) BETWEEN %s AND %s
                ORDER BY date DESC
            """, (user['id'], start_date, end_date))
            sales_data = [dict(r) for r in c.fetchall()]

            if sales_data:
                df = pd.DataFrame(sales_data)
                st.dataframe(df, use_container_width=True)

                # Export CSV
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    "📥 Télécharger en CSV",
                    csv,
                    f"rapport_ventes_{start_date}_{end_date}.csv",
                    "text/csv"
                )
            else:
                st.info("Aucune donnée pour cette période")
        except Exception as e:
            st.error(f"Erreur lors de la génération du rapport : {e}")

    # --- Rapport Produits ---
    elif report_type == "Produits":
        st.subheader("📦 État du stock")
        try:
            c.execute("SELECT * FROM products WHERE user_id=%s", (user['id'],))
            products_data = [dict(r) for r in c.fetchall()]

            if products_data:
                df = pd.DataFrame(products_data)
                display_df = df[['name', 'price', 'stock', 'description']].copy()
                display_df['price'] = display_df['price'].apply(format_price)
                st.dataframe(display_df, use_container_width=True)
            else:
                st.info("Aucun produit enregistré")
        except Exception as e:
            st.error(f"Erreur lors de la récupération des produits : {e}")

    # --- Rapport Chiffre d'affaires ---
    else:  # Chiffre d'affaires
        st.subheader("💰 Analyse du chiffre d'affaires")
        try:
            c.execute("""
                SELECT date(date) as sale_date, SUM(total) as daily_ca
                FROM sales
                WHERE user_id=%s AND date(date) BETWEEN %s AND %s
                GROUP BY date(date)
                ORDER BY date(date)
            """, (user['id'], start_date, end_date))
            ca_data = [dict(r) for r in c.fetchall()]

            if ca_data:
                df = pd.DataFrame(ca_data)
                fig = px.line(df, x='sale_date', y='daily_ca', title='Évolution du chiffre d\'affaires')
                st.plotly_chart(fig, use_container_width=True)

                total_ca = df['daily_ca'].sum()
                st.metric("Chiffre d'affaires total", format_price(total_ca))
            else:
                st.info("Aucune donnée pour cette période")
        except Exception as e:
            st.error(f"Erreur lors de l'analyse : {e}")

    conn.close()