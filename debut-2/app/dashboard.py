"""
dashboard.py
------------
The live-updating IPO dashboard. Run with:

    streamlit run app/dashboard.py

What it does:
  1. Shows every tracked IPO with live current price + % change.
  2. Lets you add a new IPO you want to track.
  3. Lets you pick one IPO and compare its price trajectory (since
     listing day) against a set of past IPOs, so you can visually see
     whether it's tracking more like a "winner" or a "loser".
  4. Shows a simple model-based Bullish/Bearish signal, clearly
     labeled as a demo, not financial advice.
"""

import os
import sys
import sqlite3
from datetime import datetime, date

import pandas as pd
import streamlit as st

# --- make sibling folders importable (data/, model/) ---
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from data.fetch_prices import refresh_all, fetch_and_store_ticker, update_ipo_summary, get_connection
from model.predict import predict_signal

DB_PATH = os.path.join(PROJECT_ROOT, "data", "ipo_data.db")

st.set_page_config(page_title="Debut", layout="wide")


# ---------- data access helpers ----------

def load_ipos() -> pd.DataFrame:
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("SELECT * FROM ipos ORDER BY ipo_date DESC", conn)
    conn.close()
    return df


def load_history(ticker: str) -> pd.DataFrame:
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql(
        "SELECT days_since_ipo, close_price FROM price_history WHERE ticker = ? ORDER BY days_since_ipo",
        conn, params=(ticker,)
    )
    conn.close()
    return df


def add_new_ipo(ticker, company_name, ipo_date_str, offer_price):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        INSERT INTO ipos (ticker, company_name, ipo_date, offer_price)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(ticker) DO UPDATE SET
            company_name=excluded.company_name,
            ipo_date=excluded.ipo_date,
            offer_price=excluded.offer_price
    """, (ticker.upper(), company_name, ipo_date_str, offer_price))
    conn.commit()
    conn.close()


# ---------- UI ----------

st.title("🎬 Debut")
st.caption("*Every IPO's opening night, tracked.*")
st.caption(
    "Educational / portfolio project. Signals shown are from a simple demo "
    "model trained on a handful of past IPOs — **not financial advice.**"
)

with st.sidebar:
    st.header("Controls")

    if st.button("🔄 Refresh live prices", use_container_width=True):
        with st.spinner("Fetching latest prices..."):
            refresh_all()
        st.success("Prices updated.")
        st.rerun()

    st.divider()
    st.subheader("Track a new IPO")
    with st.form("add_ipo_form"):
        new_ticker = st.text_input("Ticker (e.g. AAPL)")
        new_name = st.text_input("Company name")
        new_date = st.date_input("IPO date", value=date.today())
        new_offer_price = st.number_input("Offer price ($)", min_value=0.01, step=0.5)
        submitted = st.form_submit_button("Add & fetch data")

    if submitted and new_ticker and new_name:
        add_new_ipo(new_ticker, new_name, new_date.isoformat(), new_offer_price)
        conn = get_connection()
        with st.spinner(f"Fetching price history for {new_ticker.upper()}..."):
            day1_close, current_price = fetch_and_store_ticker(conn, new_ticker.upper(), new_date.isoformat())
            if day1_close is not None:
                update_ipo_summary(conn, new_ticker.upper(), day1_close, current_price)
        conn.close()
        if day1_close is not None:
            st.success(f"Added {new_ticker.upper()} and fetched its price history.")
        else:
            st.warning(
                f"Added {new_ticker.upper()} to the list, but couldn't fetch price data — "
                f"double-check the ticker symbol is correct, then hit 'Refresh live prices'."
            )
        st.rerun()

# ---------- main table ----------

ipos_df = load_ipos()

if ipos_df.empty:
    st.warning("No IPOs in the database yet. Run `data/seed_data.py` or add one from the sidebar.")
    st.stop()

ipos_df["pct_change"] = (
    (ipos_df["current_price"] - ipos_df["offer_price"]) / ipos_df["offer_price"] * 100
).round(1)

signals = []
for _, row in ipos_df.iterrows():
    sig = predict_signal(row["offer_price"], row["day1_close"])
    if sig:
        signals.append(f"{sig['signal']} ({sig['confidence']}%)")
    else:
        signals.append("—")
ipos_df["model_signal"] = signals

st.subheader("Tracked IPOs")
display_df = ipos_df[[
    "ticker", "company_name", "ipo_date", "offer_price",
    "current_price", "pct_change", "model_signal", "last_updated"
]].rename(columns={
    "ticker": "Ticker", "company_name": "Company", "ipo_date": "IPO Date",
    "offer_price": "Offer $", "current_price": "Current $",
    "pct_change": "% Change", "model_signal": "Model Signal",
    "last_updated": "Last Updated"
})
st.dataframe(display_df, use_container_width=True, hide_index=True)

st.divider()

# ---------- comparison chart ----------

st.subheader("Compare trajectories since IPO day")
st.caption(
    "First 100 trading days since listing. Pick a recent IPO and compare it "
    "against others to see whether it's tracking more like a historical "
    "winner or a historical loser."
)

CHART_WINDOW_DAYS = 100

col1, col2 = st.columns([1, 2])

with col1:
    focus_ticker = st.selectbox("IPO to focus on", ipos_df["ticker"].tolist())
    compare_tickers = st.multiselect(
        "Compare against",
        [t for t in ipos_df["ticker"].tolist() if t != focus_ticker],
        default=[t for t in ipos_df["ticker"].tolist() if t != focus_ticker][:3]
    )

with col2:
    chart_data = {}
    for ticker in [focus_ticker] + compare_tickers:
        hist = load_history(ticker)
        if hist.empty:
            continue
        # Only keep the first 100 trading days since listing, and drop any
        # pre-IPO rows (days_since_ipo < 0) that could sneak in.
        hist = hist[(hist["days_since_ipo"] >= 0) & (hist["days_since_ipo"] <= CHART_WINDOW_DAYS)]
        if hist.empty:
            continue
        offer_price = ipos_df.loc[ipos_df["ticker"] == ticker, "offer_price"].iloc[0]
        hist["pct_change_from_offer"] = (hist["close_price"] - offer_price) / offer_price * 100
        chart_data[ticker] = hist.set_index("days_since_ipo")["pct_change_from_offer"]

    if chart_data:
        combined = pd.DataFrame(chart_data)
        st.line_chart(combined)
        st.caption("X-axis = trading days since IPO (first 100 days). Y-axis = % change from offer price.")
    else:
        st.info("No price history yet for these tickers — click 'Refresh live prices' in the sidebar.")

st.divider()
st.subheader("How the model works")
st.markdown("""
The **Model Signal** column comes from a logistic regression trained on
historical IPOs in this database, using two features available shortly
after an IPO lists:

- **Offer price** — the price shares were sold at pre-listing
- **Day-1 pop %** — how much the stock moved on its first trading day

It predicts the probability that the stock will be trading **above its
offer price 90 days later**. This is intentionally simple and trained
on a small dataset — it's built to demonstrate the ML pipeline, not to
be a reliable trading signal. Always do independent research before
making investment decisions.
""")
