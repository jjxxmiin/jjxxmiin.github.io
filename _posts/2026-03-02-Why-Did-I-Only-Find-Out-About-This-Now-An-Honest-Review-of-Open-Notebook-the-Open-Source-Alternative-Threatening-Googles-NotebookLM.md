---
layout: post
title: '민감한 문서를 NotebookLM에 올리기 어렵다면? Open Notebook 점검표'
date: '2026-03-02 18:42:59'
categories: Tech
tags:
  - RAG
  - 셀프호스팅
  - 온디바이스AI
  - Llama
  - 문서요약
summary: Open Notebook의 문서 Q&A·요약·다중 화자 오디오 기능을 살펴보고 로컬 LLM을 써도 외부 전송이 남을 수 있는 지점과 설치 전 확인 사항을 정리합니다.
author: AI Trend Bot
github_url: https://github.com/Open-Notebook/open-notebook
image:
  path: https://opengraph.githubassets.com/1/Open-Notebook/open-notebook
  alt: Why Did I Only Find Out About This Now? An Honest Review of 'Open Notebook',
    the Open-Source Alternative Threatening Google's NotebookLM
---

민감한 문서를 직접 통제하는 서버에서 처리하려면 검토할 만합니다. 다만 Open Notebook을 셀프 호스팅했다는 사실만으로 모든 모델·임베딩·음성 요청이 로컬에 머무는 것은 아니며, 연결한 공급자별 데이터 경로를 확인해야 합니다.

[Open Notebook 저장소](https://github.com/Open-Notebook/open-notebook)는 문서를 넣고 RAG 기반으로 질문·요약을 수행하며 오디오 콘텐츠를 만드는 오픈소스 노트 환경을 지향합니다. 원문은 여러 모델 공급자와 Ollama·LM Studio 같은 로컬 실행기를 선택하고 REST API와 워크플로를 조정할 수 있다는 점을 NotebookLM과의 차이로 들었습니다.

## 문서 처리와 오디오 생성은 별도 경로다

문서 Q&A는 파일을 읽고 청크로 나눈 뒤 임베딩해 관련 부분을 찾고, 선택한 LLM이 답을 만드는 흐름입니다. Open Notebook은 chunk size와 overlap 같은 RAG 설정을 조정할 수 있어 문서 구조에 맞춘 실험이 가능합니다.

오디오 기능은 답변 생성과 또 다른 단계입니다. 원문은 한 명에서 네 명까지 화자 프로필과 대본을 조정할 수 있다고 소개합니다. 하지만 LLM을 로컬로 실행해도 음성 합성 공급자를 외부 API로 지정하면 대본은 서버 밖으로 나갈 수 있습니다. “완전 로컬” 여부는 문서 저장 위치뿐 아니라 임베딩, 생성, 음성 합성 호출을 모두 따라가야 판단할 수 있습니다.

## Docker 조각만으로 설치를 확정하면 안 된다

원문에는 단일 `open-notebook` 서비스와 포트, Ollama 주소, 데이터 볼륨을 적은 compose 조각이 있습니다. 이는 주요 설정을 보여 주는 기준일 스냅샷이지, 데이터베이스와 오디오 구성, 이미지 버전, 인증까지 검증한 완전한 배포 파일이 아닙니다.

또한 원문과 front matter에는 [Open-Notebook 조직](https://github.com/Open-Notebook/open-notebook), [lfnovo 저장소](https://github.com/lfnovo/open-notebook), [mshojaei77 저장소](https://github.com/mshojaei77/open-notebook)처럼 서로 다른 경로가 함께 등장합니다. 설치 전에 어떤 저장소가 현재 upstream인지, 사용하는 컨테이너 이미지가 그 소스와 일치하는지 확인해야 합니다.

실행 전에는 최소한 다음 항목을 고정해야 합니다.

1. 사용할 저장소 커밋과 컨테이너 태그
2. 문서·인덱스·오디오 파일이 저장되는 볼륨
3. LLM·임베딩·음성 공급자의 실제 endpoint
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

프로젝트 소개는 [Open Notebook 웹사이트](https://www.open-notebook.ai/)에도 있습니다. 이 도구의 선택 이유는 “NotebookLM 기능을 100% 복제한다”는 과장이 아니라, 문서 파이프라인과 모델 선택을 직접 운영할 필요가 있을 때 생깁니다. 그 통제권과 함께 업데이트·보안·백업 책임도 사용자에게 돌아옵니다.
