"""화면·보고서에 쓰는 코드 → 한글 표 (V1.0.0, 사용자 명세 2026-11-13 6-3·7-2·2-1, 결정 D6·범위 밖 3건 포함).

결과 데이터(JSON·기술 부록·엑셀 기술부록)의 코드는 그대로 둔다. 사람이 읽는 화면·Word·PDF 본문만 바꾼다.
화면은 /api/finding-categories 응답(names·code_words·field_words)으로 이 표를 받는다(app.js에 같은 표를 두지 않는다 — F1 T4).
"""
from __future__ import annotations

import re
from typing import Dict

from packages.common.enums import FindingType

# 결과 유형 97종의 한글 이름(목록·보고서 '유형' 칸, 인젝션 결과 제목 속 유형 이름).
FINDING_TYPE_NAMES: Dict[str, str] = {
    "CASE_NOT_FOUND": "판례 미발견",
    "CASE_METADATA_MISMATCH": "판례 서지 불일치",
    "CASE_QUOTE_MISMATCH": "판례 인용문 불일치",
    "CASE_HOLDING_DISTORTION": "판시 취지 왜곡",
    "CASE_CITATION_ERROR": "판례 인용 오류",
    "LAW_CITATION_ERROR": "법령 인용 오류",
    "TEMPORAL_LAW_MISMATCH": "법령 적용 시점 불일치",
    "ACADEMIC_CITATION_ERROR": "학술 문헌 인용 오류",
    "FACT_CONTRADICTION": "사실관계 불일치",
    "CROSS_DOCUMENT_CONTRADICTION": "문서 간 모순",
    "TIMELINE_CONTRADICTION": "날짜 선후 불일치",
    "ARITHMETIC_MISMATCH": "계산 불일치",
    "METADATA_ANOMALY": "문서 속성 이상",
    "HIDDEN_TEXT_MISMATCH": "숨은 글자 불일치",
    "OCR_LAYER_MISMATCH": "OCR 층 불일치",
    "OCR_LOW_QUALITY": "글자 인식 품질 낮음",
    "SIGNATURE_INVALID": "전자서명 무효",
    "MODIFIED_AFTER_SIGNATURE": "서명 뒤 수정",
    "PAGE_STRUCTURE_OUTLIER": "쪽 구조 이상",
    "PROMPT_INJECTION_SUSPECTED": "프롬프트 속임수 의심",
    "HIDDEN_INSTRUCTION": "숨은 지시문",
    "META_INSTRUCTION": "기계 지시문",
    "SYSTEM_OVERRIDE_ATTEMPT": "시스템 지시 무력화 시도",
    "ROLE_OVERRIDE_ATTEMPT": "역할 바꾸기 시도",
    "VERIFICATION_SUPPRESSION": "검증 회피",
    "OUTPUT_MANIPULATION_ATTEMPT": "결과 조작 시도",
    "ENCODED_INSTRUCTION": "인코딩된 지시문",
    "OBFUSCATED_INSTRUCTION": "난독화한 지시문",
    "UNICODE_SMUGGLING": "유니코드 은닉",
    "OCR_LAYER_INJECTION": "OCR 층 인젝션",
    "METADATA_INJECTION": "문서 속성 인젝션",
    "MULTIMODAL_INJECTION": "이미지 인젝션",
    "RAG_POISONING_SIGNAL": "참고자료 오염 신호",
    "TOOL_MANIPULATION_ATTEMPT": "도구 조작 시도",
    "DATA_EXFILTRATION_INSTRUCTION": "정보 유출 지시문",
    "MODEL_OUTPUT_QUARANTINED": "모델 응답 격리",
    "AI_AUTHORSHIP_LIKELY": "AI 작성 참고 신호",
    "AI_FULL_GENERATION_SUSPECTED": "전체 AI 작성 의심",
    "AI_HALLUCINATED_CONTENT": "AI 지어낸 내용 의심",
    "LEGAL_ARGUMENT_INVALID": "법률 주장 부당",
    "STYLE_SHIFT": "문체 급변",
    "MODEL_ATTRIBUTION_SIGNAL": "생성 모델 흔적",
    "RESIDUAL_TRACKED_CHANGE": "변경 추적 잔존",
    "RESIDUAL_COMMENT": "메모 잔존",
    "DELETED_TEXT_RECOVERABLE": "삭제 글자 복구 가능",
    "PRIOR_VERSION_RECOVERABLE": "이전 판 복구 가능",
    "REDACTION_FAILURE": "가림 처리 실패",
    "HIDDEN_SHEET_OR_ROW": "숨긴 시트·행",
    "CROPPED_IMAGE_RESIDUE": "잘린 이미지 잔존",
    "TEMPLATE_RESIDUE": "서식 문구 잔존",
    "SPECIMEN_DOCUMENT_DECLARED": "견본 문서 표시",
    "INVALID_IDENTIFIER": "식별번호 형식 오류",
    "PLACEHOLDER_IDENTIFIER": "임시 식별번호",
    "AUTHORSHIP_METADATA_LEAK": "작성자 정보 노출",
    "GEOLOCATION_METADATA_LEAK": "위치 정보 노출",
    "STEGANOGRAPHIC_PAYLOAD": "이미지 속 숨은 자료",
    "TRACKING_CANARY_DETECTED": "추적 표식 발견",
    "DOCUMENT_FINGERPRINT_SUSPECTED": "문서 식별 표식 의심",
    "COVERT_CHANNEL_SUSPECTED": "은닉 통로 의심",
    "PRIVILEGE_EXPOSURE_RISK": "비밀유지 자료 노출 위험",
    "OUTBOUND_LEAK_RISK": "외부 유출 위험",
    "ISSUE_EVASION_SIGNAL": "쟁점 회피 신호",
    "IMPLICIT_ADMISSION_SIGNAL": "묵시적 인정 신호",
    "LIABILITY_HEDGING_SIGNAL": "책임 회피 표현 신호",
    "COERCIVE_LANGUAGE_SIGNAL": "강압적 표현 신호",
    "SELECTIVE_QUOTATION_SIGNAL": "선택적 인용 신호",
    "CASE_RELEVANCE_WEAK": "판례 관련성 약함",
    "STATUTE_NONEXISTENT": "법령 목록에 없음",
    "STATUTE_TEXT_MISMATCH": "조문 내용 불일치",
    "INTERNAL_CITATION_ERROR": "문서 안 참조 오류",
    "QUOTE_MISMATCH": "인용문 불일치",
    "FACT_UNSUPPORTED": "근거 없는 사실 주장",
    "EVIDENCE_NOT_PROVIDED": "증거 미제출",
    "EVIDENCE_REFERENCE_MISSING": "증거 표시 누락",
    "HASH_FORMAT_INVALID": "해시값 형식 오류",
    "HASH_MISMATCH": "해시값 불일치",
    "EVIDENCE_DATE_INVALID": "증거 날짜 오류",
    "EVIDENCE_TIMELINE_INVERSION": "증거 날짜 선후 뒤바뀜",
    "EVIDENCE_NUMBERING_GAP": "증거 번호 누락",
    "EVIDENCE_LIST_MISMATCH": "증거 목록 불일치",
    "EVIDENCE_PERSON_INCONSISTENT": "증거 인물 불일치",
    "EVIDENCE_FORM_DEFECT": "증거 형식 흠결",
    "EVIDENCE_PURPOSE_MISMATCH": "입증 취지 불일치",
    "STATEMENT_BEYOND_PERCEPTION": "지각 범위 밖 진술",
    "CROSS_DOC_COPY": "다른 문서 복사",
    "MODEL_FACT_REMARK": "모델 사실관계 의견",
    "SOURCE_CONFLICT_IGNORED": "상충 자료 누락",
    "CALCULATION_INVARIANT_VIOLATION": "계산 조건 위반",
    "LEGAL_REQUIREMENT_OMITTED": "법률 요건 누락",
    "OVERCLAIM": "과장된 주장",
    "UNSUPPORTED_GENERALIZATION": "근거 없는 일반화",
    "REASONING_GAP": "논리 비약",
    "AUTHORITY_RANK_ERROR": "법원(法源) 위계 오류",
    "DRAFT_ARTIFACT": "초안 흔적",
    "UNCERTAINTY_NOT_DISCLOSED": "불확실성 미고지",
    "UNSUPPORTED_FORMAT": "지원하지 않는 형식",
    "PARSE_ERROR": "읽기 오류",
}

# 의도·분류·신호·행 상태·참고문헌 처리 코드. 엔진이 실제로 내는 값만 둔다.
CODE_WORDS: Dict[str, str] = {
    "INSTRUCTION_OVERRIDE": "지시 무시",
    "ROLE_OVERRIDE": "역할 바꾸기",
    "OUTPUT_MANIPULATION": "결과 조작",
    "SYSTEM_SECRET_EXTRACTION": "시스템 정보 빼내기",
    "TOOL_MANIPULATION": "도구 조작",
    "PERSISTENT_INSTRUCTION": "지속 지시",
    "DATA_EXFILTRATION": "정보 유출",
    "UNSPECIFIED": "유형 미상",
    "RETROACTIVE_APPLICATION_ERROR": "소급 적용 오류",
    "INSTRUCTION_LIKE": "지시형 문구",
    "PROMPT_INJECTION_LIKELY": "인젝션 의심",
    "AI_PARTIAL_GENERATION": "일부 AI 작성",
    "AI_FULL_GENERATION_LIKELY": "전체 AI 작성 의심",
    "HUMAN_AUTHORED_LIKELY": "사람 작성 가능성",
    "ZERO_WIDTH": "폭 0 문자",
    "BIDI_CONTROL": "글자 방향 제어 문자",
    "HOMOGLYPH": "닮은꼴 문자",
    "TAG_CHARACTERS": "태그 문자",
    "SEPARATED_INSTRUCTION": "쪼갠 지시문",
    "INDEXED": "색인 완료",
    "INDEXED_PARTIAL": "일부 색인",
    "PARSE_FAILED": "읽기 실패",
    "QUARANTINED": "보안 격리",
    "NOT_SELECTED_METADATA": "후보 제외(폴더·파일명 기준)",
    "DUPLICATE_REUSED": "같은 내용 사본(기존 색인 사용)",
    "NOT_A_CASE_TABLE": "판례표 아님",
    "SELECTED_PENDING": "선정·처리 대기",
    "UNSUPPORTED_TYPE": "지원하지 않는 형식",
    "UNAVAILABLE": "조회 불가",
    "TEXT_INDEXED": "본문 색인",
    "REFERENCE_PARTIALLY_READ": "일부 쪽만 읽음",
    "REFERENCE_INSTRUCTION_PAGES_EXCLUDED": "지시문 의심 쪽 제외",
    "REFERENCE_QUARANTINED": "지시문 의심으로 보안 격리",
    "ENCRYPTED_REFERENCE": "암호화된 파일",
    "REFERENCE_PARSE_FAILED": "본문 추출 실패",
    "REFERENCE_PARSE_TIMEOUT": "본문 추출 시간 초과",
    "REFERENCE_TEXT_LIMIT": "분량 한도 초과",
    "REFERENCE_CASE_TABLE_PARTIAL": "판례표 일부만 읽음",
    "REFERENCE_EMPTY": "본문 없음",
    "REFERENCE_PROCESSING_FAILED": "처리 중 오류",
    "REFERENCE_TRASHED": "휴지통에 있음",
    "REFERENCE_MOVED": "등록 폴더 밖으로 이동됨",
    "REFERENCE_DOWNLOAD_BLOCKED": "내려받기 금지 파일",
    "REFERENCE_CHANGED_DURING_DOWNLOAD": "내려받는 중 파일 변경",
    "REFERENCE_CHECKSUM_MISMATCH": "파일 검증값 불일치",
    "UNSUPPORTED_REFERENCE_FORMAT": "지원하지 않는 형식",
    "UNSUPPORTED_OR_UNSAFE_REFERENCE": "지원하지 않거나 안전하지 않은 파일",
    "NAME_PATH_NOT_RELATED": "폴더·파일명이 서면과 관련 없음",
    "NAME_PATH_MATCH": "폴더·파일명 일치",
    "DRIVE_FULLTEXT_MATCH": "Drive 본문 검색 일치",
    "TITLE_WORD_MATCH": "우선 자료 제목 일치",
    "CANDIDATE_LIMIT": "후보 수 한도 초과",
    "NOT_SELECTED": "후보 아님",
    "NOT_PROCESSED": "미처리",
    "SYNC_INTERRUPTED": "동기화 중단",
    "FILES_DEFERRED": "다음 동기화로 미룸",
    "DOWNLOAD_BUDGET_EXHAUSTED": "내려받기 용량 한도 도달",
    "INDEX_FILE_BUDGET_EXHAUSTED": "색인 파일 수 한도 도달",
    "SYNC_BUDGET_EXHAUSTED": "동기화 한도 도달",
    "DOWNLOAD_NOT_ALLOWED": "내려받기 불가",
    "DOWNLOAD_FAILED": "내려받기 실패",
    "EXTRACT_FAILED": "추출 실패",
    "EXTRACT_TIMEOUT": "추출 시간 초과",
    "PARSE_TIMEOUT": "읽기 시간 초과",
    "FILE_SIZE_LIMIT": "파일 크기 한도 초과",
    "FILE_COUNT_LIMIT": "파일 수 한도 초과",
    "FOLDER_LIMIT": "폴더 깊이·개수 한도 초과",
    "INCOMPLETE_LISTING": "목록 조회 불완전",
    "ROOT_FOLDER_UNAVAILABLE": "등록 폴더 접근 불가",
    "MISSING_REVISION": "파일 판 정보 없음",
    "INVALID_DRIVE_ID": "잘못된 Drive 식별자",
    "INVALID_TOKEN_ENDPOINT": "인증 설정 오류",
    "DRIVE_AUTH_FAILED": "Drive 인증 실패",
    "DRIVE_CREDENTIALS_MISSING": "Drive 인증 정보 없음",
    "DRIVE_FULLTEXT_FORBIDDEN": "Drive 본문 검색 권한 없음",
    "DRIVE_HTTP_401": "Drive 인증 거부(401)",
    "DRIVE_HTTP_403": "Drive 접근 거부(403)",
    "DRIVE_HTTP_429": "Drive 요청 한도 초과(429)",
    "DRIVE_NETWORK_ERROR": "Drive 연결 오류",
    "CONNECT_FAILED": "연결 실패",
    "READ_TIMEOUT": "응답 시간 초과",
    "STREAM_INTERRUPTED": "전송 중단",
    "REPEATED_PAGE_TOKEN": "목록 조회 반복 오류",
    "NETWORK_DISABLED": "네트워크 사용 안 함",
    "CACHE_BUSY": "색인 저장소 사용 중",
    "SYNC_FAILED": "동기화 실패",
    "RELEVANT_REFERENCE_FOUND": "관련 자료 있음",
    "NO_CANDIDATE_CHUNK": "관련 발췌 후보 없음",
    "BELOW_RELEVANCE_THRESHOLD": "관련도 기준 미달",
    "NO_SHARED_KEY_TERMS": "공통 핵심어 없음",
    "NO_ELIGIBLE_REFERENCE": "읽을 수 있는 자료 없음",
    "NO_RELEVANT_DRIVE_REFERENCE": "관련 Drive 자료 없음",
    "RELEVANT_REFERENCES_NOT_FULLY_READ": "참고자료 분량 초과로 일부 문서 미대조",
    "NO_READABLE_DRIVE_REFERENCE": "판독 가능한 Drive 참고자료 문서 없음",
    "REFERENCE_LIBRARY_UNAVAILABLE": "참고자료 라이브러리 색인 준비 미완료",
    "MODEL_NOT_AVAILABLE_OR_QUICK_PROFILE": "빠른 검토 프로필 설정 또는 모델 가용성 부족",
    "DOCUMENT_UNREADABLE": "서면 문서 텍스트 정규화 실패로 판독 불가",
    "NO_TEXT_AFTER_REMOVING_INSTRUCTIONS": "지시문 제거 후 분석 대상 본문 텍스트 부족",
    "EXACT_QUOTES_CHECKED_NOT_ENTAILMENT_OR_LEGAL_VALIDITY": "원문 발췌 일치만 확인(내용 함의·법적 타당성 판단 아님)",
    "MODEL_RETURNED_NO_ADVICE_NOT_LEGAL_CLEARANCE": "모델 추가 의견 없음(적법성 확인 아님)",
    "NO_GROUNDED_MODEL_ADVICE": "근거가 확인된 모델 의견 없음",
    "MODEL_RESPONSE_REJECTED": "모델 응답 형식 불합격",
    "MODEL_UNAVAILABLE": "모델 응답 없음",
    "NOT_EXECUTED": "미실행",
    "SEARCH_LIMIT": "검색 한도 초과",
    "SEARCH_COMPLETED": "검색 완료",
    "SECURITY_QUARANTINE": "보안 격리",
    "HIDDEN_SHEET": "숨긴 시트",
    "HIDDEN_ROW": "숨긴 행",
    "WHITE_ON_WHITE": "흰 바탕 흰 글자",
    "NOT_ASSESSED": "평가 안 함",
    "NOT_CHECKED": "대조 안 함",
    "NOT_MENTIONED": "참고자료 언급 없음",
    "PENDING_REVIEW": "참고자료 지지 미확정",
    "OFFICIAL_NOT_FOUND": "공식 DB 미확인",
    "OFFICIAL_CONFIRMED": "공식 원문 확인",
    "UNVERIFIED_SCOPE": "미확인 범위",
    "NOT_IN_REFERENCE": "표준판례 목록에 없음",
    "IN_REFERENCE": "표준판례 목록에 있음",
    "PARTIALLY_VERIFIED": "일부 확인",
    "NOT_FOUND": "출처에서 미확인",
    "PARTIAL_COMPLETED": "일부 미확인",
    "NOT_FOUND_IN_SEARCHED_SCOPE": "조회 범위에서 미발견",
    "ADVISORY_REVIEWED": "근거 인용 대조 · AI 참고 의견",
    "REVIEWED_NO_ADVICE": "AI 대조 응답 완료 · 추가 의견 없음(적법성 확인 아님)",
    "RETRIEVED_ONLY": "검색 완료 · AI 대조 미실행",
    "INCOMPLETE_COVERAGE": "관련 자료 검토 범위 미완결",
    "NOT_RELEVANT": "관련 자료 없음 · Drive 자료 미활용",
    "SOURCE_REVIEW_ONLY": "출처 검토만(직접 인용과 별도)",
    "MISSING_KEY": "연결 키 미설정",
}

# 엔진 문장 속 소문자 식별자(검사 층·필드·출처 이름).
FIELD_WORDS: Dict[str, str] = {
    "visible_text": "본문",
    "encoded_text": "인코딩된 문자열",
    "hidden_text": "숨김 글자",
    "ocr_layer": "OCR 인식 글자",
    "form_field": "입력란",
    "image_alt": "이미지 설명",
    "ai_score": "점수",
    "finding.confidence": "값",
    "reference_date": "기준일",
    "law_go_kr": "국가법령정보센터",
    "reference_library": "참고자료 라이브러리",
    "source_run_id": "원본 실행 번호",
}

# 보고서 칸에 단어 하나로 들어가는 값(밑줄이 없어 readable이 건드리지 않는 것). 화면 labels와 같은 말.
WORD_NAMES: Dict[str, str] = {
    "CRITICAL": "매우 높음", "HIGH": "높음", "MEDIUM": "보통", "LOW": "낮음", "INFO": "참고",
    "UNCERTAIN": "판단 유보", "VERIFIED": "확인됨", "UNVERIFIED": "확인 불가", "CONTRADICTED": "불일치",
    "SUSPICIOUS": "확인 필요", "SKIPPED": "미실행", "ERROR": "처리 오류", "COMPLETED": "검증 완료", "FAILED": "실행 실패",
    "STATUTE": "법령", "CASE": "판례", "ACADEMIC": "학술 문헌",
    # 참고문헌 라이브러리·검토 상태(화면 statuses와 같은 말)와 참고 의견 관계
    "READY": "동기화 완료", "PARTIAL": "부분 처리·제한 있음",
    # 참고 의견 관계는 화면 REFERENCE_RELATIONS와 같은 말
    "SUPPORTS": "부합", "CONTRADICTS": "불부합", "CONTEXT": "맥락 참고", "INSUFFICIENT": "근거 부족", "MATCH": "일치",
    "True": "예", "False": "아니오", "None": "기록 없음",
}


def word(value) -> str:
    """단어 하나짜리 코드 값(심각도·상태·판정·인용 종류)을 한글로. 모르면 readable 규칙을 따른다."""
    text = str(value if value is not None else "")
    return WORD_NAMES.get(text) or CODE_WORDS.get(text) or readable(text)


def korean_time(value) -> str:
    """ISO 시각을 한국 시각 'YYYY-MM-DD HH:MM'으로. 읽을 수 없으면 원래 값(없으면 '기록 없음')."""
    from datetime import datetime, timedelta, timezone

    if not value:
        return "기록 없음"
    try:
        moment = value if isinstance(value, datetime) else datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return str(value)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone(timedelta(hours=9))).strftime("%Y-%m-%d %H:%M")


# 화면 friendlyText와 같은 문장 단위 치환(순서 그대로).
_PHRASES = (("UNVERIFIED", "확인하지 못함"), ("Source", "출처"), ("Creator", "작성 프로그램"), ("Producer", "PDF 생성 프로그램"),
            ("Author", "작성자"), ("QUARANTINED", "안전 검토 필요"), ("UNCERTAIN", "판단 유보"),
            ("Python 계산엔진으로 검산한 결정론적 결과이다.", "계산식에 따라 자동 검산한 결과입니다."))

_PAREN_CODE = re.compile(r"\s*\(([A-Z][A-Z0-9]*_[A-Z0-9_]+)\)")
_CODE = re.compile(r"\b[A-Z][A-Z0-9]*_[A-Z0-9_]+\b")
_FIELD = re.compile(r"\bfinding\.confidence\b|\b[a-z]+_[a-z_]+\b")


def readable(text) -> str:
    """사람이 읽는 문장에서 코드를 한글로 바꾼다. 화면 app.js friendlyText와 같은 규칙이다.

    - '[RAG참고자료] ' 접두와 괄호 속 코드 '(XXX_YYY)'는 지운다(같은 뜻의 한글이 이미 앞에 있다).
    - 표에 있는 코드·식별자만 바꾸고, 모르는 것(개인정보 가림 토큰 [PERSON_003], 파일명 등)은 그대로 둔다.
    """
    value = str(text if text is not None else "")
    value = value.replace("Creator와 Producer가", "작성 프로그램과 PDF 생성 프로그램이").replace("UNVERIFIED로", "미확인 상태로")
    value = value.replace("[RAG참고자료] ", "").replace("[RAG참고자료]", "")
    value = _PAREN_CODE.sub("", value)
    value = _CODE.sub(lambda m: FINDING_TYPE_NAMES.get(m.group(0)) or CODE_WORDS.get(m.group(0)) or m.group(0), value)
    value = _FIELD.sub(lambda m: FIELD_WORDS.get(m.group(0), m.group(0)), value)
    for technical, simple in _PHRASES:
        # 영문 낱말은 다른 코드의 일부(예: REFERENCE_QUARANTINED)를 바꾸지 않도록 경계에서만 바꾼다.
        if technical.isascii() and technical.isalpha():
            value = re.sub(rf"(?<![A-Za-z0-9_]){technical}(?![A-Za-z0-9_])", simple, value)
        else:
            value = value.replace(technical, simple)
    return value


assert set(FINDING_TYPE_NAMES) == set(FindingType.__members__), "FindingType 전부에 한글 이름이 있어야 한다"
