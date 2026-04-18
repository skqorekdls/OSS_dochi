from __future__ import annotations

import math
import random
import time
from collections import defaultdict

CATEGORY_ORDER = ["champion_basics", "skill_knowledge", "position_sense", "lore_world", "item_shop"]
DIFFICULTY_RATIO = {"easy": 0.4, "medium": 0.4, "hard": 0.2}


def _equal_targets(total: int, order: list[str]) -> dict[str, int]:
    base = {key: total // len(order) for key in order}
    remaining = total - sum(base.values())
    for key in order[:remaining]:
        base[key] += 1
    return base


def _difficulty_targets(total: int) -> dict[str, int]:
    raw = {k: total * v for k, v in DIFFICULTY_RATIO.items()}
    base = {k: math.floor(v) for k, v in raw.items()}
    remaining = total - sum(base.values())
    for key in sorted(raw.keys(), key=lambda x: raw[x] - base[x], reverse=True)[:remaining]:
        base[key] += 1
    return base


def _matrix_targets(total: int, category_targets: dict[str, int], difficulty_targets: dict[str, int]) -> dict[tuple[str, str], int]:
    matrix = {}
    row_rem = category_targets.copy()
    col_rem = difficulty_targets.copy()
    frac = []
    for cat in CATEGORY_ORDER:
        for diff in ["easy", "medium", "hard"]:
            ideal = category_targets[cat] * difficulty_targets[diff] / total
            whole = math.floor(ideal)
            matrix[(cat, diff)] = whole
            row_rem[cat] -= whole
            col_rem[diff] -= whole
            frac.append((ideal - whole, cat, diff))
    frac.sort(reverse=True)
    while sum(row_rem.values()) > 0:
        for _, cat, diff in frac:
            if row_rem[cat] > 0 and col_rem[diff] > 0:
                matrix[(cat, diff)] += 1
                row_rem[cat] -= 1
                col_rem[diff] -= 1
                break
    return matrix


def build_question_set(all_questions: list[dict], count: int, seed: int | None = None) -> list[dict]:
    rng = random.Random(seed)
    buckets: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for q in all_questions:
        buckets[(q["category"], q["difficulty"])].append(q)
    for bucket in buckets.values():
        rng.shuffle(bucket)

    category_targets = _equal_targets(count, CATEGORY_ORDER)
    difficulty_targets = _difficulty_targets(count)
    targets = _matrix_targets(count, category_targets, difficulty_targets)

    selected = []
    used_ids: set[int] = set()
    for cat in CATEGORY_ORDER:
        for diff in ["easy", "medium", "hard"]:
            need = targets[(cat, diff)]
            take = buckets[(cat, diff)][:need]
            selected.extend(take)
            used_ids.update(q["id"] for q in take)

    if len(selected) < count:
        leftovers = [q for q in all_questions if q["id"] not in used_ids]
        rng.shuffle(leftovers)
        selected.extend(leftovers[: count - len(selected)])

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


def reset_quiz_state(session_state):
    for key in ["quiz_started", "quiz_finished", "selected_questions", "current_index", "answers", "score", "timer_seconds", "question_started_at"]:
        if key in session_state:
            del session_state[key]


def current_question(session_state) -> dict | None:
    if not session_state.get("quiz_started"):
        return None
    idx = session_state.get("current_index", 0)
    questions = session_state.get("selected_questions", [])
    if idx >= len(questions):
        return None
    return questions[idx]


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
