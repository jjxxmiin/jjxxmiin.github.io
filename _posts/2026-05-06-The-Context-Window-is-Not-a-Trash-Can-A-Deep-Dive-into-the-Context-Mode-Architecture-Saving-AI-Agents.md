---
layout: post
title: "AI 에이전트 로그가 컨텍스트를 다 먹는다면? Context Mode 도입 기준"
date: '2026-05-06 07:26:01'
categories: Tech
tags:
  - MCP
  - 벡터DB
  - AI에이전트
summary: "대용량 도구 출력을 로컬 SQLite에 보관하고 BM25로 필요한 조각만 돌려주는 Context Mode의 구조, 98% 수치와 정보 유실 위험을 정리합니다."
description: "Context Mode가 tool output을 SQLite FTS5·BM25로 가상화하는 방식을 retrieval recall·원본 확대, hook coverage·sandbox·보존과 end-to-end 비용으로 검증합니다."
github_url: https://github.com/mksglu/context-mode
faq:
  - question: "Context Mode를 쓰면 context token을 항상 98% 줄일 수 있나요?"
    answer: "아닙니다. 해당 수치는 특정 output 사례의 프로젝트 측정이며 데이터 크기·검색·재확대와 model 행동에 따라 전체 절감률이 달라집니다."
  - question: "BM25 검색만으로 중요한 log 한 줄을 놓치지 않나요?"
    answer: "보장할 수 없습니다. 어휘가 다르거나 희귀한 원인이 낮게 rank될 수 있어 query 확장, 주변 문맥과 원본 범위를 다시 읽는 fallback이 필요합니다."
  - question: "어떤 tool output을 먼저 가상화하는 편이 좋은가요?"
    answer: "크고 다시 조회할 수 있는 build log·DOM·JSON부터 시작하고 짧은 오류·최종 결과·비가역 작업 응답은 원문을 직접 전달하는 편이 안전합니다."
image:
  path: https://opengraph.githubassets.com/1/mksglu/context-mode
  alt: "mksglu/context-mode GitHub 저장소 대표 이미지"
---

**대용량 로그와 DOM이 에이전트 문맥을 잠식한다면 Context Mode처럼 원본을 로컬에 두고 필요한 조각만 검색하는 방식이 효과적일 수 있습니다.** 다만 압축 과정에서 결정적 한 줄을 놓치면 토큰은 줄어도 디버깅 정확도는 나빠집니다.

[mksglu/context-mode](https://github.com/mksglu/context-mode)는 MCP 도구와 에이전트 사이의 virtualization layer를 지향합니다. 원문 기준 Elastic License 2.0, subprocess sandbox, SQLite FTS5·BM25와 lifecycle hook이 핵심입니다. 14개 이상 도구 호환과 98% 절감은 프로젝트가 제시한 스냅샷 수치로 읽어야 합니다.

## 원본 출력은 샌드박스에 남기고 요약만 전달한다

PreToolUse가 curl·파일 읽기 같은 대용량 호출을 감지해 별도 subprocess로 보냅니다. 실행 결과 원본은 컨텍스트에 넣지 않고 로컬 저장소에 청킹·인덱싱합니다. PostToolUse는 짧은 요약과 검색 핸들만 모델에 돌려줍니다.

원문은 315KB 출력을 5.4KB로 줄인 사례를 소개합니다. 데이터 종류와 요약 규칙에 따라 압축률은 달라집니다. API 토큰이 98% 줄었다고 곧바로 전체 비용·지연도 같은 비율로 줄지는 않습니다.

모든 출력에 같은 정책을 적용하면 오히려 위험합니다. 수백 KB build log·DOM·API 목록은 저장 후 검색하기 좋지만, shell의 exit code, compiler 첫 오류와 결제 API의 최종 상태는 짧고 결정적이므로 즉시 context에 남겨야 합니다. tool별 크기, 재조회 가능성, 구조와 의사결정 중요도로 direct·virtualized 정책을 나눕니다.

요약에는 “성공” 같은 자연어만 두지 말고 tool, exit status, byte·line 수, 저장 handle, redaction과 잘린 범위를 구조화합니다. 모델이 결과가 비어 있는 것과 retrieval이 실패한 것을 구분할 수 있어야 합니다. 원본 handle은 session에서 안정적으로 유지하고 다음 질문 전에 파일이 정리되거나 다른 실행 결과를 가리키지 않게 합니다.

## FTS5·BM25는 가볍지만 동의어와 의미를 놓친다

SQLite 전문 검색은 별도 vector DB 없이 빠르게 키워드 관련 조각을 찾습니다. 세션 compact 전에 결정과 변경 이벤트를 snapshot으로 남기고, 다음 시작에 필요한 과거를 검색하는 데도 사용합니다. 원문은 파일·Git·오류 등 15개 이벤트 범주를 설명합니다.

어휘가 일치하지 않으면 핵심 로그가 순위 밖으로 밀릴 수 있습니다. “exception”만 기록됐는데 “error”로 찾거나, 변수명과 도메인 용어가 달라지면 의미 검색보다 취약합니다. 원본으로 다시 확대해 읽는 경로와 여러 검색어를 시도하는 fallback이 필요합니다.

구조가 있는 JSON과 test log는 청킹 경계를 고려해야 합니다. stack trace 한 frame씩 자르거나 JSON object가 둘로 갈리면 검색된 조각만으로 원인을 읽기 어렵습니다. record·test case·timestamp 구간을 유지하고 hit 앞뒤 문맥을 함께 반환합니다. 너무 많은 작은 chunk는 rank noise를 늘리고 너무 큰 chunk는 token 절감 이점을 줄이므로 실제 질문의 answer span으로 조정합니다.

검색 query를 모델이 한 번 잘못 만들었다고 “정보 없음”으로 끝내지 않습니다. error code·symbol·file path를 추출해 여러 query를 시도하고, hit가 낮으면 recent tail·head와 희귀 token 주변을 읽습니다. 최종 결론에 사용한 조각에서 원본 handle·offset으로 돌아갈 수 있어야 감사와 재현이 가능합니다.

## hook 지원과 격리 범위를 플랫폼마다 확인한다

원문의 JSON은 PreToolUse, PostToolUse, SessionStart hook을 연결하는 구조 예시일 뿐, 모든 IDE에서 그대로 동작하는 설치 파일이 아닙니다. hook 이름과 허용 형식이 달라질 수 있고, 일부 플랫폼은 호출을 가로채지 못할 수 있습니다.

subprocess에서 환경변수 60개 이상을 차단한다는 설명도 실제 허용 목록을 확인해야 합니다. 파일·네트워크·자식 프로세스 권한이 남아 있다면 “sandbox”라는 이름만으로 안전하지 않습니다. 로컬 DB에는 코드와 로그가 저장되므로 권한·암호화·삭제 주기도 필요합니다.

hook coverage는 정상 호출뿐 아니라 streaming, cancellation, timeout과 도구가 예외를 던진 경우까지 봅니다. PreToolUse만 실행되고 PostToolUse가 빠지면 process나 임시 파일이 남을 수 있고, 일부 결과가 원래 context와 DB에 동시에 들어가 절감률이 달라질 수 있습니다. tool call ID로 시작·종료·저장을 묶고 orphan cleanup을 운영합니다.

SQLite에는 source code, customer log와 secret이 섞일 수 있습니다. workspace·사용자별 DB를 분리하고 directory permission, backup 제외, retention과 secure deletion 요구를 정합니다. 검색 결과에 다른 repository·session이 섞이지 않도록 tenant key를 query에서 강제합니다. environment variable 차단과 별개로 tool output 자체의 secret redaction도 필요합니다.

## 도입 시험은 절감률과 누락률을 함께 잰다

실제 Playwright 실패 로그와 대형 JSON을 골라 원본을 준 에이전트, Context Mode를 쓴 에이전트의 토큰·지연·정답을 비교합니다. 고의로 드문 오류 한 줄을 섞어 검색이 찾아내는지 확인하고, 실패하면 원본 범위를 넓히도록 규칙을 둡니다.

[Model Context Protocol](https://modelcontextprotocol.io)은 연결 형식일 뿐 출력 압축을 자동 제공하지 않습니다. Context Mode의 가치는 도구 결과 수명 주기를 별도 계층으로 만든 데 있으며, 중요한 세부를 버리지 않는 관찰·복구 체계를 갖출 때만 실무 이득이 됩니다.

## retrieval 누락을 어떻게 계량할까

대표 session에서 정답에 필요한 line·JSON field를 미리 표시한 golden set을 만듭니다. 원문 전체, Context Mode 기본 검색, query 확장과 원본 fallback을 각각 실행해 answer accuracy, evidence recall, input token, tool 재호출, p50·p95 시간과 SQLite 크기를 비교합니다. token 절감만 아니라 정답 한 건당 전체 비용을 봅니다.

희귀 error 한 줄, 서로 다른 파일의 같은 symbol, 부정 표현과 100MB output을 주입합니다. 모델이 근거를 찾지 못했을 때 추측하지 않고 원본 범위를 넓히는지도 평가합니다. retrieval hit가 있지만 답이 틀린 경우와 hit 자체가 없는 경우를 나눠야 indexing·prompt 중 무엇을 고칠지 알 수 있습니다.

운영 경보에는 virtualization 대상 byte, direct 반환 비율, 검색 hit·원본 확대, DB write 실패, orphan과 session별 저장량을 둡니다. DB나 hook가 실패하면 중요한 짧은 결과는 직접 전달하고 큰 결과는 명시적으로 실패시켜야지 빈 요약으로 계속 진행하면 안 됩니다. 사용자가 원본을 열 수 없는 상태에서는 자동 결론의 confidence를 낮춥니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [공식 GitHub 저장소](https://github.com/mksglu/context-mode)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [agentmemory를 붙이면 AI가 어제를 기억할까: 검색·삭제·오염 테스트]({% post_url 2026-05-12-Seniors-Perspective-No-More-Nice-to-Meet-You-from-AI-How-agentmemory-Cures-LLMs-Short-Term-Amnesia %}) — agentmemory의 4단계 기억과 BM25·벡터 검색을 살펴보고, 장기 기억을 도입하기 전 정확도·오염·삭제·장애 복구를 검증하는 방법을 정리합니다.
- [Rowboat는 정말 로컬 AI 동료일까: Markdown 기억과 외부 API 경계]({% post_url 2026-02-17-Rowboat-The-Local-First-AI-Coworker %}) — Rowboat가 업무 기억을 Markdown으로 남기는 방식과 Gmail·OAuth·LLM API를 연결할 때 달라지는 프라이버시 경계를 살펴봅니다.
- [Qwen-Agent로 함수 호출·RAG·WebUI를 묶기 전 확인할 것]({% post_url 2026-03-06-Alibabas-Hidden-Weapon-Qwen-Agent-Uncovering-the-Pragmatic-Agent-Framework-Threatening-LangChains-Throne %}) — Qwen-Agent의 LLM·Tool·Memory/RAG·Agent 구조와 WebUI·코드 실행 기능을 살피고, 원문 예제의 가짜 응답·버전 누락·격리 한계를 짚습니다.
<!-- internal-links:end -->

## 자주 묻는 질문

### Context Mode를 쓰면 context token을 항상 98% 줄일 수 있나요?

아닙니다. 해당 수치는 특정 output 사례의 프로젝트 측정이며 데이터 크기·검색·재확대와 model 행동에 따라 전체 절감률이 달라집니다.

### BM25 검색만으로 중요한 log 한 줄을 놓치지 않나요?

보장할 수 없습니다. 어휘가 다르거나 희귀한 원인이 낮게 rank될 수 있어 query 확장, 주변 문맥과 원본 범위를 다시 읽는 fallback이 필요합니다.

### 어떤 tool output을 먼저 가상화하는 편이 좋은가요?

크고 다시 조회할 수 있는 build log·DOM·JSON부터 시작하고 짧은 오류·최종 결과·비가역 작업 응답은 원문을 직접 전달하는 편이 안전합니다.
