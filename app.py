# app.py
import io

import streamlit as st
import sqlite3
import hashlib
import os
from fpdf import FPDF
from datetime import datetime
import pandas as pd
import plotly.express as px
from PIL import Image

from database import login_user

# --- CONFIGURATION PAGE ---
st.set_page_config(
    page_title="Glow Essentials - Admin",
    layout="wide",
    page_icon="✨",
    initial_sidebar_state="collapsed"
)
# --- CLASSE PDF PERSONNALISÉE ---
from fpdf import FPDF
from datetime import datetime


# 🔹 Fonction de nettoyage (TRÈS IMPORTANT)
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


class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 16)
        self.cell(0, 10, safe_text("GLOW ESSENTIALS"), 0, 1, 'C')

        self.set_font('Arial', 'I', 10)
        self.cell(0, 5, safe_text("Catalogue de produits"), 0, 1, 'C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, safe_text(f"Page {self.page_no()}"), 0, 0, 'C')


def generate_catalog_pdf(products, user_name):
    pdf = PDF()
    pdf.add_page()

    pdf.set_font('Arial', 'B', 14)
    pdf.cell(0, 10, safe_text(f"Vendeur: {user_name}"), 0, 1)
    pdf.ln(5)

    for product in products:

        y_before = pdf.get_y()

        # 🔹 IMAGE (CORRIGÉ)
        image_path = product.get('image', '')

        if image_path and os.path.exists(image_path):
            pdf.image(image_path, x=10, y=y_before, w=30)
            pdf.set_xy(45, y_before)
        else:
            pdf.set_x(10)

        # 🔹 NOM
        pdf.set_font('Arial', 'B', 11)
        pdf.cell(0, 6, safe_text(product['name']), 0, 1)

        pdf.set_x(45 if image_path and os.path.exists(image_path) else 10)

        # 🔹 PRIX
        pdf.set_font('Arial', '', 10)
        pdf.cell(0, 5, safe_text(f"Prix: {product['price']} FCFA"), 0, 1)

        pdf.set_x(45 if image_path and os.path.exists(image_path) else 10)

        # 🔹 STOCK
        pdf.cell(0, 5, safe_text(f"Stock: {product['stock']}"), 0, 1)

        pdf.set_x(45 if image_path and os.path.exists(image_path) else 10)

        # 🔹 DESCRIPTION
        if product.get("description"):
            pdf.multi_cell(0, 5, safe_text(product["description"]))

        # 🔹 Ajuster hauteur pour éviter chevauchement
        y_after = pdf.get_y()
        pdf.set_y(max(y_after, y_before + 35))

        pdf.ln(5)

        # 🔹 Séparateur
        pdf.set_draw_color(200, 200, 200)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(5)

    return pdf
# --- BASE DE DONNÉES ---
DB_FILE = "vendeur.db"

def get_db_connection():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    conn = get_db_connection()
    c = conn.cursor()

    # Table users
    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        is_admin INTEGER DEFAULT 0,
        must_change_password INTEGER DEFAULT 1
    )
    """)

    # Vérifier et ajouter la colonne created_at si elle n'existe pas
    c.execute("PRAGMA table_info(users)")
    columns = [col["name"] for col in c.fetchall()]
    if "created_at" not in columns:
        try:
            c.execute("ALTER TABLE users ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
        except:
            pass

    # Table products
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

    # Vérifier et ajouter la colonne created_at si elle n'existe pas
    c.execute("PRAGMA table_info(products)")
    columns = [col["name"] for col in c.fetchall()]
    if "created_at" not in columns:
        try:
            c.execute("ALTER TABLE products ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
        except:
            pass

    # Table sales
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

    # Vérifier et ajouter la colonne date si elle n'existe pas (pour compatibilité)
    c.execute("PRAGMA table_info(sales)")
    columns = [col["name"] for col in c.fetchall()]
    if "date" not in columns:
        try:
            c.execute("ALTER TABLE sales ADD COLUMN date TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
        except:
            pass

    # Création admin par défaut
    c.execute("SELECT * FROM users WHERE is_admin=1")
    if not c.fetchone():
        c.execute("INSERT INTO users (username, password, is_admin, must_change_password) VALUES (?, ?, ?, ?)",
                  ("admin", hash_password("admin123"), 1, 0))
        conn.commit()

    conn.close()

# --- HASH PASSWORD ---
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# --- FONCTIONS UTILITAIRES ---
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

# Initialisation base de données
init_database()

# --- LOGIN SCREEN ---
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
                        st.session_state.notifications.append({
                            "type": "success",
                            "message": f"Bienvenue {user['username']} !"
                        })
                        st.rerun()
                    else:
                        st.error("❌ Identifiants incorrects")
            with col_btn2:
                if st.button("Mot de passe oublié ?", use_container_width=True):
                    st.info("Contactez l'administrateur pour réinitialiser votre mot de passe")

    st.stop()

# --- UTILISATEUR CONNECTÉ ---
user = st.session_state.user

# --- HEADER ---
col_logo, col_user, col_logout = st.columns([2, 1, 1])
with col_logo:
    st.markdown("<h1 style='margin: 0;'>Gestin de Vente </h1>", unsafe_allow_html=True)

with col_user:
    st.markdown(f"""
    <div style="text-align: right; padding: 10px;">
        <span style="font-weight: bold;">👤 {user['username']}</span>
        <br>
        <span style="font-size: 12px;">{'Administrateur' if user['is_admin'] else 'Vendeur'}</span>
    </div>
    """, unsafe_allow_html=True)

with col_logout:
    if st.button("🚪 Déconnexion", use_container_width=True):
        logout()

st.markdown("---")


# --- NAVIGATION ---
nav_items = [
    {"name": "Dashboard", "icon": "📊", "admin_only": False},
    {"name": "Catalogue", "icon": "📦", "admin_only": False},
    {"name": "Ventes", "icon": "🛒", "admin_only": False},
    {"name": "Rapports", "icon": "📈", "admin_only": False}
]

if user['is_admin']:
    nav_items.insert(1, {"name": "Utilisateurs", "icon": "👥", "admin_only": True})

st.markdown('<div style="margin: 20px 0;">', unsafe_allow_html=True)
nav_cols = st.columns(len(nav_items))

for idx, item in enumerate(nav_items):
    with nav_cols[idx]:
        if st.button(
                f"{item['icon']} {item['name']}",
                use_container_width=True,
                type="secondary" if st.session_state.page != item['name'] else "primary"
        ):
            st.session_state.page = item['name']
            st.rerun()
st.markdown('</div>', unsafe_allow_html=True)

page = st.session_state.page

# ================== PAGES ==================

# --- DASHBOARD ---
if page == "Dashboard":
    st.header("📊 Tableau de bord")

    conn = get_db_connection()
    c = conn.cursor()

    # Statistiques
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        c.execute("SELECT COUNT(*) as count FROM products WHERE user_id=?", (user['id'],))
        products_count = c.fetchone()['count']
        st.metric("Produits en stock", products_count)

    with col2:
        c.execute("SELECT SUM(stock) as total_stock FROM products WHERE user_id=?", (user['id'],))
        total_stock = c.fetchone()['total_stock'] or 0
        st.metric("Unités totales", total_stock)

    with col3:
        c.execute("SELECT SUM(total) as ca FROM sales WHERE user_id=?", (user['id'],))
        total_ca = c.fetchone()['ca'] or 0
        st.metric("Chiffre d'affaires", format_price(total_ca))

    with col4:
        c.execute("SELECT COUNT(*) as count FROM sales WHERE user_id=?", (user['id'],))
        sales_count = c.fetchone()['count'] or 0
        st.metric("Ventes réalisées", sales_count)

    # Graphique des ventes

    # Dernières ventes
    st.markdown("---")
    st.subheader("🕒 Dernières ventes")
    c.execute("""
        SELECT * FROM sales 
        WHERE user_id=? 
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

# --- UTILISATEURS CRUD (ADMIN) ---
elif page == "Utilisateurs" and user['is_admin']:
    st.header("👥 Gestion des Utilisateurs")

    conn = get_db_connection()
    c = conn.cursor()

    # Formulaire d'ajout
    with st.expander("➕ Créer un nouveau compte", expanded=False):
        with st.form("create_user_form"):
            col1, col2 = st.columns(2)
            with col1:
                username = st.text_input("Nom d'utilisateur", placeholder="ex: jean.dupont")
                password = st.text_input("Mot de passe", type="password", placeholder="Mot de passe")
            with col2:
                is_admin = st.checkbox("Administrateur")
                must_change = st.checkbox("Doit changer le mot de passe à la première connexion", value=True)

            if st.form_submit_button("Créer le compte", use_container_width=True):
                if username and password:
                    try:
                        c.execute("""
                            INSERT INTO users (username, password, is_admin, must_change_password) 
                            VALUES (?,?,?,?)
                        """, (username, hash_password(password), int(is_admin), int(must_change)))
                        conn.commit()
                        st.success(f"✅ Utilisateur {username} créé avec succès!")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("❌ Ce nom d'utilisateur existe déjà")
                else:
                    st.error("Veuillez remplir tous les champs")

    # Liste des utilisateurs
    st.subheader("👥 Utilisateurs existants")
    try:
        c.execute("SELECT * FROM users ORDER BY id DESC")
        users = [dict(r) for r in c.fetchall()]
    except:
        c.execute("SELECT * FROM users ORDER BY id DESC")
        users = [dict(r) for r in c.fetchall()]

    for user_item in users:
        with st.container():
            col1, col2, col3, col4 = st.columns([2, 1, 1, 0.5])
            with col1:
                st.write(f"**{user_item['username']}**")
                created_date = user_item.get('created_at', 'Date inconnue')
                if created_date and created_date != 'Date inconnue':
                    st.caption(f"ID: {user_item['id']} | Créé le: {created_date[:10]}")
                else:
                    st.caption(f"ID: {user_item['id']}")
            with col2:
                if user_item['is_admin']:
                    st.write("👑 Administrateur")
                else:
                    st.write("👤 Vendeur")
            with col3:
                if user_item['must_change_password']:
                    st.write("🔑 Mot de passe à changer")
                else:
                    st.write("✅ Compte actif")
            with col4:
                if user_item['username'] != "admin":
                    if st.button("🗑️", key=f"del_user_{user_item['id']}"):
                        c.execute("DELETE FROM users WHERE id=?", (user_item['id'],))
                        conn.commit()
                        st.success(f"Utilisateur {user_item['username']} supprimé")
                        st.rerun()
            st.markdown("<hr>", unsafe_allow_html=True)

    conn.close()

# --- CATALOGUE ---
elif page == "Catalogue":
    st.header("📦 Gestion du Catalogue")

    conn = get_db_connection()
    c = conn.cursor()

    # Onglets
    tab1, tab2, tab3 = st.tabs(["📝 Mes produits", "➕ Ajouter un produit", "📄 Générer PDF"])

    with tab2:
        with st.form("add_product_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("Nom du produit", placeholder="Ex: Crème hydratante")
                description = st.text_area("Description", placeholder="Description détaillée du produit...")
            with col2:
                price = st.number_input("Prix (FCFA)", min_value=0, step=100)
                stock = st.number_input("Stock initial", min_value=0, step=1)
                image_file = st.file_uploader("Image du produit", type=["jpg", "jpeg", "png"])

            if st.form_submit_button("Ajouter au catalogue", use_container_width=True):
                if name and price and image_file:
                    # Sauvegarde de l'image
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"{timestamp}_{image_file.name}"
                    path = f"images/{filename}"

                    # Créer le dossier images s'il n'existe pas
                    if not os.path.exists("images"):
                        os.makedirs("images")

                    with open(path, "wb") as f:
                        f.write(image_file.getbuffer())

                    c.execute("""
                        INSERT INTO products (user_id, name, description, price, stock, image) 
                        VALUES (?,?,?,?,?,?)
                    """, (user['id'], name, description, price, stock, path))
                    conn.commit()
                    st.success("✅ Produit ajouté avec succès!")
                    st.rerun()
                else:
                    st.error("Veuillez remplir tous les champs obligatoires")

    with tab1:
        try:
            c.execute("SELECT * FROM products WHERE user_id=? ORDER BY id DESC", (user['id'],))
            products = [dict(r) for r in c.fetchall()]
        except:
            c.execute("SELECT * FROM products WHERE user_id=?", (user['id'],))
            products = [dict(r) for r in c.fetchall()]

        if products:
            # Affichage en grille
            cols = st.columns(3)
            for idx, product in enumerate(products):
                with cols[idx % 3]:
                    with st.container():
                        try:
                            if os.path.exists(product['image']):
                                img = Image.open(product['image'])
                                st.image(img, use_container_width=True)
                            else:
                                st.image("https://via.placeholder.com/300x200?text=Image+non+disponible", use_container_width=True)
                        except:
                            st.image("https://via.placeholder.com/300x200?text=Image+non+disponible", use_container_width=True)

                        st.markdown(f"**{product['name']}**")
                        st.markdown(f"💰 {format_price(product['price'])}")
                        st.markdown(f"📦 Stock: {product['stock']}")

                        with st.expander("Description"):
                            st.write(product['description'] or "Aucune description")

                        if st.button("🗑️ Supprimer", key=f"del_{product['id']}", use_container_width=True):
                            c.execute("DELETE FROM products WHERE id=?", (product['id'],))
                            if os.path.exists(product['image']):
                                try:
                                    os.remove(product['image'])
                                except:
                                    pass
                            conn.commit()
                            st.rerun()
        else:
            st.info("Aucun produit dans votre catalogue. Commencez par en ajouter !")

    with tab3:
        st.subheader("📄 Générer le catalogue PDF")

        c.execute("SELECT * FROM products WHERE user_id=?", (user['id'],))
        products = [dict(r) for r in c.fetchall()]

        if products:
            st.write(f"**{len(products)} produits** seront inclus dans le catalogue")

            if st.button("📥 Générer le catalogue PDF", use_container_width=True):

                with st.spinner("Génération du PDF en cours..."):

                    pdf = generate_catalog_pdf(products, user['username'])

                    # 🔹 dossier
                    os.makedirs("catalogues", exist_ok=True)

                    filename = f"catalogues/catalogue_{user['username']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

                    # 🔹 sauvegarde disque
                    pdf.output(filename)

                    # 🔹 mémoire
                    pdf_buffer = io.BytesIO()
                    pdf_output = pdf.output(dest='S')

                    if isinstance(pdf_output, str):
                        pdf_output = pdf_output.encode('latin-1')

                    pdf_buffer.write(pdf_output)
                    pdf_buffer.seek(0)

                    st.success("✅ Catalogue généré avec succès !")

                    st.download_button(
                        label="📥 Télécharger le catalogue PDF",
                        data=pdf_buffer,
                        file_name=os.path.basename(filename),
                        mime="application/pdf",
                        use_container_width=True
                    )

                    st.info(f"📁 Sauvegardé dans : {filename}")

        else:
            st.warning("Aucun produit disponible.")
    conn.close()

# --- VENTES ---
elif page == "Ventes":
    st.header("🛒 Enregistrement des ventes")

    conn = get_db_connection()
    c = conn.cursor()

    tab1, tab2 = st.tabs(["💳 Nouvelle vente", "📜 Historique"])

    with tab1:
        c.execute("SELECT * FROM products WHERE user_id=? AND stock>0", (user['id'],))
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
                    c.execute("""
                        INSERT INTO sales (user_id, product_id, product_name, quantity, total) 
                        VALUES (?,?,?,?,?)
                    """, (user['id'], selected_product['id'], selected_product['name'], quantity, total_price))

                    c.execute("UPDATE products SET stock=stock-? WHERE id=?", (quantity, selected_product['id']))
                    conn.commit()

                    st.success(f"✅ Vente de {quantity} {selected_product['name']} enregistrée!")
                    st.balloons()
                    st.rerun()
        else:
            st.warning("⚠️ Aucun produit en stock disponible pour la vente")

    with tab2:
        c.execute("SELECT * FROM sales WHERE user_id=? ORDER BY date DESC", (user['id'],))
        sales = [dict(r) for r in c.fetchall()]

        if sales:
            for sale in sales:
                with st.container():
                    col1, col2, col3, col4 = st.columns([2, 1, 1, 0.5])
                    with col1:
                        st.write(f"**{sale['product_name']}**")
                        sale_date = sale.get('date', '')
                        if sale_date:
                            st.caption(f"{sale_date[:10] if sale_date else 'Date inconnue'}")
                    with col2:
                        st.write(f"Quantité: {sale['quantity']}")
                    with col3:
                        st.write(format_price(sale['total']))
                    with col4:
                        if st.button("↩️", key=f"undo_{sale['id']}"):
                            c.execute("UPDATE products SET stock=stock+? WHERE id=?", (sale['quantity'], sale['product_id']))
                            c.execute("DELETE FROM sales WHERE id=?", (sale['id'],))
                            conn.commit()
                            st.success("Vente annulée")
                            st.rerun()
                    st.markdown("<hr>", unsafe_allow_html=True)
        else:
            st.info("Aucune vente enregistrée pour le moment")

    conn.close()

# --- RAPPORTS ---
elif page == "Rapports":
    st.header("📊 Rapports et Analyses")

    conn = get_db_connection()
    c = conn.cursor()

    # Filtres
    col1, col2, col3 = st.columns(3)
    with col1:
        start_date = st.date_input("Date début", value=datetime.now().replace(day=1))
    with col2:
        end_date = st.date_input("Date fin", value=datetime.now())
    with col3:
        report_type = st.selectbox("Type de rapport", ["Ventes", "Produits", "Chiffre d'affaires"])

    if report_type == "Ventes":
        st.subheader("📊 Détail des ventes")
        try:
            c.execute("""
                SELECT * FROM sales 
                WHERE user_id=? AND date(date) BETWEEN ? AND ?
                ORDER BY date DESC
            """, (user['id'], start_date, end_date))

            sales_data = [dict(r) for r in c.fetchall()]
            if sales_data:
                df = pd.DataFrame(sales_data)
                st.dataframe(df, use_container_width=True)

                # Export
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
            st.error(f"Erreur lors de la génération du rapport: {e}")

    elif report_type == "Produits":
        st.subheader("📦 État du stock")
        c.execute("SELECT * FROM products WHERE user_id=?", (user['id'],))
        products_data = [dict(r) for r in c.fetchall()]

        if products_data:
            df = pd.DataFrame(products_data)
            display_df = df[['name', 'price', 'stock', 'description']].copy()
            display_df['price'] = display_df['price'].apply(format_price)
            st.dataframe(display_df, use_container_width=True)
        else:
            st.info("Aucun produit enregistré")

    else:  # Chiffre d'affaires
        st.subheader("💰 Analyse du chiffre d'affaires")
        try:
            c.execute("""
                SELECT date(date) as sale_date, SUM(total) as daily_ca
                FROM sales 
                WHERE user_id=? AND date(date) BETWEEN ? AND ?
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
            st.error(f"Erreur lors de l'analyse: {e}")

    conn.close()


