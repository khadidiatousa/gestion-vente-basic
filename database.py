# database.py
import psycopg2
from psycopg2.extras import RealDictCursor
import hashlib
from datetime import datetime
import os

# -------------------- CONFIG DB --------------------
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "vendeur")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "password")
DB_PORT = os.getenv("DB_PORT", 5432)

# -------------------- Connexion DB --------------------
def get_db_connection():
    conn = psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        port=DB_PORT,
        cursor_factory=RealDictCursor
    )
    c = conn.cursor()
    return conn, c

# -------------------- Hash mot de passe --------------------
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# -------------------- Login utilisateur --------------------
def login_user(username, password):
    conn, c = get_db_connection()
    c.execute("SELECT * FROM users WHERE username=%s", (username,))
    user = c.fetchone()
    conn.close()
    if user and user["password"] == hash_password(password):
        return dict(user)
    return None

# -------------------- Initialisation DB --------------------
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
        logo TEXT
    )
    """)

    # Table products
    c.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
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
        id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
        product_id INTEGER REFERENCES products(id) ON DELETE CASCADE,
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
            "INSERT INTO users (username, password, is_admin, must_change_password) VALUES (%s,%s,%s,%s)",
            ("admin", hash_password("admin123"), 1, 0)
        )
        conn.commit()

    conn.close()