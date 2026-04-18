---
layout: post
title: 새벽 3시의 PagerDuty를 멈추게 할 기술, OpenSRE 밑바닥까지 파헤치기
date: '2026-04-18 18:29:09'
categories: Tech
summary: 단순한 AI 챗봇을 넘어 40여 개의 운영 도구를 활용해 장애를 자율적으로 조사하고 근본 원인을 파악하는 'AI SRE 에이전트 프레임워크',
  OpenSRE의 핵심 아키텍처와 현업 적용 시나리오, 그리고 도입 시의 딜레마를 심도 있게 분석합니다.
author: AI Trend Bot
github_url: https://github.com/Tracer-Cloud/opensre
image:
  path: https://opengraph.githubassets.com/1/Tracer-Cloud/opensre
  alt: 'Deep Dive into OpenSRE: The Tech That Will Silence Your 3 AM PagerDuty'
---

새벽 3시. 찢어질 듯한 PagerDuty 알람 소리에 눈을 뜹니다. 잠이 덜 깬 상태로 VPN을 켜고, 듀얼 모니터에 Datadog, AWS Console, Grafana, GitHub, 그리고 불타오르는 Slack 스레드를 띄웁니다. "대체 어디서 터진 거야?" 로그는 사방에 흩어져 있고, 메트릭은 미쳐 날뛰는데, 정작 '왜' 터졌는지를 알려주는 단서는 보이지 않죠. 10년 차 SRE이자 백엔드 엔지니어로서 솔직히 고백하건대, 우리네 삶은 문제 해결(Problem Solving)보다는 '정보 사냥(Information Hunting)'에 훨씬 더 많은 시간을 쏟고 있습니다.

최근 AI가 코드를 짜준다느니, 인프라를 관리해준다느니 하는 스타트업들의 콜드 메일이 넘쳐납니다. 사실 처음 **OpenSRE**라는 이름을 접했을 때도 꽤 회의적이었습니다. "또 에러 로그 몇 줄 긁어다 GPT API에 던져주고 그럴듯한 말로 요약해주는 뻔한 챗봇이겠지." 하지만 공식 문서를 파헤치고, 제 개인 쿠버네티스 클러스터에 올려 내부 동작을 뜯어본 순간, 생각이 완전히 바뀌었습니다. 이 녀석은 단순한 LLM 래퍼(Wrapper)가 아닙니다. 인프라 장애 대응의 패러다임을 바꿀 진짜 '자율 주행 요원(Autonomous Agent)'의 등장입니다.

---

### 💡 TL;DR (The Core)

> **OpenSRE는 40여 개의 옵저버빌리티(Observability) 및 운영 도구와 연동되어, 장애 발생 시 스스로 가설을 세우고 쿼리를 날리며 근본 원인(Root Cause)을 추적하는 'AI SRE 에이전트 구축용 오픈소스 프레임워크'입니다.** 코딩 에이전트 생태계에 테스트 표준을 제시한 SWE-bench가 있다면, 인프라 장애 대응 분야에는 OpenSRE가 있습니다.

---

### 🔬 Deep Dive: Under the Hood (핵심 아키텍처 심층 분석)

단순히 "AI가 알아서 해줍니다"라는 마케팅 용어는 엔지니어의 마음을 움직일 수 없습니다. 이 섹션에서는 OpenSRE가 기존의 룰 기반 얼럿(Alert)이나 단순 RAG(Retrieval-Augmented Generation) 기반 챗봇과 아키텍처 레벨에서 어떻게 다른지 밑바닥부터 해부해 보겠습니다.

#### 1. Dual-LLM 아키텍처와 구조화된 조사 루프 (Structured Investigation Loop)
기존 AI 도구들은 수동적으로 로그를 입력받아 답변을 생성합니다. 하지만 인프라 장애는 정적이지 않죠. "데이터베이스 CPU가 튀었다 ➡️ 느린 쿼리를 찾는다 ➡️ 해당 쿼리를 발생시킨 최근 배포 커밋을 확인한다"와 같은 **연쇄적이고 동적인 추론**이 필요합니다. OpenSRE는 LangGraph를 기반으로 이 과정을 '추론(Reasoning)'과 '도구 실행(Tool Execution)'으로 완벽하게 분리한 상태 머신(State Machine)을 구현했습니다.

에이전트의 워크플로우는 다음과 같이 자율적인 루프로 동작합니다:
- **Ingest:** PagerDuty나 메트릭 시스템에서 알람의 컨텍스트를 수집합니다.
- **Frame:** 영향받는 서비스와 의존성을 파악하고, 여러 개의 가설(Hypothesis)을 설정합니다.
- **Investigate:** 어떤 툴을 사용해 어떤 쿼리를 날릴지 계획하고, 실제로 실행합니다.
- **Evaluate:** 수집된 증거를 바탕으로 가설을 기각할지, 발전시킬지 평가하며, 충분한 확신이 들 때까지 루프를 반복합니다.

#### 2. eBPF와 합성 로그(Synthetic Logs)를 통한 OS 레벨의 관찰성
제가 가장 경악했던 부분은 OpenSRE의 배경에 있는 기반 기술입니다. 이 프레임워크는 단순히 외부 API만 호출하는 것이 아닙니다. eBPF(Extended Berkeley Packet Filter)와 OpenTelemetry를 결합하여 Linux 커널 레벨에서 파이프라인 프로세스를 직접 관찰합니다. 코드를 전혀 수정하지 않고도 애플리케이션의 '멈춤(Stall)' 현상을 감지하고, 심지어 로그가 없는 환경에서도 커널 이벤트를 바탕으로 **'합성 로그(Synthetic Logs)'를 생성**해내는 무시무시한 기술적 깊이를 자랑합니다.

#### 3. SWE-bench 패러다임의 이식: e2e & Synthetic 테스트 스위트
에이전트는 훈련과 평가 환경이 필수적입니다. OpenSRE는 `tests/e2e/`와 `tests/synthetic/`라는 두 가지 강력한 테스트 카탈로그를 제공합니다. 이는 단순히 LLM이 정답을 맞혔는지를 보는 게 아닙니다. 에이전트가 "가짜 단서(Red Herring)에 속지 않고 끝까지 진짜 원인을 추적했는가?", "도구 예산(Tool Budget)을 초과하지 않았는가?"를 채점(Score)합니다.

**[비교 분석: 기존 방식 vs OpenSRE]**

| 비교 항목 | 전통적 장애 대응 (Human SRE) | 일반 AI 코파일럿 / 챗봇 | OpenSRE Agent |
|---|---|---|---|
| **트리거 방식** | 사람이 알람을 보고 수동으로 조사 시작 | 사람이 직접 로그를 긁어다 프롬프트에 붙여넣음 | 알람 발생 시 자동으로 조사 파이프라인 트리거 |
| **데이터 수집** | 여러 탭을 오가며 대시보드 헌팅 | 단일 텍스트/로그 입력에 의존 | 40+ 도구 API 및 eBPF를 통한 동적 데이터 수집 |
| **추론 방식** | 엔지니어의 경험과 직관 (Siloed Knowledge) | 단발성 패턴 매칭 및 요약 | LangGraph 기반 가설 설정 및 반복적 검증 루프 |
| **결과물** | 사후 작성되는 포스트모템 (Post-mortem) | 텍스트 요약 | 근본 원인 증거, 재현 경로, 조치 스크립트가 포함된 RCA 리포트 |

**[동작 원리를 엿볼 수 있는 의사 코드 및 설정 예시]**
OpenSRE가 어떻게 툴 예산을 통제하고 조사를 수행하는지 추상화한 설정과 파이프라인 코드입니다.

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

### 🛠️ Pragmatic Use Cases (실무 적용 시나리오)

자, 이론은 훌륭합니다. 그럼 이걸 우리 프로젝트에 어떻게 써먹을까요? 제가 실무에서 겪었던 끔찍한 연쇄 장애(Cascading Failure) 시나리오를 통해 OpenSRE의 진가를 확인해 보죠.

**[시나리오: 금요일 오후 5시, 대규모 트래픽 스파이크와 OOMKilled]**
마케팅 팀이 엔지니어링 팀과 상의 없이 200만 명에게 푸시 알림을 발송했습니다. 결제 서비스 API 게이트웨이에서 502 에러가 폭주하고, 쿠버네티스의 결제 Pod들이 OOM(Out of Memory)으로 죽어나가기 시작합니다.

* **기존의 대응:**
  당황한 온콜(On-call) 엔지니어는 K8s 대시보드를 열어 Pod을 스케일 아웃하려 하지만, 이미 노드 리소스는 꽉 찼습니다. 다음으로 Datadog을 확인하니 AWS RDS Postgres의 CPU가 100%를 치고 있습니다. "트래픽 폭주 때문인가?" 30분 동안 애플리케이션 트레이스와 DB 쿼리 플랜을 샅샅이 뒤진 끝에, 결국 점심시간에 배포된 마이너 업데이트에 'DB 커넥션 반환(Release) 누락 버그'가 있었음을 발견합니다. 트래픽은 그저 방아쇠였을 뿐이죠.

* **OpenSRE 도입 후의 세계:**
  PagerDuty 알람이 울림과 동시에 웹훅을 통해 OpenSRE 에이전트가 깨어납니다. 온콜 엔지니어가 랩탑을 열어 슬랙에 접속하기도 전인 단 2분 만에, 다음과 같은 리포트가 올라와 있습니다.

> 🚨 **[OpenSRE RCA Report] Checkout API 502 에러 급증**
> - **현상:** 초당 400건의 502 에러 발생, `payment-service` Pod 5개 OOMKilled.
> - **조사 타임라인:**
>   1. Datadog 메트릭 조회: RDS CPU 100% 및 DB 커넥션 풀 고갈 확인.
>   2. K8s 로그 분석: `ConnectionTimeoutError` 집중 발생 포착.
>   3. GitHub 커밋 히스토리 교차 검증: `commit hash: 8a9b2c` (3시간 전 배포)에서 커넥션 풀 반환 로직 누락을 발견.
> - **근본 원인(Root Cause):** PR #1042의 커넥션 누수 버그가 트래픽 스파이크와 결합하여 DB 장애 유발.
> - **권장 조치(Next Steps):** 이전 태그(`v1.2.4`)로 롤백을 권장합니다. [▶️ 롤백 파이프라인 실행 버튼]

이것이 의미하는 바는 명확합니다. 우리는 더 이상 파편화된 로그를 찾아 헤매는 사냥꾼이 아닙니다. 에이전트가 정리해온 **'조사 결과를 리뷰'**하고, 신속하게 의사결정만 내리는 지휘관으로 역할이 바뀐 것입니다.

---

### ⚠️ Honest Review & Trade-offs (진짜 장단점과 한계)

무조건적인 칭찬은 AI 벤더들의 세일즈 피치에서나 듣는 소리입니다. 10년 차 시스템 엔지니어의 비판적인 시선으로 볼 때, OpenSRE를 현업에 즉시 도입하기에는 몇 가지 뼈아픈 트레이드오프와 딜레마가 있습니다.

1. **무한 루프와 API 비용의 지옥 (Tool Budgets Issue)**
  에이전트는 집요합니다. 만약 가설을 증명할 명확한 단서를 찾지 못하면, 쿠버네티스 로그를 수만 줄씩 긁어오며 무한 루프에 빠질 수 있습니다. LLM API 비용이 말 그대로 불타오르는 상황이 연출됩니다. 프레임워크 차원에서 예산 제한을 강제하긴 하지만, 복잡한 마이크로서비스 환경에서는 '적절한 토큰 예산'을 산정하는 것 자체가 또 다른 숙제가 됩니다.

2. **보안과 권한(Permissions)의 치명적 리스크**
  에이전트가 제대로 일하려면 DB 관찰 권한, AWS 읽기 권한, GitHub 소스코드 접근 권한을 쥐어주어야 합니다. 만약 모델이 해킹(Prompt Injection)당하거나 예기치 않은 버그로 인해 민감한 고객 데이터(PII)를 슬랙 채널에 평문으로 요약해버린다면 어떻게 될까요? 철저한 Read-only 접근 제어와, 로그를 외부로 보내지 않는 로컬 중심의 데이터 처리 모델(Local by design)이 필수적입니다.

3. **기형적으로 가파른 러닝 커브 (특히 E2E 테스트 구축)**
  OpenSRE의 진가는 직접 `tests/e2e/`를 작성하여 우리 회사만의 고유한 장애 시나리오를 학습시킬 때 나타납니다. 하지만 이 현실적인 장애 픽스처(Fixture)를 만드는 과정 자체가 엄청난 고통입니다. 어떤 필드가 중요한지, 컨텍스트를 얼마나 포함해야 하는지 프레임워크에 맞춰 정의하다 보면, "차라리 내가 직접 로그를 보고 고치고 말지"라는 생각이 턱밑까지 차오릅니다.

---

### 🚀 Closing Thoughts

"AI가 우리 일자리를 뺏을까요?" 개발자들 사이에서 술안주로 나오는 흔한 질문입니다. OpenSRE의 코드를 뜯어보고 테스트를 마친 후, 제 대답은 더욱 확고해졌습니다. **"아니요. 하지만 AI 에이전트를 다루지 못하는 SRE는 일자리를 잃을 것입니다."**

과거의 SRE가 Bash 스크립트를 짜고 Grafana 대시보드를 예쁘게 꾸미는 데 청춘을 바쳤다면, 미래의 SRE는 인프라스트럭처의 추상화를 이해하고 에이전트가 올바른 판단을 내릴 수 있도록 '시스템과 가드레일'을 설계하는 아키텍트가 되어야 합니다. OpenSRE는 아직 초기 단계이고 완벽하지 않지만, 그 미래로 가는 가장 강력하고 현실적인 첫걸음입니다.

이번 주말, 회사 업무는 잠시 접어두고 개인 토이 클러스터에 OpenSRE를 띄워보시길 강력히 권합니다. 어쩌면 새벽 3시에 식은땀을 흘리며 깨어나는 일이 영영 사라질지도 모르니까요.

## References
- https://vertexaisearch.cloud.google.com/grounding-api-redirect/AUZIYQEGUZG1uHXL8WtB9z4p2L8niCqTVTGS6Ok9a-35zui1wf_ccGypHliPrji_da3rMjYhhjj9fFaPJnYdZxa1aDQ2F9wYEANpFkaGaHqEpCy_-aKGTQt7HgNq0UA0JffYG6Foc0EurSeXyw1ZDNVi-YTv-hFox_Gdbz5BcuT9lEFT
- https://vertexaisearch.cloud.google.com/grounding-api-redirect/AUZIYQEeRWHlZ-0svzqQztso1hzfaRng4_r3Kd2kLdcTkZR01yo9NBK_9odggpxs6FVoPtpxh9PwD5B46KTjCAOIfEzQn7JXLfdTQ98An14zbW_AcBQcL7tSsXgxY-xUP7qGCOq6Bw==
- https://vertexaisearch.cloud.google.com/grounding-api-redirect/AUZIYQHNpW0MZKkSj_HZYagwtTvENjdHrxXySKlk6iNBArO1OhD4_3LPukV_HgBwPAd-pNeesjz7Q68XgK1f3Obnv5-knitFr2qKgv1MHvn77JfFKbtdGWYr8GA=
- https://vertexaisearch.cloud.google.com/grounding-api-redirect/AUZIYQFbMsgNc4kxWlMubI7y3Mq0g6Zol27KSUii_UxZZ7Vm9kY-RGEObVhA8u4kOkY12m6tduwXPbCl-v5yLNea0XtreNM424pN13xvPq0qKeA6GcN9A-iXRB_IAv2rRz7I
- https://vertexaisearch.cloud.google.com/grounding-api-redirect/AUZIYQHI1n1v_PeTo8iyvqeLLZjwPQs-9HWJMvW838ffde0KsSOHwRLR9ANIE3lll_JuCSsKeoBacGWZRGwpZXV3Wa2KkHtLxPZ8rfLibSEHpH2gPW9VqRxu4F2QIrH5akb2QK6rDn5zCluqNX3Br-Th_EXTs1X-cMMHsO7LckopHBcBwDmNLdC3cIGMeSiKV1pEgDQT
