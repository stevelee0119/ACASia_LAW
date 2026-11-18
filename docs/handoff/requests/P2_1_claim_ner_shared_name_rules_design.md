# P2-1② 설계 메모: 주장 엔진 NER의 이름·법인 판정을 개인정보 엔진 공용 규칙과 일치시킴

- 작성일: 2026-11-18
- 작성: 구현 에이전트(Claude Code, 2026-11-18 사용자 지시로 구현 담당)
- 기준 브랜치: `origin/Steve_ACASiaLAW` (`63c060d22a0c6d9d4f7f497d628ee55288b558b8`)
- 근거 요구: `Acasia_Law_V0_22_0_개선_구현_지시문.md`의 **P2-1 ②항**("`claim_engine/extractor.py`의 `extract_entities`가
  `pii_engine/detector.py`의 `is_valid_korean_name_structure`·`LEGAL_MILITARY_STOPWORDS`·`COMPANY_STOPWORDS`를 공유하지 않음").
  지시문 원문은 저장소 밖(`/home/antigravity/`)에 있어 평가 측 원문 대조표는 원문 등록 후에 작성한다.

## 1. 현재 상태와 재현된 결함

`extract_entities`는 `pii_engine`의 일부 규칙만 공유한다.

| 공유 중 | 공유 안 됨(이번 대상) |
|---|---|
| `PARTY_HEADER_STOPWORDS`, `REPRESENTATIVE_NAME_STOPWORDS`, `PERSON_CATEGORY_STOPWORDS`, `MILITARY_NOUNS`, `_CATEGORY_JOSA_TAIL_RE`, `_has_category_name_ambiguity` | `is_valid_korean_name_structure`, `LEGAL_MILITARY_STOPWORDS`, `COMPANY_STOPWORDS` |

같은 낱말 목록을 두 엔진이 따로 들고 있어, 개인정보 엔진이 사람 이름으로 보지 않는 토큰을 주장 엔진은
`EntityType.PERSON`으로 올린다. 저장소 밖 자료 없이 합성 문장으로 재현했다(기준 `63c060d`).

| 합성 문장 | `is_person_name` | `is_valid_korean_name_structure` | 비고 |
|---|---|---|---|
| 피고 **사단장**은 … | True(오탐) | True | `사`가 단성에 있어 구조 검사만으로는 못 막는다 → 낱말 목록 필요 |
| 원고 **목적물**을 … | True(오탐) | True | `목`이 단성에 있음 → 낱말 목록 필요 |
| 피고 **지휘관**이 … | True(오탐) | True | 같음 |
| 증인 **검사원**은 … | True(오탐) | **False** | 구조 검사(성씨 체계)만으로 막힌다 |

법인 쪽도 같다. `COMPANY_MODIFIER_STOPWORDS`에 `COMPANY_STOPWORDS`가 빠져 `대금조항`·`계약조건`·`목적물`·
`특약사항`·`따라` 등 25개 낱말이 수식어 배제에 걸리지 않아, `주식회사`·`㈜` 인접 문맥에서 법인명으로 올라올 수 있다.

중복 없이 새로 더해지는 낱말은 사람 100개·법인 25개다(겹침 사람 49·법인 1).

**두 수단은 서로 보완 관계다.** 구조 검사는 성씨 체계에 없는 토큰(`검사원`)을, 낱말 목록은 성씨로 시작하는
직책·물건 명사(`사단장`·`목적물`·`지휘관`)를 막는다. 둘 중 하나만 넣으면 위 4건을 모두 막지 못한다.

## 2. 변경 설계

새 탐지 범주를 만들지 않고, **이미 보호 시험이 붙어 있는 개인정보 엔진의 공용 규칙을 주장 엔진이 재사용**한다.
낱말을 새로 쓰지 않으므로 서면 문구·사건 값 하드코딩에 해당하지 않는다.

1. `packages/claim_engine/extractor.py`에서 `packages.pii_engine.detector`의
   `COMPANY_STOPWORDS`·`LEGAL_MILITARY_STOPWORDS`·`is_valid_korean_name_structure`를 추가로 들여온다.
2. `_PERSON_STOPWORDS`에 `LEGAL_MILITARY_STOPWORDS`를 합친다.
3. `COMPANY_MODIFIER_STOPWORDS`에 `COMPANY_STOPWORDS`를 합친다.
4. `is_person_name`에 `after_text` 인자를 더하고, 기존 검사를 모두 통과한 뒤
   `is_valid_korean_name_structure(name, after_text, is_explicit_label=True)`로 성씨 체계·서술형 종결을 확인한다.
   `PERSON_CONTEXT_RE`는 `원고`·`피고`·`증인`·`소외` 등 **명시적 당사자 표기 직후**만 잡으므로
   `is_explicit_label=True`가 맞다(후행 문맥으로 정상 이름을 지우지 않는다, TK-39 결정과 같은 취급).
5. 호출부(`extract_entities`)가 일치 뒤 20자를 `after_text`로 넘긴다.

바꾸지 않는 것: `PERSON_CONTEXT_RE`·`COMPANY_CONTEXT_RE`의 문맥 정의, 법원·금액 추출,
`resolve_entities`의 동일 대상 통합, 개인정보 엔진 쪽 규칙(이 변경은 주장 엔진 단방향 재사용이다),
공용 입력(`exhibit_rows()` 등), 보호 경로.

## 2-1. 구현 중 발견한 추가 결함(같은 회차에서 함께 고침)

시험을 쓰다가 같은 추출 경로의 결함을 하나 더 찾았다. `_strip_company_josa`가 쓰는
`_COMPANY_JOSA_TAIL_RE`에 복합 조사(`로부터`·`으로부터`·`에게서`)가 없어, `'…상사로부터'`처럼 쓰이면
조사가 법인명에 그대로 남는다(`엡실론상사로부터`). 같은 법인이 `엡실론상사`와 `엡실론상사로부터` 두
엔티티로 갈려 `resolve_entities`의 동일 대상 통합도 빗나간다.

복합 조사를 짧은 조사보다 앞에 두어 고쳤다(정규식 대안 순서가 우선순위다). 기존 `으로` 처리는 그대로다
(`감마물산으로` → `감마물산`). 두 글자 이상 남아야 떼는 기존 가드(`m.start() >= 2`)도 유지한다.
사용자 지시(2026-11-13 '처음 의도한 개선·보완은 그 릴리스에 포함')에 따라 다음 판으로 미루지 않았다.

## 3. 알려진 한계(이번 범위 밖)

`is_valid_korean_name_structure`는 한국 성씨 체계(단성 116·복성 7)를 요구하므로, 한글로 음역한 외국인 성명은
구조 검사에서 빠진다. 이는 **개인정보 엔진의 기존 동작과 같다**(두 엔진이 같은 규칙을 쓰게 되므로 새로 생기는
불일치는 없다). 외국인 성명 처리는 두 엔진 공통 과제이므로 별도 티켓으로 올리고 이번 변경에서 다루지 않는다.

## 4. 시험(양성·대조 각 3건 이상, 합성 값만 사용)

- **대조군(계속 검출돼야 함)**: 단성 3음절, 복성 4음절, 조사 결합형 등 정상 성명 3건 이상과
  정상 법인명 3건 이상. 변경 전후 모두 검출.
- **양성(새로 배제돼야 함)**: 직책 명사·물건 명사·검사 명사가 당사자 표기 뒤에 온 4건과
  계약 용어가 `주식회사` 앞에 온 법인 수식어 3건.
- **회귀**: `tests/test_claim_engine*`, `tests/regression`, `tests/acceptance`, 고정 dev·holdout 성적표
  (`PERSON` 엔티티를 쓰는 성명 표기 불일치 탐지가 줄지 않아야 한다).

수용 기준은 평가 측(Codex) 판정이며, 이 메모의 통과 기록이 수용을 뜻하지 않는다.
