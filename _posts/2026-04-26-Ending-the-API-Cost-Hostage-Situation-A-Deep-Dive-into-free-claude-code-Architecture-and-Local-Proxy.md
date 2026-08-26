---
layout: post
title: 'free-claude-code는 정말 무료일까: 8082 Proxy, Tool Parser, VRAM 비용'
date: '2026-04-26 18:33:29'
categories: Tech
tags:
  - Claude
  - ClaudeCode
  - Qwen
  - DeepSeek
  - 온디바이스AI
summary: 'Claude Code 형식과 로컬, 타사 모델 사이를 번역하는 8082 프록시 구조를 살펴보고, 휴리스틱 도구 파싱, 프로토콜 변화, GPU 비용 때문에 0원이 아닌 이유를 짚습니다.'
description: "free-claude-code의 Anthropic-compatible 8082 proxy를 streaming, tool call 계약, heuristic parser 오인, auth, loopback, secret, VRAM TCO, version 회귀 기준으로 검증합니다."
github_url: https://github.com/Alishahryar1/free-claude-code
faq:
  - question: "free-claude-code를 쓰면 Claude Code 비용이 완전히 0원이 되나요?"
    answer: "아닙니다. 로컬 GPU, 전기, 운영 또는 타사 API 비용과 느린 model, tool 오류의 재시도, 사람 수정 비용이 남습니다."
  - question: "ANTHROPIC_BASE_URL만 8082로 바꾸면 모든 기능이 호환되나요?"
    answer: "메시지, streaming, tool ID, 취소, error와 protocol version까지 왕복해야 하므로 model별 계약 test 없이 보장할 수 없습니다."
  - question: "heuristic tool parser는 언제 특히 위험한가요?"
    answer: "작은 model이 설명 속 command와 실제 호출을 구분하지 못하거나 JSON, XML tag를 깨뜨릴 때 오실행, 누락, 반복 loop가 생길 수 있습니다."
image:
  path: https://opengraph.githubassets.com/1/Alishahryar1/free-claude-code
  alt: "Alishahryar1/free-claude-code GitHub 저장소 대표 이미지"
---

free-claude-code는 Anthropic 토큰 비용을 없애는 제품이 아니라 다른 모델, 로컬 GPU, 프록시 운영비로 비용과 호환성 책임을 옮기는 도구입니다. 실제 채택은 같은 issue에서 공식 경로와 총 완료비용, tool 성공률, 사람 수정, protocol 회귀를 비교해 결정해야 합니다.

## 프록시가 번역해야 하는 것은 URL만이 아니다

Claude Code 쪽은 Anthropic의 `/v1/messages` 요청과 도구 사용 형식을 기대합니다. 로컬 Llama, Qwen이나 다른 공급자는 모델 이름, 메시지와 tool call 형식이 다를 수 있습니다. 원문이 소개한 FastAPI 프록시는 그 사이에서 요청을 변환하고 결과를 Claude Code가 이해할 형태로 다시 감쌉니다.

원문은 75개가 넘는 공급자 호환, 다섯 종류의 trivial call 차단, rolling-window throttle과 exponential backoff를 기능으로 제시합니다. 이 범위는 저장소 시점과 모델별 구현에 따라 달라질 수 있으므로 팀이 쓸 모델, 스트리밍과 도구 호출을 각각 확인해야 합니다.

클라이언트가 응답을 받았다는 사실만으로 호환이 끝나지 않습니다. 파일 편집, 명령 실행과 하위 에이전트처럼 외부 효과가 있는 기능은 tool ID, 결과 연결과 중단 신호까지 왕복해야 합니다.

| 계약 항목 | 확인할 round trip | 실패했을 때의 위험 |
|---|---|---|
| message role | system, user, assistant, tool 순서 | 지시 우선순위, context 손실 |
| streaming | chunk 순서, finish, usage | 잘린 JSON, 중복 text |
| tool call | call ID, name, typed argument | 다른 결과 연결, 오실행 |
| tool result | 성공, error와 재시도 의미 | 무한 loop, 중복 side effect |
| cancellation | client cancel→model, tool 중단 | 비용, process가 계속 실행 |
| error | rate limit, auth, timeout mapping | 잘못된 재시도, fallback |

contract fixture는 model별로 고정하고 Claude Code, proxy update 전에 실행합니다. text-only 성공만으로 승격하지 않고 file edit diff, shell 실패, 여러 tool call과 stream 중단을 포함합니다. proxy가 모르는 새 field를 조용히 버리기보다 unsupported error로 멈추게 합니다.

## 8082 설정은 완전한 실행 절차가 아니다

원문은 다음 환경 변수를 핵심 연결점으로 설명합니다.

```bash
export ANTHROPIC_BASE_URL="http://localhost:8082"
```

이 한 줄은 이미 프록시가 8082 포트에서 안전하게 실행 중이라는 전제입니다. 설치, 버전, 인증, Claude Code와 모델 공급자 설정, TLS와 방화벽이 빠져 있습니다. 저장소의 현재 사용법과 이용하는 서비스의 정책을 먼저 확인해야 합니다.

원문의 JSON도 Ollama 로컬 엔드포인트, Qwen 모델 매핑, DeepSeek 키와 휴리스틱 옵션을 보여 주는 개념 설정입니다. 실제 스키마와 비밀 처리 방식이 검증되지 않았고, 로컬 포트를 다른 사용자가 접근할 수 있는 환경이라면 인증 없는 프록시가 코드와 명령을 대신 실행하는 위험한 진입점이 될 수 있습니다.

처음에는 loopback에만 바인딩하고 비밀 키를 설정 파일에 직접 쓰지 않으며, 읽기 전용 저장소로 연결을 시험하는 편이 안전합니다.

loopback이어도 같은 host의 다른 process가 port에 접근할 수 있습니다. local authentication, OS user 권한과 firewall을 적용하고 request body, header에 secret, source code가 log로 남지 않게 합니다. container에서 실행한다면 `localhost`가 host인지 container인지와 port publish 범위를 확인합니다.

provider key는 secret manager나 제한된 environment로 주입하고 config export, error traceback에 노출되지 않게 합니다. 사용자별 quota와 model allowlist가 없으면 한 process가 전체 key budget을 소진할 수 있습니다. proxy health와 admin endpoint도 외부에 열지 않습니다.

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

parser test에는 자연어 code 예시를 실행하지 않아야 하는 negative case를 충분히 넣습니다. tool argument 안의 quote, newline, Unicode, 여러 call 순서와 부분 stream을 fuzz하고 parse 실패 시 임의 command로 fallback하지 않습니다. write tool은 parser 결과 뒤에도 path, 권한, approval을 다시 검사합니다.

## 무료 여부는 전기, 하드웨어, 재작업까지 계산한다

의미 있는 자율 코딩에 원문은 32B 이상 로컬 모델과 강한 하드웨어가 필요할 수 있다고 지적합니다. API 토큰이 0원이더라도 GPU 구입, 전기, 모델 로딩 시간과 느린 생성 때문에 사람이 기다리는 비용이 생깁니다. FastAPI 변환 계층도 지연과 장애 지점을 하나 추가합니다.

반면 반복적인 대규모 수정처럼 많은 토큰을 쓰고 사내 GPU가 이미 놀고 있다면 로컬 경로가 유리할 수 있습니다. 모델이 도구를 자주 틀려 재시도와 사람 수정이 늘면 저렴한 토큰이 더 비싼 작업 결과가 됩니다. 같은 이슈에서 총 완료 시간, 성공한 tool call 비율, 재시도와 사람이 고친 줄을 함께 비교해야 합니다.

## 호환성 회귀를 감당할 수 있을 때만 쓴다

이 프록시는 Claude Code 프로토콜 변화에 의존합니다. 클라이언트 형식이 바뀌면 어제 되던 도구 호출이 오늘 깨질 수 있습니다. 버전을 고정하고 업데이트 전에 계약 테스트를 실행하며, 실패하면 공식 경로나 수동 작업으로 돌아갈 방법을 남겨야 합니다.

폐쇄망에서도 프록시만 로컬이라고 데이터가 모두 내부에 머무는 것은 아닙니다. 선택한 공급자와 원격 측정, 모델 다운로드 경로를 끝까지 확인해야 합니다. free-claude-code의 도입 기준은 “무료 Claude”라는 이름이 아니라, 필요한 기능을 허용된 모델로 재현하면서 프로토콜 유지보수를 팀이 감당할 수 있는가입니다.

파일럿에서는 20개 정도의 실제 작은 issue를 공식 경로와 proxy+model 경로에서 실행합니다. 최종 test, diff, tool call 정밀도, p95, 재시도, GPU, API, 사람 review 시간을 기록합니다. token 단가가 낮아도 merge 가능한 결과 한 건의 총비용이 높으면 “무료”가 아닙니다.

업데이트 전략은 client, proxy, model을 동시에 바꾸지 않고 한 축씩 승격합니다. contract test가 실패하면 이전 고정 version이나 공식 경로로 돌아가며, 진행 중 작업의 state, diff가 손실되지 않는지 확인합니다. protocol을 추정해 조용히 계속하는 것보다 명시적 중단이 안전합니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [공식 GitHub 저장소](https://github.com/Alishahryar1/free-claude-code)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [Wigolo: AI 코딩 에이전트에게 무제한 로컬 웹 검색과 크롤링 능력을 달아주는 법]({% post_url 2026-07-18-Wigolo-Empowering-AI-Coding-Agents-with-Unlimited-Local-Web-Search-and-Crawling %}) — Wigolo는 외부 API 과금 없이 내 PC의 자원을 활용해 AI 코딩 에이전트에게 무제한 웹 검색, 크롤링, 캐싱을 제공하는 로컬 기반 MCP 서버입니다. 단순한 검색을 넘어 JS 렌더링, PDF 파싱, 데이터 영속성 관리를 통해…
- [cc-switch: 여러 AI 코딩 도구의 API 설정과 프로바이더를 한곳에서 관리하는 데스크톱 제어 센터]({% post_url 2026-08-17-cc-switch-All-in-One-Configuration-Manager-and-Local-Proxy-Gateway-for-AI-Coding-CLI-Tools %}) — cc-switch는 Claude Code, OpenAI Codex, Gemini CLI 등 다양한 AI 코딩 도구의 프로바이더 설정과 API 키를 통합 관리하는 오픈소스 데스크톱 애플리케이션입니다. 로컬 프록시 게이트웨이, 자동…
- [클로드 요금제 총정리, Free부터 Max 20x까지 뭘 골라야 하나 (2026년 8월 기준)]({% post_url 2026-08-23-claude-pricing-guide-free-pro-max-team-comparison %}) — 클로드 유료 구독은 Pro 월 20달러부터 시작하고 Max는 5x 100달러, 20x 200달러입니다. Claude Code는 Pro 이상 모든 유료 등급에 추가 요금 없이 포함됩니다. 대부분의 사람에게는 Pro가 정답이고, Max는…
<!-- internal-links:end -->

## 자주 묻는 질문

### free-claude-code를 쓰면 Claude Code 비용이 완전히 0원이 되나요?

아닙니다. 로컬 GPU, 전기, 운영 또는 타사 API 비용과 느린 model, tool 오류의 재시도, 사람 수정 비용이 남습니다.

### ANTHROPIC_BASE_URL만 8082로 바꾸면 모든 기능이 호환되나요?

메시지, streaming, tool ID, 취소, error와 protocol version까지 왕복해야 하므로 model별 계약 test 없이 보장할 수 없습니다.

### heuristic tool parser는 언제 특히 위험한가요?

작은 model이 설명 속 command와 실제 호출을 구분하지 못하거나 JSON, XML tag를 깨뜨릴 때 오실행, 누락, 반복 loop가 생길 수 있습니다.

참고 자료:

- [GitHub 저장소](https://github.com/Alishahryar1/free-claude-code)
- [GitHub 저장소](https://github.com/Alishahryar1/free-claude-code/issues)
- [antigravity.codes 원문](https://antigravity.codes/free-claude-code-run-claude-code-with-any-llm-provider/)
- [medium.com 원문](https://medium.com/@syedasif/building-a-cost-effective-ai-proxy-how-to-use-claude-code-cli)
- [mindstudio.ai 원문](https://mindstudio.ai/blog/how-to-run-local-ai-models-with-claude-code-to-cut-costs)
- [공식 문서](https://agentgateway.dev/docs/claude-code-cli-proxy)
