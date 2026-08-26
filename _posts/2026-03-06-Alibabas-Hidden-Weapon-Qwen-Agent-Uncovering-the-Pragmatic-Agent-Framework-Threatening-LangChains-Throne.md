---
layout: post
title: 'Qwen-Agent로 함수 호출, RAG, WebUI를 묶기 전 확인할 것'
date: '2026-03-06 18:22:25'
categories: Tech
tags:
  - Qwen
  - RAG
  - LLM
  - 멀티에이전트
  - AI에이전트
summary: 'Qwen-Agent의 LLM, Tool, Memory/RAG, Agent 구조와 WebUI, 코드 실행 기능을 살피고, 원문 예제의 가짜 응답, 버전 누락, 격리 한계를 짚습니다.'
description: 'Qwen-Agent의 LLM, Tool, Memory/RAG, Agent 구조와 WebUI, code interpreter를 살펴보고, 도구 schema, 격리, 검색 근거, routing 검증법을 설명합니다.'
github_url: https://github.com/QwenLM/Qwen-Agent
image:
  path: https://opengraph.githubassets.com/1/QwenLM/Qwen-Agent
  alt: "QwenLM/Qwen-Agent GitHub 저장소 대표 이미지"
faq:
  - question: 'Qwen-Agent 예제의 WeatherTool이 실제 날씨를 조회하나요?'
    answer: '원문 예제는 도구 등록 형식을 보여 주며 실제 API 호출은 빠지고 고정 문자열을 반환합니다. 운영 도구에는 인증, 입력 검증, timeout, 오류와 출처 시각이 필요합니다.'
  - question: 'Code interpreter를 function list에 넣으면 안전한 sandbox가 되나요?'
    answer: '도구 이름을 추가하는 것과 host 격리는 별개입니다. File, network, process, CPU, memory 제한과 실행 image, 출력 검사를 직접 구성하고 escape, 과부하 시험을 해야 합니다.'
  - question: 'GroupChat과 Router를 쓰면 단일 Agent보다 항상 좋아지나요?'
    answer: '역할과 정보가 실제로 다를 때는 도움이 될 수 있지만 같은 model이 같은 문맥을 반복하면 비용과 drift가 늘 수 있습니다. 단일 Agent 기준선과 정확도, 지연, token을 비교해야 합니다.'
---

Qwen-Agent는 Qwen 계열의 도구 호출, 문서 검색, 단일, 다중 에이전트와 Gradio WebUI를 한 프레임워크에서 시험할 수 있지만, 원문의 예제만으로 안전한 프로덕션 앱이 완성되지는 않습니다. 핵심은 LLM, Tool, Memory/RAG, Agent의 실패를 분리하고 코드 실행과 브라우저 권한을 서버에서 제한하는 것입니다. 도입 여부는 프레임워크 이름보다 실제 도구 성공률, 근거 정확도, 격리와 버전 유지비로 판단해야 합니다.

## 네 구성요소를 먼저 분리한다

LLM 래퍼는 모델 API 입출력을 맞추고, Tool은 Python 함수를 호출 가능한 스키마로 노출합니다. Memory & RAG는 PDF, Word, Excel 같은 문서를 파싱하고 청킹해 문맥으로 전달하는 역할로 소개됩니다. Agent 계층은 Assistant에서 GroupChat과 Router까지 실행 루프를 구성합니다.

이 구분을 유지하면 실패 원인을 찾기 쉽습니다. 모델이 잘못된 함수를 골랐는지, 인자가 틀렸는지, 검색 문서가 빠졌는지, 라우터가 잘못된 에이전트로 보냈는지를 각각 기록해야 합니다.

## 도구 등록 예제는 날씨 API가 아니다

원문의 WeatherTool 코드는 BaseTool과 register_tool을 이용해 description, parameters, call 메서드를 연결하는 형식을 보여줍니다. 실제 API 호출은 주석 처리되어 있고 항상 “맑음, 22도”라는 문자열을 반환합니다. 따라서 실행해도 현재 날씨를 조회하는 완전한 도구가 아닙니다.

실제 도구에는 입력 검증, 시간 초과, 오류 타입, 비밀키 보관과 허용된 목적지 목록이 필요합니다. 모델이 만든 JSON을 바로 파일이나 네트워크 작업에 넘기지 말고 스키마와 권한을 서버 쪽에서 다시 검사해야 합니다.

## WebUI와 코드 인터프리터의 범위를 구분한다

원문은 WebUI(bot).run()으로 Gradio 인터페이스를 띄우고 code_interpreter 같은 도구를 function_list에 추가하는 예를 제시합니다. 그러나 주식 분석 코드는 모델 식별자와 API 키 자리표시자만 있고 yfinance 설치, 네트워크 권한, 샌드박스 경계를 정의하지 않습니다. 완전 실행 예제로 볼 수 없습니다.

코드 실행 기능을 시험한다면 호스트 파일과 자격 증명에 접근하지 못하는지, 무한 실행과 메모리 초과가 종료되는지부터 확인해야 합니다. GUI가 뜬다는 사실과 실행 환경이 안전하다는 사실은 별개입니다.

## RAG와 BrowserQwen은 정확성을 보장하지 않는다

Qwen-Agent는 문서 파서와 BrowserQwen을 통해 파일이나 현재 브라우저 DOM을 문맥으로 활용하는 구성을 소개합니다. 표, 병합 셀, 스캔 PDF가 제대로 추출되는지, 페이지의 숨겨진 값이나 세션 정보가 불필요하게 전달되지 않는지 검증해야 합니다.

검색 결과가 들어가도 답이 근거를 따르는지 별도 채점이 필요합니다. 문서 버전과 인용 위치를 결과에 남기고, 브라우저에서는 읽기와 쓰기 권한을 분리하는 편이 안전합니다.

## 다른 프레임워크와 이름으로 경쟁시키지 않는다

“LangChain보다 가볍다” 같은 평가는 같은 기능, 버전, 의존성으로 측정해야 의미가 있습니다. 먼저 도구 하나, 문서 하나, 단일 에이전트로 성공률과 지연을 측정한 뒤 Router나 GroupChat을 추가해야 합니다. Qwen이 아닌 OpenAI 호환 엔드포인트를 쓸 때도 함수 스키마와 메시지 형식이 동일하게 작동하는지 확인해야 합니다.

원문의 API와 예시는 버전이 고정되지 않은 스냅샷입니다. 현재 설치와 호출법은 [GitHub 저장소](https://github.com/QwenLM/Qwen-Agent), [프로젝트 글](https://qwenlm.github.io/blog/qwen-agent-2405/), [Hugging Face 데모](https://huggingface.co/spaces/Qwen/Qwen-Agent)를 사용 시점에 대조해야 합니다.

## Tool schema는 어떤 계약을 가져야 하나

Description은 model이 도구를 고르는 근거이고 parameter schema는 서버가 허용할 입력의 경계입니다. “파일을 처리한다”처럼 넓은 설명보다 읽기 가능한 directory와 지원 확장자, 결과 형식을 적어야 합니다. Model이 optional field를 빠뜨리거나 enum 밖 값을 보내는 경우를 server에서 거부해야 합니다.

Tool return도 자유로운 문자열 하나보다 status, data, source, retryable error를 구분하는 편이 좋습니다. API가 실패했는데 자연어 error를 정상 결과로 오해하면 agent가 잘못된 답을 만듭니다. 외부 쓰기 tool에는 idempotency key와 dry-run, 승인 상태를 포함합니다.

실행 log에는 model이 만든 raw argument와 validation 뒤의 argument, tool latency와 결과를 남기되 secret은 가립니다. 같은 prompt를 반복해 tool 선택과 argument 안정성을 측정하고, 잘못된 호출이 실제 외부 action으로 이어지지 않는 test environment를 사용합니다.

## Code interpreter는 어떤 경계에서 시작해야 하나

별도 container나 microVM에서 read-only base image와 비어 있는 작업 directory를 사용합니다. Host home, Docker socket, cloud credential을 mount하지 않고 outbound network를 기본 차단합니다. 실행 시간, process 수, disk, memory와 output 크기를 제한해 무한 loop와 압축 폭탄을 막습니다.

사용자가 올린 파일 이름과 content도 신뢰하지 않습니다. Extension과 실제 형식을 확인하고 macro, archive 내부 path traversal을 검토합니다. 생성된 chart나 CSV를 다시 model에 전달할 때 formula injection과 hidden content가 없는지 확인해야 합니다.

완료 뒤 environment를 폐기하고 audit에 code hash, dependency, exit code와 artifact 목록을 남깁니다. Model이 계산한 숫자는 같은 code를 다시 실행해 재현되는지 확인할 수 있어야 합니다. UI에 결과만 보여 주고 실행 code를 숨기면 오류 검토가 어려워집니다.

## RAG는 문서를 어떤 단위로 검증할까

PDF, Word, Excel을 각각 대표하는 실패 문서를 고릅니다. PDF 읽기 순서, 표 header, 병합 cell과 sheet 경계가 보존되는지 보고, chunk에 원본 파일, 페이지, section metadata가 붙는지 확인합니다. 검색 성공과 parsing 성공을 분리합니다.

질문 세트에는 답이 있는 문서, 여러 문서가 충돌하는 경우, 답이 없는 경우를 포함합니다. Agent가 근거 passage를 인용하고 모르는 질문에서 추측하지 않는지 봅니다. Browser DOM에는 password input과 hidden token이 있을 수 있으므로 필요한 영역만 추출하고 form write는 별도 권한으로 둡니다.

Memory가 과거 문서를 cache한다면 document update와 삭제가 언제 반영되는지도 중요합니다. 오래된 chunk를 답에 사용했을 때 source version을 표시하고 index 재생성, rollback 절차를 마련합니다.

## Router와 GroupChat은 언제 추가할까

한 Agent가 도구 하나와 문서 하나를 안정적으로 처리한 뒤 역할을 분리합니다. Router는 query 유형을 나눌 때, GroupChat은 researcher, executor, reviewer처럼 산출물이 다른 역할에 의미가 있습니다. 단순한 날씨 조회에 여러 Agent를 붙이면 조율 비용만 커질 수 있습니다.

Routing 평가에는 잘못된 Agent 선택과 fallback, 분류 confidence를 기록합니다. GroupChat에는 최대 round와 최종 decision owner를 정하고 서로의 문장을 반복하는 cycle을 중단합니다. Reviewer가 code를 직접 수정하는지 검증만 하는지도 권한으로 구분합니다.

Framework 비교는 같은 model, tool, task와 관찰 가능성으로 맞춥니다. Package 수나 code 줄 수보다 성공률, p95 latency, tool 오류 복구, trace와 upgrade 시간을 봅니다. Qwen-Agent가 적합한지는 경쟁 이름이 아니라 현재 Qwen model과 필요한 UI, RAG, tool 경계를 얼마나 단순하게 구현하는지로 결정합니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [공식 GitHub 저장소](https://github.com/QwenLM/Qwen-Agent)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [AI 사용자 기억에 벡터 DB가 꼭 필요할까? Memori와 SQL의 경계]({% post_url 2026-03-05-Review-AI-Finally-Starts-Remembering-Me--A-Deep-Dive-into-the-SQL-Native-AI-Memory-Engine-Memori %}) — Memori가 LLM 호출 전후에 개입해 사실, 선호, 규칙을 SQL에 저장하는 구조와 대규모 문서 검색은 여전히 벡터 DB가 필요한 이유를 설명합니다.
- [PraisonAI: YAML과 파이썬 코드로 구축하는 자율형 멀티 AI 에이전트 오케스트레이션]({% post_url 2026-08-10-PraisonAI-Low-Code-Multi-Agent-AI-Framework-for-Autonomous-Workflows %}) — PraisonAI는 코드 몇 줄이나 간단한 YAML 설정만으로 자율형 멀티 AI 에이전트 시스템을 구축하고 배포할 수 있게 해주는 오픈소스 프레임워크입니다. 100개 이상의 LLM 지원, 메모리 관리, RAG, MCP 도구 연동을…
- [RAG 파이프라인이 너무 복잡하다면? Unbody GraphQL 도입 전 확인할 것]({% post_url 2026-03-02-Why-Didnt-I-Know-This-Sooner-Honest-Review--Deep-Dive-into-Unbody-the-Supabase-of-AI %}) — Unbody가 데이터 수집, 인덱싱, 추론, 서빙을 GraphQL로 묶는 구조와 빠른 MVP의 장점, 청킹, 임베딩을 세밀하게 제어하기 어려운 한계를 정리합니다.
<!-- internal-links:end -->

## 자주 묻는 질문

### Qwen-Agent 예제의 WeatherTool이 실제 날씨를 조회하나요?

원문 예제는 도구 등록 형식을 보여 주며 실제 API 호출은 빠지고 고정 문자열을 반환합니다. 운영 도구에는 인증, 입력 검증, timeout, 오류와 출처 시각이 필요합니다.

### Code interpreter를 function list에 넣으면 안전한 sandbox가 되나요?

도구 이름을 추가하는 것과 host 격리는 별개입니다. File, network, process, CPU, memory 제한과 실행 image, 출력 검사를 직접 구성하고 escape, 과부하 시험을 해야 합니다.

### GroupChat과 Router를 쓰면 단일 Agent보다 항상 좋아지나요?

역할과 정보가 실제로 다를 때는 도움이 될 수 있지만 같은 model이 같은 문맥을 반복하면 비용과 drift가 늘 수 있습니다. 단일 Agent 기준선과 정확도, 지연, token을 비교해야 합니다.
