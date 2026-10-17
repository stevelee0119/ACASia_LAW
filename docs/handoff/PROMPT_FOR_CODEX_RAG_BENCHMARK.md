# Codex Drive 대조 고정 세트 작성 프롬프트 (2026-10-17)

> **왜 만드나:** 고정 벤치 2판(`c078b250e6e61e9f`)에는 참고자료가 없어 Drive 대조를 잴 수 없다. 10/09 Drive 대조 세트(지문 `2dc61fb15bf67e83`)는 TK-70 개발에 쓰여 처음 보는 자료가 아니다. 그래서 서면과 참고자료를 함께 담은 새 고정 세트를 만든다. 채점은 `scripts/score_report.py`의 명세 형식(`rag_relationship`·`no_rag_relationship`, `scope: claim`)을 쓴다.
> **사용법(사용자):** **저장소를 연결하지 않은 Codex 새 세션**에서 '--- 프롬프트 시작 ---'부터 '--- 프롬프트 끝 ---'까지만 붙여 넣는다. 보관·점검 절차는 고정 벤치 2판과 같다. 해시 대조, 두 곳 이상 보관, 다른 새 세션의 독립 점검(같은 스크립트)을 마친 뒤 보관 확인을 알린다.
> **측정(평가 측):** 모든 묶음의 `drive_refs/` 파일을 측정 전용 Drive 폴더 하나에 올린다(묶음별 하위 폴더). 묶음마다 서면 전체를 한 프로젝트로 온라인 검증하고, 보고서를 묶음의 `spec.json`으로 채점한다. 다른 묶음의 참고자료는 자연스러운 방해 자료가 된다. 측정 기간에는 Drive 폴더를 고치지 않는다.

--- 프롬프트 시작 ---

# 과제: 법률 서면 검토 도구의 '참고자료 대조' 고정 시험 세트 작성

너는 출제자다. 한국 법률 서면을 검토하는 보조 도구가 있다. 이 도구는 사용자가 Google Drive 폴더에 둔 참고자료(내부 규정, 지침, 계약서, 회의록, 공문 등)를 찾아 읽는다. 그리고 서면의 주장이 참고자료와 맞는지, 어긋나는지 의견을 낸다. 이 기능을 채점할 **처음 보는 고정 시험 세트**를 만든다. 한 번 만들면 바꾸지 않고 도구의 새 판마다 같은 세트로 잰다.

## 0. 격리 조건 (가장 먼저 지킨다)
1. 이 세션에서는 어떤 저장소나 코드도 열거나 검색하지 않는다. GitHub 페이지도 열지 않는다. 제품 이름으로 웹 검색도 하지 않는다.
2. 이전에 만든 시험 세트(봉인 세트, 고정 벤치마크, 개발 말뭉치, 참고자료 대조 세트)의 파일·문장·사건 설정·서식 틀을 재사용하지 않는다. 모두 새로 만든다.
3. 산출물은 이 세션의 작업 폴더에만 만들고 사용자에게 넘긴다. git 커밋·PR·외부 업로드는 하지 않는다. Drive 업로드는 사용자가 한다.
4. 채점·도구 실행은 하지 않는다. 6절의 자체 점검만 실행한다.
5. 채팅 보고에는 건수와 오류·경고 수만 쓴다(7절 양식). 문장·정답·사건 설정을 쓰지 않는다.
6. 사용자가 7절 '보관 확인'을 마쳤다고 알리기 전에는 작업 폴더 사본을 지우지 않는다. 알리면 세트·생성 스크립트·점검 스크립트 사본을 모두 지우고 지웠다고 알린다.

## 1. 구성 기준
| 항목 | 기준 |
|---|---|
| 묶음 | 5개. 묶음 하나가 한 사건이고, 도구는 묶음의 서면 전체를 한 프로젝트로 검토한다. 묶음끼리 사건·기관·인물·번호를 공유하지 않는다 |
| 서면 | 묶음마다 2건(전체 10건). 소장·준비서면·답변서·의견서·진정서 등에서 고른다. 한 건은 2~4쪽 |
| 참고자료 | 묶음마다 2~3건(전체 10~15건). 그 사건의 내부 규정·운영 지침·계약서·약관·회의록·공문·업무 매뉴얼 등. 한 건은 1~4쪽 |
| 양성 항목 | 묶음마다 8개 이상(전체 40개 이상). 서면의 주장이 그 묶음 참고자료의 특정 조항·문장과 **분명히 어긋나는** 경우 |
| 대조 항목 | 묶음마다 8개 이상(전체 40개 이상). 서면의 주장이 참고자료와 **맞거나**, 참고자료가 **다루지 않는** 내용이라 어긋남이 없는 경우. 맞는 경우와 다루지 않는 경우를 둘 다 넣는다 |
| 대조군 묶음 | 5개 묶음 가운데 1개는 양성 없이 대조 항목만 둔다(전체 양성 40개 이상은 나머지 4개 묶음에서 채운다) |

**어긋남의 종류**를 묶음마다 4종 이상 섞고, 한 종류가 전체 양성의 25%를 넘지 않게 한다.
- 수치: 기간·기한·금액·비율·횟수·인원
- 주체·권한: 누가 결정·승인·통지하는가
- 조건·예외: 요건 누락, 예외를 원칙처럼 서술, 적용 범위 확대·축소
- 절차·순서: 단계 생략, 순서 뒤바뀜, 필수 협의·통지 누락
- 판(시점): 개정 전 조항을 현행처럼 인용(참고자료 안에 개정 이력이나 시행일을 둔다)
- 위치·형식: 근거가 표 안·별표·부칙·각주에 있음, 또는 근거와 주장이 떨어진 조항에 있음

**작성 규칙**
- 참고자료 파일 이름은 실제 사무실에서 쓰는 **한국어 제목**으로 한다(예: '○○재단 연구비 집행 기준'). 영문 약어·번호만으로 된 이름을 쓰지 않는다.
- 서면은 참고자료를 자연스럽게 언급한다(예: '피고의 관리규약에 따르면'). 하지만 참고자료 조항 번호를 매번 적지는 않는다. 적은 경우와 적지 않은 경우를 섞는다.
- 양성 주장은 한 문장 안에서 어긋남이 드러나게 쓴다. 참고자료를 직접 인용하는 척하며 바꿔 쓴 경우와, 인용 없이 단정한 경우를 섞는다.
- 대조 항목 중 '맞는 경우'는 참고자료 문구를 그대로 베끼지 말고 바꿔 말한다(같은 뜻이 다른 표현인 경우를 포함한다).
- 같은 서면 안에 양성과 대조를 섞는다. 양성끼리 몰아 쓰거나 '다음은 틀린 주장' 같은 표시를 넣지 않는다.
- 사건·기관·인물·금액·주소는 가공한다. 실존 기관·실제 개인정보를 쓰지 않는다. 실존 법령을 인용해도 되지만, 이 세트의 채점 대상은 참고자료 대조뿐이다.
- 바닥글에 '시험용 가상 문서' 표시를 넣어도 된다.

**파일**
- 서면은 텍스트 레이어가 있는 **PDF**로 만든다(reportlab + 한글 TTF 또는 `UnicodeCIDFont("HYSMyeongJo-Medium")`).
- 참고자료는 **DOCX**(python-docx)와 PDF를 섞는다. 표가 든 참고자료를 2건 이상 넣는다.
- 스캔 이미지·암호화·매크로를 쓰지 않는다.

## 2. 폴더
```
ragbench_<작성일 YYYYMMDD>/
  set01/
    briefs/
      RB-01.pdf
      RB-02.pdf
    drive_refs/
      <한국어 제목>.docx
      <한국어 제목>.pdf
    spec.json
  set02/
  ...
  set05/
```
- 서면 파일 이름은 `RB-NN.pdf`이고, 번호는 세트 전체에서 겹치지 않게 이어 붙인다.
- 참고자료 파일 이름은 세트 전체에서 겹치지 않게 한다.
- 정답 해설·생성 스크립트를 이 폴더에 두지 않는다.

## 3. `spec.json` (묶음마다 하나)
```json
{
  "name": "ragbench_<YYYYMMDD>_setNN",
  "rule_version": "1",
  "description": "참고자료 대조 고정 세트 묶음 setNN. 양성 N·대조 N. 작성 Codex 별도 세션, 작성일 <YYYY-MM-DD>.",
  "checks": [
    {"id": "P-01-1", "kind": "rag_relationship", "relationship": "CONTRADICTS", "scope": "claim",
     "text": "<서면 문장 안에 그대로 있는 문자열>", "label": "양성: RB-01 · <어긋남 종류> · <참고자료 제목>"},
    {"id": "C-01-1", "kind": "no_rag_relationship", "relationship": "CONTRADICTS", "scope": "claim",
     "text": "<서면 문장 안에 그대로 있는 문자열>", "label": "대조(맞음 또는 미언급): RB-01"}
  ]
}
```
- `id`: 양성은 `P-<서면번호>-<순번>`, 대조는 `C-<서면번호>-<순번>`. 묶음 안에서 겹치지 않는다.
- `kind`: 양성은 `rag_relationship`, 대조는 `no_rag_relationship`. `relationship`은 둘 다 `"CONTRADICTS"`, `scope`는 둘 다 `"claim"`.
- `text`: 그 주장 문장을 특정하는 문자열이다.
  - 서면 PDF 글에 **그대로** 있어야 한다.
  - 10자 이상이어야 한다.
  - 줄바꿈으로 끊기지 않게 한 줄 안에 둔다.
  - 같은 묶음의 서면 전체에서 **한 번만** 나와야 한다.
  - 끝 문장부호는 넣지 않는다.
- `label`: 사람이 볼 설명이다. 채점에는 쓰지 않는다. 양성은 어긋남 종류와 근거 참고자료 제목을 적는다.
- 문서 문장 외의 해설(왜 어긋나는지)은 `label`에 짧게만 적는다.

## 4. 내용 확인 (작성자가 스스로)
- 양성마다 근거가 되는 참고자료 문장이 실제로 있고, 서면 주장과 동시에 참일 수 없는지 확인한다.
- 대조 중 '맞는 경우'는 참고자료와 뜻이 같은지 확인한다. '다루지 않는 경우'는 참고자료 어디에도 그 사항이 없는지 확인한다.
- 대조군 묶음의 서면에는 참고자료와 어긋나는 주장이 하나도 없어야 한다.

## 5. 금지
- 참고자료와 서면에 같은 긴 문장을 그대로 두어 복사로 찾을 수 있게 만들지 않는다(대조 '맞는 경우'도 바꿔 말한다).
- 한 주장에 양성과 대조가 함께 걸리게 하지 않는다.

## 6. 자체 점검 (오류 0이어야 넘긴다)
`pip install pdfplumber python-docx` 뒤, 세트 폴더 밖에 아래 스크립트를 `check_ragbench.py`로 저장하고 `python check_ragbench.py <ragbench 폴더>`로 실행한다. 출력의 요약 줄과 [오류]·[경고] 줄을 그대로 보고에 붙인다.
```python
import hashlib, json, re, sys, unicodedata
from pathlib import Path
import pdfplumber, docx

norm = lambda s: " ".join(unicodedata.normalize("NFKC", s or "").split())
root = Path(sys.argv[1])
errors, warnings = [], []
name_key = lambda q: q.name
sets = sorted((p for p in root.iterdir() if p.is_dir() and p.name.startswith("set")), key=name_key)
stray = [p for p in root.iterdir() if not (p.is_dir() and p.name.startswith("set"))]
if stray: errors.append(f"폴더 맨 위에 묶음 밖 항목 {len(stray)}개")
digest = hashlib.sha256()
for f in sorted((p for p in root.rglob("*") if p.is_file()), key=lambda q: q.relative_to(root).as_posix()):
    rel = f.relative_to(root).as_posix()
    if rel.split("/")[0].startswith("set"):
        digest.update(rel.encode("utf-8")); digest.update(hashlib.sha256(f.read_bytes()).digest())
briefs_all, refs_all, pos_all, neg_all, control_sets = set(), set(), 0, 0, 0
for s in sets:
    b, r, sp = s / "briefs", s / "drive_refs", s / "spec.json"
    extra = [p.name for p in s.iterdir() if p.name not in ("briefs", "drive_refs", "spec.json")]
    if extra: errors.append(f"{s.name}: 허용되지 않은 항목 {len(extra)}개")
    if not (b.is_dir() and r.is_dir() and sp.is_file()):
        errors.append(f"{s.name}: briefs/·drive_refs/·spec.json 필요"); continue
    pdfs = sorted(b.iterdir(), key=name_key)
    if len(pdfs) != 2 or any(not re.fullmatch(r"RB-\d{2}\.pdf", p.name) for p in pdfs):
        errors.append(f"{s.name}: 서면은 RB-NN.pdf 2건")
    text = {}
    for p in pdfs:
        if p.name in briefs_all: errors.append(f"{s.name}: 서면 이름 중복 {p.name}")
        briefs_all.add(p.name)
        with pdfplumber.open(p) as f:
            text[p.stem] = norm(" ".join(pg.extract_text() or "" for pg in f.pages))
        if not text[p.stem]: errors.append(f"{s.name}/{p.name}: 글을 읽지 못함")
    refs = sorted(r.iterdir(), key=name_key)
    if not 2 <= len(refs) <= 3: errors.append(f"{s.name}: 참고자료 {len(refs)}건(2~3건)")
    for p in refs:
        if p.suffix.lower() not in (".pdf", ".docx"): errors.append(f"{s.name}/drive_refs: pdf·docx만")
        if p.name in refs_all: errors.append(f"{s.name}: 참고자료 이름 중복")
        refs_all.add(p.name)
        if not re.search(r"[가-힣]", p.stem): warnings.append(f"{s.name}/drive_refs: 한국어 제목이 아닌 파일")
        if p.suffix.lower() == ".docx":
            if not norm(" ".join(x.text for x in docx.Document(p).paragraphs)) and not docx.Document(p).tables:
                errors.append(f"{s.name}/drive_refs: 빈 docx")
    spec = json.loads(sp.read_text(encoding="utf-8"))
    if spec.get("rule_version") != "1" or not str(spec.get("name", "")).endswith(s.name):
        errors.append(f"{s.name}: spec name·rule_version")
    ids, pos, neg = set(), 0, 0
    joined = " ".join(text.values())
    for c in spec.get("checks", []):
        cid = c.get("id", "?")
        if cid in ids: errors.append(f"{s.name}: id 중복 {cid}")
        ids.add(cid)
        if c.get("kind") not in ("rag_relationship", "no_rag_relationship") or c.get("relationship") != "CONTRADICTS" \
                or c.get("scope") != "claim":
            errors.append(f"{s.name}/{cid}: kind·relationship·scope")
        pos += c.get("kind") == "rag_relationship"; neg += c.get("kind") == "no_rag_relationship"
        t = norm(c.get("text"))
        if len(t) < 10: errors.append(f"{s.name}/{cid}: text 10자 미만")
        n = joined.count(t)
        if n == 0: errors.append(f"{s.name}/{cid}: text가 서면 글에 없음")
        elif n > 1: errors.append(f"{s.name}/{cid}: text가 서면에 {n}번 나옴")
        if t != t.rstrip(".,」』)"): warnings.append(f"{s.name}/{cid}: 끝 문장부호")
    if pos == 0: control_sets += 1
    elif pos < 8: errors.append(f"{s.name}: 양성 {pos}개(8개 이상)")
    if neg < 8: errors.append(f"{s.name}: 대조 {neg}개(8개 이상)")
    pos_all += pos; neg_all += neg
if len(sets) != 5: errors.append(f"묶음 {len(sets)}개(5개)")
if control_sets != 1: errors.append(f"대조군 묶음 {control_sets}개(1개)")
if pos_all < 40: errors.append(f"양성 {pos_all}개(40개 이상)")
if neg_all < 40: errors.append(f"대조 {neg_all}개(40개 이상)")
print(f"세트 {root.name}, 지문 {digest.hexdigest()[:16]}, 묶음 {len(sets)}, 서면 {len(briefs_all)}, 참고자료 {len(refs_all)}, "
      f"양성 {pos_all}, 대조 {neg_all}, 대조군 묶음 {control_sets}, 오류 {len(errors)}, 경고 {len(warnings)}")
print("\n".join(["[오류] " + e for e in errors] + ["[경고] " + w for w in warnings]))
```

## 7. 넘기기와 보고
- 세트 폴더 전체를 zip 하나(`ragbench_<YYYYMMDD>.zip`)로 묶고, zip SHA-256을 구해 보고에 적는다.
- **보관 확인(사용자가 한다, 끝나면 이 세션에 알린다):** 해시 대조 → zip 그대로 두 곳 이상 보관 → 다른 폴더에 풀어 독립 점검(다른 새 세션, 같은 스크립트, 지문 일치).
- 채팅 보고는 아래 양식만 쓴다.
```
Drive 대조 고정 세트 ragbench_<YYYYMMDD> 작성 완료(지문 <16자리>, zip SHA-256 <64자리>)
- 묶음 5, 서면 N, 참고자료 N(표 포함 N, docx N·pdf N), 양성 N, 대조 N(맞음 N·미언급 N), 대조군 묶음 1
- 어긋남 종류별 양성 수: 수치 N, 주체·권한 N, 조건·예외 N, 절차·순서 N, 판(시점) N, 위치·형식 N
- 자체 점검: <check_ragbench.py 출력 요약 줄과 [오류]·[경고] 줄 그대로>
```

--- 프롬프트 끝 ---
