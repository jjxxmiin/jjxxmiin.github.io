---
layout: post
title: '민감한 문서를 NotebookLM에 올리기 어렵다면? Open Notebook 점검표'
date: '2026-03-02 18:42:59'
categories: Tech
tags:
  - 음성AI
  - 오픈소스
  - LLM
  - RAG
  - 온디바이스AI
summary: Open Notebook의 문서 Q&A, 요약, 다중 화자 오디오 기능을 살펴보고 로컬 LLM을 써도 외부 전송이 남을 수 있는 지점과 설치 전 확인 사항을 정리합니다.
description: "Open Notebook의 ingestion, embedding, RAG, audio pipeline을 설명하고 self-hosting에서 upstream, endpoint, citation accuracy, ACL, backup과 외부 data 전송을 검증하는 법을 정리합니다."
faq:
  - question: "Open Notebook을 self-host하면 문서가 모두 local에만 있나요?"
    answer: "Storage가 local이어도 embedding, LLM, TTS provider를 cloud endpoint로 쓰면 chunk, prompt, script가 전송될 수 있어 component별 network flow를 확인해야 합니다."
  - question: "Citation이 표시되면 답변 근거가 정확한가요?"
    answer: "아닙니다. Retrieved chunk가 claim을 실제 지원하는지 span-level faithfulness와 page, section location을 labeled question set에서 검증해야 합니다."
  - question: "NotebookLM 대체 여부는 기능 수로 결정하나요?"
    answer: "자사 document의 answer quality, latency, privacy, ACL과 update, backup 운영비를 같은 workflow에서 비교해야 하며 open source 선택은 운영 책임도 가져옵니다."
github_url: https://github.com/Open-Notebook/open-notebook
image:
  path: https://opengraph.githubassets.com/1/Open-Notebook/open-notebook
  alt: "Open-Notebook/open-notebook GitHub 저장소 대표 이미지"
---

민감한 문서를 직접 통제하는 서버에서 처리하려면 검토할 만합니다. 다만 Open Notebook을 셀프 호스팅했다는 사실만으로 모든 모델, 임베딩, 음성 요청이 로컬에 머무는 것은 아니며, 연결한 공급자별 데이터 경로를 확인해야 합니다. Citation faithfulness, document ACL, 삭제와 backup, upgrade까지 통과할 때 self-hosting의 통제권이 실제 운영 이점이 됩니다.

[Open Notebook 저장소](https://github.com/Open-Notebook/open-notebook)는 문서를 넣고 RAG 기반으로 질문, 요약을 수행하며 오디오 콘텐츠를 만드는 오픈소스 노트 환경을 지향합니다. 원문은 여러 모델 공급자와 Ollama, LM Studio 같은 로컬 실행기를 선택하고 REST API와 워크플로를 조정할 수 있다는 점을 NotebookLM과의 차이로 들었습니다.

## 문서 처리와 오디오 생성은 별도 경로다

문서 Q&A는 파일을 읽고 청크로 나눈 뒤 임베딩해 관련 부분을 찾고, 선택한 LLM이 답을 만드는 흐름입니다. Open Notebook은 chunk size와 overlap 같은 RAG 설정을 조정할 수 있어 문서 구조에 맞춘 실험이 가능합니다.

오디오 기능은 답변 생성과 또 다른 단계입니다. 원문은 한 명에서 네 명까지 화자 프로필과 대본을 조정할 수 있다고 소개합니다. 하지만 LLM을 로컬로 실행해도 음성 합성 공급자를 외부 API로 지정하면 대본은 서버 밖으로 나갈 수 있습니다. “완전 로컬” 여부는 문서 저장 위치뿐 아니라 임베딩, 생성, 음성 합성 호출을 모두 따라가야 판단할 수 있습니다.

## Docker 조각만으로 설치를 확정하면 안 된다

원문에는 단일 `open-notebook` 서비스와 포트, Ollama 주소, 데이터 볼륨을 적은 compose 조각이 있습니다. 이는 주요 설정을 보여 주는 기준일 스냅샷이지, 데이터베이스와 오디오 구성, 이미지 버전, 인증까지 검증한 완전한 배포 파일이 아닙니다.

또한 원문과 front matter에는 [Open-Notebook 조직](https://github.com/Open-Notebook/open-notebook), [lfnovo 저장소](https://github.com/lfnovo/open-notebook), [mshojaei77 저장소](https://github.com/mshojaei77/open-notebook)처럼 서로 다른 경로가 함께 등장합니다. 설치 전에 어떤 저장소가 현재 upstream인지, 사용하는 컨테이너 이미지가 그 소스와 일치하는지 확인해야 합니다.

실행 전에는 최소한 다음 항목을 고정해야 합니다.

1. 사용할 저장소 커밋과 컨테이너 태그
2. 문서, 인덱스, 오디오 파일이 저장되는 볼륨
3. LLM, 임베딩, 음성 공급자의 실제 endpoint
4. 외부 네트워크를 차단했을 때 남는 기능
5. 백업과 사용자 인증 방식

## NotebookLM과 비교할 때 기능 수보다 운영 책임을 본다

Open Notebook의 장점은 모델과 파이프라인을 선택할 수 있다는 점입니다. 사내 문서에 맞춰 청킹을 바꾸거나, 로컬 모델과 외부 고성능 모델을 업무별로 나눌 수 있습니다. REST API가 필요한 자체 워크플로에도 맞출 여지가 있습니다.

대신 속도와 품질은 선택한 하드웨어와 모델에 달려 있습니다. GPU가 약하면 많은 문서를 임베딩하거나 긴 오디오를 만들 때 오래 걸릴 수 있습니다. 원문은 출처 표시 기능이 기본 수준이며 개선이 필요하다고 적습니다. 답변이 어느 문단에서 왔는지 정교하게 확인해야 하는 업무라면 citation 정확도를 먼저 시험해야 합니다.

## 작은 검증 세트로 결정한다

도입 여부는 기능표보다 실제 문서로 판단하는 편이 낫습니다. 표, 긴 PDF, 서로 충돌하는 문서를 섞은 작은 세트를 만들고 다음을 확인할 수 있습니다.

- 답변이 정확한 문서 위치를 가리키는가
- 청크 크기를 바꿨을 때 누락이 줄어드는가
- 로컬 모델에서 허용 가능한 응답 시간이 나오는가
- 오디오 대본이 출처 내용과 어긋나지 않는가
- 서비스 로그와 외부 연결에 민감한 문장이 남는가

프로젝트 소개는 [Open Notebook 웹사이트](https://www.open-notebook.ai/)에도 있습니다. 이 도구의 선택 이유는 “NotebookLM 기능을 100% 복제한다”는 과장이 아니라, 문서 파이프라인과 모델 선택을 직접 운영할 필요가 있을 때 생깁니다. 그 통제권과 함께 업데이트, 보안, 백업 책임도 사용자에게 돌아옵니다.

## Data Flow Map은 어떻게 그릴까

Upload부터 output까지 component와 endpoint를 한 줄로 연결합니다.

```text
document storage → parser, chunker → embedding endpoint
→ vector store → retrieval → LLM endpoint
→ answer, citation storage → optional TTS endpoint → audio file
```

각 화살표에 data type, encryption, retention과 operator를 적습니다. External network를 차단한 test에서 어떤 기능이 실패하는지 보면 hidden cloud dependency를 찾을 수 있습니다. Application log, error trace에 document content가 남는지도 확인합니다.

## Citation Accuracy를 어떤 질문으로 평가할까

정답 문단이 한 chunk에 있는 질문, 표와 본문을 함께 봐야 하는 질문, 두 문서가 충돌하는 질문과 답이 없는 질문을 만듭니다. Answer correctness와 retrieved source recall, citation precision, faithfulness를 분리합니다.

| Test | 기대 동작 | 대표 failure |
|---|---|---|
| 단일 fact | 정확한 page, span 인용 | 관련 문서지만 claim 미지원 |
| Multi-hop | 두 source를 모두 연결 | 한 chunk만 보고 단정 |
| Conflicting docs | version, date를 밝혀 충돌 표시 | 최신성을 임의 선택 |
| No answer | 없다고 응답 | 일반지식 hallucination |

Chunk size, overlap, embedding과 reranker를 바꿀 때 같은 set으로 회귀를 봅니다. Citation UI가 있다는 사실과 support evidence가 정확한지는 다릅니다.

## Document ACL은 Index에도 유지되는가

원본 storage 권한만 보호하고 shared vector index에서 다른 user의 chunk가 검색되면 data leak이 생깁니다. Tenant, user, document ACL을 metadata filter와 generation 단계에 모두 적용하고 denied-document query를 negative test로 둡니다.

Document 삭제 때 raw file, chunk, embedding, cache, answer와 audio derivative가 모두 제거되는지 확인합니다. Backup과 log retention은 삭제 SLA와 함께 설계합니다. User export와 audit log도 필요합니다.

## Audio 기능은 별도 Product로 평가한다

Answer가 맞아도 script가 내용을 과장하거나 여러 speaker가 근거 없는 dialogue를 추가할 수 있습니다. Script-to-source faithfulness, pronunciation, speaker consistency, generation time과 TTS external transfer를 측정합니다. 민감 문서에는 audio 생성 자체를 금지할 수 있습니다.

긴 audio를 다시 만들 때 incremental update가 가능한지, source가 바뀌면 stale episode를 어떻게 표시할지도 운영 문제입니다. Entertainment용 자연스러움과 compliance document의 정확성을 같은 기준으로 보지 않습니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [공식 GitHub 저장소](https://github.com/Open-Notebook/open-notebook)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [Firecrawl: 웹사이트를 LLM 전용 마크다운 데이터로 변환하는 오픈소스 웹 스크래퍼]({% post_url 2026-08-19-Firecrawl-Open-Source-Web-Scraper-Turning-Websites-into-LLM-Ready-Markdown-Data %}) — Firecrawl은 복잡한 동적 웹사이트, PDF, 문서를 AI 모델이 바로 소비할 수 있는 깨끗한 마크다운과 구조화된 JSON 데이터로 변환해주는 오픈소스 웹 데이터 API입니다. JavaScript 렌더링, 프록시 순환, 노이즈…
- [Open WebUI만 설치하면 사내 AI가 완성될까: 로컬 추론, RAG, RBAC의 경계]({% post_url 2026-03-25-Breaking-Free-from-the-Comfort-of-ChatGPT-to-Build-a-Local-AI-Assistant-Open-WebUI-Architecture-and-Survival-Guide %}) — Open WebUI의 SvelteKit, FastAPI, 내장 RAG 구조를 살펴보고, 로컬 설치가 곧 데이터 보호나 운영 준비를 뜻하지 않는 이유를 점검합니다.
- [RAG가 엉뚱한 문서를 찾는다면? RAFT의 Distractor 학습법]({% post_url 2025-02-20-raft %}) — 정답 문서와 방해 문서를 함께 넣고 근거를 인용하게 만드는 RAFT의 데이터 구성, 성능표, 적용 조건
<!-- internal-links:end -->

## 자주 묻는 질문

### Open Notebook을 self-host하면 문서가 모두 local에만 있나요?

Storage가 local이어도 embedding, LLM, TTS provider를 cloud endpoint로 쓰면 chunk, prompt, script가 전송될 수 있어 component별 network flow를 확인해야 합니다.

### Citation이 표시되면 답변 근거가 정확한가요?

아닙니다. Retrieved chunk가 claim을 실제 지원하는지 span-level faithfulness와 page, section location을 labeled question set에서 검증해야 합니다.

### NotebookLM 대체 여부는 기능 수로 결정하나요?

자사 document의 answer quality, latency, privacy, ACL과 update, backup 운영비를 같은 workflow에서 비교해야 하며 open source 선택은 운영 책임도 가져옵니다.
