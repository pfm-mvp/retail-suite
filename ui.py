import streamlit as st

def inject():
    css = '''
    <style>
      .pfm-card { border-radius:16px; padding:16px; background:#F9F7FB; border:1px solid #EEE; }
      .pfm-badge { display:inline-block; padding:2px 8px; border-radius:999px; background:#762181; color:white; font-size:12px; }
      .kpi { border-radius:12px; padding:12px 14px; color:white; font-weight:700; }
      .kpi.good { background:#16A34A; }  /* green */
      .kpi.bad  { background:#F04438; }  /* red */
      .kpi.neutral  { background:#762181; }  /* purple */
    </style>
    '''
    st.markdown(css, unsafe_allow_html=True)

def kpi(label, value, state="neutral"):
    cls = f"kpi {state}"
    html = f'''
    <div class="{cls}">
      <div style="opacity:.9;font-size:12px;font-weight:500">{label}</div>
      <div style="font-size:22px;">{value}</div>
    </div>
    '''
    st.markdown(html, unsafe_allow_html=True)
