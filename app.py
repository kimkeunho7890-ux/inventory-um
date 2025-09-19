import streamlit as st
import pandas as pd
import numpy as np
import os

st.set_page_config(layout="wide")
st.markdown("""<style>.stDataFrame {font-size: 0.8rem;}.stDataFrame th, .stDataFrame td {padding: 4px 5px;}.streamlit-expander .stDataFrame {font-size: 0.8rem;}.streamlit-expander .stDataFrame th, .streamlit-expander .stDataFrame td {padding: 4px 5px;}.stMarkdown {margin-bottom: -20px;}</style>""", unsafe_allow_html=True)
st.title('📱 재고 현황 대시보드 (최종 완성본)')

@st.cache_data(ttl=600)
def load_data_from_db():
    DB_URL = os.environ.get('DATABASE_URL')
    if not DB_URL:
        st.error("데이터베이스 URL을 찾을 수 없습니다.")
        return None
    if DB_URL.startswith("postgres://"):
        DB_URL = DB_URL.replace("postgres://", "postgresql://", 1)
    try:
        conn = st.connection('db', type='sql', url=DB_URL)
        df = conn.query('SELECT * FROM inventory_data')
        all_groups = df['영업그룹'].unique()
        custom_order = ['부산', '울산', '경남', '대구', '경주포항', '구미']
        remaining_groups = sorted([g for g in all_groups if g not in custom_order])
        final_order = custom_order + remaining_groups
        df['영업그룹'] = pd.Categorical(df['영업그룹'], categories=final_order, ordered=True)
        return df
    except Exception as e:
        st.error(f"데이터베이스 연결에 실패했습니다. 관리자 페이지에서 데이터를 먼저 업로드해주세요.")
        return None

df = load_data_from_db()
if df is None:
    st.stop()

st.sidebar.header('필터')
group_options = df['영업그룹'].cat.categories.tolist()
selected_groups = st.sidebar.multiselect('영업그룹', group_options, default=group_options)
available_personnel = df[df['영업그룹'].isin(selected_groups)]['담당'].unique()
selected_personnel = st.sidebar.multiselect('담당', available_personnel, default=available_personnel)
df_filtered = df[df['영업그룹'].isin(selected_groups) & df['담당'].isin(selected_personnel)]

st.header('📊 모델별 판매 요약 (상위 20개)')
model_summary = df_filtered.groupby('모델명', observed=True).agg(재고수량=('재고수량', 'sum'), 판매수량=('판매수량', 'sum')).sort_values(by='판매수량', ascending=False)
total_volume_summary = model_summary['재고수량'] + model_summary['판매수량']
model_summary['재고회전율'] = np.divide(model_summary['판매수량'], total_volume_summary, out=np.zeros_like(total_volume_summary, dtype=float), where=total_volume_summary!=0).apply(lambda x: f"{x:.2%}")
top_20_summary = model_summary.head(20)
st.dataframe(top_20_summary.T.astype(str), use_container_width=True)

st.write("📈 **요약 모델 바로 조회**")
top_20_models = top_20_summary.index.tolist()
if 'clicked_model' not in st.session_state: st.session_state.clicked_model = None
cols = st.columns(5, gap="small")
for i, model_name in enumerate(top_20_models):
    if cols[i % 5].button(model_name, key=f"model_btn_{i}"):
        st.session_state.clicked_model = model_name
        st.rerun()

st.header('🔎 상세 검색')
show_color = st.checkbox("색상별 상세 보기")
default_selection = [st.session_state.clicked_model] if st.session_state.clicked_model else []
inventory_sorted_models = df.groupby('모델명', observed=True)['재고수량'].sum().sort_values(ascending=False).index.tolist()
selected_models = st.multiselect("모델명을 선택하세요", inventory_sorted_models, default=default_selection)

if selected_models:
    detail_summary = df[df['모델명'].isin(selected_models)]
    if show_color:
        # ... (색상별 보기 로직)
    else:
        # ... (기본 상세 보기 로직)

st.header('📄 계층형 상세 데이터 보기')
# ... (계층형 보기 전체 로직)