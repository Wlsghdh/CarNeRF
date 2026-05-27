"""LLM prompt injection 방어용 sanitize.

판매자 매물 설명 / 사용자 리뷰 / 결함 박스 설명처럼 외부 입력이
시스템 프롬프트 옆에 그대로 붙으면, "이전 지시 무시하고 …" 같은
명령으로 모델 응답을 조작할 수 있다. 길이 컷 + 지시 키워드 mask로
1차 방어한다 (완벽한 방어는 불가능 — sandboxing/구조화 응답 병행).
"""
import re

# 길이 제한 — 정상 입력은 한참 짧음. 초과분은 prompt 토큰 절약 + 폭주 방지.
_MAX_DESC_CHARS = 500
_MAX_REVIEW_CHARS = 400

# 흔한 injection 시도 패턴. 한국어/영어 변형 포함.
_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior|above)\s+(instructions?|prompts?)",
    r"disregard\s+(all\s+)?(previous|prior|above)",
    r"forget\s+(all\s+)?(previous|prior|above)",
    r"이전\s*(의|모든)?\s*(지시|명령|규칙|프롬프트)\s*(은|는|를)?\s*무시",
    r"위\s*(의|에\s*있는|모든)?\s*(지시|명령|규칙|프롬프트)\s*(을|를)?\s*무시",
    r"규칙\s*(을|를)?\s*무시",
    r"prompt\s*injection",
    r"system\s*[:：]\s*",
    r"<\s*/?\s*(system|assistant|instruction)\s*>",
    # role-play 우회
    r"이제부터\s*너는\s*",
    r"you\s+are\s+now\s+",
    # JSON 응답 강제 우회 시도
    r'"\s*fit\s*"\s*:\s*true',
    r'"\s*reason\s*"\s*:',
]

_PATTERN_RE = re.compile("|".join(_INJECTION_PATTERNS), re.IGNORECASE)


def sanitize_user_text(text: str, max_chars: int = _MAX_DESC_CHARS) -> str:
    """외부 입력 텍스트를 LLM 프롬프트에 넣기 전 정화.

    - 길이 컷 (`max_chars` 초과분 `[…생략]` 으로 대체).
    - injection 키워드는 `[차단됨]` 으로 mask.
    - 줄바꿈/탭 정규화 (구조 깨기 시도 방지).
    - 빈 문자열/None 안전 처리.
    """
    if not text:
        return ""
    s = str(text)
    # 1) 정규화
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n{3,}", "\n\n", s).strip()
    # 2) injection 키워드 mask
    s = _PATTERN_RE.sub("[차단됨]", s)
    # 3) 길이 컷
    if len(s) > max_chars:
        s = s[:max_chars].rstrip() + " […생략]"
    return s


def sanitize_review(text: str) -> str:
    """사용자 리뷰 본문용 — 길이 한도가 더 짧다."""
    return sanitize_user_text(text, max_chars=_MAX_REVIEW_CHARS)
