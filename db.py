import sqlite3
import os

DB_FILE = os.path.join(os.path.dirname(__file__), "smartcart.db")


def get_db():
    # timeout=10 makes sqlite wait for a lock instead of instantly erroring out
    # when two requests hit the db at almost the same time
    conn = sqlite3.connect(DB_FILE, timeout=10)
    conn.row_factory = sqlite3.Row
    # WAL mode lets reads and writes happen at the same time much better
    # than sqlite's default mode - matters once more than one person is using this
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    conn = get_db()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            username TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS stores (
            store_name TEXT PRIMARY KEY
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS owners (
            username TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            store_name TEXT NOT NULL UNIQUE
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            store_name TEXT NOT NULL,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            code TEXT NOT NULL,
            UNIQUE(store_name, code)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS receipts (
            receipt_id TEXT PRIMARY KEY,
            store_name TEXT NOT NULL,
            customer_username TEXT,
            items_json TEXT NOT NULL,
            total REAL NOT NULL,
            payment_method TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'paid',
            created_at TEXT NOT NULL
        )
    """)

    conn.commit()

    # put a few starter stores/products in so the app isn't empty on first run
    existing = c.execute("SELECT COUNT(*) FROM stores").fetchone()[0]
    if existing == 0:
        starter_stores = ["Big Bazaar", "Reliance Fresh", "Spencer's", "Phoenix Mall"]
        c.executemany(
            "INSERT INTO stores (store_name) VALUES (?)",
            [(s,) for s in starter_stores],
        )

        starter_products = [
            ("Big Bazaar", "Milk Packet", 25, "SC1001"),
            ("Big Bazaar", "Bread", 30, "SC1002"),
            ("Reliance Fresh", "Rice 1kg", 65, "SC1003"),
            ("Reliance Fresh", "Eggs (6pc)", 42, "SC1004"),
            ("Spencer's", "Chips", 50, "SC1005"),
            ("Phoenix Mall", "Toothpaste", 60, "SC1006"),
        ]
        c.executemany(
            "INSERT INTO products (store_name, name, price, code) VALUES (?, ?, ?, ?)",
            starter_products,
        )
        conn.commit()

    conn.close()


def get_all_stores():
    conn = get_db()
    rows = conn.execute("SELECT store_name FROM stores ORDER BY store_name").fetchall()
    conn.close()
    return [row["store_name"] for row in rows]


def create_store(store_name):
    conn = get_db()
    conn.execute("INSERT INTO stores (store_name) VALUES (?)", (store_name,))
    conn.commit()
    conn.close()


def get_products_for_store(store_name):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM products WHERE store_name = ?", (store_name,)
    ).fetchall()
    conn.close()
    return rows


def find_product(store_name, code):
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM products WHERE store_name = ? AND code = ?",
        (store_name, code),
    ).fetchone()
    conn.close()
    return row


def add_product(store_name, name, price, code):
    conn = get_db()
    conn.execute(
        "INSERT INTO products (store_name, name, price, code) VALUES (?, ?, ?, ?)",
        (store_name, name, price, code),
    )
    conn.commit()
    conn.close()


def store_exists(store_name):
    conn = get_db()
    row = conn.execute(
        "SELECT 1 FROM stores WHERE store_name = ?", (store_name,)
    ).fetchone()
    conn.close()
    return row is not None


def create_customer(username, password_hash):
    conn = get_db()
    conn.execute(
        "INSERT INTO customers (username, password_hash) VALUES (?, ?)",
        (username, password_hash),
    )
    conn.commit()
    conn.close()


def get_customer(username):
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM customers WHERE username = ?", (username,)
    ).fetchone()
    conn.close()
    return row


def create_owner(username, password_hash, store_name):
    conn = get_db()
    conn.execute(
        "INSERT INTO owners (username, password_hash, store_name) VALUES (?, ?, ?)",
        (username, password_hash, store_name),
    )
    conn.commit()
    conn.close()


def get_owner(username):
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM owners WHERE username = ?", (username,)
    ).fetchone()
    conn.close()
    return row


def save_receipt(receipt_id, store_name, customer_username, items_json, total, payment_method, created_at):
    conn = get_db()
    conn.execute(
        """INSERT INTO receipts
           (receipt_id, store_name, customer_username, items_json, total, payment_method, status, created_at)
           VALUES (?, ?, ?, ?, ?, ?, 'paid', ?)""",
        (receipt_id, store_name, customer_username, items_json, total, payment_method, created_at),
    )
    conn.commit()
    conn.close()


def get_receipt(receipt_id):
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM receipts WHERE receipt_id = ?", (receipt_id,)
    ).fetchone()
    conn.close()
    return row


def mark_receipt_verified(receipt_id):
    conn = get_db()
    conn.execute(
        "UPDATE receipts SET status = 'verified' WHERE receipt_id = ?", (receipt_id,)
    )
    conn.commit()
    conn.close()


def delete_product(product_id):
    conn = get_db()
    conn.execute("DELETE FROM products WHERE id = ?", (product_id,))
    conn.commit()
    conn.close()
