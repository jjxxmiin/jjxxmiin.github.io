---
layout: post
title: "Athena-Public은 모델을 바꿔도 기억할까: 10K 부팅·278개 프로토콜 검증"
date: '2026-03-01'
categories: Tech
tags:
  - LLM
  - 컨텍스트윈도우
summary: "Athena-Public이 로컬 마크다운으로 상태를 보존하는 방식과 10K 부팅·278개 프로토콜 주장을 살펴보고, 검색·충돌·클라우드 전송 한계를 정리합니다."
description: "Athena-Public이 Markdown state와 retrieval로 model 교체 뒤 기억을 이어가는 방식, 10K·278개 protocol 주장의 범위와 검색 recall·충돌·privacy 검증법을 설명합니다."
faq:
  - question: "Markdown 파일이 남아 있으면 새 model이 자동으로 기억하나요?"
    answer: "아닙니다. 관련 file을 검색하고 최신·적용 범위를 해석해 prompt에 넣어야 하며 retrieval이 실패하면 disk의 기록은 현재 작업에 쓰이지 않습니다."
  - question: "10K boot와 context 95% 수치는 모든 model에서 같나요?"
    answer: "프로젝트가 제시한 구성 설명이며 model tokenizer, tool instruction과 선택 file에 따라 실제 token·가용 context가 달라지므로 session별 측정이 필요합니다."
  - question: "로컬 Markdown이면 기밀 data가 외부로 나가지 않나요?"
    answer: "저장은 local이어도 cloud LLM prompt에 file 내용이 들어가면 외부 요청 경로를 통과하므로 file classification·redaction과 model별 전송 정책이 필요합니다."
github_url: https://github.com/winstonkoh87/Athena-Public
image:
  path: https://opengraph.githubassets.com/1/winstonkoh87/Athena-Public
  alt: "winstonkoh87/Athena-Public GitHub 저장소 대표 이미지"
---

Athena-Public은 모델을 바꿔도 로컬 파일에 기록한 상태를 남길 수 있지만, 새 모델이 그 파일을 올바르게 검색하고 해석해야 기억이 실제 작업으로 이어집니다. 핵심 검증은 disk 보존 자체가 아니라 relevant memory retrieval, 최신 규칙 우선순위와 cloud model로 전달되는 file 범위입니다.

[프로젝트](https://github.com/winstonkoh87/Athena-Public)의 문장 “Own the state. Rent the intelligence.”는 핵심을 잘 요약합니다. 모델 내부에 프로젝트 기억을 맡기는 대신 마크다운 파일로 상태를 소유하고, 필요할 때 다른 모델이 읽게 하는 접근입니다. 파일의 지속성과 모델의 기억 능력을 같은 것으로 보지 않는 것이 평가의 출발점입니다.

## 모델 독립성은 어디까지 가능한가

결정 기록, 코딩 규칙, 세션 요약을 평범한 파일로 저장하면 특정 채팅 서비스에 묶이는 정도를 줄일 수 있습니다. Git으로 변경을 비교하거나 잘못된 규칙을 되돌리기도 쉽습니다. 모델을 교체해도 파일 자체는 사라지지 않습니다.

하지만 새 모델이나 도구가 다음 조건을 충족해야 합니다.

- 로컬 워크스페이스를 읽고 쓸 권한이 있는가
- 작업과 관련된 파일을 검색할 수 있는가
- 오래된 규칙과 최신 규칙의 우선순위를 해석하는가
- 작업 뒤 무엇을 기억으로 남길지 일관되게 결정하는가

웹 채팅처럼 로컬 파일 접근이 없는 환경에서는 이 흐름을 그대로 쓸 수 없습니다. 모델 독립성은 모든 모델에서 자동 작동한다는 뜻이 아니라, 호환되는 파일 접근형 도구 사이에서 상태를 옮길 수 있다는 뜻에 가깝습니다.

## 10K 부팅과 278개 프로토콜은 무엇을 뜻하나

Athena-Public은 약 10K 토큰으로 정체성과 278개 의사결정 프로토콜의 인덱스를 부팅하고, 컨텍스트의 95%를 실제 작업에 남긴다는 구성을 제시합니다. 여섯 개의 헌법적 규칙과 네 단계의 권한 수준도 행동 경계를 만드는 요소입니다.

이 숫자들은 프로젝트가 제시한 구성의 설명이지 모든 모델·컨텍스트 창에서 같은 비율을 보장하는 측정값은 아닙니다. 실제 토큰은 선택한 파일, 도구가 덧붙이는 지시, 세션 기록에 따라 달라집니다. 278개 규칙을 전부 주입하는 것과 필요한 규칙의 인덱스만 읽는 것도 구분해야 합니다.

임베딩·키워드·리랭킹을 결합한 검색은 수백 세션의 파일을 모두 넣는 비용을 줄입니다. 반대로 검색이 틀리면 파일이 디스크에 있어도 모델은 기억하지 못합니다. Session 500에서 Session 5의 패턴을 찾았다는 사례와 800세션 규모는 장기 사용 가능성을 보여 주지만, 자신의 프로젝트 용어와 질문으로 재현해야 합니다.

## 설치 조각에서 빠진 전제

원문에 나온 시작 흐름은 다음과 같습니다.

```bash
git clone https://github.com/winstonkoh87/Athena-Public.git ~/.athena-workspace
cd ~/.athena-workspace

ls -a
# .agent/   -> 워크플로와 스킬
# .context/ -> 규칙, 세션 기록, 의사결정 문서
```

이 코드는 저장소를 홈 디렉터리 아래에 복제해 구조를 보는 스냅샷입니다. 버전 고정, 기존 경로 충돌, 파일 권한, 백업, IDE의 로컬 접근 허용, 실제 초기화와 진단 절차는 포함하지 않습니다. 원문에서 v1.4의 `athena init`과 `--doctor`가 언급되지만, 위 코드만으로 해당 과정까지 끝났다고 볼 수 없습니다.

기존 프로젝트에 라이브러리 하나를 추가하는 방식과도 다릅니다. Athena 워크스페이스를 중심에 두거나 IDE의 여러 루트 기능으로 작업 폴더를 연결해야 할 수 있으므로, 먼저 복제된 테스트 프로젝트에서 파일 읽기·쓰기 범위를 확인하는 편이 안전합니다.

## 로컬 저장과 로컬 처리는 다르다

마크다운이 내 디스크에 있다는 사실은 상태의 소유권과 감사를 돕습니다. 그러나 클라우드 LLM이 파일 내용을 입력으로 받으면 그 데이터는 추론 요청 경로를 따라 외부로 전송될 수 있습니다. “로컬이므로 기밀이 절대 나가지 않는다”는 결론은 성립하지 않습니다.

권한을 줄 때는 기억 폴더와 실제 프로젝트 폴더를 나누고, 비밀·개인정보가 기록되지 않도록 규칙을 둬야 합니다. 외부 모델로 보낼 수 있는 파일과 로컬에서만 처리할 파일을 구분하는 것도 필요합니다. [관련 사용자 커뮤니티](https://www.reddit.com/r/google_antigravity/)의 사례는 아이디어를 얻는 자료가 될 수 있지만, 자신의 데이터 정책을 대신 결정하지는 않습니다.

## 기억 파일이 늘수록 충돌 관리가 중요하다

278개 프로토콜과 수백 세션의 기록은 풍부한 맥락이면서 동시에 유지보수 대상입니다. 두 규칙이 충돌하거나 예전 결정이 남으면 모델은 어느 지시를 따라야 할지 흔들릴 수 있습니다. 파일마다 작성 시각, 적용 범위, 우선순위와 폐기 상태를 남기고 정기적으로 중복을 정리해야 합니다.

도입 전에는 작은 프로젝트에서 모델 두 개를 번갈아 쓰며 동일한 결정 질문을 반복해 봅니다. 검색된 파일, 답의 근거, 수정된 기억을 로그로 비교하고 오래된 규칙이 최신 결정을 덮지 않는지 확인합니다. Athena-Public의 가치는 “건망증 완치”가 아니라 기억을 모델 밖의 검토 가능한 상태로 옮긴다는 데 있습니다.

## 무엇을 기억하고 언제 폐기할까

모든 대화를 memory로 저장하면 검색 noise와 개인정보만 늘 수 있습니다. Stable project rule, decision과 근거, 진행 중 task state, 일시적인 observation을 구분하고 보존 기간을 다르게 둡니다.

| Memory 유형 | 예 | Lifecycle |
|---|---|---|
| Constitution·규칙 | 금지 API, review 기준 | 명시적 version·승인 뒤 변경 |
| Decision record | database 선택과 근거 | superseded 상태와 후속 결정 연결 |
| Session summary | 완료·미완료 task | 다음 session 확인 뒤 archive |
| Temporary evidence | log·검색 결과 | source timestamp와 expiry 설정 |
| Secret·개인정보 | token·customer data | 저장 금지 또는 별도 vault |

Model이 “앞으로 항상”이라고 쓴 문장을 곧바로 최고 우선 규칙으로 승격하지 않습니다. 사람이 승인한 source, scope와 expiry가 있어야 합니다. 새 결정을 저장할 때 기존 memory와 충돌하는 후보를 보여 주고 replace·merge·보류를 선택하게 합니다.

## Retrieval이 실제로 기억을 찾았는지 어떻게 재나

과거 session에서 답을 아는 질문을 만들어 expected file을 label합니다. Keyword가 그대로 있는 쉬운 query뿐 아니라 표현이 바뀐 질문, 최근·오래된 결정, 서로 충돌하는 기록을 섞습니다. Retrieval recall@k, 잘못 가져온 file 수와 최종 답의 citation을 기록합니다.

파일을 찾았지만 model이 무시한 failure와 아예 검색되지 않은 failure를 구분합니다. Oracle로 정답 file을 직접 넣은 조건이 성공하면 retriever가 병목이고, oracle에서도 틀리면 rule 해석·prompt가 병목입니다. Session 수를 늘릴 때 token과 latency가 어떻게 변하는지도 봅니다.

## Model 교체 Test는 어떤 순서로 할까

먼저 model A에서 decision을 만들고 memory에 저장한 뒤, fresh session의 model B에 관련 질문을 줍니다. 둘에게 같은 retrieval result를 제공해 답·적용 scope가 일치하는지 봅니다. 그다음 model B가 새 결정을 저장하고 A로 돌아와 round-trip을 확인합니다.

Tokenizer와 instruction following이 달라 긴 protocol을 자르는 위치가 바뀔 수 있습니다. Markdown syntax를 공통 schema로 제한하고 parser validation을 둡니다. Model별로 boot token, retrieval latency, rule violation과 잘못된 memory write를 비교해야 “model independent”의 실제 범위를 알 수 있습니다.

Backup과 Git history가 있어도 민감 data가 commit되면 history에 남습니다. Memory repository의 접근권한, encryption·retention과 삭제 절차를 일반 source code보다 엄격하게 정할 수 있습니다. Cloud model로 전달되는 file 목록도 audit log에 남깁니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [공식 GitHub 저장소](https://github.com/winstonkoh87/Athena-Public)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [긴 대화 RAG에서 관련 문서를 다시 골라야 할까? QRRanker의 4B 해법]({% post_url 2026-02-25-Query-focused-and-Memory-aware-Reranker-for-Long-Context-Processing %}) — QRRanker가 4B 모델의 query-focused attention head로 후보 문서를 함께 재정렬하고 대화·서사 메모리를 활용하는 방법과 적용 한계를 정리합니다.
- [headroom: AI 코딩 에이전트의 컨텍스트 한계를 넘는 압축 기술]({% post_url 2026-07-07-Headroom-Context-Compression-Layer-for-AI-Agents %}) — Headroom은 대형 언어 모델(LLM)에 전달되는 방대한 도구 출력과 로그, RAG 결과물을 최대 95%까지 압축하여 토큰 비용을 줄이고 답변 정확도를 유지하는 오픈소스 기반의 컨텍스트 압축 레이어입니다.
- [TencentDB-Agent-Memory: AI 코딩 에이전트가 맥락 폭발을 막고 진짜 기억을 갖는 법]({% post_url 2026-07-15-TencentDB-Agent-Memory-How-AI-Coding-Agents-Prevent-Context-Bloat-and-Build-Real-Memory %}) — 기존 벡터 데이터베이스의 평면적 구조를 탈피해 대화(L0)부터 페르소나(L3)까지 4단계로 지식을 압축하는 완전 로컬 에이전트 기억 시스템입니다. 장기 실행 작업에서 발생하는 '맥락 폭발'을 막기 위해 방대한 도구 로그를 외부 파일로…
<!-- internal-links:end -->

## 자주 묻는 질문

### Markdown 파일이 남아 있으면 새 model이 자동으로 기억하나요?

아닙니다. 관련 file을 검색하고 최신·적용 범위를 해석해 prompt에 넣어야 하며 retrieval이 실패하면 disk의 기록은 현재 작업에 쓰이지 않습니다.

### 10K boot와 context 95% 수치는 모든 model에서 같나요?

프로젝트가 제시한 구성 설명이며 model tokenizer, tool instruction과 선택 file에 따라 실제 token·가용 context가 달라지므로 session별 측정이 필요합니다.

### 로컬 Markdown이면 기밀 data가 외부로 나가지 않나요?

저장은 local이어도 cloud LLM prompt에 file 내용이 들어가면 외부 요청 경로를 통과하므로 file classification·redaction과 model별 전송 정책이 필요합니다.
