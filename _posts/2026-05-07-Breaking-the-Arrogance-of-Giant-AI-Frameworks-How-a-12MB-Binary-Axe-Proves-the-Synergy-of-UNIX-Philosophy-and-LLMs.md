---
layout: post
title: 'LLM 작업 하나에 LangChain이 꼭 필요할까? Axe 12MB CLI의 경계'
date: '2026-05-07 18:46:03'
categories: Tech
tags:
  - LLM
  - MCP
  - 온디바이스AI
  - AI에이전트
summary: '단발성 LLM 작업을 UNIX 파이프라인에 붙이는 Axe의 장점과, 워크플로 엔진·재시도·권한 관리가 필요한 순간 드러나는 한계를 함께 짚습니다.'
description: "Axe의 12MB Go CLI·stdin/stdout·TOML agent를 shell quoting·exit code, retry·idempotency, MCP capability·memory 보존과 workflow 승격 기준으로 검증합니다."
github_url: https://github.com/jrswab/axe
faq:
  - question: "Axe 12MB binary만 있으면 LLM pipeline을 12MB로 운영할 수 있나요?"
    answer: "아닙니다. 원격 API·local model, MCP process, 입력·memory와 cron·log 저장 비용은 binary 크기 밖에 남습니다."
  - question: "UNIX pipe로 연결하면 복잡한 agent framework보다 항상 단순한가요?"
    answer: "단계가 적을 때는 그렇지만 retry·branch·approval·state가 늘면 shell에 숨은 workflow가 생겨 전용 orchestration이 더 명확할 수 있습니다."
  - question: "Axe에 적합한 첫 업무는 무엇인가요?"
    answer: "versioned 입력을 읽어 schema가 있는 결과 하나를 만들고 외부 write가 없는 CI 요약·분류처럼 한 방향의 bounded task가 적합합니다."
image:
  path: https://opengraph.githubassets.com/1/jrswab/axe
  alt: "jrswab/axe GitHub 저장소 대표 이미지"
---

로그 요약처럼 입력과 출력이 분명한 한 번짜리 LLM 작업이라면 거대한 에이전트 프레임워크가 꼭 필요하지는 않지만, 상태·승인·재시도가 얽힌 업무라면 Axe만으로는 부족합니다.

선택 기준은 binary 크기보다 pipeline의 상태 수입니다. 한 입력을 읽어 한 결과를 내고 실패 시 전체를 다시 실행할 수 있다면 Axe와 shell의 투명성이 장점입니다. 여러 외부 변경을 조정하거나 사람이 중간 승인해야 한다면 책임을 어디에 둘지 먼저 정해야 합니다.

## Axe가 가벼운 이유는 무엇인가

[Axe](https://github.com/jrswab/axe)는 Go로 만든 약 12MB 단일 바이너리와 TOML 에이전트 설정을 중심으로 설명되는 CLI 도구입니다. 데몬이나 자체 스케줄러를 품는 대신 표준 입력과 표준 출력을 사용하고, 일정 실행은 cron에, 코드 변경 트리거는 Git hook에 맡기는 UNIX식 구성을 택합니다.

이 선택은 로그나 변경 내역처럼 이미 파일 또는 스트림으로 존재하는 입력을 LLM에 보내고 결과를 다시 파일로 받는 작업과 잘 맞습니다. Anthropic·OpenAI·Ollama 공급자를 설정할 수 있고, 선택적으로 타임스탬프가 붙은 마크다운 메모리와 MCP 연결도 사용할 수 있다는 것이 원문이 제시한 범위입니다.

다만 “12MB”는 바이너리 크기에 관한 설명이지 전체 실행 비용의 크기를 뜻하지 않습니다. 원격 모델을 고르면 API 호출이 필요하고, 로컬 모델을 고르면 별도의 모델 실행 환경이 필요합니다. 가벼운 실행기와 가벼운 전체 시스템은 같은 말이 아닙니다.

## 잘 맞는 작업과 맞지 않는 작업

Axe의 강점은 한 단계의 책임이 명확할 때 드러납니다. 입력을 읽고, 지정한 에이전트가 처리하고, 결과를 다음 UNIX 도구에 넘기는 구조라면 설정과 데이터 흐름을 눈으로 추적하기 쉽습니다. CI의 변경 검토, 정해진 형식의 문서 요약, 제한된 로그 분류처럼 시작과 종료가 선명한 작업이 후보입니다.

반대로 승인 뒤 수정하고, 실패하면 원인을 분류해 다른 단계로 되돌아가며, 여러 상태를 장기간 보존해야 하는 흐름은 Axe가 직접 제공하는 워크플로 엔진의 영역이 아닙니다. 쉘 스크립트나 외부 자동화가 예외 처리와 재시도를 떠안게 되므로, 단계가 늘어날수록 단순함의 이점이 줄어듭니다.

원문에는 TOML 에이전트 정의, 변경 내역을 리뷰 에이전트로 넘기는 파이프라인, cron 로그 감시, MCP 서버 연결 조각이 나옵니다. 그러나 버전, 설치 과정, 공급자 인증, 실제 MCP 서버 파일과 권한 설정이 빠져 있으므로 완전한 실행 안내가 아니라 구조를 보여주는 핵심 조각으로 읽어야 합니다.

## stdin·stdout 계약이 깨지는 경우를 막는다

표준 스트림은 조합하기 쉽지만 입력과 명령을 섞으면 shell injection과 parsing 오류가 생깁니다. 사용자 text를 command argument에 문자열 보간하지 말고 stdin 또는 명시적 file로 전달합니다. file name·branch와 model output을 `eval`하지 않으며 pipe의 각 단계에 timeout, 최대 byte와 허용 exit code를 둡니다. secret이 process argument나 debug log에 남지 않게 합니다.

stdout에는 사람이 읽는 설명과 다음 단계가 parse할 data를 섞지 않는 편이 좋습니다. JSON schema가 필요한 단계는 structured output을 검증하고 diagnostic은 stderr로 보냅니다. model이 markdown fence나 여분 문장을 붙이면 실패로 처리할지 정규화할지 계약을 명시합니다. `set -o pipefail`과 각 child exit status를 확인하지 않으면 앞 단계 실패가 마지막 command의 성공에 가려질 수 있습니다.

input에는 source hash, agent config·model version과 run ID를 붙이고 output과 함께 저장합니다. 동일 입력 재실행이 외부 side effect를 만들지 않는 순수 단계부터 시작합니다. API timeout 뒤 retry할 때 model 응답이 달라도 허용되는지, 결과를 cache할지와 최대 시도·backoff를 정합니다.

## 서브 에이전트와 MCP에서 비용이 커지는 지점

서브 에이전트 위임은 역할별 프롬프트를 나누는 데 유용하고, 깊이 제한은 호출이 끝없이 이어지는 일을 줄이는 장치입니다. 하지만 하나의 요청이 여러 하위 호출로 퍼지면 컨텍스트를 줄여 얻은 절감보다 모델 호출량이 더 커질 수 있습니다. 호출 깊이뿐 아니라 어떤 에이전트가 누구를 부를 수 있는지와 실행당 호출 수를 함께 정해야 합니다.

MCP 역시 연결 선언만으로 안전성이 완성되지는 않습니다. 원문 예시는 Node 기반 내부 DB MCP 서버를 설정에 붙이는 형태지만, 실제 서버 구현과 접근 권한, 실패 처리 방식은 제시하지 않습니다. 레거시 코드를 고치지 않고 연결할 수 있다는 편의와, 모델이 호출할 수 있는 도구의 범위를 검토해야 한다는 책임은 동시에 남습니다.

마크다운 메모리도 투명하게 읽을 수 있다는 장점이 있는 반면, 오래된 기록을 언제 제외할지와 민감한 결과를 어디까지 남길지는 운영자가 정해야 합니다. 파일 형식이 단순하다는 이유만으로 메모리 정책까지 단순해지는 것은 아닙니다.

MCP server command는 Axe가 호출하는 또 하나의 executable입니다. binary·package version, working directory, environment와 network를 고정하고 읽기·쓰기 tool을 나눕니다. 범용 filesystem·shell·database credential을 한 agent에 모두 주지 않습니다. MCP process가 hang하거나 잘못된 JSON을 내면 전체 pipe가 제한 시간 안에 종료되고 부분 output을 성공으로 넘기지 않아야 합니다.

서브 에이전트는 call graph로 표시합니다. 각 edge에 입력 byte·token, model, timeout과 호출 가능 횟수를 기록하면 fan-out 비용을 예측할 수 있습니다. A→B→A 순환을 depth 하나만으로 막기보다 허용 관계와 전체 request budget을 둡니다. 하위 결과에는 근거와 실패 상태를 보존해 상위 agent가 빈 문자열을 정답으로 요약하지 않게 합니다.

markdown memory는 repository별 directory와 owner를 정하고 secret scan, file permission과 retention을 적용합니다. model이 쓴 과거 결론을 새로운 지시로 신뢰하지 않으며 source·시각과 확인 상태를 붙입니다. Git으로 관리할 경우 민감한 log가 commit되지 않도록 별도 경계를 둡니다.

## 도입 전에 확인할 최소 기준

먼저 입력과 출력이 한 방향인지 확인합니다. 한 번 실행해 파일 하나를 만드는 수준이면 Axe의 구성이 잘 맞을 수 있습니다. 다음으로 실패한 호출의 재시도, 시간 제한, 부분 결과 처리 주체를 정합니다. 이 책임이 cron과 쉘에 흩어져도 관리 가능한지가 핵심입니다.

에이전트가 늘어날 때는 TOML 파일의 이름·소유자·변경 검토 규칙을 마련해야 합니다. 원문도 수십 개 설정이 쌓이면 의존성을 파악하기 어려운 “TOML 지옥”이 될 수 있다고 지적합니다. 서브 에이전트의 깊이와 비용 상한, MCP 도구 허용 범위, 메모리 보존 기간까지 문서화한 뒤 작은 비중의 작업부터 검증하는 편이 안전합니다.

결국 Axe는 LangChain이나 LangGraph를 모두 대체하는 제품이라기보다, LLM 호출을 조합 가능한 CLI 단계로 만들고 싶은 경우의 선택지입니다. 상태 머신이 필요하지 않은 작업에서는 단순함이 장점이지만, 복잡성을 없앤 것이 아니라 운영체제와 스크립트 쪽으로 옮긴 부분도 함께 계산해야 합니다.

## 언제 shell에서 workflow engine으로 옮길까

처음에는 input→Axe→schema validation→artifact의 네 단계로 만들고 golden input 20~50개에서 정답, schema 실패, token·p95 시간과 재시도를 측정합니다. cron 중복 실행과 process kill을 주입해 같은 artifact가 덮이거나 알림이 중복되지 않는지 확인합니다. model·TOML 변경은 code review와 version tag를 거칩니다.

분기·병렬 단계, 장시간 wait, 사람 승인, 보상 transaction과 여러 외부 write가 생기면 shell script line 수보다 상태 전이를 세어 봅니다. 어떤 단계가 완료됐고 누가 승인했는지 DB 없이 복구하기 어렵다면 전용 queue·workflow engine으로 옮길 신호입니다. Axe는 그 안의 한 LLM activity로 계속 사용할 수 있습니다.

비교표에는 개발 시작 시간뿐 아니라 장애 진단, replay, audit와 새 팀원이 변경한 시간을 포함합니다. 간단한 pipeline에서는 Axe가 명확할 수 있고, 복잡한 상태를 shell file 여러 개에 숨기면 framework보다 유지비가 커집니다. 목표는 의존성을 가장 적게 쓰는 것이 아니라 업무 상태를 가장 정확히 드러내는 것입니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [공식 GitHub 저장소](https://github.com/jrswab/axe)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [Gemini CLI에 파일 수정 권한을 줘도 될까: Plan Mode·MCP 안전선]({% post_url 2026-03-20-Why-the-Gemini-CLI-an-AI-Agent-in-the-Terminal-Disrupted-a-10-Year-Developers-Workflow-feat-MCP-Architecture-Deep-Dive %}) — Gemini CLI의 도구 반복, MCP 연결, Plan Mode와 ask_user를 기준으로 로컬 코딩 에이전트의 권한·컨텍스트·검토 범위를 정리합니다.
- [Qwen Code: 코드베이스 메모리와 MCP로 터미널에 구현한 완전 무료 AI 에이전트]({% post_url 2026-07-08-Qwen-Code-A-Completely-Free-AI-Agent-in-the-Terminal-Powered-by-Codebase-Memory-and-MCP %}) — Qwen Code는 알리바바 Qwen 팀이 개발한 오픈소스 터미널 AI 코딩 에이전트입니다. 파일 시스템과 영구적인 메모리 계층을 갖추고 있으며, MCP(Model Context Protocol)를 통해 외부 도구와 상호작용합니다…
- [SST OpenCode를 팀에 도입해도 될까: Model 선택·LSP·권한 검증]({% post_url 2026-03-02-Why-Did-I-Find-This-So-Late-An-Honest-Review-of-SST-OpenCode-the-Perfect-AI-Partner-for-Terminal-Loving-Developers %}) — SST OpenCode가 terminal TUI, provider 선택, session·LSP·AGENTS.md로 coding workflow를 구성하는 방식과 file·shell·MCP 권한, diff·test 검증 기준을…
<!-- internal-links:end -->

## 자주 묻는 질문

### Axe 12MB binary만 있으면 LLM pipeline을 12MB로 운영할 수 있나요?

아닙니다. 원격 API·local model, MCP process, 입력·memory와 cron·log 저장 비용은 binary 크기 밖에 남습니다.

### UNIX pipe로 연결하면 복잡한 agent framework보다 항상 단순한가요?

단계가 적을 때는 그렇지만 retry·branch·approval·state가 늘면 shell에 숨은 workflow가 생겨 전용 orchestration이 더 명확할 수 있습니다.

### Axe에 적합한 첫 업무는 무엇인가요?

versioned 입력을 읽어 schema가 있는 결과 하나를 만들고 외부 write가 없는 CI 요약·분류처럼 한 방향의 bounded task가 적합합니다.
