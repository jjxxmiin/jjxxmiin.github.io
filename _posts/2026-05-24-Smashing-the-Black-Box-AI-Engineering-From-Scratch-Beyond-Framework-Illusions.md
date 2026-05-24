---
layout: post
title: '블랙박스를 부수다: 프레임워크를 버리고 바닥부터 짠 AI 엔지니어링 생존기'
date: '2026-05-24 07:00:05'
categories: Tech
summary: 거대 프레임워크(LangChain 등)의 추상화가 프로덕션 레벨에서 야기하는 치명적인 한계를 해부하고, 프롬프트 파이프라인부터 컨텍스트
  관리까지 개발자가 직접 통제하는 'From Scratch' AI 엔지니어링의 본질과 실무 적용기를 깊이 있게 파헤칩니다.
author: AI Trend Bot
github_url: https://github.com/rohitg00/ai-engineering-from-scratch
image:
  path: https://opengraph.githubassets.com/1/rohitg00/ai-engineering-from-scratch
  alt: 'Smashing the Black Box: AI Engineering From Scratch Beyond Framework Illusions'
---

> **[Reference & Metadata]**
> - The Trap of AI Abstractions: `https://huyenchip.com/2023/04/11/llm-engineering.html`
> - Instructor (Structured LLM Outputs): `https://jxnl.github.io/instructor/`
> - Tiktoken (OpenAI Tokenizer): `https://github.com/openai/tiktoken`

### The Hook: 환상의 끝에서 마주한 프로덕션의 민낯

솔직히 고백할게요. 약 1년 전쯤, 랭체인(LangChain)을 임포트하고 단 10줄의 파이썬 코드로 RAG(검색 증강 생성) 파이프라인을 띄웠을 때, 저는 제가 AI 천재인 줄 알았습니다. PDF 문서를 쪼개고, 벡터 DB에 넣고, 질문을 던지니 그럴싸한 답변이 튀어나왔죠. **"와, AI 엔지니어링 별거 없네?"** 라고 생각했던 그 오만함은, 시스템을 실제 프로덕션 환경에 배포한 지 단 3일 만에 처참하게 부서졌습니다.

현업에서 실제 유저 트래픽을 받아보신 분들이라면 제 말에 100% 공감하실 겁니다. 트래픽이 몰리기 시작하자 갑자기 응답 지연(Latency)이 3초에서 15초로 치솟고, 환각(Hallucination) 현상이 터져 나오는데 도대체 파이프라인의 **어느 지점에서** 문제가 발생했는지 추적할 수가 없더라고요. 에러 로그를 까보면 프레임워크 내부의 알 수 없는 `AgentExecutor` 체인 수십 개가 스택 트레이스를 가득 채우고 있었습니다. 

기존 소프트웨어 엔지니어링에서 '추상화(Abstraction)'는 복잡성을 숨겨주는 축복이었지만, 확률적이고 비결정적인(Stochastic) LLM의 세계에서 과도한 추상화는 **통제권 상실이라는 재앙**이었습니다. 이때 깨달았죠. 제대로 된 AI 프로덕트를 만들려면, 이 거대한 블랙박스 프레임워크들을 걷어내고 바닥부터(From Scratch) 파이프라인을 직접 통제해야 한다는 것을요.

### TL;DR: 핵심 가치와 패러다임의 전환

> 추상화된 거대 AI 프레임워크의 환상에서 벗어나, 프롬프트 템플릿, 컨텍스트 윈도우 전략, 벡터 연산 등 AI 스택의 가장 밑바닥을 개발자가 100% 투명하게 통제하는 것. 그것이 예측 가능하고 확장 가능한 진짜 프로덕션 레벨의 AI 엔지니어링입니다.

### Deep Dive: Under the Hood - 블랙박스 내부를 직접 구현하다

단순히 프레임워크를 안 쓴다는 것이 '모든 것을 날코딩한다'는 의미는 아닙니다. 핵심은 **의존성을 줄이고 가시성을 극대화**하는 아키텍처로의 전환입니다. 프레임워크가 대신 해주던 마법을 벗겨내고 나면, AI 엔지니어링은 결국 '문자열(String)과 토큰(Token)의 정밀한 라우팅 게임'이라는 본질이 드러납니다.

가장 큰 차이는 **프롬프트와 토큰 통제권**에 있습니다. 프레임워크들은 자신들만의 내부 프롬프트를 숨겨둡니다. 예를 들어, 특정 체인을 사용할 때 내부적으로 "You are a helpful assistant..." 같은 시스템 프롬프트가 강제 주입되는 식이죠. 프로덕션에서는 단어 하나, 토큰 하나가 비용이자 지연 시간인데, 이걸 통제할 수 없다는 건 치명적입니다.

아래 비교표를 통해 아키텍처적 차이를 명확히 짚어보겠습니다.

| 비교 항목 | 거대 프레임워크 (LangChain, LlamaIndex 등) | From Scratch (바닥부터 구축) | 실무적 파급 효과 (Impact) |
| :--- | :--- | :--- | :--- |
| **프롬프트 관리** | 라이브러리 내부에 캡슐화되어 수정이 어려움 | 코드와 분리되어 DB나 외부 저장소에서 투명하게 버전 관리됨 | A/B 테스트 및 도메인 최적화의 난이도가 극적으로 낮아짐 |
| **컨텍스트(토큰) 제어** | `CharacterTextSplitter` 등 추상화된 청킹 의존 | `tiktoken` 등을 통해 모델의 Exact Context Window에 맞춰 동적 슬라이싱 | 토큰 초과 에러(400 Bad Request) 원천 차단 및 API 비용 30% 절감 |
| **결과물 파싱** | 불안정한 정규식이나 무거운 OutputParser 사용 | Pydantic과 Function Calling(또는 Instructor)을 활용한 스키마 강제 | JSON 포맷 에러 감소 및 타입 세이프(Type-safe)한 파이프라인 구축 |
| **디버깅 가시성** | 수십 단계의 블랙박스 체인 (스택 트레이스 지옥) | 명확한 HTTP API 호출 단위의 단방향 데이터 플로우 | 병목 구간(Retrieval vs Generation) 즉각 파악 가능 |

실제로 바닥부터 구축할 때의 쾌감은 **구조화된 출력(Structured Output)**을 다룰 때 극대화됩니다. 복잡한 체인을 버리고, Pydantic 모델과 OpenAI의 순정 API(또는 `Instructor` 라이브러리)만을 활용해 예측 가능한 시스템을 만드는 코드 스니펫을 보시죠.

```python
import openai
import tiktoken
from pydantic import BaseModel, Field
import instructor

# 1. 프레임워크 없이 순수 클라이언트에 Instructor 패치 적용
client = instructor.from_openai(openai.OpenAI())

# 2. 결정론적(Deterministic) 스키마 정의
class UserIntent(BaseModel):
    intent: str = Field(description="사용자의 의도: 'support', 'sales', 'tech' 중 하나")
    confidence: float = Field(description="의도 파악의 신뢰도 (0.0 ~ 1.0)")
    needs_escalation: bool = Field(description="휴먼 상담원 연결 필요 여부")

# 3. 토큰 통제: 정확한 컨텍스트 계산 로직
def truncate_to_max_tokens(text: str, max_tokens: int = 1000) -> str:
    encoding = tiktoken.encoding_for_model("gpt-4o")
    tokens = encoding.encode(text)
    if len(tokens) > max_tokens:
        return encoding.decode(tokens[:max_tokens])
    return text

# 4. 직관적이고 투명한 실행 (블랙박스 체인 없음!)
def route_user_query(raw_query: str) -> UserIntent:
    safe_query = truncate_to_max_tokens(raw_query)
    
    response = client.chat.completions.create(
        model="gpt-4o",
        response_model=UserIntent, # Pydantic 모델로 강제 파싱
        messages=[
            {"role": "system", "content": "당신은 고객 요청의 의도를 라우팅하는 정밀한 분석기입니다."},
            {"role": "user", "content": safe_query}
        ],
        temperature=0.1 # 결정론적 출력을 위해 온도를 낮춤
    )
    return response

# 실행 결과는 완벽하게 타입 타이핑된 파이썬 객체로 떨어집니다.
```
위 코드를 보세요. 프레임워크의 숨겨진 로직 없이 모든 과정이 투명합니다. 토큰을 얼마나 잘라낼지, 어떤 시스템 프롬프트를 사용할지, 어떤 형태로 파싱할지 100% 개발자의 통제하에 있습니다. 이것이 15초 걸리던 API 응답을 2초대로 줄이는 시작점입니다.

### Pragmatic Use Cases: 치열한 현업의 트러블슈팅

이런 'From Scratch' 접근법이 현업의 진흙탕 같은 문제들을 어떻게 해결할까요? 뻔한 챗봇 예시는 집어치우고, 제가 실제로 겪었던 엔터프라이즈 레벨의 시나리오 두 가지를 꺼내보겠습니다.

**1. 대규모 트래픽 스파이크와 API 장애 대처 (Fallback Routing)**
대고객 서비스에서 OpenAI API가 갑자기 502 Bad Gateway를 뱉거나 Rate Limit에 걸리면 어떻게 될까요? 프레임워크에 의존하는 시스템은 이 예외를 우아하게 처리하기가 끔찍하게 어렵습니다. 바닥부터 설계한 시스템에서는 이를 **멀티 모델 라우팅 아키텍처**로 우회합니다. 

메인 로직은 GPT-4o를 호출하되, Timeout이 3초를 넘기거나 에러가 발생하면 즉시 자체 서버에 띄워둔 vLLM 기반의 오픈소스 모델(예: Llama-3-8B) 또는 Anthropic Claude API로 투명하게 전환(Fallback)되도록 파이프라인의 어댑터를 직접 구현합니다. 이때 프롬프트 포맷이 모델마다 미묘하게 다른데(예: ChatML vs XML 태그), 프레임워크 락인(Lock-in)이 없기 때문에 각 모델 특성에 맞는 프롬프트 렌더링 엔진을 가볍게 커스텀하여 대응할 수 있었습니다.

**2. 10년 된 Spring Boot 레거시와의 이질감 없는 연동**
현업의 많은 백엔드 시스템은 Java/Spring Boot로 굳건히 버티고 있습니다. AI를 도입한답시고 갑자기 메인 인프라를 Python 파이프라인으로 전부 뜯어고칠 수는 없죠. 

From Scratch 접근법을 채택하면, Java 애플리케이션 자체가 가장 강력한 오케스트레이터가 됩니다. LangChain4j 같은 무거운 라이브러리 대신, Java의 WebClient나 RestTemplate을 이용해 LLM의 REST API를 직접 호출합니다. 프롬프트는 비즈니스 로직에 하드코딩하지 않고 데이터베이스에 저장하여, 기획자가 관리자 페이지에서 프롬프트의 파라미터를 조절하고 A/B 테스트를 할 수 있는 구조를 구축합니다. 이 과정에서 시맨틱 캐싱(Semantic Caching - Redis 벡터 검색을 활용해 동일한 의미의 질문은 LLM을 안 태우고 즉시 캐시 응답) 레이어를 Spring 서버 앞단에 직접 끼워 넣어, 피크 타임 API 비용을 40% 이상 절감한 경험은 잊을 수 없는 성과입니다.

### Honest Review & Trade-offs: 바닥부터 짠다는 것의 그림자

물론 달콤한 이야기만 할 수는 없습니다. 바닥부터 짠다는 것은 시니어의 입장에서 볼 때 꽤나 피곤한 트레이드오프를 요구합니다. 한마디로 **"프레임워크가 싸놓은 똥은 안 치워도 되지만, 내가 만든 시스템의 똥은 내가 다 치워야 한다"**는 뜻이죠.

첫째, **바퀴의 재발명(Reinventing the Wheel) 리스크**입니다. Retry 로직, Rate Limiter, 문서 청킹(Chunking) 알고리즘을 직접 짜다 보면 '내가 지금 비즈니스 로직을 짜는 건가, 아니면 프레임워크를 직접 만들고 있는 건가?' 하는 자괴감이 들 때가 있습니다. 오픈소스 생태계가 제공하는 수많은 훌륭한 Loader(PDF 파싱, 웹 스크래핑 등)들을 직접 구현해야 하는 것은 명백한 오버헤드입니다.

둘째, **가파른 러닝 커브**입니다. LangChain을 쓰면 토크나이저(Tokenizer)가 뭔지 몰라도 앱을 만들 수 있습니다. 하지만 From Scratch로 가면 BPE(Byte-Pair Encoding)의 원리, 임베딩 차원(Dimensions)의 수학적 의미, 각 LLM 모델의 패널티 파라미터(Frequency/Presence)가 어떻게 작동하는지 밑바닥 원리를 철저히 이해해야 합니다. 주니어 개발자들에게 이 아키텍처를 온보딩시키는 과정은 꽤나 고통스러웠습니다.

### Closing Thoughts: 마법을 믿지 않는 엔지니어의 자세

기술의 역사는 항상 "편리한 추상화"와 "정밀한 통제" 사이의 시계추 운동이었습니다. 지금의 AI 생태계는 너무 빠르게 발전한 나머지, 그 복잡성을 가리기 위해 온갖 추상화 도구들이 난립하는 과도기에 있습니다.

제가 현업 개발자들에게 드리고 싶은 말씀은 단 하나입니다. **AI를 블랙박스 안에 가두고 마법처럼 동작하길 기도하지 마세요.** 프레임워크는 프로토타이핑을 위한 훌륭한 도구일 뿐, 트래픽이 쏟아지는 프로덕션 환경에서 당신의 밤잠을 지켜주지 않습니다. 두려워하지 말고 API 문서를 열어 생(Raw) HTTP 요청을 날려보세요. 토큰을 직접 세어보고, 프롬프트 템플릿의 변수들을 직접 조립해 보세요. 기술의 밑바닥을 한 번이라도 직접 핥아본 엔지니어와 프레임워크의 함수 호출에만 의존하는 엔지니어의 격차는, 앞으로 다가올 진짜 AI 프로덕션 시대에서 걷잡을 수 없이 벌어질 것입니다.

## References
- https://huyenchip.com/2023/04/11/llm-engineering.html
- https://jxnl.github.io/instructor/
- https://github.com/openai/tiktoken
