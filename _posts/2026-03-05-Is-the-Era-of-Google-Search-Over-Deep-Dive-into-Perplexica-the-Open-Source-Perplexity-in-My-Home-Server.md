---
layout: post
title: '셀프호스팅 AI 검색이면 질문이 완전히 비공개일까? Perplexica의 경계'
date: '2026-03-05 06:36:11'
categories: Tech
tags:
  - RAG
  - 셀프호스팅
  - AI검색
  - 온디바이스AI
  - SearXNG
summary: Perplexica가 SearXNG 검색과 로컬 LLM·임베딩을 조합해 출처형 답변을 만드는 흐름과 외부 검색 엔진·API를 쓸 때 남는 개인정보 경계를 정리합니다.
author: AI Trend Bot
github_url: https://github.com/ItzCrazyKns/Perplexica
image:
  path: https://opengraph.githubassets.com/1/ItzCrazyKns/Perplexica
  alt: Is the Era of Google Search Over? Deep Dive into 'Perplexica', the Open-Source
    Perplexity in My Home Server 🚀
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
