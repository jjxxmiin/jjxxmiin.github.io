---
layout: post
title: "OpenSRE가 장애 원인을 스스로 찾을까: 조사 Loop, 권한, 근거 검증"
date: '2026-04-18 18:29:09'
categories: Tech
tags:
  - AI보안
  - AI에이전트
summary: "OpenSRE가 alert에서 가설, tool 조회, 증거 평가를 반복하는 구조를 살펴보고, read-only 권한, 예산, PII, red herring, RCA 근거와 운영 도입 범위를 검증합니다."
description: "OpenSRE의 incident investigation loop를 hypothesis, tool budget, read-only 권한, evidence provenance, PII masking, synthetic incident, human approval 기준으로 분석합니다."
github_url: https://github.com/Tracer-Cloud/opensre
faq:
  - question: "OpenSRE가 제시한 root cause를 바로 믿고 자동 rollback해도 되나요?"
    answer: "안 됩니다. 사용한 query, 시간 범위, source와 반증을 사람이 확인하고, rollback 같은 변경은 별도 정책과 승인 뒤 실행해야 합니다."
  - question: "운영 도구에 read-only 권한만 주면 안전한가요?"
    answer: "변경 위험은 줄지만 source code, log, PII를 읽고 외부 model이나 channel로 전송할 수 있어 field masking, egress, 감사 통제가 더 필요합니다."
  - question: "OpenSRE 효과는 어떤 장애로 먼저 평가하나요?"
    answer: "원인과 정답 timeline이 알려진 과거 또는 synthetic incident에서 근거 적중률, red herring, tool call, 시간과 사람 조사 단축을 비교합니다."
image:
  path: https://opengraph.githubassets.com/1/Tracer-Cloud/opensre
  alt: "Tracer-Cloud/opensre GitHub 저장소 대표 이미지"
---

**OpenSRE는 alert를 받아 가설을 만들고 여러 운영 도구에서 증거를 조회하는 조사 loop를 구성하려는 framework입니다.** 정보 수집 시간을 줄일 수 있지만 Agent가 만든 RCA는 확정 사실이 아니며 query, 시간 범위, source와 반증을 사람이 검토해야 합니다. 초기에는 read-only synthetic incident에서 기존 runbook과 비교하고 변경 action은 분리해야 합니다.

[OpenSRE 저장소](https://github.com/Tracer-Cloud/opensre)에서 실제 connector, state graph, test와 권한 경계를 확인하는 것이 출발점입니다. 도구 수나 “자율 SRE”라는 이름보다 어떤 가설이 어떤 관측으로 지지, 기각됐는지 재현 가능한지가 중요합니다.

## 가설과 Tool 실행을 분리하면 무엇이 달라질까

### 조사 Loop는 Ingest, Frame, Investigate, Evaluate로 이어진다
장애 조사는 “database CPU 상승→slow query 확인→최근 배포와 대조”처럼 관측에 따라 다음 query가 달라집니다. 원문은 LangGraph 기반으로 추론과 tool 실행을 상태로 나누는 구조를 설명합니다. “완벽한 분리”보다 각 상태의 입력, 출력과 budget이 code에 명시되는지 확인해야 합니다.

워크플로는 다음 단계로 설명할 수 있습니다.
- **Ingest:** PagerDuty나 메트릭 시스템에서 알람의 컨텍스트를 수집합니다.
- **Frame:** 영향받는 서비스와 의존성을 파악하고, 여러 개의 가설(Hypothesis)을 설정합니다.
- **Investigate:** 어떤 툴을 사용해 어떤 쿼리를 날릴지 계획하고, 실제로 실행합니다.
- **Evaluate:** 수집된 증거로 가설을 기각, 유지하고 budget이나 종료 조건까지 반복합니다.

“충분한 확신”을 모델의 self-score 하나로 정하면 안 됩니다. 가설별 source 수, 독립적인 신호, 반증 query와 남은 미확인 항목을 구조화하고 최대 step, 시간에 닿으면 결론 미확정으로 끝냅니다. CPU 상승과 배포가 같은 시각에 있었다는 상관을 원인으로 바꾸지 않게 causal 근거를 요구합니다.

tool query에는 incident 시간창, service, environment와 filter를 기록합니다. 서로 다른 timezone이나 sampling 때문에 지표와 log가 어긋날 수 있으므로 RCA report에서 실제 조회 범위를 보여 줍니다. 같은 query를 반복하거나 범위를 무한히 넓히는 경우를 budget에서 감지합니다.

### eBPF, OpenTelemetry 주장은 구성 요소별로 확인한다

원문은 eBPF와 OpenTelemetry를 결합한 OS 수준 관측과 synthetic log를 설명합니다. 이 기능이 OpenSRE repository 자체에 포함되는지, 별도 Tracer infrastructure 또는 선택적 connector인지 의존성과 실행 경로에서 확인해야 합니다. kernel 권한, 지원 OS, version과 overhead도 별도 평가 대상입니다.

synthetic log는 관측에서 만든 해석이지 application이 직접 남긴 원문 log와 같지 않습니다. report에 `observed`, `derived`, `inferred` provenance를 표시하고 생성 규칙과 원 event를 연결합니다. 추론된 stall을 확정 error처럼 취급하면 잘못된 가설이 뒤 query를 지배할 수 있습니다.

### E2E, Synthetic test는 답뿐 아니라 조사 경로를 평가해야 한다

원문은 `tests/e2e/`와 `tests/synthetic/` 카탈로그를 언급합니다. 실제 존재, fixture, score 방식은 선택한 commit에서 확인합니다. 최종 원인 문자열뿐 아니라 red herring을 사실로 채택했는지, 필요한 source를 조회했는지, tool budget과 시간 안에 끝났는지를 평가하는 접근이 중요합니다.

과거 incident를 fixture로 만들 때 production secret과 PII를 제거하고 timestamp, service 관계는 유지합니다. 정답 RCA와 최소 필요 evidence를 사람이 표시하며, 여러 원인이 함께 있었던 incident를 단일 label로 단순화하지 않습니다. model, connector version 변경마다 같은 set을 다시 실행합니다.

**[비교 분석: 기존 방식 vs OpenSRE]**

| 비교 항목 | 전통적 장애 대응 (Human SRE) | 일반 AI 코파일럿 / 챗봇 | OpenSRE Agent |
|---|---|---|---|
| **트리거 방식** | 사람이 알람을 보고 수동으로 조사 시작 | 사람이 직접 로그를 긁어다 프롬프트에 붙여넣음 | 알람 발생 시 자동으로 조사 파이프라인 트리거 |
| **데이터 수집** | 여러 도구의 query를 사람이 구성 | 제공된 log, 검색 범위에 좌우 | 지원 connector 범위에서 query를 연속 실행 |
| **추론 방식** | 엔지니어의 경험과 직관 (Siloed Knowledge) | 단발성 패턴 매칭 및 요약 | LangGraph 기반 가설 설정 및 반복적 검증 루프 |
| **결과물** | 조사 기록과 post-mortem | 텍스트 요약 | 근거가 연결된 가설, 미확인 항목, 제안 report |

다음 YAML과 Python은 tool budget과 조사 loop를 추상화한 의사 코드입니다. 실제 schema, model, connector 설정으로 복사하지 말고 repository의 현재 example과 대조해야 합니다.

```yaml
# opensre-config.yaml (Agent Configuration)
agent:
  reasoning_model: "claude-3-5-sonnet" # 복잡한 가설 수립 및 평가용
  execution_model: "gpt-4o-mini"       # 단순 툴 파라미터 생성용
  budget:
    max_steps: 15          # 무한 루프(Hallucination) 방지용 하드 리밋
    max_execution_time: "5m"
  tools:
    - name: "kubernetes_cluster"
      permissions: ["get", "list", "logs"] # 철저한 Read-only 원칙
    - name: "datadog_apm"
    - name: "github_repo"
      repo: "my-company/backend-monorepo"
```

```python
# OpenSRE 내부 조사 루프의 핵심 로직 (Pseudo-code)
def investigate_incident(alert_context):
    hypothesis_board = frame_problem(alert_context)
    
    while not hypothesis_board.is_confident() and check_budget():
        # 1. 현재 가설을 검증하기 위한 쿼리 계획 수립
        plan = reasoning_llm.plan_next_step(hypothesis_board)
        
        # 2. 툴 실행 (예: K8s 로그 조회, Datadog 트레이스 검색)
        evidence = execute_tools(plan.tools_to_use, plan.queries)
        
        # 3. 노이즈(Red Herring) 필터링 및 가설 업데이트
        hypothesis_board = evaluator_llm.synthesize(hypothesis_board, evidence)
        
    return generate_rca_report(hypothesis_board)
```

---

## Traffic spike와 OOM 시나리오에서 무엇을 검증할까

다음은 효과를 보장하는 실제 체험이 아니라 조사 loop를 시험하기 위한 가상 incident입니다. 결제 service에 traffic이 증가하고 502, Pod OOM과 database connection 고갈이 동시에 나타났다고 가정합니다. 정답 fixture에는 배포된 connection 반환 누락이 원인이고 traffic은 촉발 요인이라는 timeline을 둡니다.

* **기존 runbook:** K8s event, memory, DB pool, slow query, 최근 deployment와 trace를 정해진 순서로 사람이 조회하고 timeline을 만듭니다. 이 결과를 OpenSRE의 비교 기준으로 남깁니다.

* **Agent 조사:** alert webhook 뒤 같은 read-only query를 수행하게 하고, connection 고갈, OOM, 배포 commit을 어느 순서로 찾는지 기록합니다. “2분” 같은 목표는 사전에 보장하지 말고 p50, p95 조사 시간과 누락된 source를 측정합니다.

> **[가상 RCA Report] Checkout API 502 증가**
> - **현상:** 초당 400건의 502 에러 발생, `payment-service` Pod 5개 OOMKilled.
> - **조사 타임라인:**
>   1. Datadog 메트릭 조회: RDS CPU 100% 및 DB 커넥션 풀 고갈 확인.
>   2. K8s 로그 분석: `ConnectionTimeoutError` 집중 발생 포착.
>   3. GitHub 커밋 히스토리 교차 검증: `commit hash: 8a9b2c` (3시간 전 배포)에서 커넥션 풀 반환 로직 누락을 발견.
> - **근본 원인(Root Cause):** PR #1042의 커넥션 누수 버그가 트래픽 스파이크와 결합하여 DB 장애 유발.
> - **권장 조치(Next Steps):** 이전 태그(`v1.2.4`)로 롤백을 권장합니다. [▶️ 롤백 파이프라인 실행 버튼]

이 report가 유용하려면 각 항목이 실제 metric query, log line과 commit diff로 열려야 합니다. `commit hash`나 error 수치를 model이 만들어낸 경우를 막기 위해 connector 결과에서만 채우고 source ID를 붙입니다. rollback 버튼은 제안과 실행을 분리하고 현재 배포, 승인자를 다시 확인합니다.

red herring도 넣습니다. 같은 시간에 무관한 cache warning이나 다른 service의 CPU spike를 제공해 Agent가 이를 근거 없이 원인으로 채택하는지 봅니다. 진짜 원인을 찾지 못하면 확정 RCA를 쓰지 않고 조사한 범위와 다음 사람이 볼 query를 남기는 것이 올바른 실패입니다.

---

## Tool budget, 권한, 평가 비용은 어디에서 생길까

1. **반복 조사와 tool budget:** 근거를 찾지 못한 Agent가 같은 K8s log를 넓은 범위로 반복 조회할 수 있습니다. 최대 step, 시간, token뿐 아니라 connector별 row, byte, 동일 query와 전체 incident 비용을 제한합니다. budget에 닿으면 일부 성공을 RCA 확정으로 바꾸지 않습니다.

2. **읽기 권한과 PII:** DB, cloud, GitHub의 read-only 권한도 민감 log와 source를 모을 수 있습니다. service account의 scope와 incident별 time range를 제한하고 model 전송 전 field masking, egress allowlist와 report channel 권한을 둡니다. 외부 문서, log의 prompt injection도 tool 권한을 바꾸지 못하게 합니다.

3. **E2E fixture 구축:** 조직의 실제 장애를 재현하려면 telemetry와 정답 timeline을 익명화해 fixture로 만드는 비용이 듭니다. 하지만 이 set 없이 model update와 connector 변경의 회귀를 알기 어렵습니다. 빈도가 높고 조사 시간이 긴 incident 유형부터 몇 개만 만듭니다.

4. **변경 action 분리:** 조사 도구와 rollback, scale, query kill 같은 실행 도구를 같은 Agent에 주지 않습니다. 제안에는 영향, 대상과 rollback plan을 포함하고 deterministic policy와 사람이 승인합니다. 승인을 기다리는 동안 상태가 바뀌면 오래된 제안을 실행하지 않습니다.

---

## 도입은 Shadow Investigation으로 시작한다

처음에는 alert를 실제로 처리하지 않고 과거 또는 synthetic incident를 읽기 전용으로 조사하게 합니다. 기존 on-call 결과와 비교해 필요한 source를 찾은 비율, 잘못 확정한 root cause, red herring, tool call, 시간과 사람이 검토한 시간을 기록합니다. 좋은 demo 하나보다 원인을 찾지 못했을 때 정직하게 중단하는지가 중요합니다.

다음 단계에서도 Agent report는 on-call의 근거 묶음으로 사용하고 자동 remediation은 분리합니다. connector version, query와 source ID가 남고 PII, 권한 test를 통과하며, 동일 incident에서 기존 runbook보다 조사 시간을 줄일 때 제한적으로 범위를 넓힙니다.

OpenSRE의 가치는 새벽 호출을 없앤다는 약속이 아니라 흩어진 관측을 가설별로 모으고 조사 경로를 재사용 가능하게 만드는 데 있습니다. 그 결과도 model의 자신감이 아니라 재현 가능한 evidence와 사람의 운영 책임 위에서만 유효합니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [공식 GitHub 저장소](https://github.com/Tracer-Cloud/opensre)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [GPT-5.6 Sol Ultrafast 프리뷰: 초당 750토큰과 실제 지연 시간 판단법]({% post_url 2026-08-17-openai-previews-gpt-5-6-sol-ultrafast-mode-powered-by-cerebras %}) — OpenAI와 Cerebras가 Cerebras 웨이퍼 스케일 엔진 기반으로 표준 대비 최대 14배 빠른 GPT-5.6 Sol Ultrafast mode API를 공개했습니다. 초당 최대 750토큰을 생성하여 실시간 음성 에이전트…
- [여러 AI 에이전트 로그를 한 화면에서 봐도 될까? Kibitz의 출처, 요약 점검]({% post_url 2026-03-19-Kibitz-Deep-Dive-Turning-Terminal-Noise-into-Narrative-The-Control-Room-for-Directing-AI-Agent-Swarms %}) — 여러 터미널 세션을 모으고 로그를 서사형 상태로 요약한다는 Kibitz의 장점과, 이름이 같은 저장소가 섞인 원문에서 먼저 확인할 출처, 기능 경계를 짚습니다.
- [AI 에이전트 로그가 컨텍스트를 다 먹는다면? Context Mode 도입 기준]({% post_url 2026-05-06-The-Context-Window-is-Not-a-Trash-Can-A-Deep-Dive-into-the-Context-Mode-Architecture-Saving-AI-Agents %}) — 대용량 도구 출력을 로컬 SQLite에 보관하고 BM25로 필요한 조각만 돌려주는 Context Mode의 구조, 98% 수치와 정보 유실 위험을 정리합니다.
<!-- internal-links:end -->

## 자주 묻는 질문

### OpenSRE가 제시한 root cause를 바로 믿고 자동 rollback해도 되나요?

안 됩니다. 사용한 query, 시간 범위, source와 반증을 사람이 확인하고, rollback 같은 변경은 별도 정책과 승인 뒤 실행해야 합니다.

### 운영 도구에 read-only 권한만 주면 안전한가요?

변경 위험은 줄지만 source code, log, PII를 읽고 외부 model이나 channel로 전송할 수 있어 field masking, egress, 감사 통제가 더 필요합니다.

### OpenSRE 효과는 어떤 장애로 먼저 평가하나요?

원인과 정답 timeline이 알려진 과거 또는 synthetic incident에서 근거 적중률, red herring, tool call, 시간과 사람 조사 단축을 비교합니다.

## References
- [OpenSRE 공식 저장소](https://github.com/Tracer-Cloud/opensre)
- [OpenTelemetry 공식 문서](https://opentelemetry.io/docs/what-is-opentelemetry/)
- [LangGraph 공식 문서](https://docs.langchain.com/oss/python/langgraph/overview)
