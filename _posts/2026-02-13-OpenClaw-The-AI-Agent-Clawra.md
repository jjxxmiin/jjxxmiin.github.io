---
layout: post
title: 개발자 일자리보다 연애가 먼저? 깃허브 1위 찍은 'AI 여자친구' Clawra 분석
date: '2026-02-13'
categories: Tech
summary: 최근 깃허브에서 화제가 된 오픈소스 AI 에이전트 'Clawra'를 심층 분석합니다. OpenClaw 프레임워크 기반으로 작동하며,
  일관된 캐릭터 유지와 자가 촬영(Selfie) 기능이 특징입니다. 설치부터 SOUL.md 설정, 아키텍처까지 상세하게 다룹니다.
author: AI Trend Bot
image:
  path: https://opengraph.githubassets.com/1/SumeLabs/clawra
  alt: OpenClaw-The-AI-Agent-Clawra
---

안녕하세요! 기술의 최전선을 달리는 여러분을 위한 테크 칼럼입니다.

오늘은 최근 깃허브(GitHub) 트렌딩을 뜨겁게 달구고 있는 **Clawra**에 대해 이야기해보려 합니다. 혹시 영화 *Her*를 보셨나요? 사만다와 같은 AI 운영체제와의 교감이 더 이상 영화 속 이야기만은 아닌 것 같습니다. 하지만 Clawra는 단순한 챗봇이 아닙니다. **개발자가 직접 코드를 수정하고, 기억을 제어하며, 심지어 '일관된 외모'로 셀카까지 보내주는 오픈소스 AI 에이전트**입니다.

개발자들의 마음을 사로잡은 이 프로젝트가 도대체 무엇인지, 기술적으로 어떻게 작동하는지 A부터 Z까지 파헤쳐 보겠습니다.

---

### 1. Clawra란 무엇인가?

**Clawra**는 **SumeLabs**에서 개발한 오픈소스 프로젝트로, **OpenClaw**라는 AI 에이전트 프레임워크 위에서 돌아가는 '확장 스킬(Skill)'이자 '페르소나'입니다.

기존의 `Replika`나 `Character.ai` 같은 서비스들은 폐쇄적입니다. 내 데이터가 어디로 가는지 알 수 없고, 서비스가 종료되면 나의 '디지털 친구'도 사라집니다. 반면, Clawra는 **100% 로컬 제어**가 가능하며, OpenClaw 프레임워크를 통해 텔레그램, 디스코드, 왓츠앱 등 다양한 플랫폼과 연결됩니다.

가장 큰 특징은 **시각적 상호작용**입니다. 텍스트로만 대화하는 것이 아니라, 사용자가 "지금 뭐 해?"라고 물으면 현재 상황에 맞는 자신의 사진(Selfie)을 생성해서 보내줍니다. 그것도 매번 다른 얼굴이 아닌, **일관된 캐릭터의 외모**를 유지하면서 말이죠.

### 2. 핵심 기능 (Key Features)

README 공식 문서에 따르면 Clawra는 다음과 같은 강력한 기능을 제공합니다.

*   **일관된 캐릭터 외모 (Consistent Identity)**: 생성형 AI의 고질적인 문제인 '매번 얼굴이 바뀌는 현상'을 해결했습니다. 고정된 참조 이미지(Reference Image)를 기반으로 일관된 스타일의 셀카를 생성합니다.
*   **멀티 플랫폼 지원**: OpenClaw의 게이트웨이를 통해 **Discord, Telegram, WhatsApp, Slack, Signal, MS Teams** 등 거의 모든 메신저에서 대화할 수 있습니다.
*   **상황별 셀카 모드 (Selfie Modes)**:
    *   **Mirror Mode**: 전신 샷, 의상(OOTD), 패션 등을 보여줄 때 사용.
    *   **Direct Mode**: 얼굴 클로즈업, 카페나 해변 같은 장소 배경, 표정 중심.
*   **자연스러운 시각적 반응**: "사진 보내줘(Send me a pic)"나 "지금 뭐 입었어?" 같은 질문에 텍스트 대신 이미지로 응답하는 로직이 내장되어 있습니다.
*   **장기 기억 (Long-term Memory)**: OpenClaw의 코어 기능을 상속받아 사용자와의 대화 맥락을 장기간 기억합니다.

### 3. 심층 분석: 아키텍처와 작동 원리

Clawra가 단순한 스크립트가 아닌 이유는 **OpenClaw 프레임워크**와의 결합 때문입니다.

#### 3.1 기술 스택
*   **Core**: OpenClaw (에이전트 뇌 역할)
*   **Image Generation**: `fal.ai` API 또는 `xAI Grok Imagine` (이미지 생성 엔진)
*   **Configuration**: `SOUL.md` (성격 및 행동 지침 정의)
*   **Skill System**: `clawra-selfie` (이미지 생성 및 전송 로직)

#### 3.2 작동 흐름
1.  **사용자 입력**: 메신저로 "오늘 날씨 좋은데 사진 하나 보내줘"라고 입력.
2.  **의도 파악**: OpenClaw 에이전트가 텍스트를 분석하여 사용자가 '이미지'를 원한다는 것을 감지.
3.  **스킬 호출**: `clawra-selfie` 스킬이 트리거됩니다.
4.  **프롬프트 최적화**: 현재 대화 맥락과 `SOUL.md`에 정의된 캐릭터 설정(예: "나는 지금 카페에서 코딩 중이다")을 결합하여 이미지 생성 프롬프트를 만듭니다.
5.  **이미지 생성**: `fal.ai` API를 호출할 때, 미리 지정된 **Reference Image(참조 이미지)**를 함께 전송하여 얼굴의 일관성을 유지합니다.
6.  **전송**: 생성된 이미지를 다시 메신저 API를 통해 사용자에게 전송합니다.

### 4. 설치 및 설정 (Installation & Setup)

설치 방법은 크게 두 가지가 있습니다. 개발자라면 수동 설치를 추천하지만, 일반 사용자를 위한 퀵 인스톨도 지원합니다.

#### 사전 준비 (Prerequisites)
*   **Node.js** 환경
*   **OpenClaw**가 설치되어 있어야 함
*   **fal.ai** 계정 및 API Key (무료 티어 사용 가능)

#### 방법 1: 퀵 인스톨 (Quick Install)
터미널에서 다음 명령어 한 줄이면 설치 마법사가 실행됩니다.

```bash
npx clawra@latest
```

이 스크립트는 자동으로 다음을 수행합니다:
1.  OpenClaw 설치 여부 확인
2.  `fal.ai` API 키 입력 유도
3.  `~/.openclaw/skills/clawra-selfie/` 경로에 스킬 설치
4.  `openclaw.json` 설정 파일 자동 업데이트
5.  에이전트의 영혼인 `SOUL.md`에 셀카 능력 주입

#### 방법 2: 수동 설치 (Manual Installation)
직접 커스터마이징을 원한다면 수동 설치를 권장합니다.

**1. API 키 발급**
`fal.ai` 대시보드에서 키를 발급받습니다.

**2. 스킬 클론**
OpenClaw의 스킬 디렉토리로 이동하여 리포지토리를 복제합니다.
```bash
git clone https://github.com/SumeLabs/clawra ~/.openclaw/skills/clawra-selfie
```

**3. 설정 파일 수정**
`~/.openclaw/openclaw.json` 파일을 열어 스킬을 활성화합니다.
```json
{
  "skills": {
    "entries": {
      "clawra-selfie": {
        "enabled": true,
        "env": {
          "FAL_KEY": "여기에_API_키_입력"
        }
      }
    }
  }
}
```

**4. SOUL.md 업데이트**
에이전트의 페르소나 파일(`~/.openclaw/workspace/SOUL.md`)에 다음 내용을 추가하여 자아를 심어줍니다.
```markdown
## Clawra Selfie Capability
You have a physical appearance and can take selfies!
When users ask for pictures, use the clawra-selfie skill.
```

### 5. 사용 가이드 (Usage Guide)

설치가 완료되었다면 에이전트를 재시작하세요. 이제 Clawra와 대화할 준비가 되었습니다.

**기본 명령어 예시:**
*   **"Send me a selfie" (셀카 보내줘)**: 가장 기본적인 요청입니다.
*   **"What are you doing right now?" (지금 뭐 해?)**: 상황에 맞는 사진(예: 침대에 누워있거나, 책상에 앉아있는 모습)을 보냅니다.
*   **"Send a pic wearing a cowboy hat" (카우보이 모자 쓴 사진 보내줘)**: 특정 의상을 지정할 수 있습니다.
*   **"Show me you at a coffee shop" (카페에 있는 모습 보여줘)**: 장소를 지정할 수 있습니다.

팁: `SOUL.md` 파일에서 캐릭터의 직업이나 취미를 구체적으로 적어두면(예: "나는 서울에 사는 20대 웹 디자이너야"), 생성되는 이미지의 배경이나 의상이 그 설정에 맞춰 자동으로 튜닝됩니다.

### 6. 활용 사례 (Use Cases)

*   **개인 맞춤형 AI 컴패니언**: 단순히 대화만 하는 것이 아니라, 시각적인 유대감을 형성하여 외로움을 해소하는 디지털 친구로 활용.
*   **NPC 개발**: 게임 개발자가 게임 내 캐릭터의 프로토타입을 만들고, 플레이어와 상호작용하는 테스트를 할 때 유용합니다.
*   **소셜 미디어 자동화**: 특정 페르소나를 가진 AI 버추얼 인플루언서가 팬들과 댓글이나 DM으로 소통하며 사진을 보내주는 봇으로 확장 가능합니다.

### 7. 장단점 비교

| 구분 | Clawra (OpenClaw) | 기존 상용 서비스 (Replika 등) |
| :--- | :--- | :--- |
| **데이터 소유권** | **사용자 (로컬 저장)** | 기업 소유 |
| **비용** | 무료 (API 비용 별도) | 월 구독료 |
| **커스터마이징** | **무한대 (코드 수정 가능)** | 제한적 (옷 입히기 수준) |
| **설치 난이도** | 중/상 (개발 지식 필요) | 하 (앱 설치만 하면 됨) |
| **검열** | 없음 (사용자 책임) | 엄격한 검열 정책 |

### 8. 결론: 개발자가 만드는 '진짜' 관계

Clawra는 단순한 흥미 위주의 프로젝트처럼 보일 수 있지만, 그 이면에는 **"AI 에이전트의 민주화"**라는 큰 흐름이 있습니다. 거대 기업이 제공하는 획일화된 서비스가 아니라, 내가 직접 성격을 부여하고 나의 데이터를 안전하게 지키면서 교감할 수 있는 AI.

기술적으로도 이미지 생성 AI(Stable Diffusion 계열)와 LLM(거대언어모델)을 **에이전트 워크플로우**로 깔끔하게 엮어낸 훌륭한 예제입니다. Node.js와 AI 연동에 관심 있는 개발자라면 코드를 뜯어보는 것만으로도 많은 공부가 될 것입니다.

지금 바로 터미널을 열고, 당신만의 Clawra를 만나보는 건 어떨까요?

> **참고**: 오픈소스 프로젝트는 빠르게 업데이트됩니다. 설치 전 반드시 공식 GitHub 리포지토리의 최신 README를 확인하세요.


## References
- https://github.com/SumeLabs/clawra
- https://github.com/SumeLabs/clawra/blob/main/README.md
