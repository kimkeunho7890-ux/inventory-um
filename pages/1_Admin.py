import streamlit as st
import pandas as pd
import numpy as np
import os

# --- 여기에 원하는 관리자 비밀번호를 설정하세요 ---
ADMIN_PASSWORD = "2178149594" 

st.title("🔑 관리자 페이지")

password = st.text_input("비밀번호를 입력하세요:", type="password")

if password == ADMIN_PASSWORD:
    st.success("인증되었습니다. 데이터를 업로드하세요.")

    inventory_file = st.file_uploader("재고리스트.csv", type=['csv'])
    sales_file = st.file_uploader("판매리스트.csv", type=['csv'])

    if inventory_file and sales_file:
        if st.button("데이터베이스에 업로드"):
            try:
                with st.spinner('데이터를 처리하고 있습니다...'):
                    # CSV 파일 읽기
                    inventory_df = pd.read_csv(inventory_file, encoding='cp949')
                    sales_df = pd.read_csv(sales_file, encoding='cp949')

                    # 데이터 처리 (앱과 동일한 로직)
                    sales_df.columns = sales_df.columns.str.replace('\\n', '', regex=True)
                    inventory_df.rename(columns={'색상': '단말기색상'}, inplace=True)

                    grouping_cols = ['영업그룹', '담당', '출고처', '모델명', '단말기색상']
                    inventory_summary = inventory_df.groupby(grouping_cols, observed=True).size().reset_index(name='재고수량')
                    sales_summary = sales_df.groupby(grouping_cols, observed=True).size().reset_index(name='판매수량')

                    df_detailed = pd.merge(inventory_summary, sales_summary, on=grouping_cols, how='outer')
                    df_detailed[['재고수량', '판매수량']] = df_detailed[['재고수량', '판매수량']].fillna(0).astype(int)

                    total_volume = df_detailed['재고수량'] + df_detailed['판매수량']
                    df_detailed['재고회전율'] = np.divide(df_detailed['판매수량'], total_volume, out=np.zeros_like(total_volume, dtype=float), where=total_volume!=0)

                    # 영업그룹 순서 지정
                    all_groups = df_detailed['영업그룹'].unique()
                    custom_order = ['부산', '울산', '경남', '대구', '경주포항', '구미']
                    remaining_groups = sorted([g for g in all_groups if g not in custom_order])
                    final_order = custom_order + remaining_groups
                    df_detailed['영업그룹'] = pd.Categorical(df_detailed['영업그룹'], categories=final_order, ordered=True)

                st.write("✅ 데이터 처리 완료. 데이터베이스에 저장 중...")

                DB_URL = os.environ.get('DATABASE_URL')
                if DB_URL and DB_URL.startswith("postgres://"):
                    DB_URL = DB_URL.replace("postgres://", "postgresql://", 1)

                conn = st.connection('db', type='sql', url=DB_URL)

                df_detailed.to_sql('inventory_data', conn.engine, if_exists='replace', index=False)

                st.success("🎉 데이터베이스 업로드 완료! 메인 페이지 데이터가 업데이트되었습니다.")
                st.balloons()

            except Exception as e:
                st.error(f"업로드 중 오류가 발생했습니다: {e}")

elif password:
    st.error("비밀번호가 틀렸습니다.")