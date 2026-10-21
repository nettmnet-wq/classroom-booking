import os
from datetime import datetime, timedelta
import pandas as pd
import streamlit as st

# 페이지 설정
st.set_page_config(
    page_title="대학 강의실 예약 및 관리 시스템", page_icon="🏫", layout="wide"
)

EXCEL_FILE = "강의실사용신청 목록.xlsx"
RESERVATIONS_FILE = "reservations.csv"


@st.cache_data
def load_excel_data():
  if not os.path.exists(EXCEL_FILE):
    return None
  df = pd.read_excel(EXCEL_FILE, skiprows=0)
  return df


# 로컬 CSV 파일 기반 예약 내역 불러오기 또는 초기화
def load_reservations():
  if os.path.exists(RESERVATIONS_FILE):
    return pd.read_csv(RESERVATIONS_FILE)
  else:
    return pd.DataFrame(
        columns=[
            "ID",
            "건물",
            "강의실",
            "소속대학",
            "신청자",
            "사용날짜",
            "요일",
            "시작시간",
            "종료시간",
            "사용목적",
            "상태",
        ]
    )


def save_reservations(df):
  df.to_csv(RESERVATIONS_FILE, index=False, encoding="utf-8-sig")


df_excel = load_excel_data()

st.title("🏫 대학 강의실 예약 및 현황 관리 프로그램")
st.markdown("9시부터 23시까지 운영되는 강의실 통합 예약 및 시각화 현황판")

if df_excel is None:
  st.error(
      f"'{EXCEL_FILE}' 파일을 찾을 수 없습니다. 파이썬 파일과 같은 폴더에 엑셀 파일을 넣어주세요!"
  )
else:
  # 사이드바 메뉴 구성
  st.sidebar.header("📌 메뉴 탐색")
  menu = st.sidebar.radio(
      "원하시는 작업을 선택하세요",
      [
          "강의실 현황 조회 (시간표)",
          "단건(일반) 예약 신청",
          "기간/요일 반복 예약 신청",
          "관리자 예약 승인 관리",
      ],
  )

  work_df = df_excel.copy()
  work_df = work_df.dropna(subset=["No", "강의동", "강의실"])

  # 숫자 컬럼 소수점 제거 정수형 변환
  work_df["No"] = work_df["No"].astype(int)
  work_df["좌석"] = pd.to_numeric(work_df["좌석"], errors="coerce").fillna(0).astype(int)

  hours_list = [f"{h:02d}:00" for h in range(9, 24)]

  # 1. 강의실 현황 조회 메뉴
  if menu == "강의실 현황 조회 (시간표)":
    st.subheader("🔍 건물별 강의실 사용 현황 조회")

    col_d1, col_d2 = st.columns([1, 1])
    with col_d1:
      buildings = work_df["강의동"].dropna().unique().tolist()
      selected_building = st.selectbox("건물을 선택하세요", buildings)
    with col_d2:
      target_lookup_date = st.date_input("조회할 날짜 선택", value=datetime.today())

    days_kr = ["월", "화", "수", "목", "금", "토", "일"]
    target_day_name = days_kr[target_lookup_date.weekday()]
    st.info(f"📅 **{target_lookup_date} ({target_day_name}요일)** 기준 현황입니다.")

    b_df = work_df[work_df["강의동"] == selected_building].copy()
    display_df = b_df[["No", "강의동", "강의실", "좌석"]].copy()

    for h in hours_list:
      display_df[h] = ""

    res_df = load_reservations()
    if not res_df.empty:
      approved_res = res_df[
          (res_df["건물"].astype(str) == str(selected_building))
          & (res_df["사용날짜"].astype(str) == str(target_lookup_date))
          & (res_df["상태"].astype(str) == "승인완료")
      ]
    else:
      approved_res = pd.DataFrame()

    # 예약된 시간대 처리
    for _, row in approved_res.iterrows():
      r_name = row["강의실"]
      s_time = row["시작시간"]
      e_time = row["종료시간"]
      univ = row["소속대학"]

      is_first = True
      for h in hours_list:
        if s_time <= h < e_time:
          if is_first:
            display_df.loc[display_df["강의실"] == r_name, h] = f"[{univ}]"
            is_first = False
          else:
            display_df.loc[display_df["강의실"] == r_name, h] = ""

    st.markdown(f"### 📍 {selected_building} 시간대별 현황판 (09:00 ~ 23:00)")
    st.markdown("💡 관리자가 승인한 예약만 현황판에 노란색 배경과 소속 대학명으로 표시됩니다.")

    def highlight_reserved(df_to_style):
      styles = pd.DataFrame("", index=df_to_style.index, columns=df_to_style.columns)

      if not approved_res.empty:
        for _, row in approved_res.iterrows():
          r_name = row["강의실"]
          s_time = row["시작시간"]
          e_time = row["종료시간"]

          idx_list = df_to_style[df_to_style["강의실"] == r_name].index
          for idx in idx_list:
            for h in hours_list:
              if s_time <= h < e_time:
                styles.loc[idx, h] = "background-color: #FFF2CC; color: #111111; font-weight: bold; text-align: center; font-size: 13px;"

      for col in hours_list:
        if col not in styles.columns:
          continue
        for idx in styles.index:
          if styles.loc[idx, col] == "":
            styles.loc[idx, col] = "text-align: center; color: #888888;"

      return styles

    styled_df = display_df.style.apply(highlight_reserved, axis=None).set_properties(**{"text-align": "center"}, subset=["No", "좌석"])
    st.dataframe(styled_df, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.subheader("📋 당일 승인된 예약 상세 내역")
    if not approved_res.empty:
      st.dataframe(approved_res[["강의실", "소속대학", "신청자", "사용날짜", "시작시간", "종료시간", "사용목적"]], use_container_width=True, hide_index=True)
    else:
      st.info("해당 날짜에 승인된 예약 내역이 없습니다.")

  # 2-1. 단건(일반) 예약 신청 메뉴
  elif menu == "단건(일반) 예약 신청":
    st.subheader("📅 강의실 단건(일반) 예약 신청")
    st.markdown("📝 신청하신 내역은 **관리자 승인 후** 현황판에 반영됩니다.")

    with st.form("single_reservation_form"):
      col1, col2 = st.columns(2)

      with col1:
        req_univ = st.text_input("소속 대학/학과 입력", placeholder="예: 대학원교학처")
        req_name = st.text_input("신청자 성명", placeholder="홍길동 조교")

      with col2:
        buildings = work_df["강의동"].dropna().unique().tolist()
        selected_building = st.selectbox("건물 선택", buildings, key="s_res_bldg")
        room_list = work_df[work_df["강의동"] == selected_building]["강의실"].dropna().unique().tolist()
        selected_room = st.selectbox("강의실 선택", room_list, key="s_res_room")

      col_d1, col_t1, col_t2 = st.columns(3)
      with col_d1:
        target_date = st.date_input("사용 날짜", value=datetime.today())
      with col_t1:
        start_time = st.selectbox("시작 시간", hours_list[:-1], key="s_start")
      with col_t2:
        end_time = st.selectbox("종료 시간", hours_list[1:], index=1, key="s_end")

      purpose = st.text_area("사용 목적", placeholder="예: 특강 및 학과 행사 진행")
      submitted = st.form_submit_button("단건 예약 신청 제출")

      if submitted:
        if not req_univ or not req_name or not purpose:
          st.warning("모든 항목(소속, 성명, 목적)을 빠짐없이 입력해 주세요!")
        elif start_time >= end_time:
          st.error("종료 시간은 시작 시간보다 이후여야 합니다!")
        else:
          days_kr = ["월", "화", "수", "목", "금", "토", "일"]
          day_name = days_kr[target_date.weekday()] + "요일"
          res_df = load_reservations()
          conflict = False

          if not res_df.empty:
            active_res = res_df[
                (res_df["건물"].astype(str) == str(selected_building))
                & (res_df["강의실"].astype(str) == str(selected_room))
                & (res_df["사용날짜"].astype(str) == str(target_date))
                & (res_df["상태"].astype(str) != "반려")
            ]
            for _, r in active_res.iterrows():
              if r["시작시간"] < end_time and r["종료시간"] > start_time:
                conflict = True
                break

          if conflict:
            st.error("❌ 해당 날짜 및 시간대에 이미 예약(또는 대기 중인 예약)이 존재합니다!")
          else:
            next_id = int(res_df["ID"].max() + 1) if not res_df.empty and "ID" in res_df.columns and not pd.isna(res_df["ID"].max()) else 1
            new_row = {
                "ID": next_id, "건물": selected_building, "강의실": selected_room,
                "소속대학": req_univ, "신청자": req_name, "사용날짜": str(target_date),
                "요일": day_name, "시작시간": start_time, "종료시간": end_time,
                "사용목적": purpose, "상태": "승인대기"
            }
            res_df = pd.concat([res_df, pd.DataFrame([new_row])], ignore_index=True)
            save_reservations(res_df)
            st.success(f"🎉 [{selected_building} {selected_room}] 단건 예약 신청이 완료되었습니다! (관리자 승인 대기 중)")

  # 2-2. 기간/요일 반복 예약 신청 메뉴
  elif menu == "기간/요일 반복 예약 신청":
    st.subheader("📅 강의실 기간 및 요일 반복 예약 신청")
    st.markdown("📝 반복 신청하신 내역도 **관리자 승인 후** 현황판에 반영됩니다.")

    with st.form("repeat_reservation_form"):
      col1, col2 = st.columns(2)

      with col1:
        req_univ = st.text_input("소속 대학/학과 입력", placeholder="예: 대학원교학처", key="r_univ")
        req_name = st.text_input("신청자 성명", placeholder="홍길동 조교", key="r_name")

      with col2:
        buildings = work_df["강의동"].dropna().unique().tolist()
        selected_building = st.selectbox("건물 선택", buildings, key="r_res_bldg")
        room_list = work_df[work_df["강의동"] == selected_building]["강의실"].dropna().unique().tolist()
        selected_room = st.selectbox("강의실 선택", room_list, key="r_res_room")

      st.markdown("---")
      col_p1, col_p2, col_p3 = st.columns(3)
      with col_p1:
        start_date = st.date_input("시작일", value=datetime.today(), key="r_sdate")
      with col_p2:
        end_date = st.date_input("종료일", value=datetime.today() + timedelta(days=30), key="r_edate")
      with col_p3:
        target_weekday = st.selectbox("반복 요일 선택", ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일"])

      col_t1, col_t2 = st.columns(2)
      with col_t1:
        start_time = st.selectbox("시작 시간", hours_list[:-1], key="r_start")
      with col_t2:
        end_time = st.selectbox("종료 시간", hours_list[1:], index=1, key="r_end")

      purpose = st.text_area("사용 목적", placeholder="예: 2학기 정규 강의 대관", key="r_purpose")
      submitted = st.form_submit_button("반복 예약 신청 제출")

      if submitted:
        if not req_univ or not req_name or not purpose:
          st.warning("모든 항목(소속, 성명, 목적)을 빠짐없이 입력해 주세요!")
        elif start_time >= end_time:
          st.error("종료 시간은 시작 시간보다 이후여야 합니다!")
        elif start_date > end_date:
          st.error("종료일은 시작일 이후여야 합니다!")
        else:
          weekday_map = {"월요일": 0, "화요일": 1, "수요일": 2, "목요일": 3, "금요일": 4, "토요일": 5}
          target_wd = weekday_map[target_weekday]
          current_d = start_date
          dates_to_reserve = []

          while current_d <= end_date:
            if current_d.weekday() == target_wd:
              dates_to_reserve.append(current_d)
            current_d += timedelta(days=1)

          if not dates_to_reserve:
            st.warning("선택하신 기간 내에 지정한 요일이 존재하지 않습니다.")
          else:
            res_df = load_reservations()
            conflict_dates = []

            if not res_df.empty:
              for d in dates_to_reserve:
                str_d = str(d)
                active_res = res_df[
                    (res_df["건물"].astype(str) == str(selected_building))
                    & (res_df["강의실"].astype(str) == str(selected_room))
                    & (res_df["사용날짜"].astype(str) == str_d)
                    & (res_df["상태"].astype(str) != "반려")
                ]
                for _, r in active_res.iterrows():
                  if r["시작시간"] < end_time and r["종료시간"] > start_time:
                    conflict_dates.append(str_d)
                    break

            if conflict_dates:
              st.error(f"❌ 다음 날짜들에 이미 예약이 존재하여 충돌이 발생했습니다:\n{', '.join(conflict_dates)}")
            else:
              next_id = int(res_df["ID"].max() + 1) if not res_df.empty and "ID" in res_df.columns and not pd.isna(res_df["ID"].max()) else 1
              new_rows = []

              for d in dates_to_reserve:
                new_rows.append({
                    "ID": next_id, "건물": selected_building, "강의실": selected_room,
                    "소속대학": req_univ, "신청자": req_name, "사용날짜": str(d),
                    "요일": target_weekday, "시작시간": start_time, "종료시간": end_time,
                    "사용목적": purpose, "상태": "승인대기"
                })
                next_id += 1

              res_df = pd.concat([res_df, pd.DataFrame(new_rows)], ignore_index=True)
              save_reservations(res_df)
              st.success(f"🎉 [{selected_building} {selected_room}] 총 {len(dates_to_reserve)}건의 반복 예약 신청이 완료되었습니다! (관리자 승인 대기 중)")

  # 3. 관리자 예약 승인 관리 메뉴
  elif menu == "관리자 예약 승인 관리":
    st.subheader("🛠️ 관리자 예약 승인 및 반려 관리")
    st.markdown("신청된 내역을 확인하고 상태를 **[승인완료]**로 변경해야 현황판에 반영됩니다.")

    res_df = load_reservations()
    if res_df.empty:
      st.info("등록된 예약 신청 내역이 없습니다.")
    else:
      edited_df = st.data_editor(
          res_df,
          column_config={
              "상태": st.column_config.SelectboxColumn("예약 상태", options=["승인대기", "승인완료", "반려"], required=True)
          },
          disabled=["ID", "건물", "강의실", "소속대학", "신청자", "사용날짜", "요일", "시작시간", "종료시간", "사용목적"],
          hide_index=True,
          use_container_width=True,
      )

      if st.button("변경 사항 저장하기"):
        save_reservations(edited_df)
        st.success("✅ 예약 상태가 성공적으로 업데이트되었습니다!")
        st.rerun()
