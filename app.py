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

DEFAULT_CATEGORIES = {
    "마트/장보기": "🛒",
    "식비/외식": "🍚",
    "카페/음료": "☕",
    "교통": "🚌",
    "의료/건강": "💊",
    "쇼핑": "👗",
    "문화/여가": "🎬",
    "기타": "📦",
}

if "categories" not in st.session_state:
    st.session_state.categories = dict(DEFAULT_CATEGORIES)

def load_data():
    try:
        url = f"{SUPABASE_URL}/rest/v1/expenses?select=*&order=date.desc"
        res = requests.get(url, headers=HEADERS, timeout=10)
        if res.status_code == 200 and res.json():
            df = pd.DataFrame(res.json())
            df["date"] = pd.to_datetime(df["date"]).dt.date
            df["amount"] = df["amount"].astype(int)
            if "id" in df.columns:
                df["id"] = df["id"].astype(int)
            return df
    except Exception as e:
        st.error(f"데이터 오류: {e}")
    return pd.DataFrame(columns=["id","date","amount","category","memo","created_at"])

def save_expense(exp_date, amount, category, memo):
    url = f"{SUPABASE_URL}/rest/v1/expenses"
    data = {"date": str(exp_date), "amount": int(amount), "category": category, "memo": memo}
    res = requests.post(url, headers=HEADERS, json=data, timeout=10)
    return res.status_code in [200, 201]

def update_expense(row_id, exp_date, amount, category, memo):
    url = f"{SUPABASE_URL}/rest/v1/expenses?id=eq.{row_id}"
    data = {"date": str(exp_date), "amount": int(amount), "category": category, "memo": memo}
    res = requests.patch(url, headers=HEADERS, json=data, timeout=10)
    return res.status_code in [200, 204]

def delete_expense(row_id):
    url = f"{SUPABASE_URL}/rest/v1/expenses?id=eq.{row_id}"
    requests.delete(url, headers=HEADERS, timeout=10)

def fmt_won(n):
    return f"{int(n):,}원"

st.title("💰 우리집 가계부")

tab1, tab2, tab3, tab4 = st.tabs(["✏️ 지출 입력", "📊 월별 현황", "📋 내역 조회/수정", "⚙️ 카테고리 관리"])

with tab1:
    st.markdown("### 오늘의 지출 입력")
    col_l, col_r = st.columns([1.2, 1])
    with col_l:
        exp_date = st.date_input("📅 날짜", value=date.today(), format="YYYY/MM/DD")
        amount_str = st.text_input("💵 금액 (원)", placeholder="예: 12000")
        st.markdown("**카테고리 선택**")
        if "selected_cat" not in st.session_state:
            st.session_state.selected_cat = "기타"
        cat_cols = st.columns(4)
        for i, (cat, icon) in enumerate(st.session_state.categories.items()):
            with cat_cols[i % 4]:
                if st.button(f"{icon} {cat[:4]}", key=f"cat_{cat}"):
                    st.session_state.selected_cat = cat
        cur_icon = st.session_state.categories.get(st.session_state.selected_cat, "📦")
        st.info(f"선택된 카테고리: {cur_icon} {st.session_state.selected_cat}")
        memo = st.text_input("📝 메모 (선택)", placeholder="예: 이마트 장보기")
        if st.button("✅ 저장하기", type="primary", use_container_width=True):
            if not amount_str:
                st.error("금액을 입력해주세요!")
            else:
                try:
                    amount = int(amount_str.replace(",", "").replace("원", ""))
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
        df = load_data()
        today = date.today()
        today_df = df[df["date"] == today] if not df.empty else pd.DataFrame()
        today_total = today_df["amount"].sum() if not today_df.empty else 0
        st.markdown(f"### {fmt_won(today_total)}")
        st.caption(today.strftime("%Y년 %m월 %d일"))
        if not today_df.empty:
            for _, row in today_df.iterrows():
                icon = st.session_state.categories.get(row["category"], "📦")
                memo_txt = f" — {row['memo']}" if row["memo"] else ""
                st.markdown(f"{icon} **{row['category']}** {fmt_won(row['amount'])}{memo_txt}")

with tab2:
    st.markdown("### 월별 지출 현황")
    df = load_data()
    if df.empty:
        st.info("아직 입력된 데이터가 없어요! 지출을 먼저 입력해주세요 😊")
    else:
        now = datetime.now()
        sel_year = st.selectbox("연도", sorted(set(d.year for d in df["date"]), reverse=True))
        sel_month = st.selectbox("월", list(range(1, 13)), index=now.month - 1, format_func=lambda x: f"{x}월")
        month_df = df[
            (pd.to_datetime(df["date"]).dt.year == sel_year) &
            (pd.to_datetime(df["date"]).dt.month == sel_month)
        ]
        monthly_total = month_df["amount"].sum()
        budget = st.number_input("💰 월 예산 설정 (원)", value=1000000, step=50000)
        ratio = min(monthly_total / budget * 100, 100) if budget else 0
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
                    labels=[f"{st.session_state.categories.get(c, '📦')} {c}" for c in cat_group["category"]],
                    values=cat_group["amount"], hole=0.5,
                    marker_colors=["#ff6b6b", "#ffa07a", "#f6c90e", "#00d4aa",
                                   "#74b9ff", "#a29bfe", "#fd79a8", "#b2bec3"]))
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
    st.markdown("### 지출 내역 조회 / 수정 / 삭제")
    df = load_data()
    if df.empty:
        st.info("아직 입력된 데이터가 없어요! 지출을 먼저 입력해주세요 😊")
    else:
        cf1, cf2 = st.columns(2)
        with cf1:
            all_cats = list(st.session_state.categories.keys())
            filter_cat = st.multiselect("카테고리 필터", options=all_cats, default=all_cats)
        with cf2:
            date_range = st.date_input("기간 선택",
                                       value=[df["date"].min(), df["date"].max()],
                                       format="YYYY/MM/DD")
        filtered = df.copy()
        if filter_cat:
            filtered = filtered[filtered["category"].isin(filter_cat)]
        if len(date_range) == 2:
            filtered = filtered[
                (filtered["date"] >= date_range[0]) &
                (filtered["date"] <= date_range[1])
            ]
        st.markdown(f"**총 {len(filtered)}건 | 합계: {fmt_won(filtered['amount'].sum())}**")

        if not filtered.empty:
            show_cols = [c for c in ["id", "date", "category", "amount", "memo"] if c in filtered.columns]
            display_df = filtered[show_cols].copy()
            col_names = {"id": "ID", "date": "날짜", "category": "카테고리", "amount": "금액(원)", "memo": "메모"}
            display_df.columns = [col_names.get(c, c) for c in show_cols]
            if "금액(원)" in display_df.columns:
                display_df["금액(원)"] = display_df["금액(원)"].apply(lambda x: f"{x:,}")
            st.dataframe(display_df, use_container_width=True, height=300)

        st.markdown("---")
        st.markdown("#### ✏️ 내역 수정")
        if not filtered.empty and "id" in filtered.columns and len(filtered) > 0:
            id_list = filtered["id"].tolist()
            sel_id = st.selectbox(
                "수정할 항목 선택", id_list,
                format_func=lambda x: f"ID {x} | {filtered[filtered['id']==x]['category'].values[0]} | {fmt_won(filtered[filtered['id']==x]['amount'].values[0])} | {filtered[filtered['id']==x]['date'].values[0]}"
            )
            sel_row = filtered[filtered["id"] == sel_id].iloc[0]
            mc1, mc2 = st.columns(2)
            with mc1:
                new_date = st.date_input("날짜 수정", value=sel_row["date"], format="YYYY/MM/DD", key="edit_date")
                new_amount = st.text_input("금액 수정", value=str(sel_row["amount"]), key="edit_amount")
            with mc2:
                cat_keys = list(st.session_state.categories.keys())
                cat_idx = cat_keys.index(sel_row["category"]) if sel_row["category"] in cat_keys else 0
                new_cat = st.selectbox("카테고리 수정", options=cat_keys, index=cat_idx, key="edit_cat")
                new_memo = st.text_input("메모 수정", value=str(sel_row["memo"]) if sel_row["memo"] else "", key="edit_memo")
            if st.button("💾 수정 저장", type="primary"):
                try:
                    ok = update_expense(sel_id, new_date,
                                        int(new_amount.replace(",", "").replace("원", "")),
                                        new_cat, new_memo)
                    if ok:
                        st.success("수정 완료!")
                        st.rerun()
                    else:
                        st.error("수정 실패!")
                except ValueError:
                    st.error("금액은 숫자만 입력해주세요!")
        else:
            st.info("수정할 항목이 없어요!")

        st.markdown("---")
        st.markdown("#### 🗑️ 내역 삭제")
        if not filtered.empty and "id" in filtered.columns and len(filtered) > 0:
            id_list2 = filtered["id"].tolist()
            del_id = st.selectbox(
                "삭제할 항목 선택", id_list2,
                format_func=lambda x: f"ID {x} | {filtered[filtered['id']==x]['category'].values[0]} | {fmt_won(filtered[filtered['id']==x]['amount'].values[0])} | {filtered[filtered['id']==x]['date'].values[0]}",
                key="del_select"
            )
            if st.button("🗑️ 삭제하기", type="primary"):
                delete_expense(del_id)
                st.success("삭제 완료!")
                st.rerun()
        else:
            st.info("삭제할 항목이 없어요!")

        st.markdown("---")
        csv = filtered.to_csv(index=False, encoding="utf-8-sig")
        st.download_button(
            label="📥 CSV 다운로드 (엑셀에서 열기)",
            data=csv,
            file_name=f"가계부_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )

with tab4:
    st.markdown("### ⚙️ 카테고리 관리")
    st.info("💡 카테고리는 이 세션에서만 유지돼요. 앱을 새로고침하면 기본값으로 돌아와요.")
    st.markdown("#### 현재 카테고리")
    cat_df = pd.DataFrame(
        [(icon, name) for name, icon in st.session_state.categories.items()],
        columns=["아이콘", "카테고리명"]
    )
    st.dataframe(cat_df, use_container_width=True, hide_index=True)
    st.markdown("#### ➕ 새 카테고리 추가")
    ac1, ac2 = st.columns(2)
    with ac1:
        new_cat_name = st.text_input("카테고리 이름", placeholder="예: 반려동물")
    with ac2:
        new_cat_icon = st.text_input("이모지 아이콘", placeholder="예: 🐶")
    if st.button("➕ 추가하기", type="primary"):
        if not new_cat_name:
            st.error("카테고리 이름을 입력해주세요!")
        elif new_cat_name in st.session_state.categories:
            st.warning("이미 있는 카테고리예요!")
        else:
            icon = new_cat_icon if new_cat_icon else "📌"
            st.session_state.categories[new_cat_name] = icon
            st.success(f"{icon} {new_cat_name} 추가 완료!")
            st.rerun()
    st.markdown("#### 🗑️ 카테고리 삭제")
    del_cat = st.selectbox("삭제할 카테고리 선택", options=list(st.session_state.categories.keys()))
    if st.button("🗑️ 카테고리 삭제", type="secondary"):
        if len(st.session_state.categories) <= 1:
            st.error("최소 1개의 카테고리는 있어야 해요!")
        else:
            del st.session_state.categories[del_cat]
            st.success(f"{del_cat} 삭제 완료!")
            st.rerun()
    st.markdown("---")
    if st.button("🔄 기본 카테고리로 초기화"):
        st.session_state.categories = dict(DEFAULT_CATEGORIES)
        st.success("기본 카테고리로 초기화했어요!")
        st.rerun()
