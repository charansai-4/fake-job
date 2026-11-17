

import sqlite3

DATABASE = "lost_found.db"


def get_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def create_table():
    conn = get_connection()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT,
            description TEXT,
            location TEXT NOT NULL,
            item_date TEXT,
            contact TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Upgrade an older database if necessary
    columns = [
        row["name"]
        for row in conn.execute("PRAGMA table_info(items)").fetchall()
    ]

    if "category" not in columns:
        conn.execute("ALTER TABLE items ADD COLUMN category TEXT")

    if "item_date" not in columns:
        conn.execute("ALTER TABLE items ADD COLUMN item_date TEXT")

    if "created_at" not in columns:
        conn.execute(
            "ALTER TABLE items ADD COLUMN created_at TIMESTAMP"
        )

    conn.commit()
    conn.close()
