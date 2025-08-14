import streamlit as st
import pandas as pd
from ui import inject
from utils_pfmx import fetch_report, normalize_report_days_to_df
from shop_mapping import SHOP_OPTIONS

st.set_page_config(page_title="Portfolio Benchmark", layout="wide")
inject()

st.title("Portfolio Benchmark")

stores = list(SHOP_OPTIONS.keys())
selected = st.multiselect("Select stores", stores, default=stores)
shop_ids = [SHOP_OPTIONS[s] for s in selected]

period = st.selectbox("Periode", ["last_month","this_month","last_quarter","this_year"], index=0)

if shop_ids:
    try:
        payload = fetch_report(
            data=shop_ids,
            data_output=["conversion_rate","sales_per_visitor","turnover","count_in"],
            source="shops",
            period=period,
            period_step="day",
        )
        df = normalize_report_days_to_df(payload)
        if df.empty:
            st.warning("Geen data gevonden.")
        else:
            # KPI's per winkel
            kpi = df.groupby("shop_id").agg(
                conversion_rate=("conversion_rate","mean"),
                sales_per_visitor=("sales_per_visitor","mean"),
                turnover=("turnover","sum"),
                count_in=("count_in","sum")
            ).reset_index()
            name_map = {v:k for k,v in SHOP_OPTIONS.items()}
            kpi["store"] = kpi["shop_id"].map(name_map)
            kpi["conversion_pct"] = kpi["conversion_rate"].apply(lambda x: x*100 if (isinstance(x,(int,float)) and x<=1) else x)
            kpi = kpi[["store","conversion_pct","sales_per_visitor","count_in","turnover"]].sort_values("turnover", ascending=False)
            # EU-format
            kpi["conversion_pct"] = kpi["conversion_pct"].map(lambda v: f"{v:,.1f}%".replace(",", "@").replace(".", ",").replace("@","."))
            kpi["sales_per_visitor"] = kpi["sales_per_visitor"].map(lambda v: f"€{v:,.2f}".replace(",", "@").replace(".", ",").replace("@","."))
            kpi["turnover"] = kpi["turnover"].map(lambda v: f"€{v:,.0f}".replace(",", "@").replace(".", ",").replace("@","."))
            kpi["count_in"] = kpi["count_in"].map(lambda v: f"{int(v):,}".replace(",", "."))

            st.dataframe(kpi, use_container_width=True)
    except Exception as e:
        st.error(f"Report call failed: {e}")
else:
    st.info("Selecteer minimaal één store.")
