# pages/01_Store_Live_Ops.py
import streamlit as st
import pandas as pd
import plotly.express as px

from ui import inject, kpi
from shop_mapping import SHOP_OPTIONS
from utils_pfmx import (
    fetch_live_locations,
    fetch_report,
    fetch_report_hourly,                 # requires the hourly helper added earlier
    normalize_report_days_to_df,
    normalize_report_hourly_to_df,       # requires the hourly normalizer added earlier
)

st.set_page_config(page_title="Store Live Ops", layout="wide")
inject()

st.title("Store Live Ops")

# --- Controls -----------------------------------------------------------------
top1, top2, top3, top4 = st.columns([2, 1.2, 1.2, 1.6])
with top1:
    store_label = st.selectbox("Store", list(SHOP_OPTIONS.keys()))
    shop_id = SHOP_OPTIONS[store_label]

with top2:
    mode = st.radio("Modus", ["Live", "Dag", "Uur"], horizontal=True)

with top3:
    conv_target = st.slider("Conversie target (%)", 5, 50, 25, 1)
with top4:
    spv_target = st.slider("SPV target (€)", 0, 200, 30, 1)

# Periode selectors (alleen voor Dag/Uur)
per_col1, per_col2, per_col3 = st.columns([1.2, 1.2, 2])
period = None
date_from = None
date_to = None
if mode in ("Dag", "Uur"):
    with per_col1:
        period = st.selectbox(
            "Periode",
            ["today", "yesterday", "this_week", "last_week", "this_month", "last_month", "date"],
            index=4 if mode == "Dag" else 3,
        )
    with per_col2:
        # optioneel group_by etc. (bewust minimal)
        pass
    with per_col3:
        if period == "date":
            d1, d2 = st.columns(2)
            with d1:
                date_from = st.text_input("date_from (YYYY-MM-DD)", value="")
            with d2:
                date_to = st.text_input("date_to (YYYY-MM-DD)", value="")

st.divider()

# --- Helper formatters ---------------------------------------------------------
def eur(v, decimals=0):
    try:
        fmt = f"€{{:,.{decimals}f}}".format(float(v))
        return fmt.replace(",", "@").replace(".", ",").replace("@", ".")
    except Exception:
        return v

def pct(v, decimals=1):
    try:
        return f"{float(v):,.{decimals}f}%".format(v).replace(",", "@").replace(".", ",").replace("@",".")
    except Exception:
        return v

def conv_to_pct(x):
    # accepteert 0.23 of 23 → maakt er % van
    try:
        x = float(x)
        return x * 100 if x <= 1 else x
    except Exception:
        return 0.0

# --- Render per modus ----------------------------------------------------------
if mode == "Live":
    st.subheader("Live bezetting (occupancy)")
    try:
        payload = fetch_live_locations(shop_ids=[shop_id])  # POST naar /live-inside, source=locations
        # payload kan variëren; probeer te tonen zoals binnenkomt
        if isinstance(payload, dict) and "data" in payload:
            data = payload["data"]
            if isinstance(data, dict):
                df = pd.DataFrame.from_dict(data, orient="index").reset_index().rename(columns={"index":"shop_id"})
            else:
                df = pd.DataFrame(data)
        elif isinstance(payload, dict):
            df = pd.DataFrame([payload])
        else:
            df = pd.DataFrame(payload)

        if not df.empty and "shop_id" in df.columns:
            df["shop_id"] = pd.to_numeric(df["shop_id"], errors="coerce").astype("Int64")
        st.dataframe(df, use_container_width=True)

        # compacte KPI weergave indien kolommen bestaan
        cols = st.columns(4)
        if "occupancy" in df.columns:
            with cols[0]: kpi("Occupancy", f"{int(df['occupancy'].iloc[0])}" if pd.notna(df['occupancy'].iloc[0]) else "-", "neutral")
        if "in_store" in df.columns:
            with cols[1]: kpi("In store nu", f"{int(df['in_store'].iloc[0])}" if pd.notna(df['in_store'].iloc[0]) else "-", "neutral")
        if "enter" in df.columns:
            with cols[2]: kpi("Enter (5m)", f"{int(df['enter'].iloc[0])}" if pd.notna(df['enter'].iloc[0]) else "-", "neutral")
        if "exit" in df.columns:
            with cols[3]: kpi("Exit (5m)", f"{int(df['exit'].iloc[0])}" if pd.notna(df['exit'].iloc[0]) else "-", "neutral")

    except Exception as e:
        st.error(f"Live call failed: {e}")

elif mode == "Dag":
    st.subheader("Dag KPI’s")
    try:
        kwargs = dict(
            data=[shop_id],
            data_output=["turnover", "conversion_rate", "sales_per_visitor", "count_in"],
            source="shops",
            period=period,
            period_step="day",
        )
        if period == "date":
            if not date_from or not date_to:
                st.warning("Vul date_from en date_to in (YYYY-MM-DD).")
            else:
                kwargs["date_from"] = date_from
                kwargs["date_to"] = date_to

        payload = fetch_report(**kwargs)  # POST naar /get-report
        df = normalize_report_days_to_df(payload)
        if df.empty:
            st.warning("Geen dagdata gevonden.")
        else:
            st.dataframe(df, use_container_width=True)

            latest = df.iloc[-1]
            conv = conv_to_pct(latest.get("conversion_rate", 0))
            spv = float(latest.get("sales_per_visitor", 0) or 0)
            tnr = float(latest.get("turnover", 0) or 0)
            cnt = int(latest.get("count_in", 0) or 0)

            c1, c2, c3, c4 = st.columns(4)
            with c1: kpi("Conversie", pct(conv, 1), "good" if conv >= conv_target else "bad")
            with c2: kpi("SPV", eur(spv, 2), "good" if spv >= spv_target else "bad")
            with c3: kpi("Bezoekers", f"{cnt:,}".replace(",", "."), "neutral")
            with c4: kpi("Omzet", eur(tnr, 0), "neutral")

            # Kleine trendplot
            plot_df = df.copy()
            plot_df["conv_pct"] = plot_df["conversion_rate"].apply(conv_to_pct)
            fig = px.line(plot_df, x="date", y=["sales_per_visitor", "conv_pct"], title="Trend: SPV en Conversie (%)")
            st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"Report call failed: {e}")

elif mode == "Uur":
    st.subheader("Uur KPI’s")
    try:
        kwargs = dict(
            data=[shop_id],
            data_output=["turnover", "conversion_rate", "sales_per_visitor", "count_in"],
            source="shops",
            period=period,  # bv. last_week
        )
        if period == "date":
            if not date_from or not date_to:
                st.warning("Vul date_from en date_to in (YYYY-MM-DD).")
            else:
                kwargs["date_from"] = date_from
                kwargs["date_to"] = date_to

        payload = fetch_report_hourly(**kwargs)  # POST met period_step="hour"
        hdf = normalize_report_hourly_to_df(payload)
        if hdf.empty:
            st.warning("Geen hourly data gevonden.")
        else:
            # Toon tabel
            st.dataframe(hdf, use_container_width=True)

            # Conversie% en SPV per uur plot
            plot_df = hdf.copy()
            if "conversion_rate" in plot_df.columns:
                plot_df["conv_pct"] = plot_df["conversion_rate"].apply(conv_to_pct)
            # Combineer date + timestamp voor x-as (als aanwezig)
            if "timestamp" in plot_df.columns:
                plot_df["x"] = plot_df["date"].astype(str) + " " + plot_df["timestamp"].astype(str)
            else:
                plot_df["x"] = plot_df["date"].astype(str)

            tcol1, tcol2 = st.columns(2)
            with tcol1:
                fig1 = px.line(plot_df, x="x", y="sales_per_visitor", title="SPV per uur")
                fig1.add_hline(y=spv_target, line_dash="dot")
                st.plotly_chart(fig1, use_container_width=True)
            with tcol2:
                fig2 = px.line(plot_df, x="x", y="conv_pct", title="Conversie (%) per uur")
                fig2.add_vline(x=None)  # no-op; enkel placeholder als je markers wilt
                st.plotly_chart(fig2, use_container_width=True)

            # Laatste uur → KPI cards vs targets (indien bruikbaar)
            latest = plot_df.iloc[-1]
            conv = float(latest.get("conv_pct", 0))
            spv = float(latest.get("sales_per_visitor", 0) or 0)
            tnr = float(latest.get("turnover", 0) or 0)
            cnt = int(latest.get("count_in", 0) or 0)
            c1, c2, c3, c4 = st.columns(4)
            with c1: kpi("Conversie (laatste uur)", pct(conv, 1), "good" if conv >= conv_target else "bad")
            with c2: kpi("SPV (laatste uur)", eur(spv, 2), "good" if spv >= spv_target else "bad")
            with c3: kpi("Bezoekers (uur)", f"{cnt:,}".replace(",", "."), "neutral")
            with c4: kpi("Omzet (uur)", eur(tnr, 0), "neutral")

    except Exception as e:
        st.error(f"Hourly call failed: {e}")

# Hint onderaan
st.caption("Alle API-calls zijn POST met herhaalde keys zonder [] voor data & data_output; live = /live-inside (source=locations), report = /get-report (source=shops).")
