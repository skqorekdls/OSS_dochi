from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path

import streamlit as st

REQUIRED_KEYS = {"id", "type", "category", "difficulty", "question", "options", "answer", "explanation"}


@st.cache_data(show_spinner="문제 데이터와 분류 정보를 불러오는 중입니다...")
def load_questions(path: str) -> dict:
    time.sleep(1.0)
    file_path = Path(path)
    with file_path.open("r", encoding="utf-8") as f:
        raw_questions = json.load(f)

    cleaned_questions = []
    valid_categories = {"champion_basics", "skill_knowledge", "position_sense", "lore_world", "item_shop"}
    valid_difficulties = {"easy", "medium", "hard"}
    seen_ids: set[int] = set()

    for item in raw_questions:
        missing = REQUIRED_KEYS - set(item.keys())
        if missing:
            raise ValueError(f"질문 ID {item.get('id')}에 누락된 필드가 있습니다: {missing}")
        if item["id"] in seen_ids:
            raise ValueError(f"중복된 질문 ID가 있습니다: {item['id']}")
        seen_ids.add(item["id"])

        if item["type"] not in {"multiple_choice", "ox"}:
            raise ValueError(f"질문 ID {item['id']}의 type 값이 잘못되었습니다.")
        if item["category"] not in valid_categories:
            raise ValueError(f"질문 ID {item['id']}의 category 값이 잘못되었습니다.")
        if item["difficulty"] not in valid_difficulties:
            raise ValueError(f"질문 ID {item['id']}의 difficulty 값이 잘못되었습니다.")
        if not isinstance(item["options"], list) or len(item["options"]) < 2:
            raise ValueError(f"질문 ID {item['id']}의 options 형식이 잘못되었습니다.")
        if item["answer"] not in item["options"]:
            raise ValueError(f"질문 ID {item['id']}의 answer가 options에 없습니다.")
        cleaned_questions.append(item)

    return {
        "questions": cleaned_questions,
        "loaded_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "category_map": {
            "champion_basics": "챔피언 상식",
            "skill_knowledge": "스킬/패시브",
            "position_sense": "포지션/운영",
            "lore_world": "롤 lore",
            "item_shop": "상점/아이템",
        },
        "difficulty_map": {"easy": "쉬움", "medium": "보통", "hard": "어려움"},
        "total_count": len(cleaned_questions),
    }
