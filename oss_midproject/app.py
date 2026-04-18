from __future__ import annotations

import math
import time
from pathlib import Path

import streamlit as st
from streamlit_autorefresh import st_autorefresh

from utils.auth import normalize_username, validate_username
from utils.data_loader import load_questions
from utils.quiz_engine import build_question_set, build_result_summary, current_question, init_quiz_state, reset_quiz_state, submit_answer

st.set_page_config(page_title="롤 상식 퀴즈", page_icon="🎮", layout="wide")

BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "data" / "questions.json"
CSS_PATH = BASE_DIR / "assets" / "style.css"

CATEGORY_MAP = {
    "champion_basics": "챔피언 상식",
    "skill_knowledge": "스킬/패시브",
    "position_sense": "포지션/운영",
    "lore_world": "롤 lore",
    "item_shop": "상점/아이템",
}
DIFFICULTY_MAP = {"easy": "쉬움", "medium": "보통", "hard": "어려움"}


def inject_css():
    with open(CSS_PATH, "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


def init_base_state():
    for key, value in {"logged_in": False, "username": ""}.items():
        if key not in st.session_state:
            st.session_state[key] = value


def render_header():
    st.markdown(
        """
        <div class="hero-card">
            <div class="hero-title">🎮 롤 상식 퀴즈</div>
            <div class="hero-sub">챔피언 · 스킬/패시브 · 포지션 · lore · 상점/아이템을 섞어 푸는 다크 테마 퀴즈</div>
            <div class="badge-row">
                <div class="badge">학번 2021204034</div>
                <div class="badge">백다인</div>
                <div class="badge">문항 수 10 / 20 / 50 / 100</div>
                <div class="badge">타이머 없음 / 15초 / 30초</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar(data_info: dict):
    with st.sidebar:
        st.markdown("## 👤 프로필")
        st.write("**이름**: 백다인")
        st.write("**학번**: 2021204034")

        st.markdown("---")
        st.markdown("## 📦 데이터")
        st.write("**총 문제 수**:", data_info["total_count"])
        st.write("**마지막 로드 시각**:", data_info["loaded_at"])

        st.markdown("---")
        st.markdown("## 🔐 로그인 상태")
        if st.session_state.logged_in:
            st.success(f"{st.session_state.username} 님 접속 중")
            if st.button("로그아웃", use_container_width=True):
                st.session_state.logged_in = False
                st.session_state.username = ""
                reset_quiz_state(st.session_state)
                st.rerun()
        else:
            st.info("사용자명을 입력하면 퀴즈를 시작할 수 있습니다.")

        st.markdown("---")
        st.markdown("## 🗂 출제 영역")
        for label in CATEGORY_MAP.values():
            st.write(f"- {label}")


def render_login_panel():
    st.markdown('<div class="panel-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">로그인</div>', unsafe_allow_html=True)
    st.write("사용자명을 입력하고 퀴즈 세션을 시작하세요.")
    username = st.text_input("사용자명", placeholder="예: faker")
    if st.button("입장하기", use_container_width=True, type="primary"):
        ok, message = validate_username(username)
        if ok:
            st.session_state.logged_in = True
            st.session_state.username = normalize_username(username)
            st.success(message)
            time.sleep(0.35)
            st.rerun()
        else:
            st.error(message)
    st.caption("공백 없는 사용자명을 사용하세요. 미리 등록된 이름과 일치하면 접속됩니다.")
    st.markdown("</div>", unsafe_allow_html=True)


def render_data_panel(data_info: dict):
    st.markdown('<div class="panel-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">데이터 룸</div>', unsafe_allow_html=True)
    st.write("문제 데이터는 JSON 파일에서 불러오고, 로딩과 검증 결과는 캐시에 저장됩니다.")
    st.write("같은 파일을 다시 읽을 때는 전처리를 반복하지 않아 더 빠르게 동작합니다.")
    st.info(f"현재 세션 기준 데이터 로드 시각: {data_info['loaded_at']}")
    st.markdown("</div>", unsafe_allow_html=True)


def render_quiz_setup(all_questions: list[dict]):
    st.markdown('<div class="panel-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">퀴즈 설정</div>', unsafe_allow_html=True)
    enabled_counts = [n for n in [10, 20, 50, 100] if n <= len(all_questions)]
    c1, c2 = st.columns(2)
    with c1:
        question_count = st.selectbox("문항 수", enabled_counts, index=0)
    with c2:
        timer_label = st.selectbox("타이머", ["없음", "15초", "30초"], index=0)
    timer_seconds = 0 if timer_label == "없음" else int(timer_label.replace("초", ""))
    st.caption("문제는 5개 카테고리에서 고르게, 난이도는 쉬움:보통:어려움 = 4:4:2 비율로 섞입니다.")
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
            <div class="small-text">지금 세션은 유지 중입니다. 문항 수와 타이머를 정한 뒤 바로 퀴즈를 시작할 수 있습니다.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    c1, c2, c3 = st.columns(3)
    c1.metric("총 문제 수", f"{data_info['total_count']}개")
    c2.metric("출제 카테고리", "5개")
    c3.metric("로그인 사용자", st.session_state.username)


def auto_submit_if_time_over(question: dict):
    timer_seconds = st.session_state.get("timer_seconds", 0)
    if timer_seconds <= 0:
        return
    elapsed = time.time() - st.session_state.question_started_at
    remaining = max(0, math.ceil(timer_seconds - elapsed))
    st_autorefresh(interval=1000, key=f"timer_refresh_{st.session_state.current_index}")
    st.markdown(f'<div class="timer-box">⏳ 남은 시간: {remaining}초</div>', unsafe_allow_html=True)
    if remaining <= 0:
        submit_answer(st.session_state, question, user_answer="시간 초과", timed_out=True)
        st.warning("시간이 초과되어 자동으로 다음 문제로 넘어갑니다.")
        time.sleep(0.35)
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
            <div class="question-meta">문제 {current_number} / {total_questions} &nbsp;&nbsp;|&nbsp;&nbsp; {CATEGORY_MAP[question['category']]} &nbsp;&nbsp;|&nbsp;&nbsp; {DIFFICULTY_MAP[question['difficulty']]}</div>
            <div class="section-title">{question['question']}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    selected_answer = st.radio("답을 선택하세요", question["options"], index=None, key=f"answer_{question['id']}")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("제출", type="primary", use_container_width=True):
            if selected_answer is None:
                st.error("답을 먼저 선택해주세요.")
            else:
                submit_answer(st.session_state, question, selected_answer)
                st.rerun()
    with c2:
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
            <div class="hero-title">🏁 결과 리포트</div>
            <div class="hero-sub">총점, 정답률, 카테고리별 성취도와 틀린 문제 복습을 확인할 수 있습니다.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    c1, c2, c3 = st.columns(3)
    c1.metric("최종 점수", f"{score} / {total_questions}")
    c2.metric("정답률", f"{accuracy}%")
    c3.metric("시간 초과", f"{sum(1 for a in st.session_state.answers if a['timed_out'])}개")

    st.markdown("### 📊 카테고리별 리포트")
    cols = st.columns(5)
    for idx, category in enumerate(["champion_basics", "skill_knowledge", "position_sense", "lore_world", "item_shop"]):
        info = summary["category_summary"].get(category, {"correct": 0, "total": 0})
        total = info["total"]
        correct = info["correct"]
        pct = 0 if total == 0 else round(correct / total * 100, 1)
        with cols[idx]:
            st.metric(CATEGORY_MAP[category], f"{correct}/{total}", f"{pct}%")

    st.markdown("### 🧠 난이도별 리포트")
    diff_cols = st.columns(3)
    for idx, difficulty in enumerate(["easy", "medium", "hard"]):
        info = summary["difficulty_summary"].get(difficulty, {"correct": 0, "total": 0})
        total = info["total"]
        correct = info["correct"]
        pct = 0 if total == 0 else round(correct / total * 100, 1)
        with diff_cols[idx]:
            st.metric(DIFFICULTY_MAP[difficulty], f"{correct}/{total}", f"{pct}%")

    st.markdown("### ❌ 틀린 문제 복습")
    wrong_answers = summary["wrong_answers"]
    if not wrong_answers:
        st.markdown('<div class="good-box">모든 문제를 맞혔습니다. 완벽한 플레이였습니다!</div>', unsafe_allow_html=True)
    else:
        for idx, item in enumerate(wrong_answers, start=1):
            picked = "시간 초과" if item["timed_out"] else item["user_answer"]
            st.markdown(
                f"""
                <div class="bad-box">
                    <b>{idx}. {item['question']}</b><br>
                    내가 고른 답: {picked}<br>
                    정답: {item['correct_answer']}<br>
                    해설: {item['explanation']}
                </div>
                """,
                unsafe_allow_html=True,
            )
    c1, c2 = st.columns(2)
    with c1:
        if st.button("다시 풀기", type="primary", use_container_width=True):
            reset_quiz_state(st.session_state)
            st.rerun()
    with c2:
        if st.button("로그아웃", use_container_width=True):
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
        left, right = st.columns([1.05, 0.95])
        with left:
            render_login_panel()
        with right:
            render_data_panel(data_info)
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
