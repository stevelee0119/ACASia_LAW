# 운영 온라인 점검용 재사용 자료

이 폴더는 **공개 가능한 합성 입력만** 보관한다. 동일 자료를 다음 배포에서 다시 사용하려면 버전 디렉터리의 파일과 `manifest.json` SHA-256을 먼저 대조한다. 수정은 기존 파일을 덮어쓰지 않고 `v2/`처럼 새 판으로 추가한다. 결과 보고서에는 입력 판, SHA, 배포 SHA, 모델·정책·Drive 상태를 함께 적는다. 조건이 다르면 단순 점수 증감으로 비교하지 않는다.

| 자료 | 위치 | 용도 |
|---|---|---|
| 서면9 표준 23항목 | `tests/fixtures/case9_state_compensation_google_docs.pdf` 및 `tests/fixtures/probes/case9_state_compensation_online.json` | 기존 공개 개발 자료와 채점 규칙 2판. 이 폴더에 복제하지 않는다 |
| 35,674자 합성 DOCX | `v1/synthetic_35674.docx` | TK-199 입력 용량·외부 AI 차단 경로. **사용자 원본의 내용·구조를 대표하지 않는다** |
| 계산·사실/법리 날짜 합성 DOCX | `v1/synthetic_features.docx` | TK-205 검토 표, TK-206 Time Table, 외부 AI 답변 영속 시험 |
| 수량·일시 모순과 정상 물류 단계 합성 DOCX | `v1/synthetic_inconsistency.docx` | TK-76 EVI-INCONS 양성·대조 |
| RAG 지지·무관 합성 자료 | `tests/fixtures/rag_controls/`, `tests/fixtures/online/tk180/` | 기존 공개 자료. 운영 Drive 연결 여부와 색인 리비전은 실행별로 확인 |

## 매번 실행할 때

1. 배포 `/api/health`의 전체 commit과 DB 상태를 확인한다. 불일치하면 새 실행을 시작하지 않는다.
2. `v1/manifest.json`의 SHA-256을 실제 파일과 대조한다. 사용자 원본이 필요한 시험은 평가자가 승인한 **비공개 영속 보관소**의 원본과 해시를 대조해 사용한다. 원본이 없으면 해당 원본 시험은 `측정 불가`로 두고 합성 대조 결과를 따로 쓴다. 사용자가 같은 파일을 매번 채팅에 다시 올릴 필요는 없다.
3. 새 평가 전용 프로젝트에 파일을 올리고 생성 응답의 프로젝트·문서·실행 ID를 저장소 밖의 접근 제한된 실행 장부에 적는다. Drive 기준 자료는 역할·파일 해시·색인 상태를 장부에 적고, 파일/폴더 ID는 저장소에 올리지 않는다.
4. 항목별 실측과 실행 건강을 분리한다. 원본 JSON·화면 캡처·입력/명세 해시를 비공개로 보존한 뒤, 공개 가능한 집계·가린 캡처만 `docs/handoff/online/<버전>_<날짜>/`에 추가해 PR로 전달한다.
5. 보존본의 SHA-256과 재열기를 검증한 뒤 **이번 실행에서 만든 프로젝트만** 휴지통으로 이동하고 삭제 목록의 `deleted_at`을 확인한다. 기존 프로젝트·공용 Drive 자료는 삭제하지 않는다. 상세 절차와 장부 열은 `docs/scorecards/online_compare_0220_0230_plan.md` 5절 및 `docs/scorecards/online_project_cleanup_record.csv`를 따른다.

실제 사건 서면·개인정보·인증정보·Drive 식별자·봉인 자료는 이 폴더나 PR에 넣지 않는다. 비공개 보관소가 마련되지 않은 원본의 운영 효과는 미측정으로 기록한다.

해시 대조는 저장소 루트에서 다음처럼 한다(경로/불일치만 출력):

```bash
python - <<'PY'
import hashlib, json, pathlib
root = pathlib.Path.cwd()
manifest = json.loads((root / 'docs/handoff/online/materials/v1/manifest.json').read_text())
for item in manifest['materials']:
    path = root / 'docs/handoff/online/materials/v1' / item['name']
    assert hashlib.sha256(path.read_bytes()).hexdigest() == item['sha256'], path
for item in manifest['repository_references']:
    path = root / item['path']
    assert hashlib.sha256(path.read_bytes()).hexdigest() == item['sha256'], path
print('online materials: hashes match')
PY
```
