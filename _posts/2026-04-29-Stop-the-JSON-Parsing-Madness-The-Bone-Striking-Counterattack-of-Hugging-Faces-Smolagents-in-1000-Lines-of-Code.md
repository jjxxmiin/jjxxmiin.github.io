---
layout: post
title: 'Smolagents CodeAgent가 JSON 파싱을 없앨까: Python 실행과 Sandbox 위험'
date: '2026-04-29 07:13:03'
categories: Tech
tags:
  - 파이썬
  - 웹개발
  - AI에이전트
summary: 'Smolagents가 JSON 도구 호출 대신 Python 코드로 여러 행동을 묶는 방식을 살펴보고, 줄어든 왕복 호출과 맞바꾼 임의 코드 실행·디버깅·격리 비용을 정리합니다.'
description: "Smolagents CodeAgent의 Python 도구 조합을 static validation, capability 제한, sandbox resource·network 경계와 JSON tool calling 비교 기준으로 검증합니다."
github_url: https://github.com/huggingface/smolagents
faq:
  - question: "CodeAgent를 쓰면 JSON parsing 오류가 완전히 사라지나요?"
    answer: "아닙니다. JSON 왕복 일부를 줄이는 대신 Python syntax·logic 오류와 실행 결과 schema 검증, sandbox 실패를 새로 다뤄야 합니다."
  - question: "additional_authorized_imports만 제한하면 생성 code가 안전한가요?"
    answer: "아닙니다. 노출한 tool과 object를 통한 file·network·외부 변경, 무한 loop와 자원 소모를 막으려면 별도 격리와 최소 capability가 필요합니다."
  - question: "CodeAgent에 적합한 첫 업무는 무엇인가요?"
    answer: "읽기 전용 tool 두세 개를 조건·반복으로 조합하는 bounded task부터 시작해 JSON 방식과 정확도, 왕복, token, 재시도와 총비용을 비교하는 것이 좋습니다."
image:
  path: https://opengraph.githubassets.com/1/huggingface/smolagents
  alt: "huggingface/smolagents GitHub 저장소 대표 이미지"
---

Smolagents의 CodeAgent는 여러 JSON tool call을 Python 한 조각으로 묶을 수 있지만, 파싱 문제가 사라지는 대신 모델이 만든 코드를 안전하게 실행하는 더 큰 책임이 생깁니다. 읽기 전용의 제한된 업무에서 JSON 방식보다 정확도·지연·재시도가 실제로 나을 때에만 외부 효과가 있는 도구로 넓혀야 합니다.

## ToolCallingAgent와 CodeAgent의 차이

JSON 기반 방식은 모델이 도구 이름과 인자를 구조화해 반환하고 프레임워크가 함수를 실행합니다. 여러 도구를 순서대로 쓰면 모델과 실행기 사이를 여러 번 왕복할 수 있습니다. CodeAgent는 `for`, `if`와 변수 같은 Python 제어 구조를 모델이 직접 작성해 한 실행 안에서 도구를 조합합니다.

페이지가 끝날 때까지 API를 반복 호출하거나 첫 결과에 따라 다음 함수를 고르는 작업에서는 왕복과 중간 토큰을 줄일 수 있습니다. Python traceback을 모델에 돌려줘 스스로 수정하게 할 수도 있습니다.

그러나 모델이 문법적으로 맞는 코드를 만들지 못하면 `IndentationError`나 이름 오류가 발생하고, 논리는 틀렸지만 실행은 되는 코드가 더 위험할 수 있습니다. “LLM은 코드에 익숙하다”는 설명은 팀의 모델과 업무에서 검증할 가설입니다.

## 원문의 할인 예제는 최소 구조를 보여 준다

예시는 `@tool`로 사용자 조회와 할인 계산 함수를 정의하고, `CodeAgent`에 두 도구와 `HfApiModel`을 전달합니다. 모델이 사용자 상태를 확인하고 활성 사용자에게 할인을 계산하는 짧은 Python을 생성하는 흐름입니다.

이 코드는 시점별 API 스냅샷입니다. smolagents 버전, 인증과 모델 접근, 설치, 오류·시간 제한과 격리 런타임이 빠져 있습니다. `additional_authorized_imports=["datetime", "math"]`는 허용 import 목록일 뿐 완전한 보안 샌드박스를 구성하는 한 줄이 아닙니다.

또한 예제 도구는 고정 딕셔너리를 반환해 안전하지만 실제 DB와 결제 도구는 외부 효과를 만듭니다. 도구 내부에서 호출자 권한, 입력 범위와 멱등성을 검증해야 하며, 생성 코드가 여러 번 함수를 호출해도 사고가 나지 않게 설계해야 합니다.

## 허용 import보다 실행 경계가 중요하다

임의 코드 실행은 파일, 프로세스, 네트워크, CPU와 메모리에 닿을 수 있습니다. import를 제한해도 이미 노출한 객체와 도구를 통해 권한을 우회할 수 있고, 무한 루프나 대량 호출이 자원을 소모할 수 있습니다.

원문은 로컬 인터프리터 외에 E2B, Modal과 Docker 같은 격리 선택지를 소개합니다. 어느 것을 쓰든 다음 경계를 직접 확인해야 합니다.

- 쓰기 가능한 파일과 작업 후 폐기 여부
- 외부 네트워크 허용 목록
- 전달되는 환경 변수와 비밀
- CPU·메모리·실행 시간·도구 호출 상한
- 생성 코드와 stdout·traceback 감사 로그
- 외부 효과가 있는 도구의 사람 승인

“코드를 믿지 말고 샌드박스를 믿는다”면 샌드박스가 실패하는 경우까지 시험해야 합니다.

## 작은 모델과 디버깅 비용을 함께 측정한다

원문은 8B·14B급 작은 모델이 JSON 스키마는 채워도 완전한 Python에서 더 자주 실패할 수 있다고 지적합니다. 큰 모델을 쓰면 코드 성공률이 오를 수 있지만 토큰 비용과 지연도 커집니다. 모델 크기별로 같은 작업의 실행 성공, 논리 정답, 재시도와 총 토큰을 비교해야 합니다.

생성 코드는 메모리에서 잠깐 실행돼 저장소의 일반 스택 트레이스보다 재현하기 어렵습니다. 매 시도에 모델 입력, 생성 코드, 도구 결과와 sandbox 이미지를 저장하지 않으면 같은 오류를 다시 만들기 어렵습니다. 자가 수정 횟수에 상한을 두고 넘으면 사람이 이어받게 해야 합니다.

## 반복 도구 조합부터 시험한다

첫 후보는 읽기 전용 API 두세 개를 조건과 루프로 묶는 작업입니다. 동일 업무를 JSON tool calling과 CodeAgent로 구현해 모델 왕복 수, 전체 지연, 토큰과 실패 유형을 비교하십시오. CodeAgent가 이길 때만 더 복잡한 ETL로 넓힙니다.

재고 확인 후 결제와 롤백처럼 트랜잭션이 필요한 흐름을 “Python 한 번”으로 묶었다고 원자적 작업이 되는 것은 아닙니다. 외부 서비스의 실패와 보상 트랜잭션은 기존 백엔드가 책임져야 합니다. Smolagents의 장점은 얇은 에이전트 코어와 유연한 도구 조합이지, JSON·보안·분산 시스템 문제의 제거가 아닙니다.

## 생성 코드와 도구 권한을 실행 전에 검사한다

CodeAgent의 실행을 `generate → validate → isolated run → result validate` 네 단계로 나누면 실패 위치가 보입니다. 실행 전 AST를 parsing해 금지된 import, dynamic evaluation, process·file 접근과 제한 없는 loop를 거부할 수 있습니다. 정적 검사는 완전한 보안 장벽이 아니지만 명백한 위험을 일찍 막습니다. 실제 격리에서는 filesystem, network, CPU·memory·wall time과 tool 호출 수를 별도로 제한합니다.

도구는 Python 함수 목록이 아니라 capability 목록으로 설계합니다. `get_customer`는 특정 ID의 읽기만, `calculate_discount`는 순수 계산만 허용하고, 결제·메일 같은 쓰기는 별도 승인 도구로 분리합니다. 생성 코드에 raw database connection이나 범용 HTTP client를 넘기면 함수 allowlist의 의미가 사라집니다. 입력 schema, 호출자 권한, rate limit과 반환 크기는 각 도구가 다시 검증해야 합니다.

외부 변경에는 plan과 commit 단계를 둡니다. 첫 실행은 대상·인자·예상 변경을 만들고 사람이 승인한 hash와 같을 때만 별도 executor가 실행합니다. timeout이나 traceback 뒤 모델이 코드를 고쳐 재시도할 때 이미 성공한 호출을 반복하지 않도록 idempotency key와 상태 조회를 사용합니다. 승인되지 않은 package 설치와 outbound domain은 code 내용과 무관하게 runtime이 막습니다.

비교 실험은 단순히 첫 응답의 token만 재면 안 됩니다. 20~50개의 대표 task에서 최종 정답, side effect 정확성, model 왕복, 생성·실행 token, 재시도, p95 지연과 사람이 복구한 시간을 기록합니다. syntax failure, 잘못된 tool argument, 논리 오류, sandbox 차단과 외부 service 오류를 나눠야 모델 교체와 framework 교체 중 무엇이 필요한지 알 수 있습니다.

모든 시도에는 task ID, model·prompt, 생성 code, tool input·output hash, sandbox image와 종료 이유를 보존합니다. 민감한 값은 원문 대신 redacted 참조를 남기되 재현에 필요한 version은 유지합니다. 같은 입력을 replay할 수 없거나 code가 log에 남지 않는 구성은 장애 분석과 감사가 어려우므로 운영 범위를 넓히지 않는 편이 안전합니다.

운영 전 회귀 세트에는 정상 경로만 넣지 않습니다. 도구가 빈 값을 반환하는 경우, schema가 바뀐 경우, 같은 쓰기 요청이 재시도되는 경우, 생성 코드가 제한 시간에 걸리는 경우를 포함해야 합니다. JSON 방식과 CodeAgent 방식에 동일한 실패 입력을 주고 잘못된 외부 변경, 복구 시간과 사람이 개입한 비율을 비교하면 단순 성공률로 숨겨진 비용이 보입니다. 모델이나 smolagents 버전을 올릴 때 이 세트를 다시 통과시키고, 권한이 추가된 도구는 기존 승인 범위와 분리해 검토해야 합니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [공식 GitHub 저장소](https://github.com/huggingface/smolagents)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [AI 코딩 에이전트에 터미널 권한을 줘도 될까? Goose의 안전 경계]({% post_url 2026-03-15-Beyond-Code-Suggestions-Taking-the-Keyboard-Dissecting-Blocks-Open-Source-AI-Agent-Goose %}) — Block의 오픈소스 에이전트 Goose가 명령 실행과 MCP 도구를 연결하는 방식을 살피고, 샌드박스·최소 권한·모델 선택의 실무 기준을 정리합니다.
- [oh-my-claudecode의 32개 Agent는 필요한가: Routing·State·검증 비용]({% post_url 2026-04-21-10-Year-Seniors-View-Is-Claude-Code-Dead-The-Shocking-Reality-and-Limits-of-oh-my-claudecode-Orchestrating-32-AIs %}) — oh-my-claudecode가 역할·model routing·hook·state로 코딩 작업을 나누는 구조를 살펴보고, 실제 병렬성·검증 독립성·token·복구·권한 한계를 평가합니다.
- [DeepSeek-TUI를 coding agent로 써도 될까: Terminal·Shell 권한·검증 기준]({% post_url 2026-05-03-Turn-Off-Copilot-and-Cursor-How-DeepSeek-TUI-in-the-Terminal-Proves-the-True-Essence-of-Engineering %}) — DeepSeek-TUI가 terminal에서 model·file·shell·MCP를 연결하는 구조를 살펴보고, native 기능 주장, context 압축, fan-out 비용과 자동 실행 권한의 위험을 검증합니다.
<!-- internal-links:end -->

## 자주 묻는 질문

### CodeAgent를 쓰면 JSON parsing 오류가 완전히 사라지나요?

아닙니다. JSON 왕복 일부를 줄이는 대신 Python syntax·logic 오류와 실행 결과 schema 검증, sandbox 실패를 새로 다뤄야 합니다.

### additional_authorized_imports만 제한하면 생성 code가 안전한가요?

아닙니다. 노출한 tool과 object를 통한 file·network·외부 변경, 무한 loop와 자원 소모를 막으려면 별도 격리와 최소 capability가 필요합니다.

### CodeAgent에 적합한 첫 업무는 무엇인가요?

읽기 전용 tool 두세 개를 조건·반복으로 조합하는 bounded task부터 시작해 JSON 방식과 정확도, 왕복, token, 재시도와 총비용을 비교하는 것이 좋습니다.

참고 자료:

- [Hugging Face 원문](https://huggingface.co/docs/smolagents)
- [GitHub 저장소](https://github.com/huggingface/smolagents)
- [deeplearning.ai 원문](https://www.deeplearning.ai/short-courses/building-code-agents-with-hugging-face-smolagents)
- [medium.com 원문](https://medium.com/@zennura26/exploring-smolagents-building-intelligent-agents-with-hugging-face-c45de65373aa)
