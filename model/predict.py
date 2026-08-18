"""
predict.py
----------
Small helper that loads the trained model and turns raw IPO features
into a human-facing signal ("Bullish" / "Bearish") with a confidence
percentage. Used by the Streamlit app.
"""

import os
import joblib
import pandas as pd

MODEL_PATH = os.path.join(os.path.dirname(__file__), "ipo_model.pkl")

_model = None


def _load_model():
    global _model
    if _model is None:
        if not os.path.exists(MODEL_PATH):
            return None
        _model = joblib.load(MODEL_PATH)
    return _model


def predict_signal(offer_price: float, day1_close: float | None):
    """
    Returns a dict: {"signal": str, "confidence": float} or None if the
    model isn't trained yet or we don't have enough info (e.g. IPO
    hasn't started trading, so no day1_close yet).
    """
    model = _load_model()
    if model is None or day1_close is None:
        return None

    day1_pop_pct = (day1_close - offer_price) / offer_price
    X = pd.DataFrame([[offer_price, day1_pop_pct]], columns=["offer_price", "day1_pop_pct"])

    proba = model.predict_proba(X)[0]  # [P(class=0), P(class=1)]
    prob_outperform = proba[1]

    signal = "Bullish" if prob_outperform >= 0.5 else "Bearish"
    confidence = max(prob_outperform, 1 - prob_outperform)

    return {"signal": signal, "confidence": round(confidence * 100, 1)}
