# database.py
import sqlite3
import hashlib
from datetime import datetime

DB_FILE = "vendeur.db"

# -------------------- Connexion DB --------------------
def get_db_connection():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

# -------------------- Hash mot de passe --------------------
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# -------------------- Login utilisateur --------------------
def login_user(username, password):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username=?", (username,))
    user = c.fetchone()
    conn.close()
    if user and user["password"] == hash_password(password):
        return dict(user)
    return None

# -------------------- Initialisation DB --------------------
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
        must_change_password INTEGER DEFAULT 1,
        entreprise TEXT,
        logo TEXT
    )
    """)

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

    # Création admin par défaut
    c.execute("SELECT * FROM users WHERE is_admin=1")
    if not c.fetchone():
        c.execute(
            "INSERT INTO users (username, password, is_admin, must_change_password) VALUES (?,?,?,0)",
            ("admin", hash_password("admin123"), 1, 0)
        )
        conn.commit()

    conn.close()