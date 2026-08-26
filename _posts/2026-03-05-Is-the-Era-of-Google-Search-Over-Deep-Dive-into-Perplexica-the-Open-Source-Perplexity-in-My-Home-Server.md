---
layout: post
title: '셀프호스팅 AI 검색이면 질문이 완전히 비공개일까? Perplexica의 경계'
date: '2026-03-05 06:36:11'
categories: Tech
tags:
  - 온디바이스AI
  - LLM
  - 오픈소스
  - 경량화
summary: Perplexica가 SearXNG 검색과 로컬 LLM·임베딩을 조합해 출처형 답변을 만드는 흐름과 외부 검색 엔진·API를 쓸 때 남는 개인정보 경계를 정리합니다.
description: 'Perplexica가 SearXNG·embedding·LLM으로 출처형 답변을 만드는 흐름과, 셀프호스팅에서도 남는 질의 노출·인용 오류·운영 비용을 설명합니다.'
github_url: https://github.com/ItzCrazyKns/Perplexica
image:
  path: https://opengraph.githubassets.com/1/ItzCrazyKns/Perplexica
  alt: "ItzCrazyKns/Perplexica GitHub 저장소 대표 이미지"
faq:
  - question: 'Perplexica를 셀프호스팅하면 검색어가 외부로 전혀 나가지 않나요?'
    answer: 'SearXNG가 외부 검색 엔진에 query를 보내고 외부 LLM을 선택하면 질문과 문서 일부가 provider로 갈 수 있습니다. DNS·proxy·engine·model endpoint와 log를 포함한 전체 경로를 확인해야 합니다.'
  - question: '답변에 citation이 있으면 내용이 근거와 일치하나요?'
    answer: '링크가 붙었다는 사실만으로 문장이 해당 페이지에서 지지되지는 않습니다. 인용 문장·문서 위치·날짜를 확인하고 여러 출처가 충돌할 때 이를 답변에 드러내는지 평가해야 합니다.'
  - question: '로컬 LLM을 쓰면 운영 비용이 없어지나요?'
    answer: 'API 비용은 줄 수 있지만 GPU·전력·저장소·업데이트와 SearXNG 유지보수 비용이 남습니다. 목표 질문에서 품질·지연·동시성과 사람 검토 시간을 함께 계산해야 합니다.'
---

완전히 비공개라고 단정할 수 없습니다. Perplexica의 UI·LLM·임베딩을 자체 서버에 둘 수 있어도 SearXNG가 질의를 보내는 외부 검색 엔진과 선택한 모델 API에는 요청 일부가 전달될 수 있으므로 전체 경로를 확인해야 합니다.

[Perplexica 저장소](https://github.com/ItzCrazyKns/Perplexica)는 검색 결과 링크를 그대로 나열하는 대신 문서를 모아 관련 부분을 고르고 출처와 함께 답을 만드는 오픈소스 AI 검색 엔진입니다. 상용 Perplexity의 기능을 모두 대신한다는 보장보다 검색·재정렬·생성 단계를 직접 설정할 수 있다는 점이 선택 이유입니다.

## 한 질문이 답변이 되기까지

Next.js·TypeScript UI는 질문과 streaming 답변을 표시합니다. 뒤에서는 질문이 일반 대화인지 웹 검색이 필요한지 분류하고, 검색에 맞는 query를 만들어 SearXNG로 보냅니다.

가져온 문서를 그대로 모두 LLM에 넣지 않습니다. 텍스트를 chunk로 나누고 embedding 유사도로 질문과 가까운 부분을 재정렬한 뒤, 상위 근거만 생성 모델에 전달합니다. 마지막 단계에서 답변 문장과 source metadata를 연결합니다.

이 과정에는 최소 네 가지 실패 지점이 있습니다.

1. 의도 분류가 검색이 필요한 질문을 일반 대화로 보낸다.
2. 검색 query가 원래 질문의 조건을 잃는다.
3. reranker가 신뢰할 근거보다 비슷한 문장을 고른다.
4. 생성 모델이 근거에 없는 내용을 덧붙인다.

답변이 자연스럽다는 이유만으로 검색 품질까지 좋다고 판단하면 안 됩니다.

## SearXNG와 로컬 LLM의 프라이버시 역할

SearXNG는 여러 검색 엔진의 결과를 모으고 사용자 추적 정보를 줄이는 메타 검색 계층입니다. 그러나 외부 엔진에 query 자체를 보내지 않고 웹을 검색할 수는 없습니다. 자체 SearXNG가 어떤 engine을 쓰며 로그와 proxy를 어떻게 설정했는지에 따라 노출 범위가 달라집니다.

Ollama 같은 로컬 LLM과 로컬 embedding을 선택하면 질문과 검색 문서를 생성 API에 보낼 필요는 줄어듭니다. OpenAI나 Claude 같은 외부 모델로 바꾸면 그 장점은 달라집니다. “self-hosted”라는 배포 형태와 “외부 통신 없음”이라는 네트워크 정책을 분리해야 합니다.

사내 오류 로그처럼 민감한 문장을 공개 웹 query에 그대로 섞지 않도록 내부 검색과 외부 검색도 분리하는 편이 안전합니다.

## 원문의 설정 조각은 버전 고정이 없다

원문은 `config.toml`에 Ollama·SearXNG 주소와 cosine similarity를 적고 container를 올리는 흐름을 소개합니다. 이 조각은 핵심 연결을 설명하지만 저장소 커밋, image tag, 인증, secret, health check와 SearXNG 설정이 빠져 있어 완전한 운영 절차가 아닙니다.

실행 전에는 현재 README에서 설정 schema를 확인하고 다음을 정해야 합니다.

- Perplexica와 SearXNG의 고정 image 버전
- 외부에 공개할 port와 인증 방식
- 로컬 모델이 요구하는 RAM·VRAM
- 검색·질문·답변 로그의 보존 기간
- 외부 model endpoint를 허용할 업무 범위

원문이 제시한 16~32GB VRAM도 특정 모델 크기와 속도를 가정한 경험적 범위입니다. 선택한 8B 또는 70B 모델과 quantization에 따라 실제 요구량은 달라집니다.

## Focus Mode도 출처 품질을 대신하지 않는다

Academic과 YouTube 같은 focus mode는 검색 대상을 좁혀 논문이나 영상 자막을 우선 찾게 합니다. 관련 없는 웹페이지를 줄이는 데는 도움이 되지만 학술 모드라고 환각이 사라지거나 모든 논문이 신뢰할 만해지는 것은 아닙니다.

자체 평가에는 최신성이 필요한 질문, 여러 출처가 충돌하는 질문, 검색 결과가 없는 질문을 포함해야 합니다. citation을 눌렀을 때 실제 문장이 답을 지지하는지 사람이 확인하고, similarity threshold를 바꿨을 때 근거 누락과 잡음이 어떻게 변하는지 기록해야 합니다.

## 선택 기준은 무료가 아니라 통제 가능성이다

Perplexica 소프트웨어를 무료로 쓸 수 있어도 서버 전력, GPU, 모델 API와 SearXNG 유지보수 비용은 남습니다. 검색 엔진의 HTML이 바뀌면 수집이 깨질 수 있고, local model이 작으면 답변 품질이 낮아질 수 있습니다.

따라서 이미 서버를 운영하고 검색 경로를 직접 감사해야 하는 팀에는 적합할 수 있습니다. 클릭 한 번의 안정성과 완성된 품질이 더 중요하면 관리형 서비스가 나을 수 있습니다. Perplexica의 핵심 가치는 “구글 검색이 끝났다”는 선언이 아니라, 의도 분류부터 citation 생성까지의 검색 체인을 팀이 관찰하고 바꿀 수 있게 하는 데 있습니다.

## 질문은 어디까지 외부로 전달되는가

사용자 질문 원문을 그대로 검색 엔진에 보내지 않고 web query로 다시 쓰더라도 민감 정보가 남을 수 있습니다. 사내 project 이름, 고객 ID, 오류 message와 access token이 query에 포함되지 않도록 입력 redaction과 내부·외부 검색 분류가 필요합니다. 모호한 질문을 확장할 때 model이 새로운 민감 표현을 덧붙이는지도 log에서 확인합니다.

SearXNG는 여러 engine을 사용할 수 있으므로 engine별로 전달되는 parameter와 지역·safe-search 설정이 다를 수 있습니다. Proxy를 거쳐도 외부 사이트 접속과 DNS 기록, response cache가 남을 수 있습니다. “No log”를 선언하는 것보다 실제 component의 log retention과 접근 권한을 정하는 편이 중요합니다.

사용자가 URL을 직접 입력하거나 검색 결과의 page를 fetch할 때 내부 주소에 접근하지 못하도록 network boundary도 검토합니다. Crawler가 localhost·metadata endpoint·사내 service를 읽을 수 있으면 SSRF 경로가 될 수 있습니다. 외부 web fetcher의 허용 scheme·address range·redirect를 제한해야 합니다.

## citation 품질은 어떻게 평가할까

정답이 알려진 최신 질문, 여러 source가 충돌하는 질문, answer가 없는 질문을 준비합니다. 각 문장을 source가 직접 지지하는지, date와 subject가 일치하는지, source 사이 불확실성을 표시하는지 사람이 판정합니다. Citation precision과 answer completeness를 분리해야 링크가 많기만 한 답을 높게 평가하지 않습니다.

Chunk similarity가 높아도 문서가 오래됐거나 SEO spam일 수 있습니다. Domain·작성자·날짜를 metadata로 남기고 신뢰할 source allowlist 또는 다양성 규칙을 설정할 수 있습니다. 다만 특정 domain을 우선하는 정책이 반대 근거를 숨기지 않는지도 함께 봐야 합니다.

생성 모델이 source에 없는 숫자를 보태거나 인용 번호를 잘못 연결할 수 있습니다. Answer sentence와 retrieved chunk의 entailment를 별도 검사하고, 근거가 부족하면 “찾지 못함”을 허용합니다. 사용자 UI에서 citation을 눌렀을 때 실제 관련 passage로 이동할 수 있으면 검토 비용이 줄어듭니다.

## 검색 품질이 낮을 때 어디부터 고칠까

먼저 web 결과 자체에 정답 page가 있는지 봅니다. 없다면 query rewriting과 engine 구성을 고치고, 결과에는 있는데 reranking에서 빠졌다면 embedding·chunk·top-k를 봅니다. 근거가 prompt에 들어갔는데 답이 틀렸다면 generation과 citation binding 문제입니다. 단계별 artifact를 저장하지 않으면 모든 오류를 LLM 탓으로 돌리게 됩니다.

긴 page를 너무 잘게 자르면 문맥이 사라지고 너무 크게 자르면 관련 없는 text가 섞입니다. 제목·section 경계를 보존하고 query 유형별로 top-k와 threshold를 조정합니다. Search result snippet만 사용하는 경우와 본문 fetch를 비교해 latency와 근거 품질 차이를 측정합니다.

최신성 질문에는 crawl·cache 시각을 표시하고 cache 무효화 정책을 둡니다. 검색 결과가 없거나 fetch가 실패했는데 오래된 cache를 새 답처럼 보여 주지 않게 해야 합니다. Source failure 비율도 answer latency와 함께 운영 지표로 둡니다.

## 운영 형태는 무엇으로 결정할까

한 명의 개인 서버는 SQLite·단일 model로 충분할 수 있지만 팀 서비스는 authentication, tenant별 history와 rate limit, backup·monitoring이 필요합니다. SearXNG와 model server 중 하나가 중단될 때 일반 대화로 fallback할지 명시적으로 실패할지 정합니다. 검색 없이 만든 답을 검색 답변처럼 citation과 함께 보여 주면 안 됩니다.

Model update와 embedding 변경은 기존 index와 답변 품질을 바꿀 수 있습니다. 고정 질문 세트를 update 전후에 실행하고 rollback 가능한 image와 config를 유지합니다. Perplexica를 선택하는 핵심은 구성 요소를 소유하는 만큼 이 변경과 장애를 책임질 수 있는지입니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [공식 GitHub 저장소](https://github.com/ItzCrazyKns/Perplexica)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [민감한 문서를 NotebookLM에 올리기 어렵다면? Open Notebook 점검표]({% post_url 2026-03-02-Why-Did-I-Only-Find-Out-About-This-Now-An-Honest-Review-of-Open-Notebook-the-Open-Source-Alternative-Threatening-Googles-NotebookLM %}) — Open Notebook의 문서 Q&A·요약·다중 화자 오디오 기능을 살펴보고 로컬 LLM을 써도 외부 전송이 남을 수 있는 지점과 설치 전 확인 사항을 정리합니다.
- [Deep Research를 맥북에서 완전 로컬로 돌릴 수 있을까? LDR의 현실]({% post_url 2026-05-07-Cramming-a-200-AI-Researcher-into-a-MacBook-Dissecting-the-Anatomy-of-Local-Deep-Research %}) — Ollama·SearXNG·LangGraph를 조합한 Local Deep Research의 반복 검색 구조를 살펴보고, 로컬 추론과 완전한 에어갭을 혼동하면 안 되는 이유를 정리합니다.
- [OpenViking은 벡터 DB를 대체할까: viking:// L0-L2 검색과 토큰 비용]({% post_url 2026-02-18-OpenViking-The-Context-Database-For-AI-Agents %}) — OpenViking이 벡터·KV 저장소 위에 파일 경로와 L0-L2 계층을 얹는 방식, 재귀 검색의 이득과 운영 전 확인할 점을 설명합니다.
<!-- internal-links:end -->

## 자주 묻는 질문

### Perplexica를 셀프호스팅하면 검색어가 외부로 전혀 나가지 않나요?

SearXNG가 외부 검색 엔진에 query를 보내고 외부 LLM을 선택하면 질문과 문서 일부가 provider로 갈 수 있습니다. DNS·proxy·engine·model endpoint와 log를 포함한 전체 경로를 확인해야 합니다.

### 답변에 citation이 있으면 내용이 근거와 일치하나요?

링크가 붙었다는 사실만으로 문장이 해당 페이지에서 지지되지는 않습니다. 인용 문장·문서 위치·날짜를 확인하고 여러 출처가 충돌할 때 이를 답변에 드러내는지 평가해야 합니다.

### 로컬 LLM을 쓰면 운영 비용이 없어지나요?

API 비용은 줄 수 있지만 GPU·전력·저장소·업데이트와 SearXNG 유지보수 비용이 남습니다. 목표 질문에서 품질·지연·동시성과 사람 검토 시간을 함께 계산해야 합니다.
