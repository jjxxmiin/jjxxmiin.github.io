---
layout: post
title: 'Context Mode가 토큰을 98% 줄인다는 수치를 믿어도 될까? 측정법과 누락'
date: '2026-05-09 18:40:24'
categories: Tech
tags:
  - 컨텍스트윈도우
  - AI에이전트
summary: 'Context Mode의 SQLite FTS5 기반 출력 압축 구조를 이해하고, 98% 절감 수치를 일반화하기 전에 확인할 저장소 불일치·검색 누락·우회 경로를 점검합니다.'
description: "Context Mode의 98% 주장을 byte·billing token·end-to-end cost로 분리하고 golden evidence recall, hook bypass·SQLite lifecycle과 품질 동등선으로 재현합니다."
github_url: https://github.com/mksglu/claude-context-mode
faq:
  - question: "Context Mode의 98% 절감은 API 청구 token도 98% 줄었다는 뜻인가요?"
    answer: "본문만으로는 단정할 수 없습니다. 반환 byte, tokenizer 입력, 검색·재확대와 여러 turn을 포함한 전체 청구량을 따로 측정해야 합니다."
  - question: "압축 전후 품질 동등선은 어떻게 확인하나요?"
    answer: "정답 근거 line을 표시한 golden log·DOM에서 answer·citation recall과 반례 누락을 비교하고 실패하면 원문 확대 경로를 사용해야 합니다."
  - question: "hook를 우회하는 tool이 있으면 어떻게 해야 하나요?"
    answer: "도구별 interception test와 runtime log로 coverage를 확인하고 큰 output이 우회하면 해당 tool을 차단하거나 같은 virtualization wrapper에 넣어야 합니다."
image:
  path: https://opengraph.githubassets.com/1/mksglu/claude-context-mode
  alt: "mksglu/claude-context-mode GitHub 저장소 대표 이미지"
---

Context Mode의 98% 절감은 제시된 출력 사례에서는 가능한 수치지만, 모든 세션의 토큰 비용과 작업 품질이 같은 비율로 좋아진다는 보장은 아닙니다. 반환 byte·실제 청구 token·검색을 포함한 전체 session 비용을 분리하고 같은 정답 근거를 회수하는지 재현해야 수치를 사용할 수 있습니다.

## 먼저 저장소와 측정 대상을 맞춰야 한다

페이지의 frontmatter는 [mksglu/claude-context-mode](https://github.com/mksglu/claude-context-mode)를 가리키지만, 본문 메타데이터와 참고 자료는 [mksglu/context-mode](https://github.com/mksglu/context-mode)를 지목합니다. [프로젝트 설명 사이트](https://context-mode.com/)와 [관련 자료](https://skillsllm.com/)도 함께 제시됩니다. 측정값을 재현하려면 어느 저장소와 버전, 어떤 도구 연결을 썼는지부터 하나로 고정해야 합니다.

원문 표에는 Playwright DOM 56KB가 299바이트, GitHub 이슈 59KB가 1.1KB, 서버 로그 45KB가 155바이트, 세션 누적 315KB가 5.4KB로 줄었다는 사례가 나옵니다. 이는 반환된 텍스트 크기를 비교한 값입니다. 모델에 실제 청구된 입력 토큰, 인덱싱을 지시하는 프롬프트, 후속 검색 결과, 여러 번 검색한 비용까지 모두 합친 측정인지 본문만으로는 확인하기 어렵습니다.

“30분에서 3시간” 역시 에이전트 지능의 객관적인 수명이라기보다 특정 작업 흐름에서 컨텍스트가 덜 차는 효과를 표현한 수치로 읽는 편이 안전합니다. 같은 질문 세트와 같은 원본 데이터로 적용 전후 성공률, 누락률, 전체 토큰을 함께 재야 합니다.

재현 manifest에는 repository URL·commit, 설치 package와 hook config, model·tokenizer, context limit, 대상 tool과 원본 fixture hash를 넣습니다. `claude-context-mode`와 `context-mode`가 redirect·rename·별도 구현인지 확인하고 한쪽의 README·benchmark를 다른 code에 붙이지 않습니다. default chunk·BM25 setting과 compaction 시점도 결과에 영향을 줍니다.

측정 단위는 네 가지로 나눕니다. 원본·반환 byte, model tokenizer로 센 input token, provider usage의 cached·uncached token, 그리고 첫 indexing부터 후속 retrieval·answer까지 전체 비용입니다. 315KB→5.4KB는 첫 번째일 수 있고 사용자가 실제로 지불하는 절감은 나머지 호출과 cache 정책에 따라 달라집니다. latency와 local CPU·disk도 함께 기록합니다.

## Context Mode는 압축보다 외부화에 가깝다

구조의 핵심은 대규모 도구 출력을 대화에 그대로 넣지 않는 것입니다. preToolUse 훅으로 실행을 가로채고, 별도 샌드박스에서 결과를 받은 뒤, 텍스트를 나눠 로컬 SQLite FTS5에 저장합니다. 모델에는 인덱싱됐다는 짧은 응답을 주고, 필요할 때 BM25 검색으로 관련 조각만 다시 가져옵니다.

Porter stemming은 영어 단어의 변형을 묶는 데 도움을 주지만, BM25는 기본적으로 어휘가 겹치는 정도에 의존합니다. 원문에 Exception만 있는데 모델이 Error만 검색하면 중요한 줄을 놓칠 수 있습니다. 출력이 사라진 것이 아니라 모델의 즉시 컨텍스트 바깥으로 옮겨졌다는 점이 중요합니다.

원문의 fetch_and_index JSON은 URL 또는 파일과 검색 의도를 받는 도구 스키마를 보여줍니다. 실제 훅 설치, 샌드박스 권한, 데이터베이스 위치, 오류 처리까지 담긴 실행 설정은 아니므로 구조 설명용 조각입니다. 지원 플랫폼과 런타임도 선택한 저장소의 문서에서 다시 확인해야 합니다.

## 절감률과 함께 누락률을 재는 방법

첫 번째 시험은 정답이 원본의 서로 다른 위치에 흩어진 로그나 DOM으로 만듭니다. 적용 전에는 전체 원본으로 답하게 하고, 적용 후에는 인덱스 검색만으로 같은 질문을 답하게 합니다. 두 결과에서 맞힌 사실, 인용한 위치, 빠뜨린 예외를 비교하면 단순 바이트 절감과 정보 손실을 분리할 수 있습니다.

두 번째로 전체 비용을 셉니다. 최초 인덱싱 알림뿐 아니라 검색 요청 횟수와 매번 돌아온 조각, 후속 대화의 입력까지 포함해야 합니다. 검색어를 여러 번 고쳐야 했다면 첫 응답이 작다는 사실만으로 전체 절감률을 말할 수 없습니다.

세 번째는 우회 경로입니다. 에이전트가 훅을 거치지 않는 cat이나 일반 웹 가져오기 도구를 사용하면 큰 출력이 다시 대화에 들어올 수 있습니다. 어떤 도구 호출이 가로채졌고 어떤 호출이 통과했는지 로그로 확인해야 합니다. 라우팅 지침은 모델의 습관을 줄일 수 있지만 시스템 수준의 강제와 같은 것은 아닙니다.

golden fixture에는 명백한 error뿐 아니라 희귀 code, 부정문, 멀리 떨어진 두 사건과 같은 이름의 다른 객체를 넣습니다. 각 질문에 필요한 line·offset을 표시하고 full-context, 한 번 BM25, query 확장·원본 확대 세 조건의 answer·evidence recall을 비교합니다. 자연스러운 문장만 채점하면 잘못된 근거를 놓치므로 citation이 실제 claim을 지지하는지도 봅니다.

chunk size, stemming과 top-k는 validation set에서 정한 뒤 test에는 고정합니다. test answer를 보고 query나 top-k를 바꾸면 검색 품질을 과대평가합니다. 한국어·code·stack trace처럼 Porter stemming 이점이 작은 데이터는 별도 범주로 보고, file path·error code용 exact search를 조합할 수 있습니다.

hook coverage는 tool 이름 목록보다 실행 test로 확인합니다. streaming·timeout·cancellation·nested MCP와 shell alias를 호출하고 original byte, intercepted byte와 context에 실제 들어간 byte를 trace합니다. 일부만 intercept되거나 DB write가 실패하면 empty summary로 진행하지 않고 원본 direct mode 또는 명시적 실패로 전환합니다.

## 도입할 때 지켜야 할 복구 경로

검색 결과에 핵심 단서가 없을 때 원문 범위를 넓히거나 특정 구간을 직접 확인하는 경로가 있어야 합니다. 무조건 짧은 결과만 유지하면 잘못된 가설을 반박할 정보까지 가려질 수 있습니다. 장애 분석에서는 일치하는 줄뿐 아니라 앞뒤 사건과 시간 순서를 복원할 수 있어야 합니다.

로컬 SQLite에 저장되는 도구 출력의 보존 기간과 접근 범위도 정해야 합니다. 대화에서 빠졌다고 데이터가 사라지는 것은 아니며, 여러 작업의 인덱스가 섞이면 오래된 결과를 현재 사실로 가져올 수 있습니다. 작업별 분리와 정리 규칙이 필요합니다.

Context Mode는 컨텍스트 윈도우를 키우는 대신 도구 출력을 로컬 검색 계층으로 옮기는 설계입니다. 대규모 로그·DOM·이슈 목록처럼 전체를 매번 읽을 이유가 적은 데이터에는 효과적일 수 있습니다. 다만 98%라는 숫자보다 같은 문제를 정확히 해결했는지, 중요한 반례를 놓치지 않았는지, 모든 도구 경로가 실제로 통제됐는지를 먼저 확인해야 합니다.

## 어떤 결과라면 운영 범위를 넓힐까

대표 session 20~50개에서 answer quality가 full-context의 허용 범위 안이고 evidence recall이 기준을 넘으며, 전체 input token·p95 latency 또는 비용이 실제로 줄어야 합니다. 원본 확대율이 지나치게 높다면 첫 응답 byte는 작아도 이점이 없습니다. 실패 유형을 retrieval miss, wrong synthesis, hook bypass와 stale index로 나눠 개선합니다.

SQLite는 workspace·session별로 분리하고 source handle, created·last access, model task와 retention을 둡니다. 다른 project hit가 섞이는 negative test와 secret redaction, process crash 뒤 orphan cleanup을 확인합니다. 사용자가 session 삭제를 요청했을 때 DB·backup에서 언제 제거되는지도 정합니다.

운영 dashboard에는 original/indexed/returned byte, billed token, retrieval·fallback, evidence miss 표본, DB error와 bypass를 표시합니다. 중요한 오류·결제·배포 결과처럼 짧고 비가역적인 응답은 virtualization에서 제외합니다. 98% 숫자를 목표로 세우면 필요한 정보까지 숨길 유인이 생기므로 품질 동등선 아래에서만 절감을 최적화합니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [공식 GitHub 저장소](https://github.com/mksglu/claude-context-mode)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [claude-relay-service를 팀 API Gateway로 써도 될까: 계정 풀링·v1.1.248 보안 리스크]({% post_url 2026-03-01-Why-Did-I-Just-Find-Out-About-This-An-Honest-Review-of-claude-relay-service %}) — Claude·OpenAI·Gemini 요청을 중계하는 CRS의 계정 풀링과 사용량 추적을 살펴보고, 약관·중앙 비밀 관리·v1.1.248 이하 인증 우회 이력을 점검합니다.
- [OV-Encoder는 비디오 토큰을 80% 줄여도 더 정확할까: 3.1~25% Residual 선택의 맹점]({% post_url 2026-02-17-OneVision-Encoder--Codec-Aligned-Sparsity-as-a-Foundational-Principle-for-Multimodal-Intelligence %}) — 코덱 잔차 영역만 토큰화하는 OV-Encoder의 +4.1% 성능과 최대 80% 토큰 절감이 성립하는 조건을 분석합니다.
- [Google Gemini 3.7 Flash 출시: 코딩 성능 향상과 50% 수준의 API 가격 할인]({% post_url 2026-08-14-google-gemini-3-7-flash-released-with-enhanced-coding-and-api-discount %}) — Google AI가 2026년 8월 13일 소프트웨어 엔지니어링과 에이전트 추론 성능을 끌어올린 Gemini 3.7 Flash 모델을 정식 출시했습니다. 100만 토큰 문맥 창과 최대 64K 출력 토큰을 지원하며…
<!-- internal-links:end -->

## 자주 묻는 질문

### Context Mode의 98% 절감은 API 청구 token도 98% 줄었다는 뜻인가요?

본문만으로는 단정할 수 없습니다. 반환 byte, tokenizer 입력, 검색·재확대와 여러 turn을 포함한 전체 청구량을 따로 측정해야 합니다.

### 압축 전후 품질 동등선은 어떻게 확인하나요?

정답 근거 line을 표시한 golden log·DOM에서 answer·citation recall과 반례 누락을 비교하고 실패하면 원문 확대 경로를 사용해야 합니다.

### hook를 우회하는 tool이 있으면 어떻게 해야 하나요?

도구별 interception test와 runtime log로 coverage를 확인하고 큰 output이 우회하면 해당 tool을 차단하거나 같은 virtualization wrapper에 넣어야 합니다.
