# streamlit_app.py
import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import datetime as dt
import random
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="Terminal Screener", layout="wide")

# ---------- CONFIG ----------
TOP_STOCKS = [
    "RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS",
    "SBIN.NS", "ITC.NS", "BAJFINANCE.NS", "AXISBANK.NS", "MARUTI.NS",
    "HDFC.NS", "LT.NS", "HINDUNILVR.NS", "SUNPHARMA.NS", "TATASTEEL.NS"
]

TOP_TICKER_LIST = [
    "SUNPHARMA.NS","HINDUNILVR.NS","POWERGRID.NS","TATASTEEL.NS","LT.NS",
    "KOTAKBANK.NS","NTPC.NS","ULTRACEMCO.NS","ONGC.NS","WIPRO.NS",
    "HCLTECH.NS","BHARTIARTL.NS","ADANIENT.NS","ADANIPORTS.NS","DIVISLAB.NS",
    "BRITANNIA.NS","TITAN.NS","EICHERMOT.NS","M&M.NS","GRASIM.NS",
]  # trim as needed

REFRESH_SECONDS = 60  # how often the app fetches fresh data (seconds)

# ---------- HELPERS ----------
@st.cache_data(ttl=60)
def fetch_latest(tickers):
    """Fetch last price & prev close via yfinance. cached for short ttl"""
    out = {}
    for t in tickers:
        try:
            tk = yf.Ticker(t)
            # small calls — history 1d for intraday last and prev
            df = tk.history(period="2d", interval="1m", auto_adjust=True)
            if df is None or df.empty:
                out[t] = {"price": 0.0, "prev": 0.0}
                continue
            closes = df["Close"].dropna()
            price = float(closes.iloc[-1])
            prev = float(closes.iloc[-2]) if len(closes) >= 2 else price
            out[t] = {"price": price, "prev": prev}
        except Exception:
            out[t] = {"price": 0.0, "prev": 0.0}
    return out

def make_topbar(nifty, sensex):
    col1, col2, col3 = st.columns([1,2,1])
    status = "OPEN" if is_market_open_ist() else "CLOSED"
    col1.markdown(f"**MARKET {status}**")
    col2.markdown(f"**NIFTY:** {nifty:.2f} &nbsp;&nbsp;&nbsp; **SENSEX:** {sensex:.2f}", unsafe_allow_html=True)
    col3.markdown(dt.datetime.now(dt.timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S"))


def is_market_open_ist():
    now = dt.datetime.utcnow() + dt.timedelta(hours=5, minutes=30)
    return (now.hour > 9 or (now.hour == 9 and now.minute >= 15)) and (now.hour < 15 or (now.hour == 15 and now.minute <= 30))


def build_table_df(stock_data):
    rows = []
    for t, v in stock_data.items():
        price = v["price"]
        prev = v["prev"]
        change = price - prev
        pct = (change / prev * 100) if prev else 0.0
        # simulated bid/ask
        spread = max(0.01, price * 0.001)
        bid = max(0.0, price - spread)
        ask = price + spread
        bq = random.randint(100, 2000)
        aq = random.randint(100, 2000)
        rows.append({
            "Stock": t.split(".")[0],
            "Price (₹)": price,
            "Change %": pct,
            "Change ₹": change,
            "Bid": bid,
            "Bid QTY": bq,
            "Ask": ask,
            "Ask QTY": aq,
            "Prev Close": prev
        })
    df = pd.DataFrame(rows)
    # keep ordering as TOP_STOCKS
    df["rank"] = df["Stock"].apply(lambda x: TOP_STOCKS.index(x + ".NS") if (x + ".NS") in TOP_STOCKS else 999)
    df = df.sort_values("rank").drop(columns="rank")
    return df

# ---------- AUTO REFRESH ----------
# Streamlit will rerun the script every REFRESH_SECONDS using st_autorefresh
st_autorefresh(interval=REFRESH_SECONDS * 1000, key="auto_refresh")

# ---------- DATA FETCH ----------
all_tickers = list(dict.fromkeys(TOP_STOCKS + TOP_TICKER_LIST))
data = fetch_latest(all_tickers)

# fetch indices (simple)
try:
    nifty = yf.Ticker("^NSEI").history(period="1d", interval="1m", auto_adjust=True")
    nifty_price = float(nifty["Close"].dropna().iloc[-1])
except Exception:
    nifty_price = 0.0
try:
    sensex = yf.Ticker("^BSESN").history(period="1d", interval="1m", auto_adjust=True")
    sensex_price = float(sensex["Close"].dropna().iloc[-1])
except Exception:
    sensex_price = 0.0

# ---------- LAYOUT ----------
st.title("Terminal Screener — Web")
make_topbar(nifty_price, sensex_price)

c1, c2 = st.columns([3,1], gap="large")

with c1:
    # ticker row (simple text rendering)
    ticker_only = [t for t in TOP_TICKER_LIST if t not in TOP_STOCKS]
    ticker_text = []
    for t in ticker_only:
        rec = data.get(t, {"price":0,"prev":0})
        amt = rec["price"] - rec["prev"]
        pct = (amt / rec["prev"] * 100) if rec["prev"] else 0.0
        color = "green" if amt >= 0 else "#ff4d4d"
        ticker_text.append(f"<span style='color:white'>{t.split('.')[0]}</span> <span style='color:{color}'>{amt:+.2f} ({pct:+.2f}%)</span>")
    st.markdown("  &nbsp;&nbsp;  ".join(ticker_text), unsafe_allow_html=True)

    # main table
    top_df = build_table_df({t: data[t] for t in TOP_STOCKS})
    def highlight(row):
        return ['color: green' if x > 0 else 'color: #ff4d4d' if col in ['Change ₹','Change %'] and (x := row['Change ₹']) else '' for col in row.index]
    st.dataframe(top_df.style.format("{:.2f}", subset=top_df.columns.tolist()), height=600)

with c2:
    st.subheader("Notes")
    st.write("- Auto-refresh every %d sec" % REFRESH_SECONDS)
    st.write("- Data via yfinance (not real-time bids)")

# End
