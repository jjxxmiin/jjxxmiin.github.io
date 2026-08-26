---
layout: post
title: "Caveman식 짧은 LLM 답변은 비용을 줄일까: 품질·가독성·측정 기준"
date: '2026-04-12 06:30:15'
categories: Tech
tags:
  - LLM
  - ClaudeCode
  - AI에이전트
summary: "Caveman식 출력 지시가 LLM의 불필요한 문구와 출력 token을 줄이는 원리, code·error 보존 한계와 품질·지연·사람의 재질문 비용을 함께 평가합니다."
description: "Caveman prompt로 LLM output token을 줄일 때 실제 절감액, code·error 보존, reasoning 품질, 독자별 가독성, prompt 충돌과 A/B 평가 기준을 설명합니다."
github_url: https://github.com/JuliusBrussee/caveman
faq:
  - question: "짧게 답하라고 지시하면 LLM API 비용이 항상 절반 이하로 줄어드나요?"
    answer: "아닙니다. 출력 token은 줄 수 있지만 입력·cache·tool 호출 비용은 남으며 절감 폭은 업무와 model, 기존 답변 길이에 따라 달라집니다."
  - question: "code와 error message를 그대로 두라는 prompt면 기술 정보가 보존되나요?"
    answer: "보장되지 않습니다. model이 중요한 조건을 생략하거나 code를 바꿀 수 있어 구조·test·원문 비교 같은 외부 검증이 필요합니다."
  - question: "Caveman식 응답은 어떤 업무에 먼저 시험할 만한가요?"
    answer: "정형 출력과 검증 규칙이 있고 긴 설명이 불필요한 내부 분류·요약부터 기존 prompt와 A/B 비교하는 것이 적합합니다."
image:
  path: https://opengraph.githubassets.com/1/JuliusBrussee/caveman
  alt: "JuliusBrussee/caveman GitHub 저장소 대표 이미지"
---

**Caveman식 지시는 인사말과 반복 설명을 줄여 출력 token을 낮출 수 있지만, 비용이 항상 절반이 되거나 기술 정보가 온전히 보존된다고 보장하지는 않습니다.** 입력 token·tool 호출은 그대로일 수 있고 너무 짧은 답은 재질문과 검토 시간을 늘릴 수 있습니다. 따라서 정형 업무에서 기존 prompt와 같은 품질 기준으로 A/B 평가한 뒤 적용해야 합니다.

[Caveman 저장소](https://github.com/JuliusBrussee/caveman)가 던지는 질문은 단순합니다. 사람이 읽는 친절한 문장이 필요 없는 내부 자동화에서도 모델이 장황하게 답한다면, 출력 형식을 더 짧고 구조적으로 제한해 낭비를 줄일 수 있는가입니다. 이름이나 과장된 절감률보다 실제 요청별 token과 오류를 측정하는 것이 중요합니다.

## 출력 token을 줄이면 전체 비용은 얼마나 줄까

이 접근을 이해하려면 LLM의 과금에서 입력과 출력, cache와 추가 tool 호출을 분리해야 합니다.

LLM은 텍스트를 tokenizer의 subword 단위로 처리합니다. “I would be happy to help” 같은 서두가 업무 결과에 필요 없다면 반복 호출에서 출력량을 늘립니다. 다만 언어와 tokenizer마다 분할이 다르고, 긴 code review에서는 서두보다 code·근거가 대부분이므로 예시 문구의 token 수를 전체 절감률로 일반화하면 안 됩니다.

Caveman 방식은 짧은 응답 지시와 모드별 system prompt를 이용하는 아이디어로 읽을 수 있습니다. 이것이 실제 proxy 기능과 검증기를 어느 범위까지 제공하는지는 선택한 저장소 version의 code로 확인해야 하며, 아래 숫자는 재현 없이 성능 보장으로 사용해서는 안 됩니다.

| 지표 (Metrics) | Native Claude Code (기존 방식) | Caveman (Ultra Mode 적용 시) | 아키텍처적 이점 (Impact) |
|---|---|---|---|
| **출력 형태** | "Sure! The issue is caused by your auth middleware... Here is the fix:" | "Bug in auth middleware. Token expiry use &lt; not &lt;=. Fix:" | 군더더기 없는 직관성 확보 |
| **사용 token** | 업무·model별 기준값 | 더 짧아질 수 있음 | 실제 API usage로 비교 |
| **응답 지연**| model·queue·출력 길이에 좌우 | 출력 decoding 구간이 줄 수 있음 | p50·p95를 같은 조건에서 측정 |
| **정보 보존** | 설명과 근거를 포함 | 중요한 조건도 생략할 수 있음 | 정답·code·error를 외부 검증 |

짧은 자연어가 가능한 업무가 있지만 시스템의 정보가 항상 code에만 있는 것은 아닙니다. 전제, 위험, 예외 조건과 결정 이유는 자연어에 있을 수 있습니다. 압축 목표는 글자 수 최소화가 아니라 다음 단계가 필요한 정보를 잃지 않는 것입니다.

아래 코드는 출력 지시와 간단한 code fence 검사를 보여 주는 의사 코드이며 실제 프로젝트 API나 충분한 무결성 검증기로 간주해서는 안 됩니다.

```python
import re
from typing import Dict

class CavemanInterceptor:
    """
    현업 파이프라인에 이식 가능한 Caveman 기반 LLM 프록시 로직
    """
    def __init__(self, target_llm_client, mode: str = "Ultra"):
        self.client = target_llm_client
        # 3가지 핵심 모드로 토큰 다이어트 강도 조절
        self.instructions: Dict[str, str] = {
            "Lite": "Remove greetings. Keep sentences short.",
            "Normal": "Use telegraphic style. Omit filler words.",
            "Ultra": "Respond like a smart caveman. Nouns, verbs, code only. NO filler. Say what need saying. Then stop."
        }
        self.base_safeguard = "CRITICAL: Keep all code blocks, technical terms, and error messages EXACTLY unchanged."
        self.system_prompt = f"{self.instructions[mode]} {self.base_safeguard}"

    def invoke(self, user_prompt: str) -> str:
        # 1. 원시인 모드 시스템 프롬프트 합성 (Prompt Injection)
        payload = self._build_payload(user_prompt, self.system_prompt)
        
        # 2. LLM 추론 요청 (이 과정에서 생성 토큰 수가 극단적으로 줄어듦)
        raw_response = self.client.generate(payload)
        
        # 3. 출력 무결성 검증 (코드 블록 훼손 방어)
        if not self._verify_technical_substance(raw_response):
            # 극단적 압축으로 인해 마크다운이나 코드가 깨졌을 경우의 Fallback 로직
            raise SerializationError("Caveman accidentally smashed the code block!")
            
        return raw_response

    def _verify_technical_substance(self, text: str) -> bool:
        # 마크다운 틱(```)이 정상적으로 닫혔는지 검증하는 최소한의 안전장치
        code_blocks = re.findall(r'```(.*?)```', text, re.DOTALL)
        return len(text.split('```')) % 2 != 0
```

이 의사 코드의 fence 개수 검사는 Markdown 구분자가 닫혔는지만 볼 뿐 code 내용이 원문과 같은지는 확인하지 못합니다. “기술 용어와 error를 바꾸지 말라”는 prompt도 model 행동을 보장하는 security boundary가 아닙니다. 기대 code·error 문자열을 별도로 비교하고 구조화된 schema, compiler와 test를 통과시켜야 합니다.

짧은 답이 실패하면 무조건 긴 답으로 다시 묻는 fallback도 비용을 두 번 쓸 수 있습니다. 먼저 요구 output을 JSON field나 code patch처럼 구체적으로 정의하고, 필수 field가 없을 때만 제한적으로 재시도합니다. prompt mode, 재시도 사유와 최종 token을 기록해야 겉으로 짧아진 첫 응답 뒤의 숨은 비용을 볼 수 있습니다.

## 어떤 업무에서 짧은 출력이 실제로 유리할까

다음 시나리오는 적용 후보일 뿐 효과를 보장하지 않습니다. 각 업무의 독자와 검증 방식이 다르므로 같은 Ultra 지시를 일괄 적용해서는 안 됩니다.

### PR review 자동화

PR comment는 문제 위치, 영향, 근거와 제안 수정이 있으면 짧아도 유용할 수 있습니다. 반면 “line 42 오류”만 남기면 왜 문제인지와 false positive를 판단하기 어렵습니다. comment당 token뿐 아니라 개발자가 설명을 다시 요청한 비율, 수락·기각과 잘못된 수정까지 비교합니다.

### Agent 사이의 인계물

기계 사이에는 원시인 문장보다 versioned schema가 더 명확합니다. `status`, `evidence`, `next_action`, `uncertainty` 같은 field를 요구하면 인사말을 없애면서 누락을 검증할 수 있습니다. payload byte 감소보다 다음 Agent가 잘못 해석하거나 재질문한 비율을 우선 봅니다.

### error log 요약

출력을 짧게 하는 것은 입력 context에 들어갈 log 양을 직접 늘리지 않습니다. input과 output token 예산은 구분해 계산해야 합니다. log는 먼저 시간·service·error signature로 집계하고 대표 원문 ID를 붙인 뒤, model에는 원인 후보·반증·다음 query를 구조화해 요구하는 편이 재현 가능합니다.

## 짧은 출력의 실패 조건은 무엇일까

### 짧은 답이 판단 근거까지 없앨 수 있다

출력 길이와 내부 reasoning의 관계는 model·API 설정에 따라 다르므로 공개 문장을 줄인다는 이유만으로 사고가 중단된다고 단정할 수 없습니다. 분명한 위험은 사용자가 확인해야 할 전제·대안·불확실성이 답에서 사라지는 것입니다. architecture 판단처럼 이유가 중요한 업무에는 결론, 근거와 반례를 필수 field로 남깁니다.

### 독자에 따라 재질문 비용이 커진다

같은 “Bug in auth”도 작성자에게는 충분하고 신규 팀원에게는 부족할 수 있습니다. 독자 역할별로 필요한 context를 정하고, 짧은 기본 답에서 근거를 펼쳐 볼 수 있는 2단 구조가 유용합니다. 출력 token 절감과 사람이 이해·검토하는 시간을 같은 비용표에 둡니다.

### 기존 prompt의 우선순위와 충돌할 수 있다

보안·domain·출력 지시가 한 system prompt에 섞이면 어느 규칙 때문에 실패했는지 찾기 어렵습니다. 안전 정책은 별도 code·tool 경계에 두고 출력 style은 가장 낮은 우선순위로 다룹니다. model·prompt version마다 고정 회귀 set으로 필수 정보 누락과 금지 행동을 확인합니다.

## 적용 여부는 같은 요청의 A/B 결과로 결정한다

실제 요청 50~100개를 분류·code review·요약처럼 업무별로 나눠 기존 prompt와 짧은 mode를 비교합니다. 입력·출력 token, p50·p95 latency, 정답과 필수 field 누락, 재시도·재질문, 사람 검토 시간을 기록합니다. 출력 비용만 줄고 오류 수정 시간이 늘면 전체 최적화가 아닙니다.

쉬운 정형 요청에서는 짧은 mode, 복잡하거나 위험한 요청에서는 근거를 포함한 mode로 route할 수 있습니다. route 기준이 불확실하면 긴 답을 기본으로 두고 평가를 쌓습니다. model이 code·error를 변경하거나 필수 정보가 누락되면 자동으로 원문 비교·test를 거쳐 제한된 fallback을 실행합니다.

결론적으로 Caveman의 유용한 교훈은 원시인 말투 자체가 아니라 output contract를 업무에 필요한 만큼만 설계하라는 것입니다. 확정되지 않은 절감률을 목표로 삼기보다 token당 유효 정보, 오류와 사람의 재작업까지 관찰해야 합니다. 짧음은 품질 검증을 통과한 뒤의 최적화 결과여야 합니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [공식 GitHub 저장소](https://github.com/JuliusBrussee/caveman)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [Claude Code Game Studios의 48개 역할은 필요한가: Gate·Context·비용]({% post_url 2026-04-15-Deep-Dive-Taming-the-Chaos-of-Vibe-Coding-with-48-AI-Agents-Unpacking-Claude-Code-Game-Studios %}) — Claude Code Game Studios가 역할·context·품질 gate를 나누는 구조를 살펴보고, 실제 격리 여부와 역할별 기여·token·deadlock·review 비용을 평가합니다.
- [oh-my-claudecode의 32개 Agent는 필요한가: Routing·State·검증 비용]({% post_url 2026-04-21-10-Year-Seniors-View-Is-Claude-Code-Dead-The-Shocking-Reality-and-Limits-of-oh-my-claudecode-Orchestrating-32-AIs %}) — oh-my-claudecode가 역할·model routing·hook·state로 코딩 작업을 나누는 구조를 살펴보고, 실제 병렬성·검증 독립성·token·복구·권한 한계를 평가합니다.
- [ai-job-search: 클로드 코드로 나만의 맞춤형 구직 에이전트 구축하기]({% post_url 2026-07-07-Building-a-Custom-Job-Search-Agent-with-ai-job-search-and-Claude-Code %}) — 클로드 코드(Claude Code)를 기반으로 공고 수집, 적합도 평가, 맞춤형 이력서 작성 등 구직 전 과정을 자동화하는 ai-job-search 프레임워크의 작동 원리와 실전 활용법을 깊이 있게 분석합니다.
<!-- internal-links:end -->

## 자주 묻는 질문

### 짧게 답하라고 지시하면 LLM API 비용이 항상 절반 이하로 줄어드나요?

아닙니다. 출력 token은 줄 수 있지만 입력·cache·tool 호출 비용은 남으며 절감 폭은 업무와 model, 기존 답변 길이에 따라 달라집니다.

### code와 error message를 그대로 두라는 prompt면 기술 정보가 보존되나요?

보장되지 않습니다. model이 중요한 조건을 생략하거나 code를 바꿀 수 있어 구조·test·원문 비교 같은 외부 검증이 필요합니다.

### Caveman식 응답은 어떤 업무에 먼저 시험할 만한가요?

정형 출력과 검증 규칙이 있고 긴 설명이 불필요한 내부 분류·요약부터 기존 prompt와 A/B 비교하는 것이 적합합니다.

## References
- [hackaday.com 원문](https://hackaday.com/2026/04/07/so-expensive-a-caveman-can-do-it/)
- [decrypt.co 원문](https://decrypt.co/2026/04/02/devs-are-making-claude-talk-like-a-caveman-to-cut-costs/)
