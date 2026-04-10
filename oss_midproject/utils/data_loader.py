
from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path

import streamlit as st


REQUIRED_KEYS = {"id", "type", "category", "difficulty", "question", "options", "answer", "explanation"}


@st.cache_data(show_spinner="퀴즈 데이터와 카테고리 정보를 불러오는 중입니다...")
def load_questions(path: str) -> dict:
    """
    실제 과제에서 캐싱을 설명하기 좋도록
    - JSON 로딩
    - 데이터 유효성 검사
    - 간단한 전처리
    를 한 번에 묶어 캐시합니다.
    """
    time.sleep(1.2)  # 캐싱 시연을 위한 의도적 지연

    file_path = Path(path)
    with file_path.open("r", encoding="utf-8") as f:
        raw_questions = json.load(f)

    cleaned_questions = []
    for item in raw_questions:
        missing = REQUIRED_KEYS - set(item.keys())
        if missing:
            raise ValueError(f"질문 ID {item.get('id')}에 누락된 필드가 있습니다: {missing}")

        if item["type"] not in {"multiple_choice", "ox"}:
            raise ValueError(f"질문 ID {item['id']}의 type 값이 잘못되었습니다.")

        if item["difficulty"] not in {"easy", "medium", "hard"}:
            raise ValueError(f"질문 ID {item['id']}의 difficulty 값이 잘못되었습니다.")

        if not isinstance(item["options"], list) or len(item["options"]) < 2:
            raise ValueError(f"질문 ID {item['id']}의 options 형식이 잘못되었습니다.")

        if item["answer"] not in item["options"]:
            raise ValueError(f"질문 ID {item['id']}의 answer가 options에 없습니다.")

        cleaned_questions.append(item)

    category_map = {
        "champion_basics": "챔피언 상식",
        "skill_knowledge": "스킬 지식",
        "position_sense": "포지션 감각",
        "lore_world": "세계관 이해",
    }

    difficulty_map = {
        "easy": "쉬움",
        "medium": "보통",
        "hard": "어려움",
    }

    return {
        "questions": cleaned_questions,
        "loaded_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "category_map": category_map,
        "difficulty_map": difficulty_map,
        "total_count": len(cleaned_questions),
    }
