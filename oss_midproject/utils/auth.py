ALLOWED_USERS = {"faker", "teemo", "lux", "garen", "jinx", "dain", "baekdain", "summoner", "demacia", "ionia"}


def validate_username(username: str) -> tuple[bool, str]:
    username = username.strip()
    if not username:
        return False, "사용자명을 입력해주세요."
    if len(username) < 2:
        return False, "사용자명은 2자 이상이어야 합니다."
    if " " in username:
        return False, "공백 없는 사용자명을 입력해주세요."
    if username.lower() not in ALLOWED_USERS:
        return False, "등록되지 않은 사용자명입니다."
    return True, "로그인되었습니다."


def normalize_username(username: str) -> str:
    return username.strip()
