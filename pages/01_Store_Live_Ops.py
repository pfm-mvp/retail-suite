# pages/01_Store_Live_Ops.py
import streamlit as st
import pandas as pd
from shop_mapping import SHOP_OPTIONS
from utils_pfmx import fetch_live_locations, fetch_report, normalize_report_days_to_df

st.set_page_config(page_title="Store Live Ops", layout="wide")

st.title("Store Live Ops - Testversie")

store_label = st.selectbox("Store", list(SHOP_OPTIONS.keys()))
shop_id = SHOP_OPTIONS[store_label]

mode = st.radio("Modus", ["Live", "Dag"], horizontal=True)

if mode == "Live":
    st.subheader("Live bezetting")
    try:
        payload = fetch_live_locations(shop_ids=[shop_id])
        st.write(payload)
    except Exception as e:
        st.error(f"Live call failed: {e}")

elif mode == "Dag":
    st.subheader("Dag KPI’s")
    try:
        payload = fetch_report(
            data=[shop_id],
            data_output=["turnover", "conversion_rate", "sales_per_visitor", "count_in"],
            source="shops",
            period="today",
            period_step="day",
        )
        df = normalize_report_days_to_df(payload)
        st.dataframe(df)
    except Exception as e:
        st.error(f"Report call failed: {e}")
