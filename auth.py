from database import c, conn, hash_password

def login_user(username, password):
    c.execute(
        "SELECT id, username, password, is_admin, must_change_password FROM users WHERE username=? AND password=?",
        (username, hash_password(password))
    )
    user = c.fetchone()
    if user:
        return dict(user)
    return None

def update_password(user_id, new_password):
    c.execute(
        "UPDATE users SET password=?, must_change_password=0 WHERE id=?",
        (hash_password(new_password), user_id)
    )
    conn.commit()