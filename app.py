# app.py
import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, date

st.set_page_config(page_title="우리집 가계부 💰", page_icon="💰", layout="wide")

st.markdown("""
<style>
.stApp { background-color: #fff9f0; }
h1 { color: #e17055; }
</style>
""", unsafe_allow_html=True)

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

CATEGORIES = {
    "마트/장보기": "🛒",
    "식비/외식": "🍚",
    "카페/음료": "☕",
    "교통": "🚌",
    "의료/건강": "💊",
    "쇼핑": "👗",
    "문화/여가": "🎬",
    "기타": "📦",
}

def load_data():
    try:
        url = f"{SUPABASE_URL}/rest/v1/expenses?select=*&order=date.desc"
        res = requests.get(url, headers=HEADERS, timeout=10)
        if res.status_code == 200 and res.json():
            df = pd.DataFrame(res.json())
            df["date"] = pd.to_datetime(df["date"]).dt.date
            df["amount"] = df["amount"].astype(int)
            return df
    except Exception as e:
        st.error(f"데이터 오류: {e}")
    return pd.DataFrame(columns=["id","date","amount","category","memo","created_at"])

def save_expense(exp_date, amount, category, memo):
    url  = f"{SUPABASE_URL}/rest/v1/expenses"
    data = {"date": str(exp_date), "amount": int(amount),
            "category": category, "memo": memo}
    res  = requests.post(url, headers=HEADERS, json=data, timeout=10)
    return res.status_code in [200, 201]

def delete_expense(row_id):
    url = f"{SUPABASE_URL}/rest/v1/expenses?id=eq.{row_id}"
    requests.delete(url, headers=HEADERS, timeout=10)

def fmt_won(n):
    return f"{int(n):,}원"

st.title("💰 우리집 가계부")

tab1, tab2, tab3 = st.tabs(["✏️ 지출 입력", "📊 월별 현황", "📋 내역 조회"])

with tab1:
    st.markdown("### 오늘의 지출 입력")
    col_l, col_r = st.columns([1.2, 1])
    with col_l:
        exp_date   = st.date_input("📅 날짜", value=date.today(), format="YYYY/MM/DD")
        amount_str = st.text_input("💵 금액 (원)", placeholder="예: 12000")
        st.markdown("**카테고리 선택**")
        if "selected_cat" not in st.session_state:
            st.session_state.selected_cat = "기타"
        cat_cols = st.columns(4)
        for i, (cat, icon) in enumerate(CATEGORIES.items()):
            with cat_cols[i % 4]:
                if st.button(f"{icon} {cat[:4]}", key=f"cat_{cat}"):
                    st.session_state.selected_cat = cat
        st.info(f"선택된 카테고리: {CATEGORIES[st.session_state.selected_cat]} {st.session_state.selected_cat}")
        memo = st.text_input("📝 메모 (선택)", placeholder="예: 이마트 장보기")
        if st.button("✅ 저장하기", type="primary", use_container_width=True):
            if not amount_str:
                st.error("금액을 입력해주세요!")
            else:
                try:
                    amount = int(amount_str.replace(",","").replace("원",""))
                    ok = save_expense(exp_date, amount, st.session_state.selected_cat, memo)
                    if ok:
                        st.success(f"저장 완료! {fmt_won(amount)} — {st.session_state.selected_cat}")
                        st.balloons()
                    else:
                        st.error("저장 실패! Supabase 연결을 확인해주세요.")
                except ValueError:
                    st.error("금액은 숫자만 입력해주세요!")
    with col_r:
        st.markdown("**📌 오늘 지출 요약**")
        df    = load_data()
        today = date.today()
        today_df    = df[df["date"] == today] if not df.empty else pd.DataFrame()
        today_total = today_df["amount"].sum() if not today_df.empty else 0
        st.markdown(f"### {fmt_won(today_total)}")
        st.caption(today.strftime("%Y년 %m월 %d일"))
        if not today_df.empty:
            for _, row in today_df.iterrows():
                icon     = CATEGORIES.get(row["category"], "📦")
                memo_txt = f" — {row['memo']}" if row["memo"] else ""
                st.markdown(f"{icon} **{row['category']}** {fmt_won(row['amount'])}{memo_txt}")

with tab2:
    st.markdown("### 월별 지출 현황")
    df = load_data()
    if df.empty:
        st.info("아직 입력된 데이터가 없어요! 지출을 먼저 입력해주세요 😊")
    else:
        now       = datetime.now()
        sel_year  = st.selectbox("연도", sorted(set(d.year for d in df["date"]), reverse=True))
        sel_month = st.selectbox("월", list(range(1,13)), index=now.month-1, format_func=lambda x: f"{x}월")
        month_df  = df[
            (pd.to_datetime(df["date"]).dt.year  == sel_year) &
            (pd.to_datetime(df["date"]).dt.month == sel_month)
        ]
        monthly_total = month_df["amount"].sum()
        budget    = st.number_input("💰 월 예산 설정 (원)", value=1000000, step=50000)
        ratio     = min(monthly_total / budget * 100, 100) if budget else 0
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric(f"{sel_month}월 총 지출", fmt_won(monthly_total))
        with c2:
            st.metric("예산 대비", f"{ratio:.1f}%")
        with c3:
            st.metric("남은 예산", fmt_won(budget - monthly_total))
        if not month_df.empty:
            ch1, ch2 = st.columns(2)
            with ch1:
                cat_group = month_df.groupby("category")["amount"].sum().reset_index()
                fig = go.Figure(go.Pie(
                    labels=[f"{CATEGORIES.get(c,'📦')} {c}" for c in cat_group["category"]],
                    values=cat_group["amount"], hole=0.5,
                    marker_colors=["#ff6b6b","#ffa07a","#f6c90e","#00d4aa",
                                   "#74b9ff","#a29bfe","#fd79a8","#b2bec3"]))
                fig.update_layout(title="카테고리별 지출", height=380,
                                  paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig, use_container_width=True)
            with ch2:
                day_group = month_df.copy()
                day_group["day"] = pd.to_datetime(day_group["date"]).dt.day
                day_sum = day_group.groupby("day")["amount"].sum().reset_index()
                fig2 = go.Figure(go.Bar(
                    x=day_sum["day"], y=day_sum["amount"],
                    marker_color="#e17055", opacity=0.85,
                    text=[fmt_won(v) for v in day_sum["amount"]],
                    textposition="outside"))
                fig2.update_layout(title="일별 지출", height=380,
                    xaxis_title="일", yaxis_title="금액(원)",
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig2, use_container_width=True)

with tab3:
    st.markdown("### 지출 내역 조회")
    df = load_data()
    if df.empty:
        st.info("아직 입력된 데이터가 없어요! 지출을 먼저 입력해주세요 😊")
    else:
        cf1, cf2 = st.columns(2)
        with cf1:
            filter_cat = st.multiselect("카테고리 필터",
                             options=list(CATEGORIES.keys()),
                             default=list(CATEGORIES.keys()))
        with cf2:
            date_range = st.date_input("기간 선택",
                             value=[df["date"].min(), df["date"].max()],
                             format="YYYY/MM/DD")
        filtered = df[df["category"].isin(filter_cat)]
        if len(date_range) == 2:
            filtered = filtered[
                (filtered["date"] >= date_range[0]) &
                (filtered["date"] <= date_range[1])
            ]
        st.markdown(f"**총 {len(filtered)}건 | 합계: {fmt_won(filtered['amount'].sum())}**")
        display_df = filtered[["date","category","amount","memo"]].copy()
        display_df.columns = ["날짜","카테고리","금액(원)","메모"]
        display_df["금액(원)"] = display_df["금액(원)"].apply(lambda x: f"{x:,}")
        st.dataframe(display_df, use_container_width=True, height=400)
        with st.expander("🗑️ 항목 삭제"):
            del_id = st.number_input("삭제할 항목 ID", min_value=1, step=1)
            if st.button("삭제", type="primary"):
                delete_expense(del_id)
                st.success("삭제 완료!")
                st.rerun()
        csv = filtered.to_csv(index=False, encoding="utf-8-sig")
        st.download_button(
            label="📥 CSV 다운로드 (엑셀에서 열기)",
            data=csv,
            file_name=f"가계부_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
