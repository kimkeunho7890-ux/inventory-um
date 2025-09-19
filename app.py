import streamlit as st
import pandas as pd
import numpy as np
import os

st.set_page_config(layout="wide")

# 모바일 화면 최적화를 위한 스타일 코드
st.markdown("""
<style>
    /* 전체적인 폰트를 약간 줄입니다 */
    .main { font-size: 0.9rem; }
    /* 데이터프레임과 마크다운 테이블의 폰트 크기 및 여백을 줄입니다 */
    .stDataFrame, .stMarkdown table { font-size: 0.8rem; }
    .stDataFrame th, .stDataFrame td, .stMarkdown th, .stMarkdown td { padding: 4px 5px; }
    /* 버튼을 작게 만듭니다 */
    .stButton>button { padding: 0.25em 0.38em; font-size: 0.8rem; }
    /* 마크다운 요소 간의 불필요한 하단 여백을 줄입니다 */
    .stMarkdown { margin-bottom: -15px; }
    /* 헤더 아래의 여백을 조절합니다 */
    h1, h2, h3 { margin-bottom: 0.5rem; }
</style>
""", unsafe_allow_html=True)

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
model_summary = df_filtered.groupby('모델명', observed=True).agg(
    재고수량=('재고수량', 'sum'),
    판매수량=('판매수량', 'sum')
).sort_values(by='판매수량', ascending=False)
total_volume_summary = model_summary['재고수량'] + model_summary['판매수량']
model_summary['재고회전율'] = np.divide(model_summary['판매수량'], total_volume_summary, out=np.zeros_like(total_volume_summary, dtype=float), where=total_volume_summary!=0).apply(lambda x: f"{x:.2%}")
top_20_summary = model_summary.head(20)
st.dataframe(top_20_summary.T.astype(str), use_container_width=True)

st.header('🔎 상세 검색')
show_color = st.checkbox("색상별 상세 보기")
inventory_sorted_models = df.groupby('모델명', observed=True)['재고수량'].sum().sort_values(ascending=False).index.tolist()
selected_models = st.multiselect("모델명을 선택하세요", inventory_sorted_models)

if selected_models:
    detail_summary = df[df['모델명'].isin(selected_models)]
    if show_color:
        #...(이하 로직은 이전과 동일)...
    else:
        grouping_cols = ['모델명', '영업그룹']
        detail_agg = detail_summary.groupby(grouping_cols, observed=True).agg(재고수량=('재고수량', 'sum'), 판매수량=('판매수량', 'sum')).reset_index()
        total_agg = detail_agg['재고수량'] + detail_agg['판매수량']
        detail_agg['재고회전율'] = (detail_agg['판매수량'] / total_agg).apply(lambda x: f"{x:.2%}")
        detail_agg['영업그룹'] = pd.Categorical(detail_agg['영업그룹'], categories=df['영업그룹'].cat.categories, ordered=True)
        sorted_detail_agg = detail_agg.sort_values(by=['영업그룹', '판매수량'], ascending=[True, False])
        st.markdown(sorted_detail_agg.to_html(index=False), unsafe_allow_html=True)

st.header('📄 계층형 상세 데이터 보기')

if 'expanded_store' not in st.session_state:
    st.session_state.expanded_store = {}

for group in [g for g in group_options if g in df_filtered['영업그룹'].unique()]:
    df_group = df_filtered[df_filtered['영업그룹'] == group]
    group_stock = df_group['재고수량'].sum(); group_sales = df_group['판매수량'].sum()
    group_turnover = (group_sales / (group_stock + group_sales)) if (group_stock + group_sales) > 0 else 0
    
    with st.expander(f"🏢 **영업그룹: {group}** (재고: {group_stock}, 판매: {group_sales}, 회전율: {group_turnover:.2%})"):
        person_summary = df_group.groupby('담당', observed=True)['판매수량'].sum().sort_values(ascending=False).reset_index()
        person_list = person_summary['담당'].tolist()
        
        if person_list:
            tabs = st.tabs(person_list)
            for i, person_name in enumerate(person_list):
                with tabs[i]:
                    df_person = df_group[df_group['담당'] == person_name]
                    df_store = df_person.groupby('출고처', observed=True).agg(재고수량=('재고수량', 'sum'), 판매수량=('판매수량', 'sum')).reset_index()
                    df_store = df_store.sort_values(by='판매수량', ascending=False)
                    store_total = df_store['재고수량'] + df_store['판매수량']
                    df_store['재고회전율'] = (df_store['판매수량'] / store_total).apply(lambda x: f"{x:.2%}")

                    header_cols = st.columns((1, 3, 1.5, 1.5, 1.5))
                    header_cols[0].markdown('**상세**')
                    header_cols[1].markdown('**판매점명**')
                    header_cols[2].markdown('**재고**')
                    header_cols[3].markdown('**판매**')
                    header_cols[4].markdown('**회전율**')

                    for idx, row in df_store.iterrows():
                        unique_key = f"{group}_{person_name}_{row['출고처']}"
                        row_cols = st.columns((1, 3, 1.5, 1.5, 1.5))

                        if row_cols[0].button("상세", key=f"btn_{unique_key}"):
                            if st.session_state.expanded_store.get(person_name) == row['출고처']:
                                st.session_state.expanded_store[person_name] = None
                            else:
                                st.session_state.expanded_store[person_name] = row['출고처']
                            st.rerun()

                        # --- <<< 1. 숫자 표시를 '박스'가 아닌 일반 텍스트로 변경 >>> ---
                        row_cols[1].markdown(f"<p style='margin-bottom: -15px;'>{row['출고처']}</p>", unsafe_allow_html=True)
                        row_cols[2].markdown(f"<p style='text-align: right; margin-bottom: -15px;'>{row['재고수량']}</p>", unsafe_allow_html=True)
                        row_cols[3].markdown(f"<p style='text-align: right; margin-bottom: -15px;'>{row['판매수량']}</p>", unsafe_allow_html=True)
                        row_cols[4].markdown(f"<p style='text-align: right; margin-bottom: -15px;'>{row['재고회전율']}</p>", unsafe_allow_html=True)

                        if st.session_state.expanded_store.get(person_name) == row['출고처']:
                            with st.container():
                                df_model = df_person[df_person['출고처'] == row['출고처']]
                                model_detail = df_model.groupby('모델명', observed=True).agg(재고수량=('재고수량', 'sum'), 판매수량=('판매수량', 'sum')).reset_index()
                                model_detail = model_detail.sort_values(by='판매수량', ascending=False)
                                model_total = model_detail['재고수량'] + model_detail['판매수량']
                                model_detail['재고회전율'] = (model_detail['판매수량'] / model_total).apply(lambda x: f"{x:.2%}")
                                
                                # --- <<< 2. 상세표 헤더를 짧게 바꾸고 순번 제거 >>> ---
                                model_detail.rename(columns={'모델명': '모델', '재고수량': '재고', '판매수량': '판매', '재고회전율': '회전율'}, inplace=True)
                                st.markdown(model_detail.to_html(index=False), unsafe_allow_html=True)
                        
                        st.markdown("<hr style='margin: 0.5rem 0;'/>", unsafe_allow_html=True)
