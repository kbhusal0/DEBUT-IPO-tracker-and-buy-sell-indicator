"""
train_model.py
---------------
Trains a simple logistic regression model that predicts whether an
IPO will be trading ABOVE its offer price 90 days after listing.

Features used (deliberately simple + explainable):
  - offer_price       : the price shares were sold at
  - day1_pop_pct       : % change from offer price to day-1 close
                         (a common "hype" signal)

Label:
  - 1 if price ~90 days after IPO > offer_price ("outperformed")
  - 0 otherwise

IMPORTANT HONESTY NOTE:
This is trained on a handful of well-known IPOs, so it will NOT be
statistically reliable — that's expected and fine for a portfolio
project. The point is to demonstrate the ML pipeline (feature
engineering -> training -> serialization -> inference in an app),
not to produce real trading signals. The README says this explicitly,
and the app displays a disclaimer.
"""

import sqlite3
import os
import joblib
import pandas as pd
from sklearn.linear_model import LogisticRegression

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "ipo_data.db")
MODEL_PATH = os.path.join(os.path.dirname(__file__), "ipo_model.pkl")

MATURITY_DAYS = 90  # how many days out we're predicting


def load_training_data():
    conn = sqlite3.connect(DB_PATH)

    ipos = pd.read_sql("SELECT ticker, ipo_date, offer_price, day1_close FROM ipos", conn)
    history = pd.read_sql("SELECT ticker, days_since_ipo, close_price FROM price_history", conn)

    conn.close()

    rows = []
    for _, ipo in ipos.iterrows():
        if pd.isna(ipo["day1_close"]):
            continue  # no price history fetched yet for this ticker

        ticker_hist = history[history["ticker"] == ipo["ticker"]]

        # Find the closing price closest to MATURITY_DAYS after IPO.
        # Only usable if the stock has actually been trading that long.
        candidates = ticker_hist[ticker_hist["days_since_ipo"] >= MATURITY_DAYS]
        if candidates.empty:
            continue  # too young to have 90-day-out data yet

        price_at_maturity = candidates.sort_values("days_since_ipo").iloc[0]["close_price"]

        day1_pop_pct = (ipo["day1_close"] - ipo["offer_price"]) / ipo["offer_price"]
        label = 1 if price_at_maturity > ipo["offer_price"] else 0

        rows.append({
            "ticker": ipo["ticker"],
            "offer_price": ipo["offer_price"],
            "day1_pop_pct": day1_pop_pct,
            "label": label,
        })

    return pd.DataFrame(rows)


def train():
    df = load_training_data()

    if len(df) < 4:
        print(f"Only {len(df)} usable training examples found "
              f"(need mature IPOs with >= {MATURITY_DAYS} days of history).")
        print("Run fetch_prices.py first, and/or add more historical IPOs to seed_data.py.")
        return

    X = df[["offer_price", "day1_pop_pct"]]
    y = df["label"]

    model = LogisticRegression()
    model.fit(X, y)

    joblib.dump(model, MODEL_PATH)

    print(f"Trained on {len(df)} IPOs:")
    print(df[["ticker", "offer_price", "day1_pop_pct", "label"]].to_string(index=False))
    print(f"\nModel saved to {MODEL_PATH}")


if __name__ == "__main__":
    train()
