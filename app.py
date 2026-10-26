from __future__ import annotations

from pathlib import Path
import pandas as pd
import streamlit as st

from db import load_config, load_daily_bars, read_table
from actionable_engine import classify_tlt_daily_state, build_actionable_rows, stock_has_recent_bearish_reversal, build_weekly_resistance_snapshot, attach_weekly_resistance_target


st.set_page_config(
    page_title="TLT Actionable Trade Dashboard",
    page_icon="📈",
    layout="wide",
)

cfg = load_config()

APP_DIR = Path(__file__).resolve().parent

db_path = Path(cfg["database"]["path"])

if not db_path.is_absolute():
    db_path = APP_DIR / db_path

ref = cfg["analysis"]["reference_symbol"].upper()
action_cfg = cfg.get("dashboard", {}).get("actionable", {})

# ---------- Styling ----------
st.markdown("""
<style>
.block-container {padding-top: 1.6rem; padding-bottom: 2rem; max-width: 1500px;}
h1 {font-size: 2.0rem !important; margin-bottom: 0.1rem !important;}
.small-muted {color:#6b7280; font-size:0.90rem;}
.state-card {
    padding: 1.15rem 1.35rem;
    border-radius: 14px;
    border: 1px solid rgba(128,128,128,.25);
    margin: .5rem 0 1.2rem 0;
}
.state-active {background: rgba(22,163,74,.10); border-left: 7px solid #16a34a;}
.state-hold {background: rgba(220,38,38,.10); border-left: 7px solid #dc2626;}
.state-neutral {background: rgba(234,179,8,.10); border-left: 7px solid #eab308;}
.state-title {font-size:1.35rem; font-weight:750; margin-bottom:.25rem;}
.state-detail {font-size:.98rem; line-height:1.45;}
.section-title {font-size:1.2rem; font-weight:700; margin-top:.6rem;}
div[data-testid="stMetric"] {
    border: 1px solid rgba(128,128,128,.18);
    padding: .65rem .8rem;
    border-radius: 10px;
}

div[data-testid="stDataFrame"] {
    font-size: 0.88rem;
}
</style>
""", unsafe_allow_html=True)

st.title("TLT Actionable Trade Dashboard")
st.caption("Client Dashboard v2.9.3.2")
st.markdown(
    '<div class="small-muted">Daily TLT swing state and stocks currently moving in sync or within their normal 1–15 trading-day response window.</div>',
    unsafe_allow_html=True
)

if not Path(db_path).exists():
    st.error(f"Database not found: {db_path}")
    st.stop()

# ---------- Load source ----------
try:
    bars = load_daily_bars(cfg)
except Exception as e:
    st.error(f"Could not load market data: {e}")
    st.stop()

tlt = bars[bars["symbol"] == ref].copy()
required_ohlc = {"open", "high", "low", "close"}
if not required_ohlc.issubset(tlt.columns):
    st.error(
        "The configured source table must contain open, high, low and close columns "
        "for the TLT candlestick reversal check."
    )
    st.stop()

state = classify_tlt_daily_state(
    tlt,
    reversal_lookback=int(action_cfg.get("reversal_lookback_bars", 3)),
    swing_lookback=int(action_cfg.get("swing_lookback_bars", 5)),
)

expected = read_table(db_path, "tlt_expected_moves_day")

# Build stock-specific bearish reversal map for current follower candidates.
stock_reversals = {}
if not expected.empty and "ticker" in expected.columns:
    candidate_tickers = sorted(set(expected["ticker"].dropna().astype(str).str.upper()))
    for ticker in candidate_tickers:
        sb = bars[bars["symbol"] == ticker].copy()
        has_rev, pattern, rev_date = stock_has_recent_bearish_reversal(sb, lookback=3)
        stock_reversals[ticker] = {
            "has_reversal": has_rev,
            "pattern": pattern,
            "date": rev_date,
        }

actions = build_actionable_rows(
    expected,
    state,
    max_lag=15,
    latest_market_date=state.asof_date,
    stock_reversals=stock_reversals,
)
weekly_resistance_snapshot = build_weekly_resistance_snapshot(
    bars,
    lookback_weeks=104,
    pivot_left=2,
    pivot_right=2,
)
actions = attach_weekly_resistance_target(actions, weekly_resistance_snapshot)



def _style_client_table(df):
    if df.empty:
        return df

    def style_row(row):
        styles = [""] * len(row)
        col_index = {c: i for i, c in enumerate(row.index)}

        action = str(row.get("Action", ""))
        signal = str(row.get("Signal", ""))
        confidence = str(row.get("Confidence", ""))
        timing = str(row.get("Timing", ""))

        if "Action" in col_index:
            if action == "ACTIONABLE NOW":
                styles[col_index["Action"]] = "background-color: rgba(22,163,74,.22); font-weight:700;"
            elif action == "MOVE IN PROGRESS":
                styles[col_index["Action"]] = "background-color: rgba(34,197,94,.14); font-weight:600;"
            elif action == "WATCH / APPROACHING":
                styles[col_index["Action"]] = "background-color: rgba(234,179,8,.18); font-weight:600;"
            elif action == "HOLD":
                styles[col_index["Action"]] = "background-color: rgba(220,38,38,.20); font-weight:700;"

        if "Signal" in col_index:
            if signal in ("Due now", "Responding", "Responded early"):
                styles[col_index["Signal"]] = "background-color: rgba(22,163,74,.14);"
            elif signal == "Approaching":
                styles[col_index["Signal"]] = "background-color: rgba(234,179,8,.14);"

        if "Confidence" in col_index:
            if confidence == "STRONG":
                styles[col_index["Confidence"]] = "background-color: rgba(22,163,74,.20); font-weight:700;"
            elif confidence == "GOOD":
                styles[col_index["Confidence"]] = "background-color: rgba(59,130,246,.14); font-weight:600;"
            else:
                styles[col_index["Confidence"]] = "background-color: rgba(234,179,8,.12);"

        if "Timing" in col_index:
            if timing == "IN SYNC":
                styles[col_index["Timing"]] = "background-color: rgba(22,163,74,.12); font-weight:600;"
            elif "1-DAY" in timing or "2-DAY" in timing or "3-DAY" in timing:
                styles[col_index["Timing"]] = "background-color: rgba(59,130,246,.10);"
            else:
                styles[col_index["Timing"]] = "background-color: rgba(168,85,247,.09);"

        return styles

    return df.style.apply(style_row, axis=1)

# ---------- Top status ----------
if state.state == "ACTIVE":
    css_class = "state-active"
elif state.state == "HOLD":
    css_class = "state-hold"
else:
    css_class = "state-neutral"

asof = state.asof_date.strftime("%Y-%m-%d") if state.asof_date is not None else "—"
reversal_note = ""
if state.reversal_pattern and state.reversal_date is not None:
    reversal_note = (
        f"<br><b>Latest reversal:</b> {state.reversal_pattern} "
        f"({state.reversal_date:%Y-%m-%d})"
    )

st.markdown(
    f"""
    <div class="state-card {css_class}">
      <div class="state-title">{state.headline}</div>
      <div class="state-detail">{state.detail}{reversal_note}</div>
    </div>
    """,
    unsafe_allow_html=True,
)

m1, m2, m3, m4 = st.columns(4)
m1.metric("TLT As Of", asof)
m2.metric("TLT Close", f"{state.close:.2f}" if state.close is not None else "—")
m3.metric(
    "Current Swing",
    f"{state.swing_return*100:+.2f}%" if state.swing_return is not None else "—"
)
m4.metric(
    "Actionable Universe",
    int((actions["Action"] == "ACTIONABLE NOW").sum()) if not actions.empty else 0
)

# ---------- Hold behavior ----------
if state.state == "HOLD":
    st.error(
        "NEW POSITIVE TLT-FOLLOWER TRADES ARE ON HOLD. "
        "The follower list remains visible below as a watch list, but new long entries "
        "should wait for TLT to establish a fresh positive daily swing."
    )
elif state.state == "NEUTRAL":
    st.warning(
        "TLT is not in a confirmed positive daily swing. "
        "Use the follower list as a watch list until the positive swing reappears."
    )

# Entry-quality visibility control.
show_overextended = st.toggle(
    "Show overextended stocks",
    value=False,
    help="Show stocks currently overextended above their 200-day moving average.",
)

if not show_overextended and actions is not None and not actions.empty and "MA200 Entry" in actions.columns:
    actions = actions[actions["MA200 Entry"] != "TOO FAR ABOVE 200DMA"].copy()

if actions.empty:
    st.info(
        "No Daily follower signals are currently available in `tlt_expected_moves_day`. "
        "Run `python run_analysis.py` to refresh the analysis."
    )
    st.stop()

# Keep only client-facing fields.
actions_display = actions.copy()

# Guarantee target fields exist before building any grids.
for c in ["Weekly Target", "Potential Upside", "200DMA Distance"]:
    if c not in actions_display.columns:
        actions_display[c] = "—"

display_cols = [
    "ticker",
    "Timing",
    "Expected",
    "Signal",
    "Confidence",
    "200DMA Distance",
    "Weekly Target",
    "Potential Upside",
    "Action",
    "Stock Reversal",
    "normal_lag",
]

for c in display_cols:
    if c not in actions_display.columns:
        actions_display[c] = "—"

display = actions_display[display_cols].copy()
display = display.rename(columns={"ticker":"Symbol"})

# Safety: the client-facing dashboard must never expose technical "bar(s)" language.
if "Expected" in display.columns:
    display["Expected"] = (
        display["Expected"]
        .astype(str)
        .str.replace("bar(s)", "trading days", regex=False)
        .str.replace("bar", "trading day", regex=False)
    )

# ---------- Actionable now ----------
now = display[display["Action"] == "ACTIONABLE NOW"].copy()
st.markdown('<div class="section-title">Actionable Now</div>', unsafe_allow_html=True)
if now.empty:
    st.caption("No stocks are due for a new TLT-following move right now.")
else:
    now_display = now.drop(columns=["normal_lag"])
    st.dataframe(
        _style_client_table(now_display),
        width="stretch",
        hide_index=True,
        column_config={
            "Symbol": st.column_config.TextColumn("Symbol", width="small"),
            "Timing": st.column_config.TextColumn("TLT Relationship", width="medium"),
            "Expected": st.column_config.TextColumn("Expected / Response Date", width="large"),
            "Signal": st.column_config.TextColumn("Current Signal", width="medium"),
            "Confidence": st.column_config.TextColumn("Confidence", width="medium"),
            "Action": st.column_config.TextColumn("Trade State", width="medium"),
        }
    )

# ---------- Timing buckets ----------
def bucket_full(title, sub, mask):
    st.markdown(f"### {title}")
    st.caption(sub)
    d = display[mask].copy()
    if d.empty:
        st.caption("No current candidates.")
        return

    d = d.sort_values(["Action", "Symbol"])
    cols = ["Symbol", "Expected", "Signal", "Confidence", "200DMA Distance", "Weekly Target", "Potential Upside", "Action"]
    if d["normal_lag"].min() >= 4:
        cols.append("Stock Reversal")
    safe_cols = [c for c in cols if c in d.columns]
    bucket_display = d[safe_cols]

    st.dataframe(
        _style_client_table(bucket_display),
        width="stretch",
        hide_index=True,
        row_height=34,
        column_config={
            "Symbol": st.column_config.TextColumn("Symbol", width="small"),
            "Expected": st.column_config.TextColumn("Expected", width="large"),
            "Signal": st.column_config.TextColumn("Signal", width="medium"),
            "Confidence": st.column_config.TextColumn("Confidence", width="medium"),
            "200DMA Distance": st.column_config.TextColumn("Vs 200DMA", width="small"),
            "Weekly Target": st.column_config.TextColumn("Weekly Target", width="small"),
            "Potential Upside": st.column_config.TextColumn("Upside", width="small"),
            "Action": st.column_config.TextColumn("Action", width="medium"),
            "Stock Reversal": st.column_config.TextColumn("Stock Reversal", width="large"),
        },
    )

bucket_full(
    "In Sync",
    "Normal response: same trading day",
    display["normal_lag"] == 0,
)

bucket_full(
    "Near-Term Followers",
    "Normal response: 1–3 trading days after TLT",
    display["normal_lag"].between(1, 3),
)

bucket_full(
    "Mid-Lag Followers",
    "Normal response: 4–7 trading days after TLT",
    display["normal_lag"].between(4, 7),
)

bucket_full(
    "Extended Lag Followers",
    "Normal response: 8–15 trading days after TLT",
    display["normal_lag"].between(8, 15),
)

# ---------- Watch / moving ----------
st.markdown('<div class="section-title">Current TLT Follower Watch List</div>', unsafe_allow_html=True)
watch = display.sort_values(["normal_lag", "Symbol"]).drop(columns=["normal_lag"])
st.dataframe(
    _style_client_table(watch),
    width="stretch",
    hide_index=True,
    row_height=34,
    column_config={
        "Symbol": st.column_config.TextColumn("Symbol", width="small"),
        "Timing": st.column_config.TextColumn("Timing", width="medium"),
        "Expected": st.column_config.TextColumn("Expected", width="large"),
        "Signal": st.column_config.TextColumn("Signal", width="medium"),
        "Confidence": st.column_config.TextColumn("Confidence", width="medium"),
            "200DMA Distance": st.column_config.TextColumn("Vs 200DMA", width="small"),
            "Weekly Target": st.column_config.TextColumn("Weekly Target", width="small"),
            "Potential Upside": st.column_config.TextColumn("Upside", width="small"),
            "Action": st.column_config.TextColumn("Action", width="medium"),
    },
)

with st.expander("How this dashboard decides whether a setup is active"):
    st.markdown("""
**TLT ACTIVE:** TLT is in a short Daily upward swing and there is no unresolved bearish reversal candle.

**TLT ON HOLD:** a bearish Daily reversal formation is detected during the upswing.

For **Lag 0-3** stocks, the overall TLT hold blocks new near-term entries.

For **Lag 4-15** stocks, the setup remains on the watch list and is not automatically marked HOLD. A Mid-Lag or Extended-Lag stock is marked HOLD only when that individual stock shows its own bearish Daily reversal candlestick.

**Bearish reversal formations checked:** Bearish Engulfing, Shooting Star, Dark Cloud Cover, Evening Star, and Bearish Harami.

**Follower timing:** the dashboard reads the existing Daily lead/lag output and groups stocks into same-day, 1–3 day, 4–7 day, and 8–15 day response windows. The detailed research metrics remain available in the original analysis dashboard.
""")


# MA200 entry overlay:
# Red "TOO FAR ABOVE 200DMA" = overextended; avoid chasing.
# Green "GOOD ENTRY / SHORT SQUEEZE" = materially below 200DMA; potential squeeze/reversion entry.
