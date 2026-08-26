---
layout: post
title: 'Langfuse로 LLM 환각 원인을 찾을 수 있을까: Trace, Span, Generation, PII'
date: '2026-04-23 06:56:11'
categories: Tech
tags:
  - 환각문제
  - LLM
  - RAG
  - 오픈소스
  - 웹개발
summary: 'Langfuse의 계층형 Trace와 비동기 전송이 RAG 실패를 어떻게 재구성하는지 살펴보고, 프롬프트 저장에 따른 PII, 스토리지, 샘플링 문제를 점검합니다.'
description: "Langfuse의 Trace, Span, Generation과 async context 전파를 RAG 오류 단계, queue loss, sampling, PII masking, self-host storage, trace completeness 기준으로 검증합니다."
github_url: https://github.com/langfuse/langfuse
faq:
  - question: "Langfuse를 붙이면 LLM hallucination을 자동으로 판정하나요?"
    answer: "아닙니다. 답을 만든 검색, prompt, model 경로를 재구성할 뿐 정답, 근거 적합성 기준과 평가 데이터는 별도로 정의해야 합니다."
  - question: "모든 prompt와 RAG chunk를 저장하는 것이 debugging에 가장 좋은가요?"
    answer: "재현에는 유용하지만 PII, 사내 문서 유출과 storage가 커져 field masking, 접근, 보존, sampling을 업무별로 정해야 합니다."
  - question: "비동기 전송이면 application latency에 영향이 없나요?"
    answer: "요청 경로의 대기는 줄지만 queue 직렬화, memory와 종료 시 유실이 생길 수 있어 overhead와 flush 정책을 직접 측정해야 합니다."
image:
  path: https://opengraph.githubassets.com/1/langfuse/langfuse
  alt: "langfuse/langfuse GitHub 저장소 대표 이미지"
---

Langfuse는 환각을 자동으로 판정하지는 않지만, 어떤 질문, 검색 결과, 모델 호출이 그 답을 만들었는지 한 요청 단위로 재구성하게 해 줍니다. 도입 효과는 dashboard 수가 아니라 실패한 답에서 누락 없이 source, prompt, model, 비용을 연결하고 민감 field를 저장 전에 제거할 수 있는지로 판단합니다.

## 평면 로그로는 RAG 실패를 설명하기 어렵다

일반 APM에는 외부 LLM HTTP 요청이 오래 걸렸다는 사실만 남을 수 있습니다. RAG 답변의 원인을 찾으려면 사용자의 입력, 검색된 청크, 생성 프롬프트, 모델 출력, 토큰과 각 단계의 지연을 연결해서 봐야 합니다.

Langfuse는 전체 요청을 Trace, 검색이나 도구 실행을 Span, LLM 호출을 Generation으로 모델링합니다. 한 사용자의 요청 아래에 검색과 생성이 부모-자식으로 묶이므로 “검색이 틀렸는가, 검색은 맞았지만 생성이 틀렸는가”를 구분할 수 있습니다. 모델별 토큰과 비용을 함께 기록할 수 있다는 점도 일반 문자열 로그와 다릅니다.

그렇다고 대시보드만으로 답의 진위를 알 수 있는 것은 아닙니다. 좋은 답, 나쁜 답의 기준, 검색 적합성 평가와 사용자 피드백을 별도로 정의해야 Trace가 품질 개선 데이터가 됩니다.

| 관측 단계 | 남길 최소 정보 | 품질 질문 |
|---|---|---|
| request Trace | request, user pseudonym, version, 최종 상태 | 같은 요청의 전체 경로가 이어지는가 |
| retrieval Span | query, source ID, rank, filter | 정답 근거가 top-k에 있었는가 |
| Generation | model, prompt version, token, latency | 올바른 근거로 틀리게 답했는가 |
| tool Span | tool, argument hash, result 상태 | 외부 실패가 답에 반영됐는가 |
| score, feedback | rubric version, evaluator, 사유 | 점수가 무엇을 의미하는가 |

평가자는 final answer만 보지 않고 retrieval recall과 grounded generation을 나눕니다. 근거가 검색되지 않은 질문을 model hallucination으로만 분류하면 잘못된 component를 고치게 됩니다. 반대로 source가 top-k에 있어도 prompt에 실제로 포함되지 않았다면 assembly Span을 추가해야 합니다.

model, prompt, retriever version을 trace에 남겨 배포 전후를 비교합니다. 시간에 따라 바뀌는 dashboard filter만으로 실험군을 만들지 말고 immutable version과 평가 set ID를 연결합니다. 사용자 feedback은 오류의 단서이지 자동 정답 label은 아니므로 사유와 함께 검토합니다.

## contextvars와 비동기 큐가 연결을 유지한다

원문은 Python SDK가 `contextvars`를, Node.js에서는 `AsyncLocalStorage`를 이용해 현재 Trace ID를 실행 문맥에 보관한다고 설명합니다. 함수 인자로 ID를 계속 넘기지 않아도 중첩 호출을 같은 Trace 아래에 놓을 수 있는 이유입니다.

이벤트 전송은 메인 요청에서 네트워크를 기다리지 않도록 백그라운드 큐에 모아 배치로 보냅니다. 응답 지연을 줄이는 대신 프로세스가 갑자기 끝나면 큐에 남은 관측 데이터가 사라질 수 있습니다. 원문이 서버리스 핸들러 끝에서 `flush()`를 언급한 이유도 이 때문입니다. 다만 매 요청마다 동기 flush를 하면 원래 피하려던 지연이 돌아올 수 있어 종료 시점과 손실 허용 범위를 함께 정해야 합니다.

queue의 최대 크기, batch, flush 간격과 backpressure를 정합니다. collector 장애 때 memory가 무한히 늘거나 application request를 막지 않는지, 반대로 중요한 error trace가 조용히 버려지지 않는지 test합니다. dropped event 수와 마지막 성공 전송 시각을 application monitoring에서 볼 수 있어야 합니다.

serverless, worker와 장기 server는 종료 semantics가 다릅니다. lifecycle hook에서 제한된 시간 안에 flush하고 timeout 뒤 남은 event를 어떻게 처리할지 정합니다. 정상, 강제 종료를 각각 재현해 trace completeness와 추가 p95 latency를 측정합니다.

MSA에서는 프론트 요청, Spring Boot와 Python 워커가 같은 ID를 전달해야 전체 경로가 이어집니다. 원문이 제시한 `X-Langfuse-Trace-Id`와 `@observe(trace_id=...)` 형태는 개념 예시이며 현재 SDK에서 그대로 지원되는 완전한 통합 사양으로 단정할 수 없습니다.

## @observe 예시는 설치 가능한 튜토리얼이 아니다

원문의 Python 조각은 `@observe()`로 상위 함수와 검색, 생성 함수를 감싸고 Langfuse가 래핑한 OpenAI 클라이언트를 호출하는 구조입니다. 그러나 패키지 버전, 인증과 Langfuse 서버 설정이 없고, 메시지의 f-string이 줄바꿈되어 그대로는 실행되지 않습니다.

따라서 이 조각에서 가져갈 것은 API 철자가 아니라 관측 경계입니다.

- 사용자 요청 전체는 하나의 Trace로 둔다.
- 검색은 입력 질의와 반환한 청크를 Span으로 남긴다.
- Generation에는 모델, 입력, 출력 토큰과 지연을 기록한다.
- 최종 응답에는 평가 점수나 사용자 피드백을 연결한다.
- 실패하더라도 Trace가 끝났는지 확인한다.

SDK 예제를 복사하기 전에 설치한 버전의 문서와 타입을 확인하고, 작은 요청 하나가 올바른 계층으로 표시되는지부터 검증해야 합니다.

## 프롬프트 전문 저장은 디버깅과 유출을 함께 만든다

환각을 재현하려면 프롬프트와 검색 청크가 유용하지만, 그 안에는 개인정보와 사내 문서가 들어갈 수 있습니다. 원문은 SaaS 대신 self-hosting을 선택할 수 있다고 설명하며, 자체 구성에는 PostgreSQL, ClickHouse와 Redis 운영 부담이 따른다고 지적합니다.

직접 호스팅해도 민감 데이터가 안전해지는 것은 아닙니다. 수집 전에 필드별 마스킹, 보존 기간, 조회 권한과 삭제 절차를 정해야 합니다. 모든 요청의 긴 RAG 컨텍스트를 저장하면 스토리지가 빠르게 늘어나므로 안정화된 경로는 일부만 샘플링하고, 오류, 고비용, 사용자 불만 요청은 더 높은 비율로 남기는 기준이 필요합니다.

masking은 저장 후 dashboard에서 가리는 것이 아니라 SDK, collector 경계에서 수행합니다. email, token 같은 pattern뿐 아니라 document field별 정책을 두고 binary, attachment 원문은 기본 수집하지 않습니다. deletion request가 PostgreSQL, ClickHouse, cache와 backup retention에 어떻게 반영되는지 확인합니다.

sampling은 trace 전체에 일관되게 적용해야 root만 남고 child Generation이 사라지는 일을 막습니다. 오류나 고비용 여부를 final 단계에서 알게 된다면 buffer 또는 tail sampling이 필요하며 그 memory 비용을 측정합니다. 샘플링되지 않은 요청에도 집계 metric은 남길지 별도 설계합니다.

데코레이터를 코드 곳곳에 직접 붙이면 도구 교체 비용도 커집니다. 비즈니스 함수가 Langfuse 객체를 직접 알지 않도록 얇은 관측 어댑터를 두면 특정 SDK에 대한 결합을 줄일 수 있습니다.

## 파일럿은 답변보다 추적 완전성을 본다

대표 RAG 질문 20~30개를 준비하고 검색 실패, 생성 실패, 타임아웃을 의도적으로 넣습니다. 각 요청에서 입력부터 최종 답까지 부모-자식 관계가 끊기지 않는지, 프로세스를 종료했을 때 큐 데이터가 얼마나 유실되는지, 마스킹할 값이 남지 않는지를 확인하십시오.

그다음 Trace 한 건당 저장 용량과 전송 오버헤드를 측정해 샘플링, 보존 정책을 정합니다. Langfuse의 도입 가치는 로그를 많이 쌓는 데 있지 않습니다. 한 건의 잘못된 답을 검색, 프롬프트, 모델과 비용 가운데 어느 단계의 문제인지 설명할 수 있게 되는 데 있습니다.

pilot 통과 기준에는 부모가 없는 span, 누락 Generation, 잘못 연결된 user request와 민감 field 0건을 포함합니다. process 강제 종료와 collector 장애에서도 허용 손실률을 기록합니다. 이 기본 trace가 안정된 뒤에만 자동 evaluator와 prompt experiment를 추가해야 잘못된 telemetry 위에 품질 결론을 쌓지 않습니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [공식 GitHub 저장소](https://github.com/langfuse/langfuse)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [Scientific Agent Skills가 환각을 막아줄까: 절차 지식과 샌드박스 분리]({% post_url 2026-05-13-Why-Your-AI-Agent-Fails-in-Production-Anatomy-of-Scientific-Agent-Skills--Sandboxed-Runtime %}) — Scientific Agent Skills의 온디맨드 절차 주입을 살펴보고, 지시문과 실제 권한 통제를 분리해 과학 워크플로를 검증하는 방법을 정리합니다.
- [Qwen-Agent로 함수 호출, RAG, WebUI를 묶기 전 확인할 것]({% post_url 2026-03-06-Alibabas-Hidden-Weapon-Qwen-Agent-Uncovering-the-Pragmatic-Agent-Framework-Threatening-LangChains-Throne %}) — Qwen-Agent의 LLM, Tool, Memory/RAG, Agent 구조와 WebUI, 코드 실행 기능을 살피고, 원문 예제의 가짜 응답, 버전 누락, 격리 한계를 짚습니다.
- [re4/LibreCode: 일렉트론을 걷어내고 로컬 AI와 리버싱을 통합한 네이티브 에디터]({% post_url 2026-07-13-re4LibreCode-The-Native-Editor-Integrating-Local-AI-and-Reversing-Toolkit-without-Electron %}) — re4/LibreCode는 .NET 10과 Avalonia UI를 기반으로 설계되어 일렉트론의 무거움을 극복하고, Ollama 기반의 완전 오프라인 로컬 AI(RAG)와 강력한 역공학(리버싱) 도구들을 단일 환경에 통합한 차세대 코드…
<!-- internal-links:end -->

## 자주 묻는 질문

### Langfuse를 붙이면 LLM hallucination을 자동으로 판정하나요?

아닙니다. 답을 만든 검색, prompt, model 경로를 재구성할 뿐 정답, 근거 적합성 기준과 평가 데이터는 별도로 정의해야 합니다.

### 모든 prompt와 RAG chunk를 저장하는 것이 debugging에 가장 좋은가요?

재현에는 유용하지만 PII, 사내 문서 유출과 storage가 커져 field masking, 접근, 보존, sampling을 업무별로 정해야 합니다.

### 비동기 전송이면 application latency에 영향이 없나요?

요청 경로의 대기는 줄지만 queue 직렬화, memory와 종료 시 유실이 생길 수 있어 overhead와 flush 정책을 직접 측정해야 합니다.

참고 자료:

- [공식 문서](https://langfuse.com/docs)
- [GitHub 저장소](https://github.com/langfuse/langfuse)
- [공식 문서](https://docs.python.org/3/library/contextvars.html)
