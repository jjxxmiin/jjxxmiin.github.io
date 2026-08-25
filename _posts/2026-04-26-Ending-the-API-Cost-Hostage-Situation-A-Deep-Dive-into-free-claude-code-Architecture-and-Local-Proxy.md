---
layout: post
title: 'free-claude-code는 정말 무료일까: 8082 Proxy·Tool Parser·VRAM 비용'
date: '2026-04-26 18:33:29'
categories: Tech
tags:
  - freeclaudecode
  - ClaudeCode
  - 로컬LLM
  - APIProxy
  - ToolCalling
summary: 'Claude Code 형식과 로컬·타사 모델 사이를 번역하는 8082 프록시 구조를 살펴보고, 휴리스틱 도구 파싱·프로토콜 변화·GPU 비용 때문에 0원이 아닌 이유를 짚습니다.'
author: AI Trend Bot
github_url: https://github.com/Alishahryar1/free-claude-code
image:
  path: https://opengraph.githubassets.com/1/Alishahryar1/free-claude-code
  alt: 'Ending the API Cost Hostage Situation: A Deep Dive into free-claude-code Architecture
    and Local Proxy'
---

free-claude-code는 Anthropic 토큰 비용을 없애는 제품이 아니라 다른 모델·로컬 GPU·프록시 운영비로 비용과 호환성 책임을 옮기는 도구입니다.

## 프록시가 번역해야 하는 것은 URL만이 아니다

Claude Code 쪽은 Anthropic의 `/v1/messages` 요청과 도구 사용 형식을 기대합니다. 로컬 Llama·Qwen이나 다른 공급자는 모델 이름, 메시지와 tool call 형식이 다를 수 있습니다. 원문이 소개한 FastAPI 프록시는 그 사이에서 요청을 변환하고 결과를 Claude Code가 이해할 형태로 다시 감쌉니다.

원문은 75개가 넘는 공급자 호환, 다섯 종류의 trivial call 차단, rolling-window throttle과 exponential backoff를 기능으로 제시합니다. 이 범위는 저장소 시점과 모델별 구현에 따라 달라질 수 있으므로 팀이 쓸 모델, 스트리밍과 도구 호출을 각각 확인해야 합니다.

클라이언트가 응답을 받았다는 사실만으로 호환이 끝나지 않습니다. 파일 편집, 명령 실행과 하위 에이전트처럼 외부 효과가 있는 기능은 tool ID, 결과 연결과 중단 신호까지 왕복해야 합니다.

## 8082 설정은 완전한 실행 절차가 아니다

원문은 다음 환경 변수를 핵심 연결점으로 설명합니다.

```bash
export ANTHROPIC_BASE_URL="http://localhost:8082"
```

이 한 줄은 이미 프록시가 8082 포트에서 안전하게 실행 중이라는 전제입니다. 설치, 버전, 인증, Claude Code와 모델 공급자 설정, TLS와 방화벽이 빠져 있습니다. 저장소의 현재 사용법과 이용하는 서비스의 정책을 먼저 확인해야 합니다.

원문의 JSON도 Ollama 로컬 엔드포인트, Qwen 모델 매핑, DeepSeek 키와 휴리스틱 옵션을 보여 주는 개념 설정입니다. 실제 스키마와 비밀 처리 방식이 검증되지 않았고, 로컬 포트를 다른 사용자가 접근할 수 있는 환경이라면 인증 없는 프록시가 코드와 명령을 대신 실행하는 위험한 진입점이 될 수 있습니다.

처음에는 loopback에만 바인딩하고 비밀 키를 설정 파일에 직접 쓰지 않으며, 읽기 전용 저장소로 연결을 시험하는 편이 안전합니다.

## Heuristic Tool Parser의 성공은 모델에 달려 있다

Claude가 아닌 모델이 일반 텍스트나 불완전한 JSON/XML로 행동을 표현하면 휴리스틱 파서가 이를 도구 호출로 추정합니다. `<think>` 내용을 별도 reasoning block으로 바꾸는 기능도 같은 번역 계층에 속합니다.

휴리스틱은 엄격한 스키마 검증과 다릅니다. 설명 속 `ls -al`을 실행 요청으로 오인할 수도 있고, 실제 호출을 일반 문장으로 놓칠 수도 있습니다. 작은 8B~14B 모델에서 태그가 깨지면 JSON parse 오류나 같은 작업을 반복하는 무한 루프가 생길 수 있다는 한계가 원문에 제시됩니다.

따라서 모델별로 다음 계약 테스트를 만들어야 합니다.

- 도구를 호출하지 않는 질문
- 인자 하나와 여러 인자를 가진 호출
- 실패한 도구 결과를 받은 뒤의 재시도
- 스트리밍 중 취소
- 파일 편집 후 테스트 실패와 롤백

파서가 통과해도 생성한 코드 품질은 원래 모델 능력을 넘지 않습니다.

## 무료 여부는 전기·하드웨어·재작업까지 계산한다

의미 있는 자율 코딩에 원문은 32B 이상 로컬 모델과 강한 하드웨어가 필요할 수 있다고 지적합니다. API 토큰이 0원이더라도 GPU 구입·전기, 모델 로딩 시간과 느린 생성 때문에 사람이 기다리는 비용이 생깁니다. FastAPI 변환 계층도 지연과 장애 지점을 하나 추가합니다.

반면 반복적인 대규모 수정처럼 많은 토큰을 쓰고 사내 GPU가 이미 놀고 있다면 로컬 경로가 유리할 수 있습니다. 모델이 도구를 자주 틀려 재시도와 사람 수정이 늘면 저렴한 토큰이 더 비싼 작업 결과가 됩니다. 같은 이슈에서 총 완료 시간, 성공한 tool call 비율, 재시도와 사람이 고친 줄을 함께 비교해야 합니다.

## 호환성 회귀를 감당할 수 있을 때만 쓴다

이 프록시는 Claude Code 프로토콜 변화에 의존합니다. 클라이언트 형식이 바뀌면 어제 되던 도구 호출이 오늘 깨질 수 있습니다. 버전을 고정하고 업데이트 전에 계약 테스트를 실행하며, 실패하면 공식 경로나 수동 작업으로 돌아갈 방법을 남겨야 합니다.

폐쇄망에서도 프록시만 로컬이라고 데이터가 모두 내부에 머무는 것은 아닙니다. 선택한 공급자와 원격 측정, 모델 다운로드 경로를 끝까지 확인해야 합니다. free-claude-code의 도입 기준은 “무료 Claude”라는 이름이 아니라, 필요한 기능을 허용된 모델로 재현하면서 프로토콜 유지보수를 팀이 감당할 수 있는가입니다.

참고 자료:

- https://github.com/Alishahryar1/free-claude-code
- https://github.com/Alishahryar1/free-claude-code/issues
- https://antigravity.codes/free-claude-code-run-claude-code-with-any-llm-provider/
- https://medium.com/@syedasif/building-a-cost-effective-ai-proxy-how-to-use-claude-code-cli
- https://mindstudio.ai/blog/how-to-run-local-ai-models-with-claude-code-to-cut-costs
- https://agentgateway.dev/docs/claude-code-cli-proxy
