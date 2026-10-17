# 고정 비공개 벤치마크 자체 점검 프롬프트 (Codex, 2026-10-10 작성, 2026-10-17 저장소 등록)

> 1판·2판 공통. 2판([작성 프롬프트](PROMPT_FOR_CODEX_FIXED_BENCHMARK_V2.md))은 원본 zip을 **풀어 둔 측정용 폴더**에서 실행하고, 출력 지문이 작성 보고의 지문과 같은지 확인한다.

> 사용법(사용자)
> - 벤치마크 폴더가 있는 PC에서 **저장소를 연결하지 않은 Codex 새 세션**을 연다. 구현 세션, 평가 세션, 벤치마크를 작성한 세션은 쓰지 않는다.
> - 아래 '--- 프롬프트 시작 ---'부터 '--- 프롬프트 끝 ---'까지만 붙여 넣고, `<BENCH_DIR>`을 벤치마크 폴더의 실제 경로(예: `~/bench/fixed_bench_20261011`)로 바꾼다.
> - Codex가 내는 3절 보고만 평가 측에 전달한다. 지문은 `scripts/fixed_benchmark.py`가 측정 때 계산하는 값과 같은 방식이라, 측정 기록의 지문과 대조해 같은 세트인지 확인한다.
> - 첫 측정(`.sealed_out/` 생성) **전에** 실행한다. 측정 뒤에는 `.sealed_out/` 때문에 '허용되지 않은 항목' 오류가 난다.

--- 프롬프트 시작 ---

# 과제: 고정 비공개 벤치마크의 형식 자체 점검 (내용 열람 금지)

너는 점검 실행자다. 사용자 PC의 벤치마크 폴더 `<BENCH_DIR>`에 대해 아래 점검 스크립트 하나만 실행하고, 정해진 양식으로 결과를 보고한다. 벤치마크를 고치지 않는다.

## 0. 금지 (가장 먼저 지킨다)
1. **벤치마크 폴더 안 파일을 열거나 읽거나 출력하지 않는다.**
   - PDF, `ground_truth.json`, `match_spec.json`에 `cat`·`type`·`head`·편집기·PDF 뷰어·`pdftotext`를 쓰지 않는다.
   - 파일 목록도 출력하지 않는다. 경로는 스크립트 인자로 넘기기만 한다.
2. **벤치마크를 고치지 않는다.** 오류가 나도 파일을 수정·삭제·이동하지 않는다. 고치는 일은 사용자가 한다.
3. **저장소·웹을 보지 않는다.** 어떤 git 저장소나 GitHub 페이지도 열지 않는다.
4. 스크립트 출력의 오류·경고 줄은 묶음 이름·문서 키·항목 번호만 담는다. 그 밖에 문서 문장으로 보이는 글이 나오면 보고에 옮기지 않는다.
5. 끝나면 스크립트 파일 사본을 지운다. 이 세션을 다른 작업에 다시 쓰지 않는다.

## 1. 준비
- Python 3.10 이상을 쓴다. `pip install pdfplumber`를 한다(이미 있으면 생략).
- 아래 2절 스크립트를 **벤치마크 폴더 밖**에 `check_bench.py`로 저장한다(예: 사용자 홈의 임시 폴더).
- `pdftotext`는 한글 글꼴을 못 읽는 환경이 있어 쓰지 않는다.

## 2. 실행
```bash
python check_bench.py <BENCH_DIR>
```
Windows PowerShell에서도 같은 명령이다(`python check_bench.py C:\bench\fixed_bench_YYYYMMDD`).

**점검 스크립트(그대로 저장한다)**
```python
import hashlib, json, subprocess, sys, unicodedata
from collections import Counter
from pathlib import Path
import pdfplumber

TYPES = {"CIT-NX", "CIT-NX-DB", "CIT-META", "CIT-FAB-Q", "CIT-MIS", "LAW-NX", "LAW-MIS", "SRC-UNV",
         "EVI-DATE", "EVI-NUM", "EVI-FORM", "EVI-INCONS", "EVI-LOGIC", "EVI-OVR", "EVI-FAKECIT", "EVI-COPY",
         "INJ-ANNOT", "INJ-ATTACH", "INJ-COVERED", "INJ-INVISIBLE-TR3", "INJ-META", "INJ-OFFPAGE", "INJ-TINY",
         "INJ-VISIBLE", "INJ-WHITE", "INJ-ZWSP", "AIGEN", "OVR", "FP-TRAP"}
NEED4 = ("CIT-NX", "CIT-NX-DB", "CIT-META", "CIT-FAB-Q", "CIT-MIS", "LAW-NX", "LAW-MIS", "SRC-UNV", "EVI-DATE",
         "EVI-NUM", "EVI-FORM", "EVI-INCONS", "EVI-LOGIC", "EVI-OVR", "EVI-FAKECIT", "EVI-COPY", "AIGEN", "OVR")
ALLOWED = {"ground_truth.json", "match_spec.json"}
norm = lambda s: " ".join(unicodedata.normalize("NFKC", s or "").split())
root = Path(sys.argv[1])
errors, warnings = [], []

# 벤치마크 폴더: 이름, 저장소 밖, 하위 묶음(setNN)만
if not root.name.startswith("fixed_bench_"):
    errors.append("벤치마크 폴더 이름은 fixed_bench_<YYYYMMDD>")
try:
    inside = subprocess.run(["git", "-C", str(root), "rev-parse", "--is-inside-work-tree"],
                            capture_output=True, text=True, timeout=10).stdout.strip() == "true"
except (OSError, subprocess.SubprocessError):
    inside = False
if inside:
    errors.append("폴더가 git 저장소 안에 있다(저장소 밖으로 옮긴다)")
stray = [p for p in root.iterdir() if not (p.is_dir() and p.name.startswith("set"))]
if stray:
    errors.append(f"벤치마크 폴더에 묶음(setNN) 밖 항목 {len(stray)}개")
sets = sorted((p for p in root.iterdir() if p.is_dir() and p.name.startswith("set")), key=lambda q: q.name)

# 지문: scripts/fixed_benchmark.py와 같은 방식(묶음 이름 + 허용 파일 이름·내용 해시)
digest = hashlib.sha256()
keys, docs_total, controls, inj_docs, n_total = set(), 0, 0, 0, 0
types_total = Counter()
for s in sets:
    tag = s.name
    if not ((s / "ground_truth.json").is_file() and (s / "match_spec.json").is_file()):
        errors.append(f"{tag}: ground_truth.json·match_spec.json 없음")
        continue
    digest.update(s.relative_to(root).as_posix().encode("utf-8"))
    for p in sorted(s.iterdir(), key=lambda q: q.name):  # OS와 무관한 순서
        if p.is_file() and (p.name in ALLOWED or p.suffix.lower() == ".pdf"):
            digest.update(p.name.encode("utf-8")); digest.update(hashlib.sha256(p.read_bytes()).digest())
    extra = [p for p in s.iterdir() if p.name not in ALLOWED and not (p.is_file() and p.suffix.lower() == ".pdf")]
    if extra:
        errors.append(f"{tag}: 허용되지 않은 항목 {len(extra)}개(종류: {sorted({p.suffix or ('폴더' if p.is_dir() else '확장자 없음') for p in extra})})")
    gt = json.loads((s / "ground_truth.json").read_text(encoding="utf-8"))
    spec = json.loads((s / "match_spec.json").read_text(encoding="utf-8"))["tokens"]
    if gt.get("item_format") != ["type", "location", "target", "explanation", "source_url"]:
        errors.append(f"{tag}: item_format이 다르다")
    if set(gt["documents"]) != set(spec):
        errors.append(f"{tag}: 두 파일의 문서 키가 다르다")
    if not 6 <= len(gt["documents"]) <= 8:
        errors.append(f"{tag}: 문서 {len(gt['documents'])}건(6~8건)")
    if not any(d.get("expected") == "PASS" for d in gt["documents"].values()):
        errors.append(f"{tag}: 대조군(PASS) 문서가 없다")
    if not any(d.get("injection_test") for d in gt["documents"].values()):
        errors.append(f"{tag}: injection_test 문서가 없다")
    n_set = 0
    for key, doc in gt["documents"].items():
        docs_total += 1
        controls += doc.get("expected") == "PASS"
        inj_docs += bool(doc.get("injection_test"))
        if key in keys:
            errors.append(f"{tag}/{key}: 문서 키가 다른 묶음과 겹친다")
        keys.add(key)
        pdf = s / doc["file"]
        if "_" in key or not key.startswith("SD-") or Path(doc["file"]).stem.split("_")[0] != key \
                or pdf.suffix.lower() != ".pdf" or not pdf.is_file():
            errors.append(f"{tag}/{key}: 키·파일명·PDF 확인")
            continue
        if doc.get("expected") not in ("PASS", "FAIL"):
            errors.append(f"{tag}/{key}: expected는 PASS 또는 FAIL")
        with pdfplumber.open(pdf) as f:
            text = norm(" ".join(page.extract_text() or "" for page in f.pages))
        if not text:
            errors.append(f"{tag}/{key}: PDF에서 글을 읽지 못함(텍스트 레이어 확인)")
        items, groups_list = doc["items"], spec.get(key, [])
        if len(items) != len(groups_list):
            errors.append(f"{tag}/{key}: items {len(items)}개, 토큰 {len(groups_list)}개")
            continue
        if sum(1 for it in items if it and it[0] == "FP-TRAP") < 2:
            errors.append(f"{tag}/{key}: FP-TRAP 2개 미만")
        seen = {}
        for i, (item, groups) in enumerate(zip(items, groups_list)):
            if len(item) != 5:
                errors.append(f"{tag}/{key}#{i}: 항목은 5칸")
                continue
            kind, target = item[0], norm(item[2])
            parts = [p.strip() for p in kind.split("/")]
            if any(p not in TYPES for p in parts):
                errors.append(f"{tag}/{key}#{i}: 유형 표기")
            if doc.get("expected") == "PASS" and kind != "FP-TRAP":
                errors.append(f"{tag}/{key}#{i}: 대조군에 결함 항목")
            if kind != "FP-TRAP":
                n_set += 1
                types_total.update(parts)
            if not groups or any(not g for g in groups):
                errors.append(f"{tag}/{key}#{i}: 빈 그룹")
                continue
            if len(groups) > 3:
                warnings.append(f"{tag}/{key}#{i}: 그룹이 3개 초과")
            sig = json.dumps(sorted(sorted(norm(t) for t in g) for g in groups), ensure_ascii=False)
            if sig in seen:
                errors.append(f"{tag}/{key}#{i}: #{seen[sig]}과 토큰 묶음이 같다")
            seen[sig] = i
            hidden = any(p.startswith("INJ-") for p in parts)
            for gi, g in enumerate(groups):
                if not hidden and not any(norm(t) in text for t in g):
                    errors.append(f"{tag}/{key}#{i} 그룹{gi}: 어느 대안도 PDF 글에 없음")
                if not any(norm(t) in target for t in g):
                    warnings.append(f"{tag}/{key}#{i} 그룹{gi}: target에 없는 토큰")
                if any(len(norm(t)) < 3 for t in g):
                    warnings.append(f"{tag}/{key}#{i} 그룹{gi}: 3자 미만 토큰")
                if any(norm(t) != norm(t).rstrip(".,」』)") for t in g):
                    warnings.append(f"{tag}/{key}#{i} 그룹{gi}: 끝 문장부호")
    if n_set < 40:
        errors.append(f"{tag}: 결함 항목 {n_set}개(묶음마다 40개 이상)")
    n_total += n_set

# 전체 구성
if len(sets) < 5: errors.append(f"묶음 {len(sets)}개(5개 이상)")
if docs_total < 30: errors.append(f"문서 {docs_total}건(30건 이상)")
if controls < 5: errors.append(f"대조군 {controls}건(묶음마다 1건 이상)")
if n_total < 200: errors.append(f"결함 항목 {n_total}개(200개 이상)")
few = [t for t in NEED4 if types_total[t] < 4]
if few: errors.append("4개 미만 유형: " + ", ".join(few))
over = [t for t, c in types_total.items() if n_total and c > n_total * 0.15]
if over: errors.append("전체의 15% 초과 유형: " + ", ".join(sorted(over)))
if types_total["LAW-MIS"] < 8: errors.append("LAW-MIS 8개 미만")
if types_total["EVI-NUM"] < 10: errors.append("EVI-NUM 10개 미만")
if controls < 6: warnings.append(f"대조군 {controls}건(6건 이상 권장)")
print(f"벤치마크 {root.name}, 지문 {digest.hexdigest()[:16]}")
print(f"묶음 {len(sets)}, 문서 {docs_total}(대조군 {controls}, 인젝션 {inj_docs}), 결함 항목 {n_total}, 유형 {len(types_total)}종, 오류 {len(errors)}, 경고 {len(warnings)}")
print("\n".join(["[오류] " + e for e in errors] + ["[경고] " + w for w in warnings]))
```

**스크립트가 보는 것**
- 폴더: 이름이 `fixed_bench_`로 시작하는지, git 저장소 밖에 있는지, 하위에 묶음 폴더(`setNN`)만 있는지, 묶음마다 허용 파일(`ground_truth.json`, `match_spec.json`, PDF)만 있는지
- 묶음마다: 문서 6~8건, 대조군(PASS) 1건 이상, 인젝션 문서 1건 이상, 결함 항목 40개 이상, 문서마다 FP-TRAP 2개 이상
- 전체: 묶음 5개 이상, 문서 30건 이상, 대조군 5건 이상(6건 이상 권장, 미만이면 경고), 결함 항목 200개 이상, INJ- 밖 유형 18종 각 4개 이상, 한 유형이 전체의 15% 이하, LAW-MIS 8개 이상, EVI-NUM 10개 이상, 문서 키가 묶음 사이에 겹치지 않음
- 형식: 문서 키와 파일명(`SD-`, `_` 없음), 항목 5칸, 유형 29종 안의 이름, 대조군에 결함 항목 없음, 정답 항목 수와 토큰 그룹 수 일치, 빈 그룹·중복 토큰 묶음 없음
- 토큰: 인젝션이 아닌 항목은 그룹마다 대안 하나 이상이 PDF 글에 그대로 있는지
- 경고: target에 없는 토큰, 3자 미만 토큰, 끝 문장부호, 그룹 3개 초과, 대조군 6건 미만
- 지문: 묶음 이름과 허용 파일의 이름·내용으로 만든 SHA-256 앞 16자리(측정 도구와 같은 방식). 내용은 출력하지 않는다.

## 3. 보고 양식 (이것만 쓴다)
```
고정 벤치마크 자체 점검 — 실행일 <YYYY-MM-DD, 한국 시각>
환경: python <버전>, pdfplumber <버전>, OS <Windows/macOS/Linux>
폴더: <폴더 이름>, 지문: <16자리>
결과: 묶음 <N>, 문서 <N>(대조군 <N>, 인젝션 <N>), 결함 항목 <N>, 유형 <N>종, 오류 <N>, 경고 <N>
오류·경고 줄: <스크립트 출력의 [오류]·[경고] 줄 그대로. 없으면 '없음'>
```
- 오류가 1개 이상이면 '전달 불가'라고 덧붙인다. 사용자가 작성 세션에 고치게 한 뒤 다시 실행한다.
- 경고는 사용자가 확인하고, 사유가 있으면 그대로 둔다.

--- 프롬프트 끝 ---
