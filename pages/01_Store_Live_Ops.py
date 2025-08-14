import streamlit as st
import pandas as pd
from ui import inject, kpi
from utils_pfmx import fetch_live_locations, fetch_report, normalize_report_days_to_df
from shop_mapping import SHOP_OPTIONS

st.set_page_config(page_title="Store Live Ops", layout="wide")
inject()

st.title("Store Live Ops")

colA, colB, colC = st.columns([2,1,1])
with colA:
    store_label = st.selectbox("Select store", list(SHOP_OPTIONS.keys()))
    shop_id = SHOP_OPTIONS[store_label]
with colB:
    conv_target = st.slider("Conversie target (%)", 5, 50, 25, 1)
with colC:
    spv_target = st.slider("SPV target (€)", 0, 200, 30, 1)

st.subheader("Live bezetting (occupancy)")
try:
    live_payload = fetch_live_locations(shop_ids=[shop_id])  # POST /live-inside, source=locations
    live_df = pd.DataFrame(live_payload if isinstance(live_payload, list) else [live_payload]) if isinstance(live_payload, (list,)) else pd.DataFrame(live_payload)
    # fallback via normalizer (payload structure can vary)
    if live_df.empty and isinstance(live_payload, dict):
        from utils_pfmx import normalize_live_to_df
        live_df = normalize_live_to_df(live_payload)
    st.dataframe(live_df, use_container_width=True)
except Exception as e:
    st.error(f"Live call failed: {e}")

st.subheader("Dag KPI’s (vandaag)")
try:
    payload = fetch_report(
        data=[shop_id],
        data_output=["turnover","conversion_rate","sales_per_visitor","count_in"],
        source="shops",
        period="today",
        period_step="day",
    )
    df = normalize_report_days_to_df(payload)
    st.dataframe(df, use_container_width=True)

    if not df.empty:
        latest = df.iloc[-1]
        conv_raw = latest.get("conversion_rate", 0)
        conv = float(conv_raw)*100 if isinstance(conv_raw, (int,float)) and conv_raw <= 1 else float(conv_raw or 0)
        spv = float(latest.get("sales_per_visitor", 0) or 0)
        tnr = float(latest.get("turnover", 0) or 0)
        cnt = int(latest.get("count_in", 0) or 0)

        c1,c2,c3,c4 = st.columns(4)
        with c1: kpi("Conversie", f"{conv:,.1f}%".replace(",", "@").replace(".", ",").replace("@","."), "good" if conv >= conv_target else "bad")
        with c2: kpi("SPV", f"€{spv:,.2f}".replace(",", "@").replace(".", ",").replace("@","."), "good" if spv >= spv_target else "bad")
        with c3: kpi("Bezoekers", f"{cnt:,}".replace(",", "."), "neutral")
        with c4: kpi("Omzet", f"€{tnr:,.0f}".replace(",", "@").replace(".", ",").replace("@","."), "neutral")
except Exception as e:
    st.error(f"Report call failed: {e}")
