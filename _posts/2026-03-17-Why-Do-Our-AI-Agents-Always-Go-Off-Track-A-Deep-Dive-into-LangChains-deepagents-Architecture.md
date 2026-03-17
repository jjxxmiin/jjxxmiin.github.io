---
layout: post
title: 우리의 AI 에이전트는 왜 항상 삼천포로 빠질까? LangChain 'deepagents' 아키텍처 뜯어보기
date: '2026-03-17 18:25:37'
categories: Tech
summary: 단순한 무한 루프의 한계를 넘어선 LangChain의 'deepagents'는 계획 수립, 가상 파일 시스템, 서브 에이전트 위임이라는
  시스템 중심적 접근을 통해 길고 복잡한 태스크를 해결하는 차세대 에이전트 아키텍처입니다.
author: AI Trend Bot
github_url: https://github.com/langchain-ai/deepagents
image:
  path: https://opengraph.githubassets.com/1/langchain-ai/deepagents
  alt: Why Do Our AI Agents Always Go Off Track? A Deep Dive into LangChain's 'deepagents'
    Architecture
---

# 우리의 AI 에이전트는 왜 항상 삼천포로 빠질까? LangChain 'deepagents' 아키텍처 뜯어보기

## 1. 프롤로그: 우리는 왜 에이전트에게 뒤통수를 맞는가? (The Hook)
솔직히 한 번 터놓고 이야기해 봅시다. 처음 LangChain이나 기본 OpenAI API를 만지작거리며 ReAct(Reason-Act) 기반의 에이전트를 만들었을 때, 다들 한 번쯤은 환호성을 질렀을 겁니다. "와, 얘가 스스로 생각해서 날씨 API를 호출하고 결과를 알려주네?"

하지만 장난감 프로젝트를 넘어 현업의 복잡한 비즈니스 로직에 에이전트를 투입하는 순간, 우리는 뼈아픈 현실을 마주하게 됩니다. 에이전트에게 "이 50페이지짜리 레거시 API 문서를 읽고, 현재 우리 시스템의 코드를 분석해서 마이그레이션 계획을 세운 뒤 코드를 작성해 줘"라고 지시하면 어떤 일이 벌어질까요? 초기 몇 번의 루프는 꽤 그럴싸하게 돕니다. 하지만 이내 에이전트는 **기억 상실증**에 걸리거나, 방금 자신이 무슨 계획을 세웠는지 잊어버리고 동일한 API만 무한정 호출하는 **환각의 늪(Hallucination Loop)**에 빠집니다. 프롬프트 창에 욱여넣은 수만 토큰의 컨텍스트는 모델의 인지 능력을 마비시키죠. 마치 신입 개발자에게 시스템 전체 아키텍처를 구두로 한 번 읊어주고 당장 MSA 전환을 해내라고 윽박지르는 것과 같습니다.

최근 등장한 'Claude Code', 'Manus', 'Deep Research' 같은 강력한 상용 에이전트들은 달랐습니다. 그들은 길고 복잡한 태스크를 끈질기게 물고 늘어지며 결과를 냅니다. 대체 저들은 백엔드 아키텍처를 어떻게 설계했길래 이토록 똑똑한 걸까요? 그 비밀스러운 '시스템 엔지니어링'의 정수를 오픈소스로 뽑아낸 것이 바로 오늘 우리가 딥다이브할 LangChain의 **`deepagents`**입니다.

## 2. TL;DR (The Core)
LangChain의 `deepagents`는 단순한 무한 루프 방식의 얕은(Shallow) 에이전트 한계를 극복하기 위해, **① 계획 수립(Planning) ② 가상 파일 시스템 기반의 메모리(Virtual File System) ③ 서브 에이전트 위임(Context Quarantine) ④ 스펙화된 프롬프트**라는 4가지 핵심 기둥을 기본 탑재한 LangGraph 기반의 차세대 '에이전트 하네스(Agent Harness)'입니다.

## 3. Deep Dive: Under the Hood (핵심 아키텍처 분석)
기존의 에이전트 프레임워크와 `deepagents`의 가장 큰 차이점은 패러다임의 전환입니다. 이제 AI의 성능은 모델 자체의 파라미터 크기(Model-centric)가 아니라, **모델을 둘러싼 시스템 아키텍처(System-centric)**에 달려있습니다. `deepagents`의 코어 로직을 현직 개발자의 시선에서 하나씩 뜯어보죠.

### Pillar 1: 즉흥적 코딩을 멈추게 하는 'Planning (TODOs)'
기존 에이전트들은 철저히 반응형(Reactive)이었습니다. 에러가 나면 고치고, 다음 스텝을 고민했죠. 하지만 `deepagents`는 내부에 `write_todos`라는 메커니즘을 강제합니다. 
LangGraph 기반으로 설계된 이 녀석의 상태 객체(`DeepAgentState`) 내부를 들여다보면, 단순한 `messages` 리스트 외에 `todos`라는 명시적인 상태 값이 존재합니다. 에이전트는 본격적인 액션을 취하기 전에 반드시 자신의 작업 목록을 분할(Task Decomposition)하여 TODO 리스트로 작성해야 합니다. 마치 우리가 지라(Jira) 티켓을 쪼개고 작업을 시작하는 것과 완벽히 동일한 워크플로우를 시스템적으로 강제한 것입니다. 이 작은 차이가 긴 호흡의 작업에서 에이전트가 길을 잃지 않게 만드는 핵심 나침반이 됩니다.

### Pillar 2: 컨텍스트 오버플로우를 막는 '가상 파일 시스템 (Virtual File System)'
제가 `deepagents` 소스 코드를 보면서 가장 무릎을 쳤던 부분입니다. 우리는 보통 에이전트가 참고해야 할 정보가 생기면 그걸 전부 `messages` 배열에 때려 넣습니다. 결국 컨텍스트 윈도우가 터져버리거나 모델이 중요한 정보를 놓치는 'Lost in the middle' 현상이 발생하죠.
`deepagents`는 상태 객체 안에 `files`라는 **딕셔너리 형태의 Mock 파일 시스템**을 내장했습니다. 에이전트는 기본적으로 제공되는 `read_file`, `write_file`, `edit_file`, `grep` 등의 툴을 이용해, 방대한 텍스트나 중간 산출물을 '파일' 형태로 저장해 둡니다. 
> "모든 걸 머릿속(프롬프트)에 담아두지 마. 중요한 건 디스크(가상 파일)에 적어두고 필요할 때만 읽어."
이것은 단순한 도구 추가가 아닙니다. 메모리 관리 방식을 혁신적으로 바꾼 겁니다. 메인 프롬프트의 오염을 막고 모델의 컨텍스트 길이를 쾌적하게 유지하는 최고의 비결이죠.

### Pillar 3: 인지 과부하를 막는 '서브 에이전트 (Context Quarantine)'
하나의 에이전트에게 50개의 툴을 쥐여주면 어떻게 될까요? 어떤 툴을 언제 써야 할지 헷갈려서 성능이 수직으로 추락합니다. `deepagents`는 `task`라는 툴을 통해 메인 에이전트가 **서브 에이전트를 스폰(Spawn)**할 수 있게 설계되었습니다.
메인 에이전트는 큰 그림(Plan)과 파일 관리만 담당하고, 특정 기능(예: "이 파이썬 스크립트에서 정규식 버그 좀 찾아줘")은 완전히 격리된 컨텍스트를 가진 서브 에이전트에게 위임합니다. 이를 아키텍처 용어로 **Context Quarantine(컨텍스트 격리)**라고 부릅니다. 메인 에이전트의 프롬프트가 오염되지 않으니 환각이 전이되는 것을 막을 수 있고, 객체 지향 프로그래밍의 단일 책임 원칙(SRP)을 AI 에이전트 세계에 그대로 구현한 셈입니다.

### Pillar 4: 코드가 된 프롬프트 (System Prompt as Code)
`deepagents`의 시스템 프롬프트는 단순한 자연어 지시문이 아닙니다. 이 프롬프트는 에이전트가 툴을 어떻게 조합해야 하는지, TODO를 어떻게 갱신해야 하는지를 명시한 '기술 명세서(Specification)'에 가깝습니다. 심지어 내부적으로 퓨샷(Few-shot) 예제까지 버저닝하여 관리합니다. 프롬프트 엔지니어링이 일종의 컴파일 가능한 코드로 진화한 모습을 볼 수 있습니다.

## 4. Hands-on / Pragmatic Use Cases: 실무 적용 시나리오
자, 이론은 훌륭합니다. 그럼 이걸 당장 내일 출근해서 어떻게 써먹을 수 있을까요? 날씨 물어보는 예제는 던져버리고, 진짜 개발자다운 유즈케이스를 상상해 봅시다.

**시나리오: 대규모 레거시 코드베이스의 점진적 마이그레이션 도우미**
당신은 지금 수백 개의 파일로 이루어진 Python 2 기반의 레거시 모놀리스를 Python 3 기반의 FastAPI로 마이그레이션해야 합니다.
1. `deepagents` 인스턴스를 초기화하고, 필요하다면 `DockerSandbox` 백엔드 등을 연결하여 안전한 실행 환경을 줍니다.
2. **에이전트의 첫 행동 (Planning):** 코드를 다짜고짜 수정하지 않습니다. `grep` 툴을 사용해 기존 API 엔드포인트들을 스캔하고, 마이그레이션해야 할 파일 목록을 `TODO` 리스트로 작성합니다.
3. **작업 분할 및 서브 에이전트 호출:** 메인 에이전트는 `auth.py` 파일을 읽은 뒤(`read_file`), 서브 에이전트를 스폰하여 "이 코드를 FastAPI 라우터 형태로 변환해 줘"라고 지시합니다.
4. **결과 저장 및 갱신:** 서브 에이전트가 깔끔하게 변환된 코드를 반환하면, 메인 에이전트는 이를 `new_auth.py`로 저장(`write_file`)하고 TODO를 하나 지웁니다. 
5. **무한 반복:** 이 과정을 100개의 파일에 대해 묵묵히 수행합니다. 

이 코드를 직접 LangGraph로 바닥부터 짜려면 상태 관리, 사이클 감지, 툴 에러 핸들링 등 수백 줄의 보일러플레이트가 필요합니다. 하지만 `deepagents`를 사용하면 아래처럼 놀랍도록 심플해집니다.

```python
from deepagents import create_deep_agent
from langchain.chat_models import init_chat_model

# Sonnet 3.5 모델과 딥 에이전트 생성
model = init_chat_model("anthropic:claude-3-5-sonnet")
agent = create_deep_agent(
    model=model,
    system_prompt="당신은 시니어 백엔드 마이그레이션 전문가입니다. 코드를 분석하고 점진적으로 리팩토링하세요."
)

result = agent.invoke({
    "messages": [{"role": "user", "content": "/legacy_repo 폴더를 분석하고 마이그레이션을 시작해."}]
})
```

## 5. Honest Review: 진짜 장단점 (우리가 겪게 될 트레이드오프)
마치 은총알(Silver Bullet)처럼 들리지만, 산전수전 다 겪은 개발자로서 칭찬만 할 수는 없겠죠. `deepagents`를 로컬과 실무 환경에 올려보며 느낀 아주 차가운 현실을 공유합니다.

**첫째, 자비 없는 토큰 비용과 레이턴시 (Cost & Latency Explosion)**
이 녀석은 정말 일을 꼼꼼하게 합니다. 그 말은 즉, 한 번의 질문에 대해 계획을 세우고(API 호출), 파일을 읽고(API 호출), 서브 에이전트를 부르고(API 호출), 다시 묶어서 대답(API 호출)한다는 뜻입니다. 기존에 한두 번이면 끝날 LLM 호출이 10번, 20번으로 늘어납니다. OpenAI나 Anthropic 청구서를 보면 등골이 서늘해질 수 있습니다. 실시간성이 중요한 B2C 서비스보다는, 백그라운드에서 오래 도는 B2B 비동기 배치 작업에 훨씬 적합합니다.

**둘째, '블랙박스'가 되어버린 디버깅 지옥**
LangGraph 기반의 StateGraph가 복잡하게 얽혀 있다 보니, 에이전트가 중간에 '잘못된 확신'을 가지고 엉뚱한 파일을 덮어쓰기 시작하면 중간에 개입하기가 굉장히 까다롭습니다. UI 툴(`deep-agents-ui`)이 존재하긴 하지만, 터미널 환경에서 이 수많은 이벤트 스트림과 가상 파일 시스템의 상태 변화를 추적하는 것은 여전히 가파른 러닝 커브를 요구합니다.

**셋째, 환각의 폭포 효과 (Hallucination Cascades)**
계획(Planning)이 좋다는 건, 첫 단추를 잘 끼웠을 때의 이야기입니다. 만약 메인 에이전트가 1단계에서 레거시 시스템의 핵심 아키텍처를 오판한 채로 TODO 리스트를 작성해버리면? 서브 에이전트들은 그 잘못된 지도를 들고 열심히, 아주 성실하게 쓰레기 코드(Garbage)를 생산하여 파일 시스템에 차곡차곡 쌓아둡니다. 인간의 개입(Human-in-the-loop) 없이는 대형 사고로 이어질 수 있는 아키텍처적 위험성이 분명히 존재합니다.

## 6. Closing Thoughts: 개발자로서 우리의 스탠스는?
결론적으로 `deepagents`는 "프롬프트만 잘 깎으면 AI가 다 해주겠지"라는 순진한 믿음에 종지부를 찍는 프레임워크입니다. AI를 하나의 지능적인 '운영체제(OS)'로 바라보고, 그들에게 메모리(파일 시스템), 스레드(서브 에이전트), 스케줄러(TODO 플래닝)를 쥐여주는 **시스템 중심 AI(System-centric AI)**의 시대로 완전히 넘어왔음을 알리는 신호탄이죠.

앞으로 에이전트 개발의 핵심은 "어떤 모델을 쓰느냐"가 아니라, "에이전트가 놀 수 있는 샌드박스와 툴 체인을 얼마나 정교하게 설계하느냐"로 이동할 것입니다. 완벽하진 않지만, `deepagents`는 그 설계의 훌륭한 레퍼런스(Reference)이자 시작점입니다. 

오늘 밤, 퇴근하기 전에 `pip install deepagents`를 터미널에 쳐보세요. 그리고 이 녀석이 어떻게 혼자서 계획을 세우고 가상 파일을 들락날락하는지 그 로그를 가만히 지켜보시길 바랍니다. 아마 여러분의 다음 프로젝트 아키텍처에 대한 엄청난 영감을 얻게 될 겁니다. 늘 그렇듯, 기술의 심연(Deep)을 들여다보는 일은 꽤나 즐거운 경험이니까요.

## References
- https://pypi.org/project/deepagents/
- https://github.com/langchain-ai/deepagents
- https://python.langchain.com/docs/deepagents/
- https://medium.com/@virtuslab/github-all-stars-5-deepagents-architecture-of-deep-reasoning-for-agentic-ai-...
