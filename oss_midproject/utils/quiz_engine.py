
from __future__ import annotations

import random
import time
from collections import defaultdict


DIFFICULTY_RATIO = {
    "easy": 0.4,
    "medium": 0.4,
    "hard": 0.2,
}


def build_question_set(all_questions: list[dict], count: int, seed: int | None = None) -> list[dict]:
    rng = random.Random(seed)

    by_difficulty: dict[str, list[dict]] = defaultdict(list)
    for q in all_questions:
        by_difficulty[q["difficulty"]].append(q)

    targets = {
        "easy": round(count * DIFFICULTY_RATIO["easy"]),
        "medium": round(count * DIFFICULTY_RATIO["medium"]),
    }
    targets["hard"] = count - targets["easy"] - targets["medium"]

    selected: list[dict] = []
    leftovers: list[dict] = []

    for difficulty in ["easy", "medium", "hard"]:
        bucket = by_difficulty[difficulty][:]
        rng.shuffle(bucket)

        take_n = min(targets[difficulty], len(bucket))
        selected.extend(bucket[:take_n])
        leftovers.extend(bucket[take_n:])

    if len(selected) < count:
        rng.shuffle(leftovers)
        needed = count - len(selected)
        selected.extend(leftovers[:needed])

    if len(selected) < count:
        raise ValueError("선택한 문항 수보다 전체 문제 수가 부족합니다.")

    rng.shuffle(selected)
    return selected[:count]


def init_quiz_state(session_state, selected_questions: list[dict], timer_seconds: int):
    session_state.quiz_started = True
    session_state.quiz_finished = False
    session_state.selected_questions = selected_questions
    session_state.current_index = 0
    session_state.answers = []
    session_state.score = 0
    session_state.timer_seconds = timer_seconds
    session_state.question_started_at = time.time()
    session_state.quiz_seed = int(time.time())


def reset_quiz_state(session_state):
    keys = [
        "quiz_started",
        "quiz_finished",
        "selected_questions",
        "current_index",
        "answers",
        "score",
        "timer_seconds",
        "question_started_at",
        "quiz_seed",
    ]
    for key in keys:
        if key in session_state:
            del session_state[key]


def current_question(session_state) -> dict | None:
    if not session_state.get("quiz_started"):
        return None

    index = session_state.get("current_index", 0)
    questions = session_state.get("selected_questions", [])

    if index >= len(questions):
        return None

    return questions[index]


def submit_answer(session_state, question: dict, user_answer: str, timed_out: bool = False):
    is_correct = user_answer == question["answer"]

    session_state.answers.append(
        {
            "id": question["id"],
            "question": question["question"],
            "category": question["category"],
            "difficulty": question["difficulty"],
            "user_answer": user_answer,
            "correct_answer": question["answer"],
            "is_correct": is_correct,
            "timed_out": timed_out,
            "explanation": question["explanation"],
        }
    )

    if is_correct:
        session_state.score += 1

    session_state.current_index += 1

    if session_state.current_index >= len(session_state.selected_questions):
        session_state.quiz_finished = True
    else:
        session_state.question_started_at = time.time()


def build_result_summary(answer_records: list[dict]) -> dict:
    category_summary = defaultdict(lambda: {"correct": 0, "total": 0})
    difficulty_summary = defaultdict(lambda: {"correct": 0, "total": 0})
    wrong_answers = []

    for record in answer_records:
        category_summary[record["category"]]["total"] += 1
        difficulty_summary[record["difficulty"]]["total"] += 1

        if record["is_correct"]:
            category_summary[record["category"]]["correct"] += 1
            difficulty_summary[record["difficulty"]]["correct"] += 1
        else:
            wrong_answers.append(record)

    return {
        "category_summary": dict(category_summary),
        "difficulty_summary": dict(difficulty_summary),
        "wrong_answers": wrong_answers,
    }
