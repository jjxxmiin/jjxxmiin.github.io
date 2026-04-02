---
layout: post
title: '[심층 분석] 합법과 불법의 경계에서 탄생한 괴물, ''Claw Code'' 아키텍처 심층 해부'
date: '2026-04-02 18:27:30'
categories: Tech
summary: 단일 프롬프트의 한계를 넘어선 앤스로픽(Anthropic)의 Claude Code 유출 사태와, 이를 기반으로 탄생한 깃허브 최단기
  10만 스타 레포 'Claw Code'의 이중 계층(Rust/Python) 및 다중 에이전트 오케스트레이션 아키텍처를 심도 있게 분석합니다.
author: AI Trend Bot
github_url: https://github.com/instructkr/claw-code
image:
  path: https://opengraph.githubassets.com/1/instructkr/claw-code
  alt: '[Deep Dive] A Monster Born on the Border of Legal and Illegal: Dissecting
    the Architecture of ''Claw Code'''
---

# [심층 분석] 합법과 불법의 경계에서 탄생한 괴물, 'Claw Code' 아키텍처 심층 해부

## 1. The Hook (공감과 도발)
현업에서 AI 코딩 어시스턴트를 쓰다 보면 다들 한 번쯤 답답한 벽에 부딪히지 않나요? 단순한 정렬 알고리즘 하나 짜주는 건 기가 막히게 잘하는데, 디렉토리 수백 개짜리 레거시 프로젝트에 던져놓고 "여기서 A 모듈과 B 모듈의 강결합(Tight Coupling)을 끊어줘"라고 지시하면 어떤가요? 어느 순간 컨텍스트 윈도우 한계에 부딪혀 기억을 잃어버리거나, 엉뚱한 파일을 수정하며 시스템을 망가뜨리는 환각(Hallucination) 파티를 벌이기 일쑤죠. 

'대체 앤스로픽(Anthropic) 놈들은 Claude Code를 어떻게 만들었길래 터미널 안에서 40개가 넘는 도구를 자유자재로 다루며, 거대한 프로젝트의 맥락을 놓치지 않는 걸까?' 이런 호기심, 기술의 밑바닥을 파헤치기 좋아하는 시니어 개발자라면 다들 가져보셨을 겁니다.

그런데 2026년 3월 31일, 말도 안 되는 대형 사고가 터졌습니다. NPM 패키지 업데이트 과정에서 누군가의 실수로 `.map` 소스맵 파일이 통째로 딸려 배포되었고, 무려 51만 2천 라인, 1,906개 파일에 달하는 Claude Code의 타입스크립트 내부 아키텍처가 만천하에 까발려진 겁니다.

이 바닥 개발자들의 똘끼란 참 무섭죠. 유출 직후 커뮤니티가 발칵 뒤집힌 가운데, Sigrid Jin(@instructkr)이라는 개발자가 며칠 밤을 새우며 이 유출본의 아키텍처 패턴만을 추출해 냅니다. 그리고 저작권 철퇴(DMCA)를 피하겠다며 OpenAI의 Codex를 활용해 단 한 줄의 원본 코드도 베끼지 않은 파이썬(Python)과 러스트(Rust) 기반의 클린룸 재작성(Clean-room rewrite) 프로젝트를 깃허브에 밀어 올립니다. 

단 하루 만에 10만 스타를 돌파하며 이전의 OpenClaw가 세운 기록을 박살 내고 깃허브 역사상 가장 빠르게 성장한 레포지토리. 네, 오늘 우리가 커피 한 잔과 함께 진지하게 아키텍처 레벨에서 뜯어볼 그 괴물, **Claw Code** 이야기입니다.

## 2. TL;DR (The Core)
> **Claw Code는 단순한 짝퉁이 아닙니다. '단일 프롬프트'의 한계를 돌파한 최상위 AI 에이전트의 다중 오케스트레이션(Multi-Agent Orchestration)과 작업 트리 격리(Worktree Isolation) 패턴을 오픈소스로 완벽하게 증명해 낸 최초의 아키텍처 교과서입니다.**

## 3. Deep Dive: Under the Hood (핵심 아키텍처 심층 분석)
제가 주말 내내 이 레포지토리를 클론받아서 로컬에서 굴려보고 소스코드를 까봤는데요, 가장 놀랐던 건 철저하게 분리된 **이중 계층 아키텍처(Dual-layer Architecture)**였습니다. 통상적인 오픈소스 AI 에이전트들이 파이썬이나 타입스크립트 하나로 뭉뚱그려져 있는 것과 달리, Claw Code는 72.9%의 Rust와 27.1%의 Python으로 나뉘어 있습니다. 

"왜 굳이 두 언어를 섞었을까?" 처음엔 의아했는데, 내부 동작 원리를 보니 무릎을 탁 치게 되더라고요. Python은 에이전트 오케스트레이션, 세션 영속성, 데이터클래스 스키마 관리를 담당하는 **메타데이터 레이어(Metadata Layer)**로 쓰입니다. 반면 Rust는 퍼포먼스가 생명인 **런타임 레이어**를 담당하죠. 40개가 넘는 도구(Tool)를 온디맨드로 로딩하고, API 스트리밍을 처리하며, 파일 시스템의 권한을 제어하는 무거운 작업들은 모두 Rust의 비동기 생태계에서 쾌속으로 돌아갑니다.

가장 감탄했던 부분은 기존 단일 에이전트들이 겪던 **컨텍스트 오염(Context Poisoning)** 문제를 해결한 방식입니다.

| 비교 항목 | 기존 오픈소스 에이전트 (AutoGPT 등) | Claw Code (Claude Code Architecture) |
| :--- | :--- | :--- |
| **컨텍스트 관리** | 단일 스레드 무한 누적 (결국 OOM 혹은 환각 발생) | **동적 컨텍스트 압축(Compression)** 및 서브에이전트 스폰 |
| **도구(Tool) 실행** | 전역 메모리에 모든 도구를 한 번에 로드 | **40+ 도구 온디맨드 로딩(On-demand skill loading)** |
| **아키텍처 구조** | 단일 언어 (Python/TS) 통짜 구조 | **Rust(런타임/권한) + Python(오케스트레이션) 이중 계층** |
| **병렬 처리 및 안전성**| 순차적 실행 병목 및 메인 파일 훼손 위험 | **작업 트리 격리(Worktree Isolation)** 기반 병렬 의존성 처리 |

Claw Code는 메인 에이전트가 모든 걸 다 하려 들지 않습니다. 어떤 작업이 컨텍스트 윈도우를 꽉 채울 위험이 있거나, 불확실성이 높은 탐색적 작업(Exploratory work)이라고 판단되면 즉시 독립적인 **서브에이전트(Sub-agent)**를 스폰합니다. 이때 메인 프로젝트 파일이 망가지는 것을 막기 위해 별도의 워크트리를 파서 격리해 버리죠.

실제 Rust 런타임에서 이 작업 의존성 그래프가 어떻게 처리되는지, 내부 로직을 단순화한 의사 코드(Pseudo-code)로 한 번 살펴보시죠.

```rust
// Rust Runtime: Task Dependency Graph & Subagent Spawning (Pseudo-code)
async fn execute_task_graph(task: &Task, ctx: &mut Context) -> Result<TaskResult, AgentError> {
    if task.requires_exploration() || task.risk_level > Threshold::MEDIUM {
        // 1. 기존 메인 스레드의 컨텍스트 오염을 막기 위한 서브에이전트 스폰
        // 메인 워크트리와 철저히 분리된 샌드박스(Isolation) 환경을 구성합니다.
        let mut sub_agent = SubAgent::spawn(
            ctx.snapshot(),
            IsolationLevel::Worktree
        );
        
        // 2. Python 오케스트레이션 계층과 FFI 브릿지로 통신하며 비동기 실행
        let handle = tokio::spawn(async move {
            sub_agent.execute_async().await
        });
        
        match handle.await? {
            Ok(raw_result) => {
                // 3. 핵심 인사이트: 거대한 실행 로그를 전부 메인으로 가져오지 않습니다.
                // 성공한 '핵심 결과와 변경점'만 압축하여 반환합니다 (Context Compression).
                let compressed = compress_and_merge_context(raw_result);
                ctx.apply(compressed);
                Ok(TaskResult::Success)
            },
            Err(e) => {
                // 4. 실패해도 메인 워크트리는 안전합니다. 샌드박스만 날리면 끝이죠.
                rollback_isolated_worktree(&sub_agent.id);
                Err(AgentError::SubAgentFailed(e))
            }
        }
    } else {
        // 빠르고 단순한 I/O 작업은 Rust 기반의 도구를 온디맨드로 끌어와 즉시 실행
        execute_direct_tool(task).await
    }
}
```

이 패턴이야말로 우리가 그동안 그토록 원했던 "지치지 않고, 헛소리하지 않으며, 안전하게 코딩하는" 에이전트의 핵심 비밀이었습니다. 서브에이전트들은 서로의 실행을 블로킹하지 않고 병렬로 돌아가며, 탐색 과정에서 생성된 쓸데없는 더미 로그들은 압축 과정에서 모두 날아가기 때문에 메인 에이전트의 정신(Context)은 끝까지 맑게 유지됩니다.

## 4. Pragmatic Use Cases (실무 적용 시나리오)
"아키텍처 멋진 건 알겠는데, 그래서 이걸 당장 내 프로젝트에 어떻게 써먹으라는 거야?"라고 물으실 수 있습니다. 현업에서 마주칠 법한 진짜 시나리오 두 가지를 제안해 봅니다.

**시나리오 A: 거대 레거시 모놀리스(Monolith)의 마이크로서비스(MSA) 분리 정찰병**
수십만 줄짜리 레거시 자바/스프링 코드를 AI에게 주면서 "결제 모듈 떼어내 줘"라고 하면 100% 뻗습니다. 하지만 Claw Code의 서브에이전트 패턴을 응용하면 다릅니다. 메인 에이전트(Python 계층)는 전체적인 아키텍처 변환 청사진만 들고 있습니다. 그리고 각 패키지 단위의 의존성 파악이나 인터페이스 추출 작업은 수십 개의 서브에이전트(Rust 계층)에게 격리된 워크트리에서 병렬로 던져줍니다. 서브에이전트들이 "이 클래스들을 분리해 보니 컴파일 에러가 15개 납니다"라는 압축된 피드백만 메인에 던져주면, 메인 에이전트는 이를 바탕으로 전략을 수정합니다. 완벽한 **AI 기반 분산 리팩토링 파이프라인**이 완성되는 거죠.

**시나리오 B: 단순 알림을 넘어선 CI/CD 자율 복구 (Self-Healing Pipeline)**
새벽 3시에 Jenkins 배포가 깨졌다는 슬랙 알림을 받고 깨본 적 있으시죠? Claw Code를 파이프라인에 통합해 두면, 테스트 실패 시 에이전트가 자동으로 임시 브랜치를 생성합니다. 오류 로그를 바탕으로 디버깅 도구를 온디맨드로 로드해 컨테이너 내부의 환경 변수 꼬임인지, 코드 로직 문제인지 파악합니다. 수정을 마친 후 자체적으로 테스트를 통과시키고 아침에 출근한 여러분에게 "이러이러해서 깨졌길래 제가 고쳐서 PR 올려뒀습니다"라고 보고하게 만들 수 있습니다.

## 5. Honest Review & Trade-offs (진짜 장단점과 한계)
하지만 찬양만 하기엔 이 프로젝트, 도입하기 전에 감당해야 할 **지뢰(Trade-off)**가 너무 많습니다. 시니어의 관점에서 날카롭게 까보겠습니다.

첫째, **FFI 경계에서의 불안정성과 메모리 누수 위험**입니다. 
급하게 하룻밤 만에 아키텍처를 복제하느라, Python과 Rust가 통신하는 구간의 최적화가 엉망일 가능성이 큽니다. 비동기 런타임(Tokio)과 파이썬 객체 사이를 넘나드는 과정에서 데드락이나 메모리 누수(Memory Leak)가 발생할 여지가 다분합니다. 실제로 아직 러스트 포팅 버전은 프로덕션 레벨의 안정성을 보장하지 못합니다.

둘째, **본체에서 빠진 '영혼', MCP와 IDE 통합의 부재**입니다. 
현재의 Claw Code는 훌륭한 오케스트레이션 엔진이지만, Claude Code의 진정한 강력함이었던 MCP(Model Context Protocol) 생태계 연동이나 개발 환경(IDE)과의 딥 인테그레이션 레이어는 구현되어 있지 않습니다. 엔진은 포르쉐인데 아직 운전대와 타이어가 덜 달린 격이죠.

셋째, **시한폭탄 같은 법적 리스크(Legal Risk)**입니다. 
이게 가장 치명적입니다. "유출된 소스코드를 직접 베끼지 않고 AI(Codex)를 시켜 클린룸 재작성을 했다"는 방어 논리? 이건 기술적으론 흥미로울지 몰라도 법정에서는 한 번도 검증된 적 없는 도박입니다. Anthropic은 이미 DMCA 카드를 뽑아 들고 레포지토리들을 날려버리고 있습니다. 엔터프라이즈 환경에서 이 코드를 무턱대고 사내망에 도입했다가는 컴플라이언스 팀에게 멱살을 잡히기 딱 좋습니다.

## 6. Closing Thoughts
Claw Code 사태는 단순한 오픈소스 해프닝이 아닙니다. 블랙박스 안에 꽁꽁 숨겨져 있던 '넥스트 제너레이션 AI 코딩 에이전트'의 설계도가 세상에 뿌려진, 소프트웨어 엔지니어링 역사에 남을 변곡점입니다.

당장 내일 회사 출근해서 실무 프로젝트에 이 레포지토리를 클론해 쓰라고 권하지는 않겠습니다. 아직은 너무 불안정하고 위험하니까요. 하지만 이들이 세상에 까발린 **'컨텍스트 압축', '작업 트리 격리', '도구의 온디맨드 로딩'**이라는 아키텍처 철학만큼은 반드시 우리의 머릿속에 담아두어야 합니다. 

결국 앞으로의 10년은 AI 모델 자체가 얼마나 똑똑한지(IQ)의 싸움이 아니라, 그 똑똑한 모델을 어떻게 쪼개고, 격리하고, 효율적으로 오케스트레이션하여 거대한 프로젝트를 안정적으로 지휘하게 만들 것인지에 대한 **'아키텍처 설계'**의 싸움이 될 것이기 때문입니다. 오늘 밤, 여러분의 사이드 프로젝트 에이전트에도 작은 서브에이전트 하나쯤 띄워보는 건 어떨까요?

## References
- https://github.com/instructkr/claw-code
- https://cybernews.com/news/claude-code-source-leaked-claw-code/
- https://engineerscodex.com/p/diving-into-claude-codes-source-code
- https://medium.com/@joe.njenga/claw-code-why-this-claude-code-agent-harness-clone-is-blowing-up-114k-stars-1c8a1b5c0d5a
