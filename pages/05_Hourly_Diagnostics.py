import streamlit as st
import pandas as pd
from ui import inject
from utils_pfmx import fetch_report_hourly, normalize_report_hourly_to_df
from shop_mapping import SHOP_OPTIONS

st.set_page_config(page_title="Hourly Diagnostics", layout="wide")
inject()

st.title("Hourly Diagnostics")

store = st.selectbox("Store", list(SHOP_OPTIONS.keys()))
shop_id = SHOP_OPTIONS[store]

period = st.selectbox("Periode", ["today","yesterday","this_week","last_week","this_month","last_month","date"], index=3)

date_from = st.text_input("date_from (YYYY-MM-DD)", value="")
date_to = st.text_input("date_to (YYYY-MM-DD)", value="")

if st.button("Fetch hourly"):
    kwargs = dict(
        data=[shop_id],
        data_output=["turnover","conversion_rate","sales_per_visitor","count_in"],
        source="shops",
        period=period,
    )
    if period == "date":
        kwargs["date_from"] = date_from or None
        kwargs["date_to"] = date_to or None

    try:
        payload = fetch_report_hourly(**kwargs)
        df = normalize_report_hourly_to_df(payload)
        st.write("Rows:", len(df))
        st.dataframe(df, use_container_width=True)
    except Exception as e:
        st.error(f"Hourly call failed: {e}")
