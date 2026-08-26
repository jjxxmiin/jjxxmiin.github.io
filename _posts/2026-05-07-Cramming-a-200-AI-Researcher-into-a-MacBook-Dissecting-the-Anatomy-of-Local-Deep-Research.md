---
layout: post
title: 'Deep Research를 맥북에서 완전 로컬로 돌릴 수 있을까? LDR의 현실'
date: '2026-05-07 07:31:16'
categories: Tech
tags:
  - 경량화
  - AI트렌드
summary: 'Ollama·SearXNG·LangGraph를 조합한 Local Deep Research의 반복 검색 구조를 살펴보고, 로컬 추론과 완전한 에어갭을 혼동하면 안 되는 이유를 정리합니다.'
description: "Local Deep Research의 Ollama·SearXNG·LangGraph 반복 search를 egress·source provenance, query budget·종료, small/large model 역할과 보고서 정확도로 검증합니다."
github_url: https://github.com/LearningCircuit/local-deep-research
faq:
  - question: "Ollama를 쓰면 Local Deep Research가 완전한 air-gap으로 동작하나요?"
    answer: "아닙니다. model 추론은 local이어도 SearXNG·web crawler·Firecrawl이 외부 질의와 page를 주고받으면 network와 data 경계가 남습니다."
  - question: "검색 반복 횟수를 늘리면 보고서 품질이 계속 좋아지나요?"
    answer: "보장하지 않습니다. 같은 출처를 반복하거나 낮은 품질 문서가 늘 수 있으므로 knowledge gap, 새 근거와 시간·query budget으로 종료해야 합니다."
  - question: "local model 연구 보고서는 어떻게 평가해야 하나요?"
    answer: "질문별 근거 coverage·인용 정확성·source 다양성·모순 처리, 전체 시간·전력·검색 요청과 실패한 claim을 기준선과 비교해야 합니다."
image:
  path: https://opengraph.githubassets.com/1/LearningCircuit/local-deep-research
  alt: "LearningCircuit/local-deep-research GitHub 저장소 대표 이미지"
---

Local Deep Research의 모델 추론은 맥북 안에서 돌릴 수 있지만, SearXNG로 웹을 검색하고 페이지를 수집한다면 시스템 전체가 완전한 로컬이나 에어갭인 것은 아닙니다. 어떤 구현을 골랐는지 고정한 뒤 검색 질의의 외부 유출, 반복 종료와 claim별 출처 정확도를 함께 검증해야 합니다.

## 하나의 제품이 아니라 여러 구현을 비교해야 한다

원문에서 Local Deep Research는 단일 표준 프로젝트가 아니라 서로 다른 구현을 묶어 부르는 이름에 가깝습니다. [LearningCircuit의 구현](https://github.com/LearningCircuit/local-deep-research), [LangChain의 로컬 연구 구현](https://github.com/langchain-ai/local-deep-researcher), [DeepResearchHybrid](https://github.com/VladPrytula/DeepResearchHybrid), [Jupyter 기반 구현](https://github.com/as2811-project/local-deep-research)이 함께 소개됩니다.

따라서 “Local Deep Research를 설치한다”는 말만으로는 동작을 특정할 수 없습니다. 어떤 저장소를 택했는지, Ollama와 LangGraph를 어떻게 연결하는지, 검색에 SearXNG를 쓰는지, 수집에 Firecrawl을 섞는지에 따라 데이터 경계와 비용이 달라집니다.

비교할 때는 먼저 모델 추론 위치, 검색 대상, 원문 수집 방식, 중간 상태 저장 방식, 반복 횟수 제한을 표로 적는 편이 낫습니다. 이름이 비슷하다는 이유로 한 저장소의 기능과 다른 저장소의 성능을 한 시스템의 특성처럼 합치면 판단이 흐려집니다.

## Deep Research의 핵심은 반복 검색이다

일반적인 RAG가 질문과 가까운 문서를 한 번 가져와 답을 만드는 흐름이라면, 여기서 설명하는 LDR은 계획·검색·수집·요약·반추·재검색을 상태 기반 루프로 잇습니다. 첫 검색 결과를 읽은 뒤 부족한 정보가 무엇인지 기록하고 다음 질의를 만드는 것이 핵심입니다. HyDE를 이용해 검색 표현을 보완하거나, LangGraph 상태에 계획과 지식 공백, 반복 횟수를 남기는 접근도 소개됩니다.

원문의 JSON은 이 상태 구조를 설명하는 예시일 뿐 그대로 실행할 수 있는 설정이 아닙니다. 실제 구현에는 노드 정의, 종료 조건, 검색기 연결, 오류 처리와 모델 선택이 더 필요합니다. “목표를 달성할 때까지 무한 반복”시키기보다 최대 반복 수와 시간 한도를 두어야 검색 오류와 비용이 커지는 일을 막을 수 있습니다.

수집한 문서가 많을 때 PCA와 KMeans로 주제를 나누고 관련 조각을 고르는 방식도 제시되지만, 군집이 출처의 신뢰성을 보장하지는 않습니다. 최종 보고서에는 어떤 문장이 어느 원문에서 왔는지 추적할 수 있어야 합니다.

research state에는 원래 질문, 하위 질문, 확인된 claim, 미해결 gap, source URL·수집 시각과 중복 hash를 둡니다. 단순히 “아직 부족하다”는 model 판단만으로 loop를 이어가면 같은 검색어를 바꿔 쓰며 반복할 수 있습니다. 전체 query·page·token·wall time과 연속 새 근거 0회 같은 결정적 종료 조건을 함께 둡니다.

하위 질문마다 최소 source 수를 채우는 것만으로는 충분하지 않습니다. 여러 blog가 같은 보도자료를 복제했을 수 있으므로 원 출처와 독립 출처를 구분합니다. 상반된 자료가 나오면 한쪽을 조용히 버리지 말고 publish date, method와 적용 범위를 나란히 남깁니다. 보고서의 문장에는 검색 결과 snippet이 아니라 실제 page의 근거가 연결돼야 합니다.

## 완전 로컬이라는 표현을 나눠서 봐야 한다

Ollama에서 모델을 실행하면 질문과 중간 추론을 외부 모델 API에 보내지 않을 수 있습니다. 그러나 SearXNG가 Google이나 DuckDuckGo 같은 외부 검색 결과를 모으고 웹페이지를 가져온다면 네트워크 통신은 계속 발생합니다. 외부 정보와 사내 문서를 함께 쓰는 구성은 로컬 추론이지 완전한 망분리 구성이 아닙니다.

정말 에어갭이 필요하다면 검색 대상을 사전에 반입한 내부 문서로 한정해야 합니다. 반대로 최신 웹 자료가 필요하다면 어떤 질의와 주소가 외부로 나가는지, 수집기가 어떤 페이지에 접근하는지, 사내 정보가 검색어에 섞이지 않는지를 별도로 통제해야 합니다.

웹 수집 자체도 안정적이지 않습니다. 반복 요청은 사이트의 속도 제한이나 Cloudflare 방어에 막힐 수 있고, Firecrawl 같은 외부 서비스를 섞으면 다시 비용과 데이터 경계를 검토해야 합니다. 차단 회피를 운영 목표로 삼기보다 접근 허용 범위와 요청 빈도를 지키고, 수집 실패를 보고서에 표시하는 편이 안전합니다.

배포 전에 data-flow를 그립니다. 사용자의 질문, 생성된 검색어, page URL·본문, embedding·summary와 최종 보고서가 어느 process·disk·network를 지나는지 표시합니다. local Ollama에도 prompt log가 남을 수 있고 SearXNG upstream에는 검색어가 보일 수 있습니다. 사내 project name·고객 ID가 query에 섞이지 않도록 redaction하고 outbound domain과 request rate를 제한합니다.

에어갭 mode는 별도 configuration으로 두고 내부 corpus 외 tool을 runtime에서 차단합니다. 외부 검색 실패 때 local 문서만으로 답했다면 “최신 웹 조사”로 표시하지 않습니다. corpus snapshot date와 미확인 범위를 보고서에 명시해야 local privacy가 freshness로 오해되지 않습니다.

## 하드웨어와 결과 품질의 현실적인 기준

원문은 8B 이하 소형 모델이 긴 반복에서 지시를 잊거나 잘못된 검색으로 흐를 수 있다고 경고하고, 14B 이상 또는 32B급 모델과 64GB RAM의 Mac이나 다중 GPU를 현실적인 후보로 제시합니다. 이는 모든 환경을 보장하는 사양이 아니라 해당 글의 경험적 기준으로 읽어야 합니다. 주제와 문서 길이, 양자화, 반복 수에 따라 필요한 자원은 달라집니다.

작은 모델을 검색어 생성과 단순 분류에, 큰 모델을 반추와 최종 종합에 배치하는 이기종 구성은 자원을 나누는 한 방법입니다. 하지만 여러 모델을 번갈아 쓰면 동일한 사실을 일관되게 유지하는지와 각 단계의 입력·출력을 더 꼼꼼히 확인해야 합니다.

원문이 제시한 15분에서 1시간의 처리 시간도 즉답형 검색과는 다른 기대치를 요구합니다. 먼저 짧은 질문 세트로 출처 누락, 같은 검색 반복, 근거 없는 종합, 종료 실패를 측정해야 합니다. 로컬이라는 이유만으로 무료·비공개·정확함이 한꺼번에 따라오는 것은 아니며, 모델·검색·수집의 경계를 나눠 검증할 때 비로소 쓸 수 있는 연구 도구가 됩니다.

## 작은·큰 model의 역할을 어떻게 검증할까

query 생성·문서 분류·최종 synthesis를 각각 작은 model과 큰 model로 바꿔 ablation합니다. 같은 source snapshot에서 subquestion coverage, relevant page 비율, claim 정확성, unsupported sentence와 총 token·시간·peak memory를 비교합니다. 작은 model이 잘못된 검색 방향을 잡으면 큰 model이 마지막에 자연스럽게 요약해도 근거는 회복되지 않습니다.

golden 질문은 단일 사실, 여러 source 종합, 시간에 따라 바뀐 정보와 상반된 주장으로 나눕니다. 보고서 문장별 citation이 실제 claim을 지지하는지 사람이 표본 검토하고, 404·수집 실패와 date mismatch를 포함합니다. 검색 API 기반 cloud research와 단순 manual search를 기준선으로 두어 local 구성의 운영비가 어떤 privacy·품질 이익으로 돌아오는지 봅니다.

실패 뒤 재실행할 때 이미 수집한 page와 state를 안전하게 재사용하고 동일 source를 무제한 다시 요청하지 않아야 합니다. model·prompt·repository commit, search engine·corpus date를 trace에 남겨 같은 보고서를 재현할 수 있게 합니다. 중간 state에 민감 정보가 있으므로 retention과 삭제도 정합니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [공식 GitHub 저장소](https://github.com/LearningCircuit/local-deep-research)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [Deer-Flow 2.0은 딥 리서치를 어떻게 나눠 실행할까: 도입 검증 가이드]({% post_url 2026-02-27-Why-Did-I-Just-Find-Out-About-This-An-Honest-Review-of-ByteDances-Insane-Research-AI-Deer-Flow-20 %}) — Deer-Flow 2.0이 계획·검색·코드 실행·보고서 생성을 여러 역할과 샌드박스로 연결하는 구조, 설치 스냅샷과 비용·검증 기준을 정리합니다.
- [DeerFlow 딥 리서치, 사내에 바로 둘 수 있을까: 구조·보안·운영 검증]({% post_url 2026-02-28-Why-Did-I-Just-Find-Out-About-This-An-Honest-Review-of-ByteDances-Open-Source-Deep-Research-Framework-DeerFlow %}) — DeerFlow의 LangGraph 기반 역할 분담과 검색·코드·보고서 파이프라인을 살피고, 샌드박스·API 키·출처·비용을 검증하는 도입 기준을 정리합니다.
- [셀프호스팅 AI 검색이면 질문이 완전히 비공개일까? Perplexica의 경계]({% post_url 2026-03-05-Is-the-Era-of-Google-Search-Over-Deep-Dive-into-Perplexica-the-Open-Source-Perplexity-in-My-Home-Server %}) — Perplexica가 SearXNG 검색과 로컬 LLM·임베딩을 조합해 출처형 답변을 만드는 흐름과 외부 검색 엔진·API를 쓸 때 남는 개인정보 경계를 정리합니다.
<!-- internal-links:end -->

## 자주 묻는 질문

### Ollama를 쓰면 Local Deep Research가 완전한 air-gap으로 동작하나요?

아닙니다. model 추론은 local이어도 SearXNG·web crawler·Firecrawl이 외부 질의와 page를 주고받으면 network와 data 경계가 남습니다.

### 검색 반복 횟수를 늘리면 보고서 품질이 계속 좋아지나요?

보장하지 않습니다. 같은 출처를 반복하거나 낮은 품질 문서가 늘 수 있으므로 knowledge gap, 새 근거와 시간·query budget으로 종료해야 합니다.

### local model 연구 보고서는 어떻게 평가해야 하나요?

질문별 근거 coverage·인용 정확성·source 다양성·모순 처리, 전체 시간·전력·검색 요청과 실패한 claim을 기준선과 비교해야 합니다.
