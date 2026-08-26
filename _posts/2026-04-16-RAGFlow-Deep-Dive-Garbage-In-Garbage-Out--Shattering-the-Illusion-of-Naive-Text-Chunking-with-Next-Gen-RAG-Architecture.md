---
layout: post
title: 'RAG 답이 틀릴 때 LLM보다 PDF를 먼저 의심해야 하는 이유: RAGFlow'
date: '2026-04-16 18:33:55'
categories: Tech
tags:
  - RAG
  - 문서AI
  - YOLO
  - 컴퓨터비전
summary: 'RAGFlow의 문서 이해형 수집 구조를 표·레이아웃·읽기 순서 중심으로 살펴보고, 검색 품질을 평가하는 실무 절차와 운영 비용을 정리합니다.'
description: "RAGFlow의 PDF layout·OCR·table parsing과 chunking을 ingestion·retrieval·generation 단계로 분리해 평가하고, bbox 근거·queue·회귀 문서·운영비를 검증합니다."
github_url: https://github.com/infiniflow/ragflow
faq:
  - question: "RAG 답이 틀리면 먼저 LLM을 바꾸는 것이 좋나요?"
    answer: "먼저 정답 표·문장이 올바른 읽기 순서와 구조로 수집되고 검색 결과에 포함됐는지 확인해야 오류 단계를 구분할 수 있습니다."
  - question: "RAGFlow를 쓰면 어떤 PDF도 정확히 구조화되나요?"
    answer: "아닙니다. 저해상도 scan, 손상된 font, 잘린 table과 새로운 layout에서는 OCR·영역 탐지가 실패할 수 있어 원문 bbox와 사람 검산이 필요합니다."
  - question: "RAGFlow 도입 효과는 어떤 지표로 비교해야 하나요?"
    answer: "문서 유형별 parsing 정답률, 근거 chunk 적중률, 최종 답 정확도와 페이지당 처리시간·재시도·저장비를 같은 질문 세트에서 비교합니다."
image:
  path: https://opengraph.githubassets.com/1/infiniflow/ragflow
  alt: "infiniflow/ragflow GitHub 저장소 대표 이미지"
---

표와 다단 편집이 많은 PDF에서 RAG 답변이 틀린다면 LLM을 바꾸기 전에 문서가 어떤 순서와 구조로 잘렸는지부터 확인해야 합니다. RAGFlow의 가치는 모델 이름보다 근거 chunk를 원문 페이지·경계 상자로 되돌릴 수 있는 수집 경로에 있으며, parsing 개선과 추가 infrastructure 비용을 같은 문서 집합에서 비교해야 합니다.

[RAGFlow](https://github.com/infiniflow/ragflow)가 겨냥하는 문제도 여기에 있습니다. 문자를 일정 길이로 자르는 방식은 구현은 쉽지만, 셀과 열의 관계나 제목과 본문의 계층을 잃기 쉽습니다. 검색기는 훼손된 조각을 충실히 찾아도 정답을 복원할 수 없습니다.

## 단순 청킹이 표와 다단 PDF를 망치는 방식

PDF의 내부 문자 순서는 사람이 화면에서 읽는 순서와 다를 수 있습니다. 두 열 문서를 가로질러 문장을 이어 붙이거나, 표의 열 이름과 값을 떨어뜨리면 임베딩 품질과 상관없이 의미가 달라집니다. 머리말과 꼬리말이 모든 조각에 반복되면 검색 결과도 오염됩니다.

RAGFlow의 Deep Document Understanding은 페이지를 시각적으로 렌더링해 제목, 본문, 표, 이미지 같은 영역과 경계 상자를 식별하고 읽기 순서를 복원하는 접근입니다. 원문은 YOLO 계열 탐지와 LayoutLM 계열 문서 모델을 설명합니다. 표에서는 행과 열 관계를 보존한 채 검색 가능한 단위로 만드는 것이 핵심입니다.

| 문서 요소 | 단순 text 추출의 실패 | 검수할 parsing 결과 |
|---|---|---|
| 2단 본문 | 왼쪽·오른쪽 열 문장이 교차 | column별 읽기 순서와 문단 경계 |
| 병합 table | header와 값이 분리 | 행·열 header를 값과 함께 표현 |
| 반복 머리말 | 모든 chunk에서 높은 빈도로 검색 | header 제거와 페이지 metadata 보존 |
| 각주 | 본문 중간에 끼거나 사라짐 | 참조 marker와 각주 연결 |
| scan | 빈 text 또는 OCR 오인 | bbox, OCR confidence와 원본 crop |

layout model이 영역을 맞혀도 chunk 경계에서 의미가 다시 깨질 수 있습니다. 표 전체를 하나의 거대한 chunk로 두면 검색은 맞아도 model context가 커지고, 셀 하나씩 자르면 header가 사라집니다. 질문이 특정 행의 값인지 여러 행 비교인지에 따라 row 단위 표현과 원표 참조를 함께 저장하는 방식이 필요합니다.

페이지를 넘는 문장과 표도 별도 실패 항목입니다. 이전 페이지 끝과 다음 페이지 시작이 같은 section인지, 반복 header가 새 table로 오인되지 않는지 확인합니다. 원문 page·bbox ID가 chunk 변환 뒤에도 남아야 답변에서 해당 위치를 다시 열 수 있습니다.

## 수집 결과를 먼저 정답표와 비교한다

도입 검증용 문서는 무작위로 고르지 않습니다. 합쳐진 셀이 있는 표, 두 단 편집, 스캔 이미지, 반복 머리말, 각주가 있는 문서를 각각 준비하고 사람이 기대하는 읽기 순서와 핵심 셀 값을 적습니다. 그 뒤 파싱 결과에서 제목 계층, 표 헤더 연결, 페이지 간 문장 결합이 보존됐는지 직접 비교합니다.

정답표에는 “전체 페이지가 예뻐 보인다” 대신 검증 가능한 항목을 둡니다. 예를 들어 7페이지 table의 `2025 Q2` 열과 `APAC` 행이 만나는 값, 3페이지 각주가 가리키는 본문 문장, 두 단 문서의 첫 다섯 문장 순서를 기록합니다. version upgrade마다 이 문서들을 다시 처리해 regression을 찾습니다.

검색 평가는 질문과 답만 보지 말고 어느 조각이 근거로 반환됐는지 함께 봐야 합니다. 정답 셀을 포함한 조각이 검색되지 않았다면 검색·청킹 문제이고, 근거는 맞는데 답이 틀렸다면 생성 단계 문제입니다. 이 구분이 있어야 모델 교체와 파서 조정을 혼동하지 않습니다.

세 단계의 denominator도 다릅니다. ingestion 평가는 문서 요소 중 올바르게 복원한 비율, retrieval은 정답 근거가 top-k에 들어온 질문 비율, generation은 올바른 근거가 주어졌을 때 답을 맞힌 비율입니다. 최종 답 점수 하나만 보면 parsing 개선이 retrieval 설정 때문에 가려지거나, 생성 model이 우연히 외부 지식으로 맞힌 답을 성공으로 셀 수 있습니다.

근거가 없는 질문도 넣습니다. 시스템이 비슷한 table을 가져와 값을 지어내지 않고 “문서에서 찾을 수 없다”고 답하는지 평가합니다. 최신 version과 폐기 version의 문서가 함께 있을 때 날짜·문서 ID filter가 올바르게 적용되는지도 중요합니다.

## 운영비는 비동기 수집 경로에서 생긴다

이 방식은 파일 업로드 즉시 끝나는 가벼운 전처리가 아닙니다. 원문이 설명하는 구성에는 Python 기반 OCR·컴퓨터 비전 처리와 MySQL, MinIO, Redis, Elasticsearch 또는 Infinity 같은 저장·색인 계층이 포함됩니다. 대량 문서는 비동기 작업으로 처리하고 실패한 페이지를 재시도할 수 있어야 합니다.

따라서 처리량은 페이지 수만이 아니라 스캔 비율, 표 밀도, OCR 필요 여부로 나눠 측정해야 합니다. GPU를 붙였을 때 단축되는 시간과 대기열 지연, 저장 공간, 색인 갱신 비용도 함께 기록합니다. 단순한 텍스트 문서만 다루는 팀에는 이 복잡성이 오히려 과할 수 있습니다.

ingestion job에는 문서 hash와 parser version을 붙여 같은 파일의 중복 처리와 부분 재시도를 구분합니다. 100페이지 중 1페이지 OCR이 실패했을 때 전체를 처음부터 다시 색인하면 비용과 duplicate chunk가 늘 수 있습니다. 실패 page만 재처리한 뒤 기존 index를 원자적으로 교체하고, 사용자가 검색 중인 version이 섞이지 않게 해야 합니다.

운영 지표는 queue 길이만으로 부족합니다. oldest job age, 문서 유형별 page 처리시간, OCR 실패·재시도, index commit 지연과 원문 대비 chunk 저장 배수를 봅니다. parser가 새 문서 형식에서 갑자기 느려지면 전체 queue를 막지 않도록 파일 크기·페이지 수 한도와 격리 queue를 둡니다.

민감 문서는 OCR 중간 image, extracted text, embedding과 실패 log에 여러 번 복제됩니다. 각 저장 계층의 암호화·접근 권한·삭제 기한을 정하고 원문 삭제 요청이 index와 cache까지 전파되는지 확인합니다. 외부 embedding model을 쓰면 어떤 chunk가 전송되는지도 별도로 검토합니다.

## 정교한 파서도 원본의 한계를 넘지는 못한다

해상도가 낮은 스캔, 잘린 표, 손상된 글꼴처럼 원본에 정보가 없으면 시각 이해 모델도 확정적인 값을 만들 수 없습니다. 레이아웃 판정 역시 모델 결과이므로 새 문서 양식이 들어올 때 회귀할 수 있습니다. 중요한 숫자는 출처 페이지와 경계 상자를 함께 노출해 사람이 검산할 수 있어야 합니다.

실무적인 출발점은 전체 저장소 이전이 아닙니다. 실패가 잦은 문서 유형 하나를 골라 기존 파서와 RAGFlow의 수집 결과, 검색 적중률, 처리 비용을 같은 질문 세트로 비교하세요. 답변 모델은 고정해야 문서 이해 개선이 실제 효과인지 분리해 볼 수 있습니다.

비교 결과에는 페이지당 처리비만 아니라 사람이 잘못된 답을 검산하는 시간도 포함합니다. table 질문의 근거 적중률이 의미 있게 올라가고 회귀 문서가 통과하지만 plain text에서는 이득이 없다면 문서 유형별 router로 RAGFlow 적용 범위를 제한할 수 있습니다. 모든 파일을 무거운 경로로 보내는 것만이 통합은 아닙니다.

실패 시 fallback도 정합니다. OCR confidence가 낮거나 table header 연결을 만들지 못한 페이지는 검색 가능한 정상 문서로 표시하지 말고 검토 queue로 보냅니다. 사용자는 답변에서 parser version과 원문 page를 확인할 수 있어야 하며, source crop을 열 수 없는 주장은 자동 업무 결정에 쓰지 않는 편이 안전합니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [공식 GitHub 저장소](https://github.com/infiniflow/ragflow)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [MarkItDown만으로 RAG 전처리가 끝날까: PDF 읽기 순서·표·VLM 비용 점검]({% post_url 2026-03-01-Why-Did-I-Just-Find-Out-About-This-A-Savior-for-RAG-Pipelines-An-Honest-Review-of-MS-MarkItDown %}) — PDF·엑셀·PPT를 마크다운으로 통일하는 MarkItDown의 역할과 다단 PDF, 병합 셀, 메타데이터, VLM 비용에서 남는 검증 과제를 정리합니다.
- [WeKnora가 표·수식 PDF RAG에 맞을까: 파싱·Hybrid Retrieval 검증]({% post_url 2026-05-15-For-Those-Tired-of-Simple-ChatUI-Shells-A-Deep-Dive-Under-the-Hood-of-WeKnora-Tencents-Hardcore-RAG-Engine %}) — WeKnora의 layout·표·수식 parsing과 BM25·dense·graph 검색, agent·MCP 구조를 살펴보고 한국어 문서 정확도·인용·자원·운영 조건을 검증합니다.
- [Open WebUI만 설치하면 사내 AI가 완성될까: 로컬 추론·RAG·RBAC의 경계]({% post_url 2026-03-25-Breaking-Free-from-the-Comfort-of-ChatGPT-to-Build-a-Local-AI-Assistant-Open-WebUI-Architecture-and-Survival-Guide %}) — Open WebUI의 SvelteKit·FastAPI·내장 RAG 구조를 살펴보고, 로컬 설치가 곧 데이터 보호나 운영 준비를 뜻하지 않는 이유를 점검합니다.
<!-- internal-links:end -->

## 자주 묻는 질문

### RAG 답이 틀리면 먼저 LLM을 바꾸는 것이 좋나요?

먼저 정답 표·문장이 올바른 읽기 순서와 구조로 수집되고 검색 결과에 포함됐는지 확인해야 오류 단계를 구분할 수 있습니다.

### RAGFlow를 쓰면 어떤 PDF도 정확히 구조화되나요?

아닙니다. 저해상도 scan, 손상된 font, 잘린 table과 새로운 layout에서는 OCR·영역 탐지가 실패할 수 있어 원문 bbox와 사람 검산이 필요합니다.

### RAGFlow 도입 효과는 어떤 지표로 비교해야 하나요?

문서 유형별 parsing 정답률, 근거 chunk 적중률, 최종 답 정확도와 페이지당 처리시간·재시도·저장비를 같은 질문 세트에서 비교합니다.
