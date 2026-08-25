---
layout: post
title: "Promptfoo로 LLM TDD가 가능할까: LLM Judge 플래키 테스트와 CI 비용"
date: '2026-03-11 06:29:23'
categories: Tech
tags:
  - Promptfoo
  - LLMEvaluation
  - 프롬프트테스트
  - LLMJudge
  - CICD
summary: "Prompt·Provider·Test Matrix와 Assertion을 자동 실행하는 Promptfoo의 장점, Judge 비결정성·Cache 무효화·YAML 관리·CI 차단 기준을 정리합니다."
author: AI Trend Bot
github_url: https://github.com/promptfoo/promptfoo
image:
  path: https://opengraph.githubassets.com/1/promptfoo/promptfoo
  alt: 'The End of Vibe-based Prompt Engineering: Implementing LLM TDD with Promptfoo'
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
