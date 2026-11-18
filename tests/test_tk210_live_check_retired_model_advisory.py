"""TK-210 실연동 점검에서 은퇴·미지원 모델의 실패를 호환성 알림으로 분리한다.

평가 측 점검 도구 결함(PR #340 I-5). `scripts/live_source_check.py`가 Gemini `/models` 목록에서
후보 모델을 자동으로 고르는데, 목록에는 남아 있으나 신규 호출이 막힌 구형 모델이 섞여 들어오고
그 404가 strict 판정을 실패로 만들었다. 0.21.0·0.23.0 배포 기록에 같은 두 모델이 같은 사유로
남아 있다.

운영 기본 모델의 실패는 알림으로 내리지 않는다. 쿼터·권한·요청 오류도 그대로 실패로 둔다.
문구는 낱말 하나가 아니라 축으로 받는다(공급자가 표현을 바꿔도 같은 뜻이면 걸리게 한다).
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _module():
    spec = importlib.util.spec_from_file_location(
        "live_source_check_under_test", ROOT / "scripts" / "live_source_check.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


lsc = _module()


# 공급자가 '이 모델은 더 못 쓴다'고 답한 꼴 — 호환성 알림
_RETIRED = [
    (404, "This model models/gemini-2.5-flash is no longer available to new users. "
          "Please update your code to use models/gemini-3.8-flash"),
    (404, "This model models/gemini-2.5-flash-lite is no longer available to new users."),
    (404, "models/example is not available to new users"),
    (400, "Model is deprecated and will be removed"),
    (404, "This model has been retired"),
    (404, "models/example is not supported for generateContent"),
    (410, "unsupported model"),
    (404, "models/example is not found for API version v1beta"),
]

# 운영 상태를 뜻하는 실패 — 알림으로 내리지 않는다
_REAL_FAILURE = [
    (429, "Quota exceeded for quota metric 'Generate requests'"),
    (403, "Permission denied: API key not valid"),
    (401, "Unauthorized"),
    (400, "Invalid JSON payload received"),
    (500, "Internal error. no longer available"),  # 5xx는 은퇴로 보지 않는다
    (503, "The service is currently unavailable"),
    (404, ""),  # 본문 없는 404는 경로 오류일 수 있다
]


@pytest.mark.parametrize("status_code,detail", _RETIRED)
def test_retired_model_phrases_are_advisory(status_code, detail):
    assert lsc._is_retired_model(status_code, detail) is True


@pytest.mark.parametrize("status_code,detail", _REAL_FAILURE)
def test_real_failures_stay_failures(status_code, detail):
    assert lsc._is_retired_model(status_code, detail) is False


def _result(name, *, status, ok, requires_key=True, advisory=False, category="gemini_models"):
    return lsc.CheckResult(name=name, category=category, configured=True,
                           status=status, ok=ok, requires_key=requires_key, advisory=advisory)


def test_partition_separates_three_buckets():
    groups = {
        "gemini_models": [
            _result("gemini:기본 (현재 설정)", status="HTTP 429", ok=False),
            _result("gemini:구형-후보", status="HTTP 404", ok=False, advisory=True),
            _result("gemini:정상-후보", status="OK", ok=True),
        ],
        "live_academic": [
            _result("공개 Source", status="RATE_LIMITED", ok=False,
                    requires_key=False, category="live_academic"),
        ],
    }
    fatal, warnings, advisories = lsc.partition_failures(groups)
    assert [item.name for item in fatal] == ["gemini:기본 (현재 설정)"]
    assert [item.name for item in warnings] == ["공개 Source"]
    assert [item.name for item in advisories] == ["gemini:구형-후보"]


def test_advisory_alone_does_not_fail_strict():
    groups = {"gemini_models": [_result("gemini:구형-후보", status="HTTP 404",
                                        ok=False, advisory=True)]}
    fatal, warnings, advisories = lsc.partition_failures(groups)
    assert fatal == [] and warnings == []
    assert len(advisories) == 1


def test_advisory_is_reported_in_markdown():
    # render_markdown은 secret·adapter_status를 직접 찾는다(기존 동작).
    groups = {
        "secret": [],
        "adapter_status": [],
        "gemini_models": [_result("gemini:구형-후보", status="HTTP 404",
                                  ok=False, advisory=True)],
    }
    text = lsc.render_markdown(groups)
    assert "호환성 알림" in text
    assert "gemini:구형-후보" in text



def test_default_is_not_advisory():
    assert _result("x", status="HTTP 404", ok=False).advisory is False
