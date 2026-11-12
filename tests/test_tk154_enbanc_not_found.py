"""TK-154: 조회 범위에서 찾지 못한 대법원 전원합의체 판결은 '부존재 의심'(HIGH), 그 밖은 LV-03 '확인 불가'(MEDIUM).

사건번호·날짜는 합성이다(실제 판결·서면의 값이 아니다).
"""
import pytest

from packages.common.enums import AdapterStatus, CitationType, FindingType, Severity, VerificationStatus
from packages.common.schemas import Citation
from packages.legal_engine.authority_status import ENBANC_PUBLICATION_LAG_DAYS, enbanc_absence_suspected
from packages.legal_engine.verifier import LegalVerifier
from packages.source_adapters import SourceRegistry
from packages.source_adapters.base import AdapterResponse

CURRENT = "2026-11-12"


class _Law:
    def __init__(self, status=AdapterStatus.READY):
        self.status = status

    def search_case(self, *args, **kw):
        return AdapterResponse(self.status, [], None, "synthetic")


def _verify(citation, status=AdapterStatus.READY, current=CURRENT):
    registry = SourceRegistry()
    registry.legal[0] = _Law(status)
    return LegalVerifier(registry).verify_case(citation, current_date=current)


def _citation(raw, number="2019다12345", court="대법원", kind="전원합의체 판결", decided="2020-03-02"):
    return Citation(citation_id="c", type=CitationType.CASE, raw_text=raw, court=court, case_number=number,
                    canonical_case_number=number, case_kind=kind, decision_date=decided, page=1)


def _not_found(verdict):
    [f] = [f for f in verdict.findings if f.type == FindingType.CASE_NOT_FOUND]
    return f


def test_old_enbanc_judgment_not_found_is_high_suspicion_not_critical():
    v = _verify(_citation("대법원 2020. 3. 2. 선고 2019다12345 전원합의체 판결"))
    f = _not_found(v)
    assert f.severity == Severity.HIGH and f.status == VerificationStatus.NOT_FOUND
    assert "ENBANC_NOT_FOUND" in f.tags and "SOURCE_LIMIT" not in f.tags and "FAKE_PRECEDENT" not in f.tags
    assert f.confidence_features["suspicion_basis"] == "ENBANC_PUBLICATION_EXPECTED"
    assert v.levels["authority_status"] == "SUSPICIOUS"
    assert "확정하지 않" in f.detail


@pytest.mark.parametrize("citation", [
    _citation("대법원 2020. 3. 2. 선고 2019다12345 판결", kind="판결"),                     # 전원합의체 표기 없음
    _citation("대법원 2026. 10. 2. 선고 2019다12345 전원합의체 판결", decided="2026-10-02"),  # 공개 지연 기간 안
    _citation("대법원 2019다12345 전원합의체 판결", decided=None),                           # 선고일 없음
    _citation("서울고등법원 2020. 3. 2. 선고 2019나12345 전원합의체 판결", number="2019나12345",
              court="서울고등법원"),                                                         # 하급심
])
def test_other_not_found_cases_keep_lv03_source_limit_medium(citation):
    f = _not_found(_verify(citation))
    assert f.severity == Severity.MEDIUM and "SOURCE_LIMIT" in f.tags


def test_lookup_failure_is_not_a_not_found_verdict():
    v = _verify(_citation("대법원 2020. 3. 2. 선고 2019다12345 전원합의체 판결"), status=AdapterStatus.ERROR)
    # 조회 실패는 '미확인'이다(기존 동작). 부존재 의심으로 올리지 않는다.
    assert all(f.status == VerificationStatus.UNVERIFIED for f in v.findings)
    assert not [f for f in v.findings if f.severity in (Severity.HIGH, Severity.CRITICAL) or "ENBANC_NOT_FOUND" in f.tags]


def test_lag_boundary():
    c = _citation("대법원 전원합의체 판결", decided="2026-05-16")
    assert ENBANC_PUBLICATION_LAG_DAYS == 180
    assert enbanc_absence_suspected(c, "2026-11-12") is True
    assert enbanc_absence_suspected(c, "2026-11-11") is False
