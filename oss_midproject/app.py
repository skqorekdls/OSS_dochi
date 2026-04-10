
from __future__ import annotations

import math
import time
from pathlib import Path

import streamlit as st
from streamlit_autorefresh import st_autorefresh

from utils.auth import ALLOWED_USERS, normalize_username, validate_username
from utils.data_loader import load_questions
from utils.quiz_engine import (
    build_question_set,
    build_result_summary,
    current_question,
    init_quiz_state,
    reset_quiz_state,
    submit_answer,
)

st.set_page_config(
    page_title="롤 상식 퀴즈",
    page_icon="🎮",
    layout="wide",
)


BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "data" / "questions.json"
CSS_PATH = BASE_DIR / "assets" / "style.css"


CATEGORY_MAP = {
    "champion_basics": "챔피언 상식",
    "skill_knowledge": "스킬 지식",
    "position_sense": "포지션 감각",
    "lore_world": "세계관 이해",
}

DIFFICULTY_MAP = {
    "easy": "쉬움",
    "medium": "보통",
    "hard": "어려움",
}


def inject_css():
    with open(CSS_PATH, "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


def init_base_state():
    defaults = {
        "logged_in": False,
        "username": "",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def render_header():
    st.markdown(
        """
        <div class="hero-card">
            <div class="hero-title">🎮 롤 상식 퀴즈</div>
            <div class="hero-sub">
                챔피언 상식, 스킬 지식, 포지션 감각, 세계관 이해를 한 번에 테스트하는 Streamlit 퀴즈 앱
            </div>
            <div class="badge-row">
                <div class="badge">학번: 2021204034</div>
                <div class="badge">이름: 백다인</div>
                <div class="badge">로그인 기능 포함</div>
                <div class="badge">캐싱 기능 포함</div>
                <div class="badge">객관식 + O/X 혼합</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar(data_info: dict):
    with st.sidebar:
        st.markdown("## 🧾 과제 정보")
        st.write("**학번**: 2021204034")
        st.write("**이름**: 백다인")
        st.write("**총 보유 문제 수**:", data_info["total_count"])
        st.write("**캐시 생성 시각**:", data_info["loaded_at"])

        st.markdown("---")
        st.markdown("## 👤 로그인 상태")
        if st.session_state.logged_in:
            st.success(f"{st.session_state.username} 님 로그인 중")
            if st.button("로그아웃", use_container_width=True):
                st.session_state.logged_in = False
                st.session_state.username = ""
                reset_quiz_state(st.session_state)
                st.rerun()
        else:
            st.info("아직 로그인하지 않았습니다.")

        st.markdown("---")
        st.markdown("## 🎯 카테고리")
        for key, label in CATEGORY_MAP.items():
            st.write(f"- {label}")

        st.markdown("---")
        st.markdown("## ⏱ 타이머 옵션")
        st.write("- 없음")
        st.write("- 15초")
        st.write("- 30초")


def render_login_panel():
    st.markdown('<div class="panel-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">로그인</div>', unsafe_allow_html=True)
    st.write("등록된 사용자명으로 로그인할 수 있습니다.")
    st.caption("예시 사용자명: " + ", ".join(sorted(ALLOWED_USERS)))

    username = st.text_input("사용자명 입력", placeholder="예: faker")
    col1, col2 = st.columns([1, 3])

    with col1:
        login_clicked = st.button("로그인", use_container_width=True)

    if login_clicked:
        ok, message = validate_username(username)
        if ok:
            st.session_state.logged_in = True
            st.session_state.username = normalize_username(username)
            st.success(message)
            time.sleep(0.4)
            st.rerun()
        else:
            st.error(message)

    st.markdown(
        """
        <div class="small-text">
            이 앱의 로그인은 과제용 간단 로그인입니다. <br>
            입력한 사용자명이 미리 정의된 목록과 일치하면 성공, 아니면 실패 처리됩니다.
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)


def render_cache_panel(data_info: dict):
    st.markdown('<div class="panel-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">캐싱 기능 설명</div>', unsafe_allow_html=True)
    st.write(
        "문제 JSON 파일을 읽고, 필수 필드 검증 및 카테고리/난이도 정보를 정리하는 전처리 과정을 "
        "`st.cache_data`로 캐싱했습니다."
    )
    st.write(
        "앱을 처음 실행할 때는 의도적으로 약간의 로딩이 보이지만, 이후 같은 데이터는 캐시에서 재사용되어 더 빠르게 동작합니다."
    )
    st.info(f"현재 화면에서 사용 중인 캐시 생성 시각: {data_info['loaded_at']}")
    st.markdown("</div>", unsafe_allow_html=True)


def render_quiz_setup(all_questions: list[dict]):
    st.markdown('<div class="panel-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">퀴즈 시작 설정</div>', unsafe_allow_html=True)

    total_available = len(all_questions)
    count_candidates = [10, 20, 50, 100]
    enabled_counts = [n for n in count_candidates if n <= total_available]

    if not enabled_counts:
        st.error("사용 가능한 문제가 부족합니다.")
        st.stop()

    col1, col2 = st.columns(2)
    with col1:
        question_count = st.selectbox("문항 수 선택", enabled_counts, index=0)

    with col2:
        timer_label = st.selectbox("타이머 설정", ["없음", "15초", "30초"], index=0)

    timer_seconds = 0 if timer_label == "없음" else int(timer_label.replace("초", ""))

    st.caption("문항은 쉬움:보통:어려움 = 4:4:2 비율에 맞춰 랜덤으로 뽑힙니다.")

    if st.button("퀴즈 시작", type="primary", use_container_width=True):
        selected = build_question_set(all_questions, question_count, seed=int(time.time()))
        init_quiz_state(st.session_state, selected_questions=selected, timer_seconds=timer_seconds)
        st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


def render_dashboard(data_info: dict):
    st.markdown(
        f"""
        <div class="panel-card">
            <div class="section-title">환영합니다, {st.session_state.username} 님</div>
            <div class="small-text">
                현재 로그인 상태가 유지되고 있습니다. 아래에서 문항 수와 타이머를 선택한 뒤 퀴즈를 시작하세요.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("총 문제 수", f"{data_info['total_count']}개")
    with col2:
        st.metric("캐시 생성 시각", data_info["loaded_at"])
    with col3:
        st.metric("로그인 사용자", st.session_state.username)


def auto_submit_if_time_over(question: dict):
    timer_seconds = st.session_state.get("timer_seconds", 0)
    if timer_seconds <= 0:
        return

    elapsed = time.time() - st.session_state.question_started_at
    remaining = max(0, math.ceil(timer_seconds - elapsed))

    st_autorefresh(interval=1000, key=f"timer_refresh_{st.session_state.current_index}")
    st.markdown(
        f'<div class="timer-box">⏳ 남은 시간: {remaining}초</div>',
        unsafe_allow_html=True,
    )

    if remaining <= 0:
        submit_answer(st.session_state, question, user_answer="시간 초과", timed_out=True)
        st.warning("시간이 초과되어 자동으로 다음 문제로 넘어갑니다.")
        time.sleep(0.4)
        st.rerun()


def render_quiz_question():
    question = current_question(st.session_state)
    if not question:
        return

    auto_submit_if_time_over(question)

    total_questions = len(st.session_state.selected_questions)
    current_number = st.session_state.current_index + 1

    st.progress(current_number / total_questions)
    st.markdown(
        f"""
        <div class="question-card">
            <div class="question-meta">
                문제 {current_number} / {total_questions}
                &nbsp;&nbsp;|&nbsp;&nbsp;
                카테고리: {CATEGORY_MAP[question['category']]}
                &nbsp;&nbsp;|&nbsp;&nbsp;
                난이도: {DIFFICULTY_MAP[question['difficulty']]}
            </div>
            <div class="section-title">{question['question']}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    widget_key = f"answer_{question['id']}"
    selected_answer = st.radio(
        "답을 선택하세요",
        question["options"],
        index=None,
        key=widget_key,
    )

    col1, col2 = st.columns(2)

    with col1:
        if st.button("제출하기", type="primary", use_container_width=True):
            if selected_answer is None:
                st.error("답을 먼저 선택해주세요.")
            else:
                submit_answer(st.session_state, question, selected_answer)
                st.rerun()

    with col2:
        if st.button("중도 종료", use_container_width=True):
            st.session_state.quiz_finished = True
            st.rerun()


def render_result_page():
    total_questions = len(st.session_state.get("selected_questions", []))
    score = st.session_state.get("score", 0)
    accuracy = 0 if total_questions == 0 else round(score / total_questions * 100, 1)

    summary = build_result_summary(st.session_state.answers)

    st.markdown(
        """
        <div class="panel-card">
            <div class="hero-title">🏁 퀴즈 결과</div>
            <div class="hero-sub">점수, 정답률, 카테고리별 리포트, 틀린 문제 복습을 확인할 수 있습니다.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("최종 점수", f"{score} / {total_questions}")
    with col2:
        st.metric("정답률", f"{accuracy}%")
    with col3:
        timeout_count = sum(1 for a in st.session_state.answers if a["timed_out"])
        st.metric("시간 초과", f"{timeout_count}개")

    st.markdown("### 📊 카테고리별 리포트")
    category_columns = st.columns(4)
    ordered_categories = ["champion_basics", "skill_knowledge", "position_sense", "lore_world"]

    for idx, category in enumerate(ordered_categories):
        info = summary["category_summary"].get(category, {"correct": 0, "total": 0})
        total = info["total"]
        correct = info["correct"]
        pct = 0 if total == 0 else round(correct / total * 100, 1)
        with category_columns[idx]:
            st.metric(CATEGORY_MAP[category], f"{correct}/{total}", f"{pct}%")

    st.markdown("### 🧠 난이도별 리포트")
    diff_columns = st.columns(3)
    for idx, difficulty in enumerate(["easy", "medium", "hard"]):
        info = summary["difficulty_summary"].get(difficulty, {"correct": 0, "total": 0})
        total = info["total"]
        correct = info["correct"]
        pct = 0 if total == 0 else round(correct / total * 100, 1)
        with diff_columns[idx]:
            st.metric(DIFFICULTY_MAP[difficulty], f"{correct}/{total}", f"{pct}%")

    st.markdown("### ❌ 틀린 문제 복습")
    wrong_answers = summary["wrong_answers"]
    if not wrong_answers:
        st.markdown(
            '<div class="good-box">모든 문제를 맞혔습니다. 완벽한 플레이였습니다!</div>',
            unsafe_allow_html=True,
        )
    else:
        for idx, item in enumerate(wrong_answers, start=1):
            box_class = "bad-box"
            user_text = item["user_answer"]
            if item["timed_out"]:
                user_text = "시간 초과"

            st.markdown(
                f"""
                <div class="{box_class}">
                    <b>{idx}. {item['question']}</b><br>
                    내가 고른 답: {user_text}<br>
                    정답: {item['correct_answer']}<br>
                    해설: {item['explanation']}
                </div>
                """,
                unsafe_allow_html=True,
            )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("다시 풀기", type="primary", use_container_width=True):
            reset_quiz_state(st.session_state)
            st.rerun()

    with col2:
        if st.button("로그아웃 후 종료", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.username = ""
            reset_quiz_state(st.session_state)
            st.rerun()


def main():
    inject_css()
    init_base_state()

    data_info = load_questions(str(DATA_PATH))
    all_questions = data_info["questions"]

    render_header()
    render_sidebar(data_info)

    if not st.session_state.logged_in:
        left, right = st.columns([1.15, 0.85])
        with left:
            render_login_panel()
        with right:
            render_cache_panel(data_info)
        return

    render_dashboard(data_info)

    if st.session_state.get("quiz_finished"):
        render_result_page()
        return

    if st.session_state.get("quiz_started"):
        render_quiz_question()
    else:
        render_quiz_setup(all_questions)


if __name__ == "__main__":
    main()
