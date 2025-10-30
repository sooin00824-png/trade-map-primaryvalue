# ================================================
# 🌍 리튬 및 코발트 국제 교역 지도 (primaryvalue 기반, 컬럼 수정 반영)
# ================================================

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import pycountry
import os
import pathlib

# ------------------------------
# ✅ Streamlit 기본 설정
# ------------------------------
st.set_page_config(page_title="국제 교역 데이터 지도", page_icon="🌐", layout="wide")
st.title("🌐 리튬 및 코발트 국제 교역 지도 (primaryvalue 기반)")

# ------------------------------
# ✅ 1. 데이터 불러오기
# ------------------------------
@st.cache_data
def load_data():
    csv_path = pathlib.Path(__file__).parent / "dataset_filtered_80.csv"
    st.write("🔍 불러오는 경로:", csv_path)
    data = pd.read_csv(csv_path, encoding="utf-8-sig")
    return data

    if not os.path.exists(csv_path):
        st.error(f"❌ 데이터 파일을 찾을 수 없습니다:\n{csv_path}")
        st.stop()

    data = pd.read_csv(csv_path, encoding="utf-8-sig")

    # 열 이름 정리
    data.columns = (
        data.columns
        .str.strip()
        .str.lower()
        .str.replace('\ufeff', '', regex=False)
    )

    # 주요 열 정리
    for col in ['period', 'cmdcode', 'reporterdesc', 'partnerdesc']:
        if col in data.columns:
            data[col] = data[col].astype(str).str.strip()

    # 연도 컬럼 추가
    if 'period' in data.columns:
        data['year'] = data['period'].astype(str).str[:4]

    return data

data = load_data()

# ------------------------------
# ✅ 2. 수치 컬럼 (primaryvalue) 처리
# ------------------------------
data['primaryvalue'] = (
    data['primaryvalue']
    .astype(str)
    .str.replace(',', '', regex=True)
    .replace('', np.nan)
    .astype(float)
)

# ------------------------------
# ✅ 3. ISO 코드 변환
# ------------------------------
def country_to_iso3(name):
    """국가명을 ISO3 코드로 변환"""
    try:
        return pycountry.countries.lookup(name).alpha_3
    except LookupError:
        return None

country_fix = {
    'Korea, Rep.': 'KOR', 'Republic of Korea': 'KOR',
    'United States': 'USA', 'USA': 'USA',
    'Russian Federation': 'RUS', 'Viet Nam': 'VNM',
    'Iran (Islamic Republic of)': 'IRN', 'Dem. Rep. of the Congo': 'COD',
    'Congo': 'COG', 'Iran': 'IRN', 'Turkiye': 'TUR',
    'United Kingdom': 'GBR', 'Brunei Darussalam': 'BRN',
    "Cote d'Ivoire": 'CIV', 'New Caledonia': 'NCL',
    'Bolivia (Plurinational State of)': 'BOL',
    'Other Asia, nes': 'OWA',
    'Palestine': 'PSE', 'Kosovo': 'XKX', 'Taiwan': 'TWN',
    'Czechia': 'CZE', 'Dominican Rep.': 'DOM',
    'China, Hong Kong SAR': 'HKG'  # ✅ 홍콩 수정 반영
}

data['partner_iso3'] = data['partnerdesc'].apply(
    lambda x: country_fix[x] if x in country_fix else country_to_iso3(x)
)

data = data.dropna(subset=['partner_iso3', 'primaryvalue'])

# ------------------------------
# ✅ 4. Streamlit UI
# ------------------------------
col1, col2, col3, col4 = st.columns(4)
with col1:
    view_mode = st.radio("보기 단위 선택", ["월별", "연도별"])
with col2:
    cmdcode = st.selectbox("📦 품목코드(HS Code)", sorted(data['cmdcode'].unique()))
with col3:
    reporter = st.selectbox("📊 보고국(Reporter)", sorted(data['reporterdesc'].unique()))
with col4:
    period = st.selectbox("📅 기간(YYYYMM)", sorted(data['period'].unique()))

if view_mode == "연도별":
    year = st.selectbox("📆 연도(YYYY)", sorted(data['year'].unique()))

# ------------------------------
# ✅ 5. 데이터 필터링
# ------------------------------
if view_mode == "월별":
    subset = data[
        (data['period'] == str(period)) &
        (data['cmdcode'] == str(cmdcode)) &
        (data['reporterdesc'] == reporter)
    ].copy()
    title_text = f"{reporter}의 {cmdcode} 수입 (기간: {period}) [log₁₀(primaryvalue)]"
else:
    subset = data[
        (data['year'] == str(year)) &
        (data['cmdcode'] == str(cmdcode)) &
        (data['reporterdesc'] == reporter)
    ].copy()
    subset = subset.groupby(['partnerdesc', 'partner_iso3'], as_index=False)['primaryvalue'].sum()
    title_text = f"{reporter}의 {cmdcode} 수입 (연도: {year}) [log₁₀(primaryvalue)]"

# ------------------------------
# ✅ 6. 지도 시각화
# ------------------------------
if subset.empty:
    st.warning("⚠️ 선택한 조건에 해당하는 데이터가 없습니다.")
else:
    subset['primaryvalue_log'] = np.log10(subset['primaryvalue'].replace(0, np.nan))

    fig = px.choropleth(
        subset,
        locations="partner_iso3",
        color="primaryvalue_log",
        hover_name="partnerdesc",
        color_continuous_scale="Viridis",
        title=title_text,
        projection="natural earth"
    )

    fig.update_layout(
        geo=dict(showframe=False, showcoastlines=True),
        coloraxis_colorbar=dict(title="log₁₀(primaryvalue)")
    )

    st.plotly_chart(fig, use_container_width=True)

# ------------------------------
# ✅ 7. 데이터 테이블 출력
# ------------------------------
st.markdown("### 🔍 Reporter 국가 수입금액(단위: USD 등)")
if view_mode == "월별":
    display_cols = ['cmdcode', 'period', 'reporterdesc', 'partnerdesc', 'primaryvalue']
else:
    display_cols = ['partnerdesc', 'partner_iso3', 'primaryvalue']

subset_display = subset.reindex(columns=[c for c in display_cols if c in subset.columns])
st.dataframe(subset_display, hide_index=True, use_container_width=True)

st.markdown("---")
st.caption("📊 Source: UN COMTRADE Database (로컬 데이터 기반)")
st.caption("Author: Soo In Kim, Date: 2025.10.30")
st.caption("주: 지도 색상은 log₁₀(primaryvalue) 기준으로 표시됩니다.")



