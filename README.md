# PFM Retail Performance Suite (Streamlit)

**Belangrijkste zekerheden voor datakoppeling**
- Alle API-calls zijn **POST** met `application/x-www-form-urlencoded`.
- Arrays gaan als **herhaalde keys zonder `[]`** (bv. `data=1&data=2&data_output=turnover&data_output=conversion_rate`).
- **Report** gebruikt je secret `API_URL` (bijv. `https://vemcount-agent.onrender.com/get-report`) met `source=shops`.
- **Live** gaat naar `.../live-inside` (zonder `/report`) met `source=locations`. `LIVE_URL` in secrets is optioneel; anders wordt het afgeleid van `API_URL`.

## Run
```bash
pip install -r requirements.txt
streamlit run Home.py
```
Vul eerst `.streamlit/secrets.toml` met je **API_URL** en eventueel **LIVE_URL**.

## Structuur
```
pfm-streamlit-suite/
├─ Home.py
├─ ui.py
├─ utils_pfmx.py
├─ shop_mapping.py
├─ pages/
│  ├─ 01_Store_Live_Ops.py
│  ├─ 02_Region_Performance_Radar.py
│  ├─ 03_Portfolio_Benchmark.py
│  └─ 04_Executive_ROI_Scenarios.py
├─ .streamlit/
│  ├─ config.toml
│  └─ secrets.toml
└─ requirements.txt
```
