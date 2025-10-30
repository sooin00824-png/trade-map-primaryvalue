# ================================================
# 🌍 리튬 및 코발트 국제 교역 지도 (primaryvalue 기반, 개선 통합 버전)
# ================================================

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import pycountry
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
    import gdown

    # Google Drive 파일 URL → 직접 다운로드용 URL로 변환
    url = "https://drive.google.com/uc?id=1WtkYFRNwlURmXJbLCsd4Ff0-GmtQoSHa"
    output = "dataset_filtered_80.csv"

    # gdown으로 다운로드
    gdown.download(url, output, quiet=False)

    # 불러온 CSV 읽기
    data = pd.read_csv(output, encoding="utf-8-sig")

    # ----------------------------
    # 🔧 기본 전처리
    # ----------------------------
    # 열 이름 표준화
    data.columns = (
        data.columns
        .str.strip()
        .str.lower()
        .str.replace('\ufeff', '', regex=False)
    )

    # 문자열 컬럼 정리
    for col in ['period', 'cmdcode', 'reporterdesc', 'partnerdesc']:
        if col in data.columns:
            data[col] = data[col].astype(str).str.strip()

    # period 형식 정리 (예: 2010-01 → 201001)
    if 'period' in data.columns:
        data['period'] = (
            data['period']
            .astype(str)
            .str.replace('-', '', regex=True)
            .str.strip()
        )

    # year 컬럼 추가
    if 'period' in data.columns:
        data['year'] = data['period'].astype(str).str[:4]

    # primaryvalue 숫자 변환
    if 'primaryvalue' in data.columns:
        data['primaryvalue'] = (
            data['primaryvalue']
            .astype(str)
            .str.replace(',', '', regex=True)
            .replace('', np.nan)
            .astype(float)
        )

    return data

data = load_data()

# ------------------------------
# ✅ 2. ISO 코드 변환
# ------------------------------
def country_to_iso3(name):
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

if 'partnerdesc' in data.columns:
    data['partner_iso3'] = data['partnerdesc'].apply(
        lambda x: country_fix[x] if x in country_fix else country_to_iso3(x)
    )

data = data.dropna(subset=['partner_iso3', 'primaryvalue'])

# ------------------------------
# ✅ 3. Streamlit UI
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
# ✅ 4. 데이터 필터링
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
# ✅ 5. 지도 시각화
# ------------------------------
if subset.empty:
    st.warning("⚠️ 선택한 조건에 해당하는 데이터가 없습니다. (기간/품목코드/국가 확인)")
else:
    subset['primaryvalue_log'] = np.log10(subset['primaryvalue'].replace(0, np.nan))

    fig = px.choropleth(
        subset,
        locations="partner_iso3",
        color="primaryvalue_log",
        hover_name="partnerdesc",
        color_continuous_scale="Viridis_r",  # 🔄 값이 클수록 진한 색
        title=title_text,
        projection="natural earth"
    )

    fig.update_layout(
        geo=dict(showframe=False, showcoastlines=True),
        coloraxis_colorbar=dict(title="log₁₀(primaryvalue)")
    )

    st.plotly_chart(fig, use_container_width=True)

# ------------------------------
# ✅ 6. 데이터 테이블 출력
# ------------------------------
st.markdown("### 🔍 Reporter 국가 수입금액(단위: USD 등)")
if view_mode == "월별":
    display_cols = ['cmdcode', 'period', 'reporterdesc', 'partnerdesc', 'primaryvalue']
else:
    display_cols = ['cmdcode', 'reporterdesc', 'partnerdesc', 'primaryvalue']

subset_display = subset.reindex(columns=[c for c in display_cols if c in subset.columns])
st.dataframe(subset_display, hide_index=True, use_container_width=True)

# ------------------------------
# ✅ 7. 부가 정보
# ------------------------------
st.markdown("---")
st.caption("📊 Source: UN COMTRADE Database (로컬 데이터 기반)")
st.caption("Author: Soo In Kim, Date: 2025.10.30")
st.caption("주1) 지도 색상은 log₁₀(primaryvalue) 기준으로 표시됨 (값이 클수록 진한 색)")
st.caption("주2) '선택한 조건에 해당하는 데이터가 없습니다'가 표시되면, 다른 품목코드·기간·국가 조합을 선택하세요.")




