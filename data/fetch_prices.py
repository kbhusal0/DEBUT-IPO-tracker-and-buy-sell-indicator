"""
fetch_prices.py
----------------
Pulls price history for every IPO in our database using yfinance
(free, no API key needed) and stores it in price_history.

Also updates each ipo's day1_close and current_price so the dashboard
table can show them without recomputing every time.

Run this:
  - once, right after seeding, to backfill history
  - periodically (e.g. every time you open the dashboard, or on a
    schedule) to keep "current_price" live
"""

import sqlite3
import os
from datetime import datetime, date
import yfinance as yf
import pandas as pd

DB_PATH = os.path.join(os.path.dirname(__file__), "ipo_data.db")


def get_connection():
    return sqlite3.connect(DB_PATH)


def fetch_and_store_ticker(conn, ticker: str, ipo_date_str: str):
    """Fetch full price history for one ticker since its IPO date and
    upsert it into price_history. Returns (day1_close, current_price)
    or (None, None) if the fetch failed."""

    ipo_date = datetime.strptime(ipo_date_str, "%Y-%m-%d").date()

    try:
        hist = yf.Ticker(ticker).history(start=ipo_date_str)
    except Exception as e:
        print(f"  [WARN] Failed to fetch {ticker}: {e}")
        return None, None

    if hist.empty:
        print(f"  [WARN] No price data returned for {ticker}")
        return None, None

    cursor = conn.cursor()
    rows_written = 0

    for row_date, row in hist.iterrows():
        row_date_obj = row_date.date()
        days_since_ipo = (row_date_obj - ipo_date).days
        close_price = round(float(row["Close"]), 2)

        cursor.execute("""
            INSERT INTO price_history (ticker, date, close_price, days_since_ipo)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(ticker, date) DO UPDATE SET
                close_price=excluded.close_price,
                days_since_ipo=excluded.days_since_ipo
        """, (ticker, row_date_obj.isoformat(), close_price, days_since_ipo))
        rows_written += 1

    conn.commit()

    day1_close = round(float(hist.iloc[0]["Close"]), 2)
    current_price = round(float(hist.iloc[-1]["Close"]), 2)

    print(f"  {ticker}: wrote {rows_written} days of history "
          f"(day1={day1_close}, current={current_price})")

    return day1_close, current_price


def update_ipo_summary(conn, ticker, day1_close, current_price):
    conn.execute("""
        UPDATE ipos
        SET day1_close = ?, current_price = ?, last_updated = ?
        WHERE ticker = ?
    """, (day1_close, current_price, datetime.now().isoformat(timespec="seconds"), ticker))
    conn.commit()


def refresh_all():
    conn = get_connection()
    tickers = conn.execute("SELECT ticker, ipo_date FROM ipos").fetchall()

    print(f"Refreshing price data for {len(tickers)} IPOs...")
    for ticker, ipo_date_str in tickers:
        day1_close, current_price = fetch_and_store_ticker(conn, ticker, ipo_date_str)
        if day1_close is not None:
            update_ipo_summary(conn, ticker, day1_close, current_price)

    conn.close()
    print("Done.")


if __name__ == "__main__":
    refresh_all()
