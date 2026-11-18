"""`LV_RAG_HYBRID_SEMANTIC` 롤백 토글 시험.

#325는 `rag_decoupled_collection`·`rag_claim_multisearch`의 OFF 경로는 시험했으나
`rag_hybrid_semantic`은 기본 ON인데 OFF 경로 시험이 없었다. 이 플래그는 `select()`·
`search_claim()`의 어간·n-gram 의미 점수(`local_semantic_score`)를 켜고 끄며, OFF일 때
0.22.0처럼 파일명·낱말 적용 비율만으로 판정해야 한다.

모든 자료·파일명·문장은 합성 값이다(평가 세트·사건 자료에서 가져오지 않았다).
"""
from __future__ import annotations

import hashlib
from dataclasses import replace

from packages.common.config import get_settings, reset_settings
from packages.rag_engine import relevance
from packages.rag_engine.library import ReferenceLibrary


ROOT = "synthetic_folder_hybrid_rollback"

# 파일명은 질의와 겹치지 않게 두어 name_coverage 기여를 없앤다(파일명 가점 없이 본문만으로 판정).
_REF_NAME = "opaque_asset_7731.txt"

# 쟁점이 여러 개인 질의. 참고자료는 그 가운데 한 쟁점만 풀어 써서 질의 전체 낱말 가중치의
# 일부만 갖는다. 그래서 적용 비율(text_coverage)은 0.14~0.20 구간에 들어가고 file_score는
# MIN_FILE_SCORE(0.25)에 못 미치지만, 의미 점수가 0.22를 넘어 body_strong으로 구제된다.
# 이 구간이 바로 하이브리드 플래그가 선택 여부를 가르는 지점이다.
_QUERY = " ".join([
    "임대차보증금 반환과 목적물 인도의 동시이행 관계를 다툰다.",
    "유치권 성립에는 점유와 견련성이 필요하다고 주장한다.",
    "전세권 설정등기와 배당요구 종기의 효력을 다툰다.",
    "하도급 대금 직접지급 요건과 통지 시기를 다툰다.",
    "공동수급체 구성원의 연대책임 범위를 다툰다.",
    "선금 반환 보증의 법적 성격과 범위를 다툰다.",
    "손해배상 예정액 감액 사유와 기준을 다툰다.",
    "소유권이전등기 말소청구의 상대방 적격을 다툰다.",
])
_REF_BODY = "임대차보증금 반환과 목적물 인도는 동시이행 관계이며 공제 범위는 연체차임에 한한다."


class _OneFileDrive:
    """목록·내려받기만 하는 최소 Drive 스텁(본문 검색은 쓰지 않는다)."""

    def __init__(self, name: str, data: bytes):
        self.name = name
        self.data = data

    def _meta(self):
        return {
            "id": "ref_hybrid_01",
            "name": self.name,
            "mimeType": "text/plain",
            "version": "1",
            "createdTime": "2026-07-01T00:00:00Z",
            "modifiedTime": "2026-10-15T00:00:00Z",
            "parents": [ROOT],
            "trashed": False,
            "size": str(len(self.data)),
            "capabilities": {"canDownload": True},
            "md5Checksum": hashlib.md5(self.data).hexdigest(),
            "folder_path": "일반자료",
        }

    def __call__(self, **kwargs):
        return self

    def remaining(self):
        return 120

    def inventory(self, *args, **kwargs):
        return [self._meta()]

    def metadata(self, file_id):
        meta = self._meta()
        meta.pop("folder_path", None)
        return meta

    def search_fulltext(self, *args, **kwargs):
        return []

    def download(self, item, **kwargs):
        return self.data, self.name, "text/plain"

    def close(self):
        pass


def _library(tmp_path):
    settings = replace(get_settings(), storage_root=tmp_path / "cache",
                       rag_drive_folder_id=ROOT, allow_network=True)
    drive = _OneFileDrive(_REF_NAME, _REF_BODY.encode())
    lib = ReferenceLibrary(
        settings, client_factory=drive,
        extractor=lambda d, *_, **kw: {
            "sha256": hashlib.sha256(d).hexdigest(), "pages": 1, "read_pages": 1,
            "extracted_text_pages": 1, "completed_pages": 1, "partial": False,
            "chunks": [{"page": 1, "start": 0, "text": d.decode()}],
        })
    lib.sync(collect_all=True)
    return lib


def _candidates(selection):
    return selection.get("candidates") or []


def test_hybrid_semantic_on_scores_candidates_and_records_the_toggle(tmp_path):
    """기본 ON: 의미 점수가 실제로 계산된다."""
    reset_settings()
    lib = _library(tmp_path)
    selection = lib.select(_QUERY)

    cands = _candidates(selection)
    assert cands, "본문 어간이 겹치는 자료가 후보에 들지 않았다"
    assert any(c["semantic_score"] > 0 for c in cands), "하이브리드 ON인데 의미 점수가 모두 0이다"


def test_hybrid_semantic_off_zeroes_semantic_score_and_keeps_term_scores(tmp_path, monkeypatch):
    """OFF: 의미 점수는 0이 되고, 낱말·파일명 기반 점수는 그대로 남는다."""
    monkeypatch.setenv("LV_RAG_HYBRID_SEMANTIC", "0")
    reset_settings()
    try:
        lib = _library(tmp_path)
        assert lib.settings.rag_hybrid_semantic is False
        selection = lib.select(_QUERY)
        cands = _candidates(selection)
        assert cands, "OFF에서도 낱말 적용 비율로 후보 자체는 평가돼야 한다"
        assert all(c["semantic_score"] == 0.0 for c in cands), "OFF인데 의미 점수가 계산됐다"
        # 낱말·파일명 축은 플래그와 무관하게 남는다(점수 산식 전체가 꺼지는 것이 아니다).
        assert all("text_coverage" in c and "name_coverage" in c for c in cands)
    finally:
        monkeypatch.delenv("LV_RAG_HYBRID_SEMANTIC", raising=False)
        reset_settings()


def test_hybrid_semantic_toggle_changes_only_the_semantic_axis(tmp_path, monkeypatch):
    """같은 자료·같은 질의에서 ON/OFF가 의미 축만 바꾸고 낱말 축은 건드리지 않는다."""
    reset_settings()
    on_cands = {c["file_id"]: c for c in _candidates(_library(tmp_path / "on").select(_QUERY))}

    monkeypatch.setenv("LV_RAG_HYBRID_SEMANTIC", "0")
    reset_settings()
    try:
        off_cands = {c["file_id"]: c for c in _candidates(_library(tmp_path / "off").select(_QUERY))}
    finally:
        monkeypatch.delenv("LV_RAG_HYBRID_SEMANTIC", raising=False)
        reset_settings()

    assert set(on_cands) == set(off_cands), "플래그가 후보 집합 자체를 바꿨다"
    for file_id, on_c in on_cands.items():
        off_c = off_cands[file_id]
        assert on_c["text_coverage"] == off_c["text_coverage"]
        assert on_c["shared_terms"] == off_c["shared_terms"]
        assert on_c["name_coverage"] == off_c["name_coverage"]
        assert off_c["semantic_score"] == 0.0
        assert on_c["semantic_score"] >= off_c["semantic_score"]


def test_hybrid_semantic_off_disables_the_body_strong_semantic_rescue(tmp_path, monkeypatch):
    """의미 점수로만 살아나는 자료(파일명 무관·적용 비율 낮음)는 OFF에서 되살아나지 않는다.

    `library.select`의 `body_strong`은 `text_coverage >= 0.20` 또는 `semantic_score >= 0.22`로
    낮은 file_score를 구제한다. OFF에서는 의미 축이 0이므로 이 구제 경로가 닫힌다.
    """
    reset_settings()
    lib = _library(tmp_path)
    cands = _candidates(lib.select(_QUERY))
    rescued = [c for c in cands
               if c["file_score"] < relevance.MIN_FILE_SCORE
               and c["text_coverage"] < 0.20
               and c["semantic_score"] >= 0.22]
    # fixture가 구제 구간을 벗어나면 이 시험은 아무것도 재지 못한다. 그때는 통과가 아니라 실패여야 한다.
    assert rescued, (
        "fixture가 body_strong 구제 구간을 벗어났다(의미 점수로만 선택되는 후보 0건). "
        f"후보: {[{k: c[k] for k in ('text_coverage', 'semantic_score', 'file_score', 'selected')} for c in cands]}")
    assert all(c["selected"] for c in rescued), "구제 구간 후보가 ON에서 선택되지 않았다"

    monkeypatch.setenv("LV_RAG_HYBRID_SEMANTIC", "0")
    reset_settings()
    try:
        off_by_id = {c["file_id"]: c for c in _candidates(_library(tmp_path / "off2").select(_QUERY))}
        for candidate in rescued:
            off_c = off_by_id[candidate["file_id"]]
            assert off_c["semantic_score"] == 0.0
            assert "LOW_FILE_SCORE" in off_c["rejected_because"], (
                "의미 점수로만 구제됐던 자료가 OFF에서도 선택됐다")
    finally:
        monkeypatch.delenv("LV_RAG_HYBRID_SEMANTIC", raising=False)
        reset_settings()
