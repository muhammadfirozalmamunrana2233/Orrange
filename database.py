import sqlite3
from config import DB_PATH
from datetime import datetime

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        full_name TEXT,
        joined_at TEXT,
        is_banned INTEGER DEFAULT 0
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS subscriptions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        plan TEXT,
        start_date TEXT,
        end_date TEXT,
        is_active INTEGER DEFAULT 1,
        FOREIGN KEY(user_id) REFERENCES users(user_id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS payment_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        plan TEXT,
        amount REAL,
        method TEXT,
        trx_id TEXT,
        status TEXT DEFAULT 'pending',
        requested_at TEXT,
        FOREIGN KEY(user_id) REFERENCES users(user_id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS cli_list (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        prefix TEXT UNIQUE,
        added_at TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS payment_methods (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        details TEXT,
        is_active INTEGER DEFAULT 1
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS subscription_plans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        months INTEGER,
        price REAL,
        is_active INTEGER DEFAULT 1
    )''')

    # Default settings
    defaults = {
        "check_interval": "10",
        "min_hits": "4",
        "max_hits": "10",
        "top_ranges": "15",
        "window_minutes": "30",
        "bot_active": "1",
        "service_info": "Orange Carrier Active Range Bot\n\nSubscribe to get real-time IPRN range alerts!",
        "support_username": "@support"
    }
    for k, v in defaults.items():
        c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v))

    # Default plans
    c.execute("INSERT OR IGNORE INTO subscription_plans (name, months, price) VALUES ('Monthly', 1, 10.00)")
    c.execute("INSERT OR IGNORE INTO subscription_plans (name, months, price) VALUES ('2 Months', 2, 18.00)")
    c.execute("INSERT OR IGNORE INTO subscription_plans (name, months, price) VALUES ('3 Months', 3, 25.00)")

    conn.commit()
    conn.close()

# ─── Users ───────────────────────────────────────────────
def add_user(user_id, username, full_name):
    conn = get_conn()
    conn.execute(
        "INSERT OR IGNORE INTO users (user_id, username, full_name, joined_at) VALUES (?, ?, ?, ?)",
        (user_id, username, full_name, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()
    conn.close()
    return row

def get_all_users():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM users").fetchall()
    conn.close()
    return rows

def ban_user(user_id, ban=True):
    conn = get_conn()
    conn.execute("UPDATE users SET is_banned=? WHERE user_id=?", (1 if ban else 0, user_id))
    conn.commit()
    conn.close()

# ─── Subscriptions ────────────────────────────────────────
def get_active_subscription(user_id):
    conn = get_conn()
    now = datetime.now().isoformat()
    row = conn.execute(
        "SELECT * FROM subscriptions WHERE user_id=? AND is_active=1 AND end_date > ? ORDER BY end_date DESC LIMIT 1",
        (user_id, now)
    ).fetchone()
    conn.close()
    return row

def add_subscription(user_id, plan, months):
    from datetime import timedelta
    conn = get_conn()
    start = datetime.now()
    end = start + timedelta(days=30 * months)
    conn.execute(
        "INSERT INTO subscriptions (user_id, plan, start_date, end_date, is_active) VALUES (?, ?, ?, ?, 1)",
        (user_id, plan, start.isoformat(), end.isoformat())
    )
    conn.commit()
    conn.close()

def revoke_subscription(user_id):
    conn = get_conn()
    conn.execute("UPDATE subscriptions SET is_active=0 WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()

def get_active_subscribers():
    conn = get_conn()
    now = datetime.now().isoformat()
    rows = conn.execute(
        "SELECT DISTINCT user_id FROM subscriptions WHERE is_active=1 AND end_date > ?", (now,)
    ).fetchall()
    conn.close()
    return [r["user_id"] for r in rows]

# ─── Payment Requests ─────────────────────────────────────
def add_payment_request(user_id, plan, amount, method, trx_id):
    conn = get_conn()
    conn.execute(
        "INSERT INTO payment_requests (user_id, plan, amount, method, trx_id, requested_at) VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, plan, amount, method, trx_id, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()

def get_pending_payments():
    conn = get_conn()
    rows = conn.execute(
        "SELECT pr.*, u.username, u.full_name FROM payment_requests pr LEFT JOIN users u ON pr.user_id=u.user_id WHERE pr.status='pending' ORDER BY pr.requested_at DESC"
    ).fetchall()
    conn.close()
    return rows

def update_payment_status(payment_id, status):
    conn = get_conn()
    conn.execute("UPDATE payment_requests SET status=? WHERE id=?", (status, payment_id))
    conn.commit()
    conn.close()

def get_payment_request(payment_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM payment_requests WHERE id=?", (payment_id,)).fetchone()
    conn.close()
    return row

# ─── CLI List ─────────────────────────────────────────────
def add_cli(prefix):
    conn = get_conn()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO cli_list (prefix, added_at) VALUES (?, ?)",
            (prefix.strip(), datetime.now().isoformat())
        )
        conn.commit()
    except:
        pass
    conn.close()

def delete_cli(prefix):
    conn = get_conn()
    conn.execute("DELETE FROM cli_list WHERE prefix=?", (prefix,))
    conn.commit()
    conn.close()

def get_all_cli():
    conn = get_conn()
    rows = conn.execute("SELECT prefix FROM cli_list ORDER BY prefix").fetchall()
    conn.close()
    return [r["prefix"] for r in rows]

def clear_all_cli():
    conn = get_conn()
    conn.execute("DELETE FROM cli_list")
    conn.commit()
    conn.close()

# ─── Settings ─────────────────────────────────────────────
def get_setting(key, default=None):
    conn = get_conn()
    row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else default

def set_setting(key, value):
    conn = get_conn()
    conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()

# ─── Payment Methods ──────────────────────────────────────
def get_payment_methods():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM payment_methods WHERE is_active=1").fetchall()
    conn.close()
    return rows

def add_payment_method(name, details):
    conn = get_conn()
    conn.execute("INSERT INTO payment_methods (name, details) VALUES (?, ?)", (name, details))
    conn.commit()
    conn.close()

def delete_payment_method(method_id):
    conn = get_conn()
    conn.execute("DELETE FROM payment_methods WHERE id=?", (method_id,))
    conn.commit()
    conn.close()

# ─── Subscription Plans ───────────────────────────────────
def get_plans():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM subscription_plans WHERE is_active=1 ORDER BY months").fetchall()
    conn.close()
    return rows

def update_plan_price(plan_id, price):
    conn = get_conn()
    conn.execute("UPDATE subscription_plans SET price=? WHERE id=?", (price, plan_id))
    conn.commit()
    conn.close()

# ─── Stats ────────────────────────────────────────────────
def get_stats():
    conn = get_conn()
    total_users = conn.execute("SELECT COUNT(*) as c FROM users").fetchone()["c"]
    active_subs = conn.execute(
        "SELECT COUNT(DISTINCT user_id) as c FROM subscriptions WHERE is_active=1 AND end_date > ?",
        (datetime.now().isoformat(),)
    ).fetchone()["c"]
    pending_pay = conn.execute("SELECT COUNT(*) as c FROM payment_requests WHERE status='pending'").fetchone()["c"]
    total_cli = conn.execute("SELECT COUNT(*) as c FROM cli_list").fetchone()["c"]
    conn.close()
    return {
        "total_users": total_users,
        "active_subs": active_subs,
        "pending_payments": pending_pay,
        "total_cli": total_cli
    }
