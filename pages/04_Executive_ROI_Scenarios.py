import streamlit as st
import pandas as pd
from ui import inject, kpi
from utils_pfmx import fetch_report, normalize_report_days_to_df
from shop_mapping import SHOP_OPTIONS

st.set_page_config(page_title="Executive ROI Scenarios", layout="wide")
inject()

st.title("Executive ROI Scenarios")

stores = list(SHOP_OPTIONS.keys())
selected = st.multiselect("Select stores", stores, default=stores)
shop_ids = [SHOP_OPTIONS[s] for s in selected]

st.subheader("Assumpties")
colA, colB, colC = st.columns(3)
with colA:
    capex = st.number_input("CAPEX per store (€)", min_value=0, value=1500, step=100)
with colB:
    opex = st.number_input("OPEX per maand per store (€)", min_value=0, value=30, step=10)
with colC:
    margin = st.slider("Brutomarge op ATV (%)", 10, 90, 50, 1)

conv_uplift = st.slider("Conversie uplift (procentpunt)", 1, 20, 5, 1)

if shop_ids:
    try:
        payload = fetch_report(
            data=shop_ids,
            data_output=["conversion_rate","sales_per_visitor","turnover","count_in"],
            source="shops",
            period="last_month",
            period_step="day",
        )
        df = normalize_report_days_to_df(payload)
        if df.empty:
            st.warning("Geen data gevonden.")
        else:
            base = df.groupby("shop_id").agg(
                conversion_rate=("conversion_rate","mean"),
                sales_per_visitor=("sales_per_visitor","mean"),
                turnover=("turnover","sum"),
                count_in=("count_in","sum")
            ).reset_index()
            name_map = {v:k for k,v in SHOP_OPTIONS.items()}
            base["store"] = base["shop_id"].map(name_map)
            # normalize conversion to fraction
            base["conv_frac"] = base["conversion_rate"].apply(lambda x: x if (isinstance(x,(int,float)) and x<=1) else x/100.0)
            uplift_frac = conv_uplift/100.0
            base["new_conv"] = (base["conv_frac"] + uplift_frac).clip(upper=1.0)
            # new sales per visitor ~ proportional to conversion uplift (simplistic)
            base["new_spv"] = base["sales_per_visitor"] * (base["new_conv"]/base["conv_frac"]).replace([float('inf')], 1.0)
            base["extra_turnover"] = (base["new_spv"] - base["sales_per_visitor"]) * base["count_in"]
            base["extra_gross_profit"] = base["extra_turnover"] * (margin/100.0)
            # costs per month, estimate payback months
            monthly_cost = opex + (capex/12.0)
            base["payback_months"] = (capex / base["extra_gross_profit"]).replace([float('inf')], 0.0).clip(lower=0.0)

            # Format
            tbl = base[["store","conversion_rate","sales_per_visitor","count_in","turnover","extra_turnover","extra_gross_profit","payback_months"]].copy()
            def eur(v, decimals=0):
                fmt = f"€{{:,.{decimals}f}}".format(v).replace(",", "@").replace(".", ",").replace("@",".")
                return fmt
            tbl["turnover"] = tbl["turnover"].map(lambda v: eur(v,0))
            tbl["sales_per_visitor"] = tbl["sales_per_visitor"].map(lambda v: eur(v,2))
            tbl["extra_turnover"] = tbl["extra_turnover"].map(lambda v: eur(max(v,0),0))
            tbl["extra_gross_profit"] = tbl["extra_gross_profit"].map(lambda v: eur(max(v,0),0))
            tbl["count_in"] = tbl["count_in"].map(lambda v: f"{int(v):,}".replace(",", "."))
            tbl["conversion_rate"] = base["conversion_rate"].apply(lambda x: x*100 if (isinstance(x,(int,float)) and x<=1) else x).map(lambda v: f"{v:,.1f}%".replace(",", "@").replace(".", ",").replace("@","."))

            st.dataframe(tbl.sort_values("extra_gross_profit", ascending=False), use_container_width=True)

            total_extra = float(base["extra_gross_profit"].sum())
            c1,c2 = st.columns(2)
            with c1: kpi("Totale extra brutowinst / mnd", eur(total_extra,0), "good" if total_extra>0 else "bad")
            with c2: kpi("CAPEX totaal", eur(capex*len(shop_ids),0), "neutral")
    except Exception as e:
        st.error(f"Report call failed: {e}")
else:
    st.info("Selecteer minimaal één store.")
