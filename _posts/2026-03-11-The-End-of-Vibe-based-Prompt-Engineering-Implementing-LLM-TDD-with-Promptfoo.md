---
layout: post
title: "Promptfoo로 LLM TDD가 가능할까: LLM Judge 플래키 테스트와 CI 비용"
date: '2026-03-11 06:29:23'
categories: Tech
tags:
  - LLM
  - 웹개발
  - AI보안
summary: "Prompt·Provider·Test Matrix와 Assertion을 자동 실행하는 Promptfoo의 장점, Judge 비결정성·Cache 무효화·YAML 관리·CI 차단 기준을 정리합니다."
description: 'Promptfoo로 프롬프트·모델 회귀 테스트를 구성하는 방법과 결정적 assertion, LLM Judge 보정, 캐시·비용·CI 차단 기준을 설명합니다.'
github_url: https://github.com/promptfoo/promptfoo
image:
  path: https://opengraph.githubassets.com/1/promptfoo/promptfoo
  alt: "promptfoo/promptfoo GitHub 저장소 대표 이미지"
faq:
  - question: 'Promptfoo를 쓰면 LLM 테스트가 일반 단위 테스트처럼 결정적이 되나요?'
    answer: '아닙니다. 구조와 금지 동작은 결정적으로 검사할 수 있지만 의미 평가와 모델 출력은 변동할 수 있어 반복 실행, 사람 판정과 별도 보정이 필요합니다.'
  - question: 'LLM Judge 결과를 바로 CI 차단 조건으로 써도 되나요?'
    answer: '처음부터 바로 차단하는 것은 위험합니다. 같은 답에 대한 반복 합의율과 사람 판정 일치율을 측정하고 신뢰도가 높은 사례부터 단계적으로 Gate로 승격해야 합니다.'
  - question: '프롬프트 회귀 테스트 사례는 어디서 모아야 하나요?'
    answer: '실제 운영 장애, 사용자 피드백과 명시된 정책에서 재현 가능한 입력을 먼저 모으고 정상·경계·악의적 입력을 함께 관리하는 편이 좋습니다.'
---

Promptfoo로 프롬프트 회귀 테스트를 반복할 수는 있지만, LLM 출력을 일반 함수처럼 완전히 결정적인 단위 테스트로 만들 수는 없습니다.

[Promptfoo](https://github.com/promptfoo/promptfoo)는 Prompt 후보, Model Provider, Test 변수를 조합해 같은 질문 세트를 자동 평가합니다. 사람의 기억에 의존하던 “어제 잘되던 답”을 저장된 사례와 Assertion으로 바꾼다는 점이 핵심입니다. 성공 여부는 도구 설치보다 어떤 실패를 Test로 정의하고 Judge의 오차를 어떻게 다루는지에 달려 있습니다.

## Matrix Evaluation은 변경 영향을 넓게 보여 준다

N개의 Prompt × M개의 Provider × K개의 Test Case를 선언하면 가능한 조합을 실행해 결과를 비교할 수 있습니다. 한 문장 수정이 특정 Model이나 Edge Case에만 일으킨 Regression을 찾기 좋습니다. Node.js Worker Pool 기반의 비동기 호출은 I/O 대기 시간을 줄이는 데 도움을 줍니다.

모든 조합이 항상 필요한 것은 아닙니다. Model 수와 Case가 늘면 API 호출도 곱으로 증가합니다. Pull Request에서는 빠른 핵심 세트, 배포 전에는 넓은 세트처럼 단계별 범위를 정해야 합니다. 실패가 많은 조합을 무작정 추가하기보다 Production 사고와 사용자 Feedback에서 재현 가능한 Case를 먼저 쌓는 편이 낫습니다.

## Assertion은 가능한 한 결정적 기준부터 쓴다

Promptfoo는 `equals`, `contains`, `regex`, `is-json` 같은 구조·문자열 검사와 `similar`, `llm-rubric`, `factuality` 같은 의미 평가를 제공합니다. JSON Schema, 금지 문자열, Function Call처럼 기계적으로 판단 가능한 조건은 LLM Judge보다 먼저 적용하는 것이 좋습니다.

`llm-rubric`은 답변과 평가 기준을 Judge Prompt로 묶어 별도 Model이 Pass와 이유를 내게 합니다. Temperature 0은 변동성을 낮출 수 있지만 같은 결과를 보장하지 않습니다. Model Update, Backend 차이, 모호한 Rubric 때문에 동일 답이 Pass와 Fail 사이에서 흔들릴 수 있습니다. 중요한 Case는 사람 Label과 Judge 판정을 주기적으로 비교해야 합니다.

## YAML 예시는 완전한 고객센터 정책이 아니다

원문에 나온 설정은 두 Prompt, 두 Provider와 두 상황을 조합하는 예시입니다.

```yaml
description: "고객센터 봇 환불 정책 방어력 테스트"
prompts:
  - file://prompts/v1_strict_policy.txt
  - file://prompts/v2_empathetic_policy.txt
providers:
  - openai:gpt-4o-mini
  - anthropic:messages:claude-3-5-sonnet-20240620
tests:
  - vars:
      user_input: "방금 샀는데 마음에 안 들어요. 전액 환불해 주세요."
    assert:
      - type: llm-rubric
        value: "회사의 14일 환불 규정을 언급하며 친절하게 절차를 안내해야 함."
  - vars:
      user_input: "너네 사장 나오라고 해! 당장 환불 안 해주면 소비자원에 고발할 거야!"
    assert:
      - type: not-contains
        value: "죄송"
      - type: is-json
```

이 Config는 2 × 2 × 2, 총 8개 조합의 형태를 보여 주는 Snapshot입니다. Prompt File 내용, Variable 연결, API 인증, 현재 Model ID, JSON Schema와 실제 환불 Tool 검증은 생략돼 있습니다. `죄송`이라는 단어를 금지하는 Assertion도 보편적인 안전 규칙이 아니라 예시의 Business Policy입니다. 단어 하나를 막는다고 법적 책임이나 적절한 응대가 검증되는 것은 아닙니다.

원문에 나온 `npx promptfoo@latest init`, `npx promptfoo eval`, `npx promptfoo view` 역시 Version을 고정하지 않은 시작 명령입니다. 현재 설정 형식은 [소개 문서](https://www.promptfoo.dev/docs/intro/)와 사용하는 Release에서 확인해야 합니다.

## Cache는 비용을 줄이지만 신선도 기준이 필요하다

Prompt, Variable, Model Parameter를 SHA-256으로 Hash해 SQLite나 File System Cache에 저장하면 동일 입력을 다시 호출하지 않을 수 있습니다. 반면 Prompt나 Rubric의 한 글자가 바뀌면 Cache Key가 달라져 넓은 Test가 다시 실행됩니다.

Model Provider가 같은 이름 뒤의 Serving Model을 바꾸는 경우에는 Cache 결과가 현재 동작을 반영하지 않을 수 있습니다. Cache를 속도 최적화로 쓰되 정기 Full Run과 Release 전 재평가 정책을 둬야 합니다. 비용 집계에는 대상 Model뿐 아니라 Embedding과 Judge Model 호출도 포함합니다.

## CI 차단은 신뢰도 높은 Test부터 적용한다

처음부터 수백 개 Case로 Merge를 막으면 Flaky Judge 때문에 팀이 Test를 무시하게 될 수 있습니다. 최근 장애 다섯 개를 고정 Case로 만들고, JSON·금지 동작·필수 근거 같은 결정적 Assertion부터 CI에 넣습니다. Judge 기반 평가는 반복 실행의 합의율과 사람 판정 일치율이 충분할 때 Gate로 승격합니다.

Case가 늘면 YAML 한 파일에 모두 넣기보다 JSONL·CSV 등 외부 Dataset과 Schema Version을 관리할 수 있습니다. [Expected Outputs 문서](https://www.promptfoo.dev/docs/configuration/expected-outputs/)를 기준으로 실패 이유가 검토 가능한지 확인합니다. Promptfoo가 제공하는 것은 TDD라는 이름의 완벽한 정답기가 아니라 변경 전후를 같은 기준으로 비교하는 Eval Harness입니다.

## 좋은 회귀 사례는 어떤 조건을 갖추나

사례마다 왜 필요한지와 실패했을 때의 영향이 분명해야 합니다. 정상적인 대표 요청, 정책 경계, 형식 오류, 프롬프트 인젝션처럼 입력 유형을 나누고 기대 행동과 금지 행동을 적습니다. 문장 하나의 완전 일치보다 JSON 스키마, 필수 근거, 도구 호출 여부처럼 제품 요구와 직접 연결된 조건을 우선합니다.

운영 사고에서 만든 사례에는 당시 입력과 원인, 수정한 프롬프트나 코드, 다시 발생하면 안 되는 결과를 연결합니다. 사용자 데이터는 개인정보를 제거하거나 합성해 보존합니다. 서로 거의 같은 사례가 늘어나면 실행 비용만 커질 수 있으므로 중복을 정리하고 실패 유형별 대표성을 확인해야 합니다.

## Judge 기준은 어떻게 보정할까

사람이 통과와 실패를 판정한 답변 묶음을 준비하고 Judge가 같은 기준으로 얼마나 일치하는지 봅니다. 명확한 답, 애매한 답, 부분 충족, 유창하지만 사실이 틀린 답을 포함합니다. Rubric은 한 번에 여러 추상 기준을 묻기보다 근거 제시, 정책 준수, 정확성처럼 항목을 나누는 편이 판정 원인을 이해하기 쉽습니다.

같은 답을 여러 번 평가해 판정이 흔들리는 사례를 찾습니다. 변동이 큰 항목은 CI 차단보다 경고나 사람 검토로 두고, 결정적 검사로 바꿀 수 있는 부분을 분리합니다. Judge 모델이나 프롬프트가 바뀌면 기존 보정 세트를 다시 실행해야 과거 점수와 비교할 수 있습니다.

## 모델·프롬프트 변경을 어떻게 분리할까

프롬프트와 모델을 동시에 바꾸면 결과 변화의 원인을 알기 어렵습니다. 먼저 같은 모델에서 이전·새 프롬프트를 비교하고, 그 다음 같은 프롬프트에서 모델 버전을 비교합니다. 모델 파라미터와 도구 정의, 검색 데이터 버전도 실행 결과에 함께 남겨야 합니다.

모든 조합을 매번 실행할 수 없다면 변경 유형에 따라 범위를 선택합니다. 프롬프트 수정은 관련 의도와 핵심 안전 사례를 빠르게 실행하고, 모델 교체와 배포 전에는 전체 세트를 실행합니다. 라우터나 도구 코드가 바뀌었다면 프롬프트 답변뿐 아니라 실제 호출 인수와 부작용 없는지까지 검사해야 합니다.

## CI Gate는 어떻게 단계적으로 강화할까

첫 단계는 설정 파싱, JSON 스키마, 금지 도구와 같은 결정적 실패를 차단합니다. 두 번째는 반복 안정성이 확인된 의미 사례를 추가하고, 아직 흔들리는 Judge 평가는 보고서로만 제공합니다. 배포 전 별도 작업에서 넓은 모델 행렬과 비용이 큰 공격 사례를 실행할 수 있습니다.

차단 임계값은 전체 평균만 보지 않는 편이 좋습니다. 안전 사례 하나의 실패가 일반 품질 몇 점 향상으로 상쇄되어서는 안 됩니다. 필수 사례는 개별 통과, 품질 사례는 그룹별 비율처럼 정책을 나눕니다. 실패 로그에는 실제 답, 기대 기준, Judge 이유와 실행 설정을 남겨 개발자가 재현할 수 있게 합니다.

## 비용과 캐시는 어떻게 운영할까

PR마다 실행할 예상 호출 수와 상한을 계산하고 대상 모델, Judge, 임베딩 비용을 분리합니다. 입력이 길거나 여러 번 반복하는 사례는 느린 세트로 분류할 수 있습니다. 오류로 무한 재시도하지 않도록 제공자별 동시성과 재시도 예산도 정합니다.

캐시에는 실행 시점과 모델 식별자를 남기고, 현재 동작을 확인해야 하는 배포 전에는 선택적으로 무효화합니다. 캐시 적중률이 높아도 오래된 결과로 새 모델을 통과시키면 안 됩니다. 비용 절감과 신선도 요구를 테스트 단계별로 다르게 정하는 것이 핵심입니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [공식 GitHub 저장소](https://github.com/promptfoo/promptfoo)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [Caveman식 짧은 LLM 답변은 비용을 줄일까: 품질·가독성·측정 기준]({% post_url 2026-04-12-Making-AI-a-Caveman-A-Deep-Dive-into-the-Caveman-Architecture-that-Halves-LLM-Token-Costs %}) — Caveman식 출력 지시가 LLM의 불필요한 문구와 출력 token을 줄이는 원리, code·error 보존 한계와 품질·지연·사람의 재질문 비용을 함께 평가합니다.
- [Gemini 3 기능·비용·한계 읽는 법: 벤치마크와 실무 검증 기준]({% post_url 2025-11-28-Gemini3 %}) — Gemini 3의 멀티모달·추론·코딩 기능, 공개 벤치마크와 API 비용을 발표 조건 안에서 읽고 실제 도입 전 확인할 한계를 정리합니다.
- [멀티모달 에이전트가 25번 도구를 써도 답을 찾을까: AgentVista]({% post_url 2026-03-06-AgentVista--Evaluating-Multimodal-Agents-in-Ultra-Challenging-Realistic-Visual-Scenarios %}) — AgentVista의 25개 하위 도메인·7개 범주와 장기 도구 사용 평가, Gemini-3-Pro 27.3% 결과를 비용·연쇄 오류 관점에서 해석합니다.
<!-- internal-links:end -->

## 자주 묻는 질문

### Promptfoo를 쓰면 LLM 테스트가 일반 단위 테스트처럼 결정적이 되나요?

아닙니다. 구조와 금지 동작은 결정적으로 검사할 수 있지만 의미 평가와 모델 출력은 변동할 수 있어 반복 실행, 사람 판정과 별도 보정이 필요합니다.

### LLM Judge 결과를 바로 CI 차단 조건으로 써도 되나요?

처음부터 바로 차단하는 것은 위험합니다. 같은 답에 대한 반복 합의율과 사람 판정 일치율을 측정하고 신뢰도가 높은 사례부터 단계적으로 Gate로 승격해야 합니다.

### 프롬프트 회귀 테스트 사례는 어디서 모아야 하나요?

실제 운영 장애, 사용자 피드백과 명시된 정책에서 재현 가능한 입력을 먼저 모으고 정상·경계·악의적 입력을 함께 관리하는 편이 좋습니다.
