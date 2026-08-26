---
layout: post
title: 'agentmemory를 붙이면 AI가 어제를 기억할까: 검색·삭제·오염 테스트'
date: '2026-05-12 18:53:07'
categories: Tech
tags:
  - AI보안
  - AI코딩
  - MCP
  - 벡터DB
  - AI에이전트
summary: 'agentmemory의 4단계 기억과 BM25·벡터 검색을 살펴보고, 장기 기억을 도입하기 전 정확도·오염·삭제·장애 복구를 검증하는 방법을 정리합니다.'
description: "agentmemory의 Working·Episodic·Semantic·Procedural memory와 BM25+vector를 promotion·stale provenance, namespace·privacy 삭제와 장애 fallback 기준으로 검증합니다."
github_url: https://github.com/rohitg00/agentmemory
faq:
  - question: "agentmemory를 설치하면 코딩 agent가 이전 session을 정확히 기억하나요?"
    answer: "보장하지 않습니다. 검색은 가능해도 잘못된·오래된 memory가 주입될 수 있어 source·commit·validity와 정답 question set을 검증해야 합니다."
  - question: "실패한 해결 절차가 Procedural Memory에 저장되면 어떻게 하나요?"
    answer: "자동 승격을 제한하고 test·사람 승인 상태를 붙이며 실패·폐기된 절차를 검색에서 제외하고 파생 index까지 정정·삭제해야 합니다."
  - question: "memory server 장애 때 agent는 어떻게 동작해야 하나요?"
    answer: "업무 위험에 따라 memory 없는 제한 mode나 fail-closed를 선택하고 명시적으로 표시하며 timeout·복구 뒤 stale 결과를 최신처럼 쓰지 않아야 합니다."
image:
  path: https://opengraph.githubassets.com/1/rohitg00/agentmemory
  alt: "rohitg00/agentmemory GitHub 저장소 대표 이미지"
---

agentmemory는 세션을 넘긴 프로젝트 맥락을 다시 찾는 데 도움을 줄 수 있지만, 틀린 기억을 오래 보존하는 문제까지 자동으로 해결해 주지는 않습니다. Memory 승격·source commit·validity와 namespace·삭제를 설계하고 server 장애에서 제한 mode를 분명히 할 때에만 장기 context 후보가 됩니다.

[agentmemory](https://github.com/rohitg00/agentmemory)는 코딩 에이전트의 활동을 수집해 Working, Episodic, Semantic, Procedural 네 단계로 정리하고 BM25와 벡터 검색을 함께 쓰는 구조로 소개됩니다. 원문의 정확도와 토큰 절감 수치는 특정 버전과 벤치마크 결과이므로 실제 저장소에서 조건을 확인하고 자체 작업으로 재검증해야 합니다.

## 네 단계는 보존 기간이 아니라 기억의 역할이다

Working Memory에는 현재 세션의 도구 호출과 오류처럼 즉시 필요한 정보가 들어갑니다. Episodic Memory는 무엇을 언제 시도했는지, Semantic Memory는 프로젝트 규칙과 구조, Procedural Memory는 문제를 해결한 순서를 담습니다. 대화를 통째로 벡터 DB에 넣는 것보다 검색 목적을 나눌 수 있다는 장점이 있습니다.

하지만 실패한 해결법이 절차 기억으로 승격되거나 임시 결정이 프로젝트 규칙으로 굳으면 이후 세션을 계속 오염시킵니다. 기억이 어느 단계로 이동했는지와 원문 근거를 볼 수 있어야 하며, 확정 규칙은 사람이 승인하도록 구분하는 편이 안전합니다.

승격 rule을 명시합니다. Working event는 session 종료와 함께 만료하고, Episodic에는 task·시각·결과를 남깁니다. Semantic rule은 repository 문서·여러 성공 task 또는 사람 승인이 있을 때만 확정하며 Procedural sequence는 test·artifact가 성공한 경우에만 후보가 됩니다. Model이 “중요하다”고 말한 것만으로 장기 memory가 되지 않게 합니다.

각 memory에 source message·tool, repository·branch·commit, created·verified·valid-until, owner와 status를 붙입니다. 새 code에서 file이 삭제되거나 rule이 바뀌면 해당 commit에 묶인 memory를 stale로 표시합니다. 과거 근거를 보존하더라도 현재 답에 넣을 때는 최신 원본과 충돌 여부를 확인합니다.

## 코드 검색에는 하이브리드가 필요한 이유

벡터 검색은 ‘인증을 왜 이렇게 설계했지’ 같은 의미 질문에 유리하지만 비슷한 클래스 이름을 혼동할 수 있습니다. BM25는 정확한 파일명, 변수명과 오류 코드를 찾는 데 강합니다. 두 결과를 합치면 자연어 맥락과 식별자를 함께 찾을 수 있지만, 잘못된 상위 결과가 사라지는 것은 아닙니다.

도입 전 정답이 알려진 질문 묶음을 만드세요. 현재 규칙, 폐기된 규칙, 비슷한 이름, 어제의 실패와 성공 절차를 각각 질문하고 반환된 기억의 출처와 시점을 기록합니다. 원문의 LongMemEval-S 95.2%나 92% 토큰 절감 주장보다 우리 저장소의 정답 검색률과 잘못 주입된 토큰 수가 더 중요한 지표입니다.

BM25와 vector 결과를 합치는 weight·dedup·top-k는 validation set에서 정하고 test에는 고정합니다. Exact symbol은 BM25, 자연어 의도는 vector가 유리할 수 있지만 동일 이름의 다른 module·branch를 namespace로 먼저 제한해야 합니다. Score가 낮거나 source를 확인할 수 없는 경우 빈 결과를 반환할 수 있어야 합니다.

answer quality와 retrieval을 분리합니다. 필요한 memory가 top-k에 있었는데 model이 무시한 경우, stale memory가 상위에 뜬 경우와 정답 자체가 저장되지 않은 경우를 나눕니다. Recall@k, stale·cross-project rate, evidence precision, injected token과 final test 성공을 기록해야 index·promotion·prompt 중 고칠 지점을 찾습니다.

## 자동 캡처에는 삭제와 경계가 따라야 한다

훅으로 파일 편집과 도구 결과를 자동 수집하면 편하지만 비밀 키, 고객 데이터, 개인 메모도 함께 들어갈 수 있습니다. 캡처할 경로와 파일 형식을 허용 목록으로 제한하고 저장 데이터의 암호화, 사용자·프로젝트별 네임스페이스와 보존 기간을 정해야 합니다.

삭제 도구가 있다는 사실만 확인하지 말고 한 기억을 지운 뒤 검색 인덱스, 압축본과 백업에서도 사라지는지 시험합니다. 틀린 아키텍처 결정을 새 결정으로 교체했을 때 오래된 기억이 다시 노출되지 않는지도 중요합니다. 팀이 하나의 메모리 서버를 공유한다면 다른 저장소의 결과가 섞이지 않는지 반드시 확인해야 합니다.

자동 capture 전에 allowlist와 redaction을 적용합니다. `.env`, key·token pattern, customer fixture와 generated binary는 수집하지 않고 tool output size를 제한합니다. User·organization·repository와 branch를 storage key에서 강제하고 client가 다른 namespace를 query parameter로 바꿀 수 없게 server auth와 결속합니다.

정정은 새 memory를 추가하는 것만으로 끝나지 않습니다. 이전 memory를 superseded로 연결하고 search index·summary와 procedural derivative를 다시 계산합니다. 사용자가 삭제하면 raw event, vector, keyword index, cache와 backup retention을 따라가며 완료 상태를 기록합니다. 감사에는 원문 secret 없이 action·scope·actor와 timestamp를 남깁니다.

## 서버가 없어도 에이전트는 안전하게 실패해야 한다

원문은 로컬 REST 서버와 MCP 도구, 여러 훅을 연결하는 구성을 설명합니다. 이 서버의 지연이나 장애가 에이전트 시작을 막았던 과거 버전 사례도 언급합니다. 메모리 시스템이 응답하지 않을 때 작업을 중단할지, 기억 없이 제한 모드로 진행할지 정책을 먼저 정해야 합니다.

첫 파일럿에서는 읽기 전용 검색만 켜고 자동 저장은 검토 대기열로 보냅니다. 검색 적중률, 오래된 기억의 비율, 삭제 소요 시간, 장애 시 시작 지연을 일주일간 재면 ‘어제 하던 일’을 되살리는 이득과 기억 관리 비용을 함께 볼 수 있습니다.

## 장애와 오염을 어떻게 주입할까

Memory server timeout, partial write, index 지연과 오래된 replica를 만들고 agent startup·search가 제한 시간 안에 반응하는지 봅니다. 실패를 빈 검색으로 위장하지 말고 “memory unavailable” 상태를 trace와 UI에 표시합니다. Code 변경처럼 원본 repository를 읽을 수 있는 업무는 제한 mode로 계속할 수 있지만 compliance rule이 memory에만 있다면 fail-closed가 맞습니다.

의도적으로 틀린 procedure, 폐기된 API, 다른 project의 같은 class와 prompt injection 문장을 저장합니다. 검색·agent가 이를 현재 지시로 따르지 않고 provenance·status를 확인하는지 평가합니다. 자동 promotion queue에서 사람 거부와 수정이 실제 serving index에 반영되는 시간도 측정합니다.

pilot metric에는 memory question 정확도, stale·cross-namespace 0건, source citation, task test, 저장·검색 p95, token, review queue·삭제와 장애 복구를 둡니다. Recent markdown summary와 repository search 같은 단순 기준선보다 반복 가능한 이득이 없으면 네 단계 memory의 운영 복잡성을 추가하지 않습니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [공식 GitHub 저장소](https://github.com/rohitg00/agentmemory)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [AI 에이전트 로그가 컨텍스트를 다 먹는다면? Context Mode 도입 기준]({% post_url 2026-05-06-The-Context-Window-is-Not-a-Trash-Can-A-Deep-Dive-into-the-Context-Mode-Architecture-Saving-AI-Agents %}) — 대용량 도구 출력을 로컬 SQLite에 보관하고 BM25로 필요한 조각만 돌려주는 Context Mode의 구조, 98% 수치와 정보 유실 위험을 정리합니다.
- [DeepTutor: 지식 그래프와 멀티 에이전트 기반의 맞춤형 AI 학습 플랫폼]({% post_url 2026-08-12-DeepTutor-Agent-Native-Lifelong-Personalized-Tutoring-Framework-by-HKU %}) — 홍콩대학교 Data Intelligence Lab이 개발한 오픈소스 AI 튜터링 플랫폼 DeepTutor의 이중 루프 아키텍처, 6대 멀티 에이전트 메커니즘, 지식 그래프 RAG 및 설치와 활용법을 상세히 분석합니다.
- [OpenHuman이 Slack·GitHub를 로컬 기억으로 모아도 될까: OAuth·동기화·가짜 기억]({% post_url 2026-05-13-What-We-Wanted-Wasnt-a-Chatbot-But-a-Clone-of-Our-Brain-Deep-Dive-into-OpenHuman-Architecture %}) — OpenHuman이 Rust·Tauri desktop에서 SaaS 활동을 markdown·SQLite memory로 수집한다는 구조를 살펴보고, OAuth·egress·압축 손실·오래된 기억과 삭제 조건을 정리합니다.
<!-- internal-links:end -->

## 자주 묻는 질문

### agentmemory를 설치하면 코딩 agent가 이전 session을 정확히 기억하나요?

보장하지 않습니다. 검색은 가능해도 잘못된·오래된 memory가 주입될 수 있어 source·commit·validity와 정답 question set을 검증해야 합니다.

### 실패한 해결 절차가 Procedural Memory에 저장되면 어떻게 하나요?

자동 승격을 제한하고 test·사람 승인 상태를 붙이며 실패·폐기된 절차를 검색에서 제외하고 파생 index까지 정정·삭제해야 합니다.

### memory server 장애 때 agent는 어떻게 동작해야 하나요?

업무 위험에 따라 memory 없는 제한 mode나 fail-closed를 선택하고 명시적으로 표시하며 timeout·복구 뒤 stale 결과를 최신처럼 쓰지 않아야 합니다.
