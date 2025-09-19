import streamlit as st
import pandas as pd
import numpy as np
import os

st.set_page_config(layout="wide")

# --- <<< 모바일 화면 및 메트릭 스타일 최종 수정 >>> ---
st.markdown("""
<style>
    .stDataFrame { font-size: 0.8rem; }
    .stDataFrame th, .stDataFrame td { padding: 4px 5px; }
    .stMarkdown { margin-bottom: 0px; }
    .stButton>button { padding: 0.25em 0.38em; font-size: 0.8rem; margin-top: 5px;}
    h1, h2, h3 { margin-bottom: 0.5rem; }
    
    /* st.metric 스타일을 주황색 테마로 변경하고 더 작게 조정 */
    [data-testid="stMetric"] {
        background-color: #FF7F0E; /* 주황색 배경 */
        border: 1px solid #FF7F0E;
        border-radius: 8px;        /* 모서리를 둥글게 */
        padding: 2px 3px;          /* 내부 여백을 줄여 폭을 좁힘 */
        color: white;              /* 기본 글씨색 */
    }
    /* 메트릭 라벨(제목) 글씨색 */
    [data-testid="stMetricLabel"] {
        font-size: 0.8rem;
        color: white;
        margin-bottom: -10px;
    }
    /* 메트릭 값(숫자) 글씨색 */
    [data-testid="stMetricValue"] {
        color: white;
    }
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
        grouping_cols = ['모델명', '단말기색상', '영업그룹']
        detail_agg = detail_summary.groupby(grouping_cols, observed=True).agg(재고수량=('재고수량', 'sum'), 판매수량=('판매수량', 'sum')).reset_index()
        for model in selected_models:
            model_df = detail_agg[detail_agg['모델명'] == model]
            unique_colors = model_df['단말기색상'].unique()
            for color in unique_colors:
                st.markdown(f"--- \n#### {model} ({color})")
                color_subset_df = model_df[model_df['단말기색상'] == color]
                total_stock = color_subset_df['재고수량'].sum(); total_sales = color_subset_df['판매수량'].sum()
                total_volume = total_stock + total_sales
                total_turnover = (total_sales / total_volume) if total_volume > 0 else 0
                total_data = {'구분': ['**색상 전체 합계**'], '재고수량': [total_stock], '판매수량': [total_sales], '재고회전율': [f"{total_turnover:.2%}"]}
                st.markdown(pd.DataFrame(total_data).to_html(index=False), unsafe_allow_html=True)
                breakdown_df = color_subset_df[['영업그룹', '재고수량', '판매수량']].copy()
                breakdown_volume = breakdown_df['재고수량'] + breakdown_df['판매수량']
                breakdown_df['재고회전율'] = (breakdown_df['판매수량'] / breakdown_volume).apply(lambda x: f"{x:.2%}")
                breakdown_df['영업그룹'] = pd.Categorical(breakdown_df['영업그룹'], categories=df['영업그룹'].cat.categories, ordered=True)
                st.markdown(breakdown_df.sort_values(by='영업그룹').to_html(index=False), unsafe_allow_html=True)
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

                    for idx, row in df_store.iterrows():
                        unique_key = f"{group}_{person_name}_{row['출고처']}"
                        
                        st.markdown(f"**🏪 {row['출고처']}**")
                        
                        metric_cols = st.columns(3)
                        metric_cols[0].metric("재고", row['재고수량'])
                        metric_cols[1].metric("판매", row['판매수량'])
                        metric_cols[2].metric("회전율", row['재고회전율'])

                        if st.button("모델별 상세 보기", key=f"btn_{unique_key}"):
                            if st.session_state.expanded_store.get(person_name) == row['출고처']:
                                st.session_state.expanded_store[person_name] = None
                            else:
                                st.session_state.expanded_store[person_name] = row['출고처']
                            st.rerun()

                        if st.session_state.expanded_store.get(person_name) == row['출고처']:
                            with st.container():
                                df_model = df_person[df_person['출고처'] == row['출고처']]
                                
                                model_detail = df_model.groupby('모델명', observed=True).agg(재고수량=('재고수량', 'sum'), 판매수량=('판매수량', 'sum')).reset_index()
                                model_detail = model_detail.sort_values(by='판매수량', ascending=False)
                                
                                model_total = model_detail['재고수량'] + model_detail['판매수량']
                                model_detail['재고회전율'] = (model_detail['판매수량'] / model_total).apply(lambda x: f"{x:.2%}")
                                
                                model_detail.rename(columns={'모델명': '모델', '재고수량': '재고', '판매수량': '판매', '재고회전율': '회전율'}, inplace=True)
                                st.dataframe(model_detail, use_container_width=True, hide_index=True)
                        
                        st.markdown("<hr style='margin: 0.5rem 0;'/>", unsafe_allow_html=True)

