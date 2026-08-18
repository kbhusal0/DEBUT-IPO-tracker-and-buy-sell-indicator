"""
setup_db.py
------------
Creates our SQLite database and the 'ipos' table.

Why SQLite?
- It's just a file (ipo_data.db) — no server to install or run.
- Perfect for learning + small projects. Swapping to Postgres later
  would only mean changing the connection string, not the logic.
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "ipo_data.db")


def create_tables():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # One row = one IPO we're tracking.
    # current_price gets updated periodically by fetch_prices.py
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ipos (
            ticker TEXT PRIMARY KEY,
            company_name TEXT NOT NULL,
            ipo_date TEXT NOT NULL,
            offer_price REAL NOT NULL,
            day1_close REAL,
            current_price REAL,
            last_updated TEXT
        )
    """)

    # One row = one ticker's closing price on one day.
    # This is what lets us draw "trajectory since IPO" comparison charts.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS price_history (
            ticker TEXT NOT NULL,
            date TEXT NOT NULL,
            close_price REAL NOT NULL,
            days_since_ipo INTEGER NOT NULL,
            PRIMARY KEY (ticker, date),
            FOREIGN KEY (ticker) REFERENCES ipos(ticker)
        )
    """)

    conn.commit()
    conn.close()
    print(f"Database ready at {DB_PATH}")


if __name__ == "__main__":
    create_tables()
