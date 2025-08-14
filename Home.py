import streamlit as st
from ui import inject

st.set_page_config(page_title="PFM Retail Performance Suite", layout="wide")
inject()

st.markdown("### PFM Retail Performance Suite")
st.markdown(
    '<div class="pfm-card">'
    '<span class="pfm-badge">Demo-ready</span><br><br>'
    'Kies een tool in de sidebar: Store Live Ops, Region Performance Radar, Portfolio Benchmark of Executive ROI Scenarios.'
    '</div>', unsafe_allow_html=True
)

st.markdown("#### Tips")
st.write("- Vul eerst `.streamlit/secrets.toml` met je API_URL en (optioneel) LIVE_URL.")
st.write("- Alle API-calls zijn **POST** en gebruiken **herhaalde querykeys zonder `[]`**.")
