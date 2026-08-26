---
layout: post
title: "Andrej Karpathy Skills는 AI 코딩 범위를 줄일까: 지침, 검증, 질문 한계"
date: '2026-04-13 07:02:18'
categories: Tech
tags:
  - AI코딩
  - AI트렌드
summary: "Andrej Karpathy Skills의 Think Before Coding, Surgical Changes, Goal-Driven 지침이 수정 범위와 검증을 돕는 방식, prompt만으로 보장할 수 없는 한계를 분석합니다."
description: "Andrej Karpathy Skills의 coding guideline을 ambiguity, surgical diff, test gate, budget 관점에서 읽고, prompt 지침과 실제 sandbox, review 통제를 구분합니다."
github_url: https://github.com/forrestchang/andrej-karpathy-skills
faq:
  - question: "CLAUDE.md나 rules file을 추가하면 AI가 관련 없는 코드를 절대 바꾸지 않나요?"
    answer: "아닙니다. 지침은 행동 경향을 바꿀 뿐 보장이 아니므로 허용 경로, diff 검사, test와 사람 review를 별도 gate로 둬야 합니다."
  - question: "모호할 때 항상 질문하게 하는 것이 좋은가요?"
    answer: "되돌리기 쉬운 작은 선택까지 모두 질문하면 지연이 커지므로, 위험, 범위, 요구사항을 바꾸는 모호성만 사람에게 올리는 기준이 필요합니다."
  - question: "Goal-Driven loop는 어떤 종료 조건이 필요한가요?"
    answer: "성공 test뿐 아니라 최대 반복, 시간, token, diff, 같은 오류 반복과 test 변경 승인 조건을 code 수준에서 고정해야 합니다."
image:
  path: https://opengraph.githubassets.com/1/forrestchang/andrej-karpathy-skills
  alt: "forrestchang/andrej-karpathy-skills GitHub 저장소 대표 이미지"
---

**Andrej Karpathy Skills는 코딩 Agent에게 가정 명시, 작은 diff와 검증 가능한 완료 조건을 반복해서 요구하는 지침 모음입니다.** 관련 없는 refactoring과 조용한 가정을 줄이는 데 도움을 줄 수 있지만 prompt만으로 수정 범위나 안전을 강제하지는 못합니다. 허용 경로, test, budget, review를 외부 gate로 두고 기존 방식과 비교해야 합니다.

[프로젝트 저장소](https://github.com/forrestchang/andrej-karpathy-skills)는 `.cursorrules`나 `CLAUDE.md` 같은 지침 파일에 행동 원칙을 넣는 접근을 보여 줍니다. 이름에 포함된 인물과 실제 저자, 공식성은 동일한 뜻이 아니므로 attribution과 지원 범위는 저장소의 maintainer, license, 문서에서 확인해야 합니다.

## 네 가지 지침은 어떤 실패를 줄이려 할까

이 프로젝트의 중심은 무거운 runtime보다 모델에 전달하는 Markdown 지침입니다. 효과를 평가할 때는 “말을 잘 듣는다”는 인상보다 관련 없는 변경, 질문 지연, test 통과와 review 수정량의 변화를 봅니다.

중요한 문제 중 하나는 모호한 상황에서 모델이 선택한 가정을 알리지 않고 구현하는 것입니다. 지침은 가정을 명시하고 위험한 선택은 질문하도록 유도합니다. 그러나 system prompt가 AST 수정 권한을 기술적으로 제한하는 것은 아니며 실제 file permission과 diff gate가 필요합니다.

| 비교 항목 | 기존 AI 코딩 어시스턴트 (Default) | Andrej Karpathy Skills 적용 시 |
| :--- | :--- | :--- |
| **모호성 처리** | 임의로 가정을 세우고 조용히 코드를 자동 완성함 | **Think Before Coding**: 가정을 명시하고, 혼란스러우면 즉시 멈추고 사용자에게 질문함 |
| **코드 수정 범위** | 주변 코드와 주석을 "개선"하려 들며 광범위한 수정을 가함 | **Surgical Changes**: 요청받은 라인만 '외과 수술처럼' 도려내고 수정하며, 기존 스타일을 철저히 유지함 |
| **설계 철학** | 확장성을 고려해 추상화된 패턴과 오버엔지니어링 적용 | **Simplicity First**: 추측성 기능(Speculative features)을 배제하고 최소한의 코드로 구현 (YAGNI 원칙 강제) |
| **검증 방식** | "완료했습니다. 코드를 확인해보세요."라며 즉시 결과물 제출 | **Goal-Driven Execution**: 테스트 등 성공 기준을 먼저 정의하고, 이를 통과할 때까지 자율 루프 실행 |

연결된 [Autoresearch 저장소](https://github.com/karpathy/autoresearch)는 성공 기준을 두고 반복 실험하는 아이디어를 살펴볼 별도 근거입니다. 이 아이디어를 코딩 작업에 옮길 때는 “어떻게 하라”는 세부 방법보다 어떤 test와 지표가 성공인지 먼저 정할 수 있습니다. 다만 반복 실행 권한과 종료 조건은 지침 문장만으로 맡기지 않습니다.

아래 JSON은 원칙을 구조화한 예시입니다. 특정 도구가 이 schema를 그대로 읽거나 `enforcement_level`을 기술적 권한으로 강제한다는 보장은 없으므로 선택한 client의 실제 지침 형식을 확인해야 합니다.

```json
{
  "karpathy_guidelines": {
    "alwaysApply": true,
    "principles": [
      {
        "name": "Think Before Coding",
        "directive": "절대 가정하지 마라. 해석이 갈릴 경우 조용히 선택하지 말고, 트레이드오프를 명시하여 사용자에게 질문하라. 불확실하면 멈춰라."
      },
      {
        "name": "Surgical Changes",
        "directive": "고장나지 않은 것을 리팩토링하지 마라. 당신의 방식과 달라도 기존 코드 스타일을 100% 매칭하라. 관계없는 데드코드를 발견하면 삭제하지 말고 언급만 하라."
      },
      {
        "name": "Goal-Driven Execution",
        "directive": "명령형 지시를 검증 가능한 목표로 변환하라. 예: '버그 수정' -> '버그를 재현하는 테스트 작성 후 통과'. 다단계 작업은 반드시 '1. [Step] -> verify: [check]' 형태의 계획을 먼저 출력하고 실행하라."
      }
    ],
    "enforcement_level": "strict"
  }
}
```

이 설정은 행동을 유도하지만 test 전 code 수정을 물리적으로 막는 lock은 아닙니다. “계획 먼저”를 출력한 뒤 바로 넓은 diff를 만들 수도 있고, 기존 test를 약화해 녹색 결과를 만들 수도 있습니다. 읽기, 쓰기 허용 경로, test command와 test file 변경 정책을 실행기에서 검사해야 지침이 운영 통제가 됩니다.

모호성도 모두 같은 위험이 아닙니다. 변수 이름처럼 되돌리기 쉬운 지역 선택은 기존 style을 따라 진행하고 기록할 수 있지만 API contract, data migration이나 외부 side effect를 바꾸는 선택은 멈추고 질문해야 합니다. 질문 기준이 없으면 작은 결정마다 사람을 호출해 생산성이 떨어집니다.

Surgical Change는 단순히 줄 수가 적다는 뜻도 아닙니다. 필요한 test와 migration까지 빠뜨린 작은 diff는 안전하지 않습니다. 요구사항을 충족하는 최소 범위를 먼저 적고 그 범위 밖 파일, format 변화와 dependency 변경을 별도 review 대상으로 표시합니다.

## 결제 모듈 변경에 적용하면 무엇을 확인할까

가상의 A사 PG 연동을 예로 들면 “새 provider 추가”만으로는 범위가 모호합니다. 기존 B, C provider는 변경하지 않는지, 새 configuration과 callback, test fixture가 필요한지, database migration과 secret 이름이 무엇인지 먼저 적습니다. 인접 code의 대규모 refactoring은 별도 제안으로 남기고 현재 작업 diff에 섞지 않습니다.

성공 기준은 숫자를 임의로 만들어 선언하지 않습니다. 기존 provider contract test를 유지하고, A사의 성공, 거절, timeout, 중복 callback 사례가 통과하며, 실제 업무가 요구한 latency와 idempotency 조건을 만족하는 식으로 정합니다. test를 작성한 Agent가 production code와 같은 잘못된 가정을 공유할 수 있으므로 specification과 사람이 review합니다.

cache 추가 같은 성능 작업도 hit rate 하나로 끝내지 않습니다. cache miss, stale data, 장애 시 fallback, key 충돌과 invalidation을 포함하고 load test 환경과 baseline을 기록합니다. Agent가 목표 숫자만 맞추려고 TTL을 늘려 오래된 결제 상태를 반환하지 않는지 business correctness를 함께 봅니다.

| 지침 | 실행기에서 보완할 gate | 측정할 결과 |
|---|---|---|
| Think Before Coding | 위험한 모호성 분류, 승인 | 불필요한 질문과 잘못된 가정 수 |
| Surgical Changes | 허용 path, diff 크기, dependency 검사 | 무관 변경, review 수정량 |
| Simplicity First | 새 abstraction, dependency 사유 | code 복잡도와 누락된 요구 |
| Goal-Driven | 고정 test, budget, 중단 상태 | 통과율, 재시도, 사람 재작업 |

## 지침이 실패하는 조건은 무엇일까

첫째는 질문 과다입니다. `null` 가능성처럼 기존 type, test에서 확인할 수 있는 사실까지 매번 사용자에게 묻는다면 속도가 느려집니다. Agent가 먼저 저장소 근거를 찾고, 되돌릴 수 없거나 요구 의미를 바꾸는 선택만 질문하도록 기준을 둡니다.

둘째는 반복 비용입니다. 계획, test, 수정 cycle이 길어지면 model call뿐 아니라 sandbox와 사람 검토 시간도 늘어납니다. 최대 turn, 시간, token, 같은 오류 횟수와 diff 크기를 code로 제한하고 상한에 닿으면 실패 원인과 마지막 상태를 사람에게 넘깁니다.

셋째는 지침 충돌과 context 부담입니다. 긴 rule file이 업무별 지침, repository 문서와 겹치면 우선순위가 불명확해질 수 있습니다. 핵심 원칙은 짧게 두고 언어, module별 규칙은 필요한 때만 읽게 하며, model, rule version마다 고정 과제로 회귀 평가합니다.

## 도입은 rule file 유무가 아니라 diff 결과로 판단한다

실제 저장소의 작은 이슈 20개 정도를 기존 설정과 지침 설정으로 나눠 실행합니다. 정답 test, 관련 없는 파일, 줄 변경, dependency 추가, 질문 수, token, 시간, 사람이 고친 diff와 되돌림을 같은 기준으로 측정합니다. 지침을 추가한 뒤 질문만 늘고 무관 변경이 줄지 않는다면 문구를 더 길게 만드는 대신 gate와 작업 정의를 고쳐야 합니다.

첫 적용은 비핵심 branch와 제한된 workspace에서 합니다. Agent는 운영 secret, 배포 권한을 갖지 않고 test 변경은 별도 review 대상으로 둡니다. rule file의 원칙을 어겼을 때 실행기가 이를 감지할 수 있어야 prompt가 단순한 희망사항을 넘어 팀의 작업 절차와 연결됩니다.

이 프로젝트에서 가져갈 핵심은 유명인의 이름이나 “완벽한 통제” 주장이 아니라 가정을 드러내고, 필요한 만큼만 고치며, 완료를 검증 가능한 상태로 정의하라는 원칙입니다. 이 원칙도 모든 업무에 동일하게 강제하기보다 위험과 되돌릴 수 있는 정도에 맞춰 조절해야 합니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [공식 GitHub 저장소](https://github.com/forrestchang/andrej-karpathy-skills)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [Nanoclaw는 가벼운 개인 AI 에이전트인가: 구조, 격리, 도입 가이드]({% post_url 2026-02-23-Nanoclaw-The-Lightweight-AI-Agent %}) — Nanoclaw가 작은 코드베이스와 컨테이너 격리로 개인용 에이전트를 구성하는 방식, 설치 흐름과 권한, 업데이트 검증 기준을 정리합니다.
- [Agent Safehouse로 macOS AI 에이전트를 가둘 수 있을까: Deny-first와 예외 권한]({% post_url 2026-03-11-Agent-Safehouse-Deep-Dive-Leashing-Your-AI-Agents-at-the-Kernel-Level-on-macOS %}) — macOS Seatbelt, sandbox-exec로 프로젝트 밖 접근을 차단하는 Agent Safehouse의 구조와, 네트워크, 홈 설정, IPC 예외 및 완전 격리가 아닌 한계를 정리합니다.
- [CoCo는 이미지 속 글자, 배치를 코드로 고칠까: +68.83%와 Sandbox 비용]({% post_url 2026-03-11-CoCo--Code-as-CoT-for-Text-to-Image-Preview-and-Rare-Concept-Generation %}) — 자연어를 실행 코드와 Draft Image로 바꾸는 CoCo의 3단계 구조, 두 벤치마크 개선 수치와 코드 실행 보안, 지연, 복잡한 장면 한계를 정리합니다.
<!-- internal-links:end -->

## 자주 묻는 질문

### CLAUDE.md나 rules file을 추가하면 AI가 관련 없는 코드를 절대 바꾸지 않나요?

아닙니다. 지침은 행동 경향을 바꿀 뿐 보장이 아니므로 허용 경로, diff 검사, test와 사람 review를 별도 gate로 둬야 합니다.

### 모호할 때 항상 질문하게 하는 것이 좋은가요?

되돌리기 쉬운 작은 선택까지 모두 질문하면 지연이 커지므로, 위험, 범위, 요구사항을 바꾸는 모호성만 사람에게 올리는 기준이 필요합니다.

### Goal-Driven loop는 어떤 종료 조건이 필요한가요?

성공 test뿐 아니라 최대 반복, 시간, token, diff, 같은 오류 반복과 test 변경 승인 조건을 code 수준에서 고정해야 합니다.

## References
- [GitHub 저장소](https://github.com/forrestchang/andrej-karpathy-skills)
- [GitHub 저장소](https://github.com/karpathy/autoresearch)
- [aakashg.com 원문](https://aakashg.com/)
- [open-vsx.org 원문](https://open-vsx.org/extension/MichielWBeijen/andrej-karpathy-skills-cursor-vscode)
