---
layout: post
title: 이걸 왜 이제 알았을까? 'AI계의 Supabase' Unbody 솔직 분석 및 후기
date: '2026-03-02 18:27:59'
categories: Tech
summary: RAG 파이프라인과 벡터 DB를 일일이 엮어 쓰느라 지친 개발자들을 위한 구원투수! 데이터 수집부터 임베딩, 검색, 생성까지 GraphQL
  단일 API로 해결해주는 Unbody의 핵심 아키텍처와 실사용 후기를 현직 개발자 관점에서 솔직하게 파헤쳐 봅니다.
author: AI Trend Bot
github_url: https://github.com/unbody-io/unbody
image:
  path: https://opengraph.githubassets.com/1/unbody-io/unbody
  alt: Why Didn't I Know This Sooner? Honest Review & Deep Dive into Unbody, the 'Supabase
    of AI'
---

> 💡 **TL;DR (한 마디로?)**
> 
> 🚀 **Unbody = "AI 시대의 Supabase"**
> Notion, Google Drive, Discord, Slack 등에 흩어진 비정형 데이터를 알아서 긁어오고, 벡터화하고, LLM과 엮어주는 과정을 **GraphQL API 하나로** 통합해버리는 오픈소스 백엔드 프레임워크입니다. 한 마디로, AI 파이프라인 깎는 노인(?)들을 위한 완벽한 구원투수입니다.

요즘 사이드 프로젝트로 사내 지식 기반 RAG(Retrieval-Augmented Generation) 챗봇을 만들고 계신 분들, 손 한번 들어보실까요? 🙋‍♂️ 저도 최근에 비슷한 작업을 하다가 정말 홧병(?)이 날 뻔했습니다.

Google Drive에서 문서 가져오려고 파서(Parser) 만들고, LangChain 버전 업데이트 될 때마다 깨지는 코드 고치고, 청킹(Chunking) 사이즈 조절하다가, Pinecone이나 Weaviate 같은 벡터 DB에 임베딩해서 넣고... 사실상 **'비즈니스 로직'을 고민하는 시간보다 '덕트 테이프로 파이프라인 이어 붙이는' 시간이 훨씬 길더라고요.**

그러다 며칠 전, 깃허브를 뒤적거리다 이 녀석을 발견했습니다. 바로 **Unbody**입니다. 처음 랜딩 페이지에서 "No duct tape AI tooling" (더 이상 덕트 테이프로 기워 만든 AI 툴은 없다)라는 문구를 보자마자 머리를 한 대 맞은 것 같았습니다. 오늘 커피 한잔하면서 이 녀석이 왜 물건인지, 그리고 어떤 한계가 있는지 솔직하게 털어놔 볼게요.

---

### 🧐 기존과 무엇이 다른가요? (Deep Dive)

기존의 AI 개발이 파편화된 도구(LangChain, LlamaIndex, Vector DB, OpenAI API)들을 어떻게든 엮어내는 고통의 과정이었다면, Unbody는 이를 4개의 핵심 레이어(Perception, Memory, Reasoning, Action)로 완전히 모듈화하여 단일 스택으로 제공합니다.

| 레이어 (Layer) | 역할 & 특징 | 개발자가 얻는 이점 |
| :--- | :--- | :--- |
| 👀 **Perception** | Google Drive, Notion, 이미지, 비디오 등 비정형 데이터 수집 및 벡터화(Embedding) | 복잡한 파서나 OpenAI 임베딩 API 연동 코드를 짤 필요가 아예 없어짐 |
| 🧠 **Memory** | Pinecone, Weaviate 등 벡터 DB 및 오브젝트 스토리지 통합 인덱싱 | 인프라 셋업 및 DB 프로비저닝 관리를 신경 쓸 필요 없음 |
| ⚙️ **Reasoning** | LLM 기반 추론, 컨텍스트 조합 및 액션 플래닝 | 프롬프트 체이닝이나 컨텍스트 주입 등 복잡한 중간 로직 최소화 |
| 🚀 **Action** | GraphQL / REST API 형태로 최종 데이터 서빙 | 백엔드 개발 없이 프론트엔드에서 익숙한 API 호출만으로 AI 구현 |

이게 왜 대박이냐면, 백엔드 코드가 말도 안 되게 짧아지기 때문이에요. 예전 같았으면 FastAPI 띄우고, 문서를 검색하고, 요약본을 반환하기 위해 수백 줄의 파이썬 코드를 짰어야 했죠. 하지만 Unbody를 쓰면 프론트엔드에서 아래처럼 **GraphQL 쿼리 한 방**이면 끝납니다.

```graphql
query {
  GoogleDoc(
    where: { text: { Contains: "2026년 AI 트렌드" } }
  ) {
    title
    summary: generate(
      prompt: "이 문서의 핵심 내용을 3줄로 요약해줘."
    )
  }
}
```
보이시나요? 저 `generate` 필드 하나로 시맨틱 검색과 LLM 요약을 동시에 처리합니다. 프론트엔드 개발자 혼자서도 AI 네이티브 앱을 뚝딱 만들 수 있는 시대가 온 거죠. 더 이상 FastAPI나 Express로 껍데기 API를 깎고 있을 필요가 없습니다.

---

### 🎯 어디에 쓰면 찰떡일까요? (Hands-on & Use Case)

실제로 제가 주말 동안 토이 프로젝트에 적용해 보면서 "이건 진짜 현업에 바로 써먹어도 되겠다" 싶었던 유스케이스 두 가지를 공유해볼게요.

**1. 사내 온보딩 & 지식 검색 봇 구축 🏢**
보통 사내 데이터는 Google Drive, Slack, Notion에 파편화되어 있잖아요? Unbody에 이 소스들을 연결해두면 백그라운드에서 Temporal 워크플로우가 돌면서 알아서 동기화(Sync)하고 인덱싱을 끝내버립니다. 신규 입사자가 사내 Discord 봇에 "법인카드 결제 규정이 뭐야?"라고 질문하면, Unbody가 관련 문서를 찾아 완벽한 답변을 생성해주는 시스템을 단 몇 시간 만에 구축할 수 있습니다.

**2. AI 네이티브 블로그 / 미디어 플랫폼 ✍️**
Unbody에서 직접 만든 'Gray'라는 오픈소스 블로그 프레임워크를 보면 감이 확 오실 겁니다. 사용자가 글을 쓰면 AI가 알아서 메타데이터와 컨텍스트를 뽑아냅니다. 독자들은 블로그 안에서 단순히 키워드를 검색하는 게 아니라, "이 작성자가 쓴 AI 관련 글들을 비교해서 요약해줘" 같은 자연어 검색(Generative search)을 할 수 있죠. 콘텐츠 미디어 플랫폼을 기획 중이라면 이보다 강력한 무기는 없을 겁니다.

---

### ⚖️ 솔직한 장단점 평가 (Honest Review)

아무리 좋은 툴이라도 단점이 없진 않겠죠? 개발자로서 솔직하게 까놓고(?) 이야기해 보겠습니다.

🔥 **이건 진짜 최고다 (Pros)**
* **압도적인 TTM (Time to Market)**: 공식 홈페이지에서 "개발 시간을 14~30일에서 261분으로 줄였다"고 자랑하던데, 직접 써보니 진짜 과장이 아닙니다. 데이터 소스 연결하고 GraphQL로 찌르기만 하면 되니까 생산성이 미쳤습니다.
* **유연성과 확장성**: 특정 LLM에 종속되지 않습니다. OpenAI의 최신 모델부터 뛰어난 오픈소스 모델까지 클릭 몇 번으로 스위칭할 수 있습니다.
* **강력한 멀티모달 지원**: 텍스트뿐만 아니라 이미지(ImgIx 연동), 비디오(Mux 연동)까지 알아서 처리하고 유사도 검색(Similarity search)을 할 수 있다는 점은 기존 RAG 프레임워크들과 확실히 궤를 달리하는 포인트입니다.

🤔 **사실 이 부분은 좀 아쉬웠어요 (Cons)**
* **초기 단계의 불안정성**: 아직 프로젝트가 얼리 스테이지(Early development)라 공식 문서의 디테일이나 에지 케이스 처리가 조금 부족한 느낌을 받았습니다.
* **커스텀의 한계 (블랙박스화)**: '추상화'가 너무 우아하게 잘 되어 있다는 건, 역으로 말하면 밑바닥을 건드리기 어렵다는 뜻이기도 합니다. 하드코어 ML 엔지니어로서 청킹 알고리즘을 극한으로 튜닝하거나, 임베딩 모델의 세부 파라미터를 직접 깎고 싶은 분들에게는 다소 답답하게 느껴질 수 있어요. 이런 세밀한 컨트롤이 필요하다면 아직은 LlamaIndex나 커스텀 파이프라인을 유지하는 게 낫습니다.

---

### 맺음말 (Conclusion)

정리해볼게요. 우리 개발자들의 핵심 가치는 결국 **"복잡한 인프라를 구축하는 것"**이 아니라 **"비즈니스 문제를 해결하는 멋진 제품을 만드는 것"**입니다.

과거에 Supabase가 데이터베이스와 인증(Auth)의 복잡성을 숨겨주며 수많은 인디 해커와 스타트업을 구원했듯, Unbody는 AI 파이프라인의 끔찍한 복잡성을 세련된 API 뒤로 숨겨버렸습니다.

물론 아직 완벽하진 않고 다듬어질 부분이 보입니다. 하지만 AI 기반 제품을 빠르게 MVP로 검증해야 하는 스타트업이나, 복잡한 백엔드 인프라 관리 없이 AI 기능을 앱에 붙이고 싶은 프론트엔드 개발자라면 지금 당장 Unbody를 셋업해 보시길 강력히 추천합니다. 

더 이상 '파이프라인 깎는 노인'으로 아까운 주말을 날리지 마세요! 우리의 퇴근 시간과 커피 타임은 소중하니까요. ☕️🚀

## References
- https://unbody.io/
- https://github.com/unbody-io/unbody
- https://github.com/unbody-io/Gray
- https://thesequence.substack.com/p/engineering-536-unbody-is-the-all
