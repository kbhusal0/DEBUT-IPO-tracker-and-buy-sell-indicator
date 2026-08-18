"""
seed_data.py
------------
Loads a starter list of real IPOs into the database.

This is our "static dataset" step. Later, fetch_prices.py will fill in
day1_close and current_price using live data from yfinance.

Feel free to add more companies to SEED_IPOS as you go.
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "ipo_data.db")

# (ticker, company_name, ipo_date, offer_price)
# offer_price = the price shares were sold at BEFORE trading opened.
SEED_IPOS = [
    ("RDDT", "Reddit Inc",        "2024-03-21", 34.00),
    ("ARM",  "Arm Holdings",      "2023-09-14", 51.00),
    ("BIRK", "Birkenstock",       "2023-10-11", 46.00),
    ("CART", "Instacart (Maplebear)", "2023-09-19", 30.00),
    ("KVYO", "Klaviyo",           "2023-09-20", 30.00),
    ("SMCI", "Super Micro Computer", "2007-03-29", 8.00),  # older, for contrast
    ("RIVN", "Rivian Automotive", "2021-11-10", 78.00),
    ("ABNB", "Airbnb",            "2020-12-10", 68.00),
    ("DASH", "DoorDash",          "2020-12-09", 102.00),
    ("COIN", "Coinbase",          "2021-04-14", 250.00),  # direct listing reference price
]


def seed():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    for ticker, name, date, offer_price in SEED_IPOS:
        cursor.execute("""
            INSERT INTO ipos (ticker, company_name, ipo_date, offer_price)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(ticker) DO UPDATE SET
                company_name=excluded.company_name,
                ipo_date=excluded.ipo_date,
                offer_price=excluded.offer_price
        """, (ticker, name, date, offer_price))

    conn.commit()
    conn.close()
    print(f"Seeded {len(SEED_IPOS)} IPOs into the database.")


if __name__ == "__main__":
    seed()
