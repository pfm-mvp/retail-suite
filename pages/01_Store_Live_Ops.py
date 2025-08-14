# pages/01_Store_Live_Ops.py
import streamlit as st
import pandas as pd
import plotly.express as px

from shop_mapping import SHOP_OPTIONS
from utils_pfmx import fetch_live_locations, fetch_report, normalize_report_days_to_df

# Hourly helpers zijn optioneel; app blijft werken als ze ontbreken
try:
    from utils_pfmx import fetch_report_hourly, normalize_report_hourly_to_df
    HAS_HOURLY = True
except Exception:
    HAS_HOURLY = False

st.set_page_config(page_title="Store Live Ops", layout="wide")

st.title("Store Live Ops")

# -------------------- Controls --------------------
c1, c2, c3, c4 = st.columns([2, 1.2, 1.2, 1.6])
with c1:
    store_label = st.selectbox("Store", list(SHOP_OPTIONS.keys()))
    shop_id = SHOP_OPTIONS[store_label]
with c2:
    mode = st.radio("Modus", ["Live", "Dag", "Uur"], horizontal=True)
with c3:
    conv_target = st.slider("Conversie target (%)", 5, 50, 25, 1)
with c4:
    spv_target = st.slider("SPV target (€)", 0, 200, 30, 1)

period = None
date_from = None
date_to = None
if mode in ("Dag", "Uur"):
    pc1, pc2 = st.columns([1.5, 2])
    with pc1:
        period = st.selectbox(
            "Periode",
            ["today", "yesterday", "this_week", "last_week", "this_month", "last_month", "date"],
            index=4 if mode == "Dag" else 3,
        )
    with pc2:
        if period == "date":
            d1, d2 = st.columns(2)
            with d1:
                date_from = st.text_input("date_from (YYYY-MM-DD)", value="")
            with d2:
                date_to = st.text_input("date_to (YYYY-MM-DD)", value="")

st.divider()

# -------------------- Helpers --------------------
def eur(v, decimals=0):
    try:
        v = float(v)
        s = f"{v:,.{decimals}f}"
        s = s.replace(",", "@").replace(".", ",").replace("@", ".")
        return "€" + s
    except Exception:
        return "€0"

def conv_to_pct(x):
    try:
        x = float(x)
        return x * 100.0 if x <= 1.0 else x
    except Exception:
        return 0.0

def fmt_pct(v, decimals=1):
    try:
        v = float(v)
        s = f"{v:,.{decimals}f}"
        s = s.replace(",", "@").replace(".", ",").replace("@", ".")
        return s + "%"
    except Exception:
        return "0%"

# -------------------- Render --------------------
if mode == "Live":
    st.subheader("Live bezetting (occupancy)")
    try:
        payload = fetch_live_locations(shop_ids=[shop_id])

        # Normaliseer payload voorzichtig naar DataFrame
        if isinstance(payload, dict) and "data" in payload and isinstance(payload["data"], dict):
            df = pd.DataFrame.from_dict(payload["data"], orient="index").reset_index().rename(columns={"index": "shop_id"})
        elif isinstance(payload, dict):
            df = pd.DataFrame([payload])
        else:
            df = pd.DataFrame(payload)

        st.dataframe(df, use_container_width=True)

        # Metrics (alleen tonen als kolommen bestaan)
        m1, m2, m3, m4 = st.columns(4)
        if "occupancy" in df.columns:
            val = df["occupancy"].iloc[0]
            m1.metric("Occupancy", f"{int(val) if pd.notna(val) else 0}")
        if "in_store" in df.columns:
            val = df["in_store"].iloc[0]
            m2.metric("In store nu", f"{int(val) if pd.notna(val) else 0}")
        if "enter" in df.columns:
            val = df["enter"].iloc[0]
            m3.metric("Enter (5m)", f"{int(val) if pd.notna(val) else 0}")
        if "exit" in df.columns:
            val = df["exit"].iloc[0]
            m4.metric("Exit (5m)", f"{int(val) if pd.notna(val) else 0}")

    except Exception as e:
        st.error(f"Live call failed: {e}")

elif mode == "Dag":
    st.subheader("Dag KPI's")
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

        payload = fetch_report(**kwargs)
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
            c1.metric("Conversie", fmt_pct(conv), delta="OK" if conv >= conv_target else "Onder target")
            c2.metric("SPV", eur(spv, 2), delta="OK" if spv >= spv_target else "Onder target")
            c3.metric("Bezoekers", f"{cnt:,}".replace(",", "."))
            c4.metric("Omzet", eur(tnr, 0))

            # Trendplot
            plot_df = df.copy()
            plot_df["conv_pct"] = plot_df["conversion_rate"].apply(conv_to_pct)
            fig = px.line(
                plot_df,
                x="date",
                y=["sales_per_visitor", "conv_pct"],
                title="Trend: SPV en Conversie (%)"
            )
            st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"Report call failed: {e}")

elif mode == "Uur":
    st.subheader("Uur KPI's")
    if not HAS_HOURLY:
        st.warning("Hourly helpers ontbreken in utils_pfmx.py. Voeg toe: fetch_report_hourly() en normalize_report_hourly_to_df().")
    else:
        try:
            kwargs = dict(
                data=[shop_id],
                data_output=["turnover", "conversion_rate", "sales_per_visitor", "count_in"],
                source="shops",
                period=period,
            )
            if period == "date":
                if not date_from or not date_to:
                    st.warning("Vul date_from en date_to in (YYYY-MM-DD).")
                else:
                    kwargs["date_from"] = date_from
                    kwargs["date_to"] = date_to

            payload = fetch_report_hourly(**kwargs)
            hdf = normalize_report_hourly_to_df(payload)

            if hdf.empty:
                st.warning("Geen hourly data gevonden.")
            else:
                st.dataframe(hdf, use_container_width=True)

                plot_df = hdf.copy()
                if "conversion_rate" in plot_df.columns:
                    plot_df["conv_pct"] = plot_df["conversion_rate"].apply(conv_to_pct)
                if "timestamp" in plot_df.columns:
                    plot_df["x"] = plot_df["date"].astype(str) + " " + plot_df["timestamp"].astype(str)
                else:
                    plot_df["x"] = plot_df["date"].astype(str)

                lc, rc = st.columns(2)
                with lc:
                    fig1 = px.line(plot_df, x="x", y="sales_per_visitor", title="SPV per uur")
                    st.plotly_chart(fig1, use_container_width=True)
                with rc:
                    fig2 = px.line(plot_df, x="x", y="conv_pct", title="Conversie (%) per uur")
                    st.plotly_chart(fig2, use_container_width=True)

                latest = plot_df.iloc[-1]
                conv = float(latest.get("conv_pct", 0))
                spv = float(latest.get("sales_per_visitor", 0) or 0)
                tnr = float(latest.get("turnover", 0) or 0)
                cnt = int(latest.get("count_in", 0) or 0)

                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Conversie (laatste uur)", fmt_pct(conv), delta="OK" if conv >= conv_target else "Onder target")
                m2.metric("SPV (laatste uur)", eur(spv, 2), delta="OK" if spv >= spv_target else "Onder target")
                m3.metric("Bezoekers (uur)", f"{cnt:,}".replace(",", "."))
                m4.metric("Omzet (uur)", eur(tnr, 0))

        except Exception as e:
            st.error(f"Hourly call failed: {e}")

st.caption("POST + herhaalde keys (zonder []) | Live = /live-inside (source=locations) | Report = /get-report (source=shops)")
