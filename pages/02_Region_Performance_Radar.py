import streamlit as st
import pandas as pd
import plotly.express as px
from ui import inject
from utils_pfmx import fetch_report, normalize_report_days_to_df
from shop_mapping import SHOP_OPTIONS

st.set_page_config(page_title="Region Performance Radar", layout="wide")
inject()

st.title("Region Performance Radar")

stores = st.multiselect("Select stores", options=list(SHOP_OPTIONS.keys()), default=list(SHOP_OPTIONS.keys()))
shop_ids = [SHOP_OPTIONS[s] for s in stores]

col1, col2 = st.columns(2)
with col1:
    conv_target = st.slider("Conversie target (%)", 5, 50, 25, 1)
with col2:
    spv_target = st.slider("SPV target (€)", 0, 200, 30, 1)

if shop_ids:
    try:
        payload = fetch_report(
            data=shop_ids,
            data_output=["conversion_rate","sales_per_visitor","count_in","turnover"],
            source="shops",
            period="last_month",
            period_step="day",
        )
        df = normalize_report_days_to_df(payload)
        if df.empty:
            st.warning("Geen data gevonden.")
        else:
            # Aggregatie per shop
            agg = df.groupby("shop_id").agg({
                "conversion_rate":"mean",
                "sales_per_visitor":"mean",
                "count_in":"sum",
                "turnover":"sum"
            }).reset_index()
            name_map = {v:k for k,v in SHOP_OPTIONS.items()}
            agg["store"] = agg["shop_id"].map(name_map)
            # Conversie in % als nodig
            agg["conversion_pct"] = agg["conversion_rate"].apply(lambda x: x*100 if (isinstance(x,(int,float)) and x<=1) else x)
            st.dataframe(agg[["store","conversion_pct","sales_per_visitor","count_in","turnover"]], use_container_width=True)

            fig = px.scatter(
                agg, x="conversion_pct", y="sales_per_visitor", size="count_in", hover_name="store",
                title="Conversie vs SPV (bubble ~ bezoekers)"
            )
            fig.add_hline(y=spv_target, line_dash="dot")
            fig.add_vline(x=conv_target, line_dash="dot")
            st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.error(f"Report call failed: {e}")
else:
    st.info("Selecteer minimaal één store.")
