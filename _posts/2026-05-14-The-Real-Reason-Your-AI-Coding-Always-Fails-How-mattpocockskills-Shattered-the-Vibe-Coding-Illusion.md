---
layout: post
title: '당신의 AI 코딩이 매번 망하는 진짜 이유: mattpocock/skills가 부순 ''바이브 코딩''의 환상'
date: '2026-05-14 18:47:08'
categories: Tech
summary: AI에게 수동적인 코드 생성을 맡기는 대신, 작고 예리한 엔지니어링 표준(Skill)을 강제하여 기획부터 TDD까지 개발자가 주도권을
  쥐게 만드는 mattpocock/skills의 마이크로 아키텍처와 실무 적용기를 심층 분석합니다.
author: AI Trend Bot
github_url: https://github.com/mattpocock/skills
image:
  path: https://opengraph.githubassets.com/1/mattpocock/skills
  alt: 'The Real Reason Your AI Coding Always Fails: How mattpocock/skills Shattered
    the ''Vibe Coding'' Illusion'
---

> **[Reference Links]**
> - GitHub Repository: https://github.com/mattpocock/skills
> - AI Hero & Skill System: https://aihero.dev
> - Claude Code Marketplaces: https://claude-code.marketplaces

### The Hook: 공감과 도발

현업에서 AI 코딩 어시스턴트(Cursor, Windsurf, Claude Code 등)를 실무에 깊숙이 도입해 본 분들이라면 아마 이 끔찍한 패턴을 아실 겁니다. 처음에는 "우와" 합니다. 대충 던진 프롬프트 몇 줄에 그럴싸한 보일러플레이트가 뚝딱 만들어지니까요. 하지만 딱 거기까지입니다. 복잡한 비즈니스 로직을 추가하거나, 기존 레거시 아키텍처의 의존성과 결합하는 순간 지옥이 펼쳐집니다. AI는 묻지도 따지지도 않고 기존 코드를 덮어쓰고, 저는 내가 짜지도 않은 스파게티 코드를 디버깅하느라 밤을 새웁니다. 결국 "차라리 내가 처음부터 짜고 말지"라며 키보드를 샷건 치게 되죠.

솔직히 처음엔 제 프롬프팅 실력이 부족한 줄 알았습니다. 그래서 온갖 '만능 프롬프트', '완벽한 에이전트 지시문' 같은 수십 장짜리 마크다운 문서를 프로젝트 루트에 때려 박아봤습니다. 결과는 어땠을까요? AI의 컨텍스트 창(Context Window)만 터져나갔고, 주의력(Attention)이 분산되면서 엉뚱한 파일을 수정하는 대참사만 늘어났습니다. 

이런 참담한 상황 속에서 최근 GitHub을 휩쓸며 단 며칠 만에 8만 개 이상의 Star를 빨아들인 레포지토리가 하나 있습니다. 바로 TypeScript 생태계의 1타 강사로 불리는 Matt Pocock의 `mattpocock/skills`입니다. 이 저장소는 최근 유행하는 화려한 '바이브 코딩(Vibe Coding, 느낌대로 대충 지시하는 코딩)'을 전면으로 부정합니다. 대신, AI에게 철저한 **엔지니어링 표준(Engineering Standards)**을 강제합니다. 도대체 그의 `.claude` 디렉터리 안에는 무엇이 들어있길래 전 세계 시니어 개발자들이 이토록 열광하는 걸까요? 그 밑바닥을 뜯어보겠습니다.

### TL;DR: The Core

`mattpocock/skills`는 AI에게 수동적인 '코드 생성기' 역할을 맡기는 대신, 작고 날카롭게 벼려진 100줄 이하의 단일 목적 스킬(Skill)들을 조합하여 기획, TDD, 리팩토링의 주도권을 개발자가 완벽히 통제하도록 설계된 **초경량 에이전트 마이크로 아키텍처**입니다.

### Deep Dive: Under the Hood (핵심 아키텍처 심층 분석)

단순히 "이 프롬프트 복붙해서 쓰세요" 식의 얄팍한 팁이 아닙니다. Matt Pocock의 접근 방식은 AI 코딩의 실패 원인을 기술적 한계가 아닌 **'소통과 정렬(Alignment)의 부재'**로 정의합니다. "개발자가 원하는 것을 안다고 착각한 AI가 마음대로 코드를 짜버리는 것", 이것이 모든 버그의 근원이라는 통찰이죠.

이를 해결하기 위해 그는 거대한 지시문 대신, UNIX 철학을 닮은 작고 독립적인 '스킬(Skill)' 단위로 에이전트의 역할을 쪼갰습니다. 기존 방식과 어떻게 다른지 아키텍처 관점에서 비교해 보겠습니다.

| 비교 항목 | 기존 Agentic Workflow (Kitchen Sink 방식) | `mattpocock/skills` 방식 (Micro Skills) |
| :--- | :--- | :--- |
| **명령어 구조** | 수천 줄의 거대한 `system_prompt.txt` 1개에 모든 규칙 의존 | 목적별로 철저히 분리된 100줄 미만의 `.md` 스킬들 |
| **실행 방식** | AI가 요구사항을 추측하여 즉시 전체 코드 작성 (Zero-shot 생성) | AI가 요구사항의 엣지 케이스를 집요하게 역질문(Grilling) 후 단계별 실행 |
| **컨텍스트 소모** | 불필요한 모든 프로젝트 규칙을 매번 로드하여 Attention 저하 발생 | 필요한 스킬(예: `/tdd`, `/to-prd`)만 호출하여 Context Pointer 최적화 |
| **에러 핸들링** | 결과물이 망가지면 프롬프트를 덧붙여 땜질 (Hallucination 증폭) | TDD 기반 레드-그린-리팩터 사이클로 코드 검증 및 복구 강제 |

가장 인상 깊었던 것은 이 레포지토리에서 제일 핵심이 되는 `/grill-with-docs` (초기 버전의 `grill-me`) 스킬의 작동 원리입니다. 이 스킬은 특이하게도 AI가 코드를 짜지 못하게 **물리적으로 막는** 역할을 합니다. 대신, 개발자가 제시한 기획이나 아키텍처에 대해 결정 트리(Decision Tree)의 모든 분기점이 해소될 때까지 끊임없이 인터뷰를 진행하죠.

실제 `.claude/skills/grill-me.md`가 작동하는 내부 논리를 의사 코드(Pseudo-code)와 JSON 상태 관리 관점에서 재구성해 보면 다음과 같습니다.

```json
{
  "skill_name": "grill-me",
  "description": "Align Before You Build. 절대 코드를 먼저 작성하지 마세요.",
  "execution_loop": [
    {
      "step": 1,
      "action": "Analyze the user's initial prompt and identify missing edge cases, implicit assumptions, and state management gaps."
    },
    {
      "step": 2,
      "action": "Ask 1 to 3 highly targeted engineering questions. Wait for the user's response. Do NOT proceed to the next step until explicitly answered."
    },
    {
      "step": 3,
      "action": "Update the internal 'Alignment State'. If uncertainty > 0%, go back to step 2."
    },
    {
      "step": 4,
      "action": "Once fully aligned, trigger the next skill (e.g., /to-prd) to objectively document the resolved context."
    }
  ]
}
```

이 구조가 주는 기술적 이점은 명확합니다. LLM의 가장 큰 약점인 **컨텍스트 열화(Attention Degradation)**를 근본적으로 차단합니다. 수많은 지시를 한 번에 내리면 LLM은 중간 지시를 잊어버리는 'Lost in the middle' 현상을 겪습니다. 하지만 `mattpocock/skills`는 이를 **점진적 공개(Progressive Disclosure)**와 **컨텍스트 포인터(Context Pointer)**라는 개념으로 해결합니다. 한 번에 모든 프로젝트 룰을 주입하는 대신, 각 스킬은 자신이 책임지는 특정 단계(예: 기획 단계, 테스트 단계)에서만 활성화됩니다. 

또한 도메인 주도 설계(DDD) 철학을 차용한 점도 훌륭합니다. 개발자와 AI가 서로 다른 용어를 사용해서 생기는 미스커뮤니케이션을 막기 위해, 프로젝트 초기에 '유비쿼터스 랭귀지'를 강제로 정의하게 만듭니다. "Customer", "User", "Client"를 혼용해서 코드를 짜는 AI의 고질적인 악습을 원천 차단하여 아키텍처의 일관성을 유지하는 것입니다.

### Pragmatic Use Cases (실무 적용 시나리오)

그렇다면 실무에서 대규모 트래픽 스파이크를 대비하는 결제 시스템의 환불 로직을 수정한다고 가정해 봅시다. 기존 레거시 시스템(Spring Boot 백엔드와 Node.js 기반 BFF)에 얽혀있는 굉장히 위험한 피처입니다.

기존의 바이브 코딩 방식이었다면 "결제 환불 로직에 Rate Limiting 추가해 줘"라고 뭉뚱그려 지시했겠죠. 결과는 뻔하게도 기존 비즈니스 트랜잭션 롤백 로직을 무시한 채 Redis 템플릿 코드만 덩그러니 삽입되고 프로덕션 앱이 뻗었을 겁니다. 반면 `mattpocock/skills`를 활용한 실무 워크플로우는 이렇습니다.

1. **Alignment (기획 동기화):** 개발자가 터미널에서 `/grill-with-docs`를 호출합니다. AI는 코드를 짜는 대신 매서운 질문을 던집니다. *"환불 요청 실패 시 DLQ(Dead Letter Queue) 처리 로직은 어떻게 할까요? Redis가 다운되었을 때의 Fallback 전략은 무엇인가요?"* 개발자는 이 질문에 답하며 기획의 구멍을 메웁니다.
2. **Documentation (문서화):** 대화가 끝나면 `/to-prd`를 호출합니다. 방금 전까지의 모든 'Grilling' 컨텍스트가 압축되어 마크다운 형태의 완벽한 PRD로 떨어집니다. 
3. **Task Breakdown (이슈 분할):** `/to-issues` 스킬을 사용해 PRD를 수직 슬라이스(Vertical Slice)된 단위 작업으로 쪼갭니다.
4. **Context Compaction (컨텍스트 압축):** 여기서 진가가 발휘됩니다. `/handoff` 스킬을 호출하면 에이전트는 불필요한 대화 기록을 날려버리고 압축된 인수인계 문서만 들고 새 세션을 시작합니다. 눈덩이처럼 불어나는 토큰 비용(Input Token)을 극적으로 최적화하는 실무 최고의 스킬입니다.
5. **Execution (실행):** 이제 본격적인 코딩입니다. `/tdd` 스킬을 실행하면, AI는 무조건 실패하는 테스트 코드(Red)부터 작성합니다. 개발자가 이를 리뷰하고 승인하면, 그걸 통과하는 실제 코드(Green)를 짜고, 마지막으로 레거시 구조에 맞게 리팩토링(Refactor)합니다.

현업에서 이 워크플로우를 타보면, 마치 깐깐하지만 실력 있는 시니어 동료와 핑퐁을 치며 페어 프로그래밍을 하는 짜릿한 느낌을 받게 됩니다.

### Honest Review & Trade-offs (진짜 장단점과 한계)

물론 10년 차 시니어 개발자의 깐깐한 시선으로 봤을 때 이 시스템이 무조건적인 만병통치약은 아닙니다. 도입 전 반드시 고려해야 할 치명적인 트레이드오프들이 존재합니다.

첫째, **극악의 러닝 커브와 인내심 요구**입니다. 이 시스템은 '빠르게 결과물만 보고 싶은' 도파민 중독형 코딩에는 최악의 궁합입니다. 코드를 한 줄 짜기 위해 AI와 스무고개를 해야 하고, TDD 사이클을 엄격하게 지켜야 합니다. "그냥 알아서 짜줘!"가 통하지 않기 때문에 초기 도입 시 체감되는 개발 속도는 오히려 현저히 떨어집니다.

둘째, **도구에 대한 종속성(Vendor Lock-in) 리스크**입니다. `mattpocock/skills`는 기본적으로 Anthropic의 Claude Code CLI나 MCP(Model Context Protocol) 생태계에 강하게 결합되어 있습니다. 물론 로컬 파일 시스템을 통해 Cursor나 Windsurf에서도 동작은 하지만, 터미널 환경에서 `.claude` 디렉터리의 컨텍스트를 네이티브하게 읽어 들이는 최적의 경험과는 미묘한 단차가 존재합니다.

셋째, **100줄 규칙이 낳는 파편화의 한계**입니다. 스킬 하나당 100줄 이하로 유지하려는 철학 자체는 훌륭합니다. 하지만 거대한 엔터프라이즈급의 복잡한 사내 표준(예: 특정 금융권의 망분리 보안 감사 룰, 사내 커스텀 사내 프레임워크 규칙 등)을 주입하기에는 스킬이 너무 쪼개져 버립니다. 수십 개의 스킬을 관리하다 보면 결국 "지금 상황에서 어떤 스킬을 체인으로 호출해야 할지"를 개발자가 다시 고민해야 하는 메타-오버헤드(Meta-overhead)가 발생합니다.

### Closing Thoughts

결론적으로 `mattpocock/skills`는 단순한 깃허브 레포지토리가 아닙니다. 이는 AI 시대를 맞이한 소프트웨어 엔지니어링 생태계에 던지는 묵직한 선언문입니다. "AI가 코드를 짜주니까 기획과 설계는 대충 느낌대로 해도 된다"는 오만한 착각의 명치를 아주 세게 때려주죠.

오히려 AI가 코드를 순식간에 찍어내는 시대일수록, **무엇을 만들 것인가를 명확히 정의하고(Alignment), 경계를 설정하며(TDD), 시스템의 구조를 철저히 통제하는 '진짜 엔지니어링 역량'**이 기하급수적으로 중요해졌음을 이 레포지토리가 증명하고 있습니다. 

단순히 프롬프트를 깎는 '프롬프트 엔지니어링'의 시대는 저물고 있습니다. 이제 우리는 AI에게 '어떻게 말할 것인가'를 고민할 시간에, 시스템의 빈틈을 '무엇으로 검증할 것인가'를 고민하는 진짜 아키텍트가 되어야 합니다. 현업에서 아직도 AI가 짜준 엉망진창인 코드를 보며 한숨을 쉬고 계신다면, 당장 프로젝트 루트에 `.claude` 폴더를 만들고 이 스킬들을 이식해 보시길 강력히 권합니다. 장담하건대, 여러분의 지긋지긋한 밤샘 디버깅 시간이 절반 이하로 줄어들 것입니다.

## References
- https://github.com/mattpocock/skills
- https://aihero.dev
- https://claude-code.marketplaces
