# Debut

A live-updating dashboard that tracks IPOs, pulls real price history,
and uses a simple ML model to flag whether a recent IPO is trending more
like a historical winner or a historical loser.

Built as a learning project to practice: working with real financial data
APIs, designing a small SQLite schema, feature engineering, training a
basic classification model, and shipping it as an interactive app.

> ** This is an educational/portfolio project, not financial advice.**
> The prediction model is trained on a small, hand-picked set of past IPOs
> and should not be used to make real investment decisions.

## What it does

- **Tracks IPOs** — company, IPO date, offer price, live current price, % change
- **Live price updates** — pulls real data from Yahoo Finance via `yfinance`
- **Trajectory comparison** — plots a chosen IPO's price movement since
  listing day against other IPOs (winners and losers), normalized by
  % change from offer price, so patterns are easy to compare visually
- **Simple buy/sell-style signal** — a logistic regression model predicts
  whether an IPO is likely to be trading above its offer price 90 days
  after listing, based on offer price and first-day price movement
- **Add your own IPOs** — track any ticker with its IPO date and offer price

## Tech stack & why

| Piece | Choice | Why |
|---|---|---|
| Language | Python | One language across data, model, and UI |
| Data | `yfinance` | Free, no API key, reliable historical price data |
| Storage | SQLite | Zero setup, file-based, easy to swap for Postgres later |
| Model | scikit-learn (Logistic Regression) | Simple, explainable, appropriate for a small dataset |
| UI | Streamlit | Live-updating, interactive web dashboard in pure Python |

## Project structure

```
debut/
├── data/
│   ├── setup_db.py       # creates the SQLite schema
│   ├── seed_data.py      # loads a starter list of real IPOs
│   └── fetch_prices.py   # pulls live/historical prices via yfinance
├── model/
│   ├── train_model.py    # trains the logistic regression model
│   └── predict.py        # loads the model, returns a signal + confidence
├── app/
│   └── dashboard.py       # the Streamlit app
├── requirements.txt
└── README.md
```

## Setup & run locally

```bash
git clone <your-repo-url>
cd debut
pip install -r requirements.txt

# 1. Create the database
python data/setup_db.py

# 2. Load starter IPOs
python data/seed_data.py

# 3. Pull real price history (needs internet)
python data/fetch_prices.py

# 4. Train the model
python model/train_model.py

# 5. Launch the dashboard
streamlit run app/dashboard.py
```

The app opens at `http://localhost:8501`. Click **"🔄 Refresh live prices"**
in the sidebar any time to pull the latest prices.

## How the model works

Two features, available within a day or two of an IPO listing:

- **Offer price** — the price shares were sold at before trading opened
- **Day-1 pop %** — how much the stock moved on its first trading day

The model predicts the probability the stock will be trading **above its
offer price ~90 days later**, based on how similar past IPOs behaved.

This is intentionally simple. With only a handful of historical IPOs to
train on, it won't be statistically robust — the goal here was to build
and demonstrate the full pipeline (data → features → model → app), not
to produce a production-grade forecasting system.

## Possible next steps

- Swap the manual "add IPO" form for a live IPO calendar API (e.g. FMP)
  to auto-discover new IPOs
- Add more features to the model: sector, deal size, market conditions
  at time of listing
- Expand the training set with a larger historical IPO dataset
- Deploy for free on Streamlit Community Cloud for a live public link
- Add scheduled background refresh instead of manual refresh
