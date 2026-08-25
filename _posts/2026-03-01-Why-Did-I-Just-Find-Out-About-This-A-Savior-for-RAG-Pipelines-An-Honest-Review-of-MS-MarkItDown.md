---
layout: post
title: "MarkItDown만으로 RAG 전처리가 끝날까: PDF 읽기 순서·표·VLM 비용 점검"
date: '2026-03-01'
categories: Tech
tags:
  - MarkItDown
  - RAG
  - 문서전처리
  - PDF파싱
  - 멀티모달
summary: "PDF·엑셀·PPT를 마크다운으로 통일하는 MarkItDown의 역할과 다단 PDF, 병합 셀, 메타데이터, VLM 비용에서 남는 검증 과제를 정리합니다."
author: AI Trend Bot
github_url: https://github.com/microsoft/markitdown
image:
  path: https://opengraph.githubassets.com/1/microsoft/markitdown
  alt: 'Why Did I Just Find Out About This? A Savior for RAG Pipelines: An Honest
    Review of MS MarkItDown'
---

MarkItDown은 여러 문서를 마크다운으로 통일하는 변환기이지, RAG 전처리 전체를 대신하는 파서나 청커는 아닙니다.

PDF·Word·Excel·PPT·HTML처럼 입력 형식이 제각각이면 변환 계층 하나만 통일해도 파이프라인은 단순해집니다. 다만 변환 결과가 생겼다는 사실과 검색에 쓸 만한 데이터가 만들어졌다는 판단은 구분해야 합니다. 표 구조, 읽기 순서, 이미지 설명, 메타데이터를 샘플 문서로 확인한 뒤 청킹과 품질 검사를 붙이는 편이 안전합니다.

## 어떤 문제를 줄여 주는가

[MarkItDown](https://github.com/microsoft/markitdown)은 여러 형식의 파일을 LLM이 다루기 쉬운 마크다운 텍스트로 바꿉니다. 제목과 목록, 표 같은 구조를 한 가지 표현으로 맞출 수 있어 포맷마다 서로 다른 출력 인터페이스를 유지하는 부담이 줄어듭니다. ZIP 내부 파일을 재귀적으로 처리할 수 있다는 점도 여러 문서가 묶인 입력에 유용합니다.

그러나 “마크다운으로 변환됨”이 “원문 의미가 보존됨”을 뜻하지는 않습니다. 도입 전에 최소한 다음 결과를 원문과 나란히 봐야 합니다.

- 제목 계층과 목록 순서가 유지되는가
- 표의 열과 행이 밀리지 않는가
- 본문과 각주, 머리글이 섞이지 않는가
- 변환 실패 파일을 별도로 기록할 수 있는가

## 기본 변환 코드는 어디까지 보여 주나

가장 작은 사용 형태는 다음과 같습니다.

```python
from markitdown import MarkItDown

md = MarkItDown()
result = md.convert("복잡한_회사_실적보고서.xlsx")
print(result.text_content)
```

이 코드는 “파일 하나를 변환해 텍스트를 얻는다”는 핵심 조각입니다. 설치할 선택 의존성, 지원 버전, 암호화되거나 손상된 파일의 처리, 예외 기록, 대용량 파일 제한은 포함하지 않습니다. 따라서 운영 절차로 복사하기보다, [배포 패키지 정보](https://pypi.org/project/markitdown/)와 대상 형식의 요구 사항을 확인하는 출발점으로 봐야 합니다.

변환 뒤에는 원본 파일명·페이지나 시트·슬라이드 같은 출처 정보를 청크와 함께 남기는 로직도 필요합니다. MarkItDown이 내놓는 순수 텍스트만 저장하면 검색 답변에서 근거 위치를 되짚기 어려울 수 있습니다.

## VLM 연동은 정확도와 비용을 함께 바꾼다

문서 안의 사진이나 다이어그램을 설명하려면 LLM 클라이언트와 모델을 넘길 수 있습니다.

```python
from markitdown import MarkItDown
from openai import OpenAI

client = OpenAI()
md = MarkItDown(llm_client=client, llm_model="gpt-4o")
result = md.convert("아키텍처_다이어그램_포함.pdf")
```

이 역시 최소 예시입니다. API 인증, 전송되는 데이터의 범위, 재시도, 비용 상한, 모델 응답 검증은 생략돼 있습니다. 이미지가 많은 문서는 호출량이 커질 수 있고, 생성된 설명에는 누락이나 잘못된 해석이 들어갈 수 있습니다. 민감 문서라면 외부 모델로 전송해도 되는지부터 확인해야 합니다.

호환 API를 제공하는 Ollama·LLaVA 계열 로컬 구성을 고려할 수 있지만, 이를 곧바로 “비용 0원”으로 표현하기는 어렵습니다. API 사용료 대신 하드웨어, 운영, 처리 시간과 모델 품질 검증 비용이 생깁니다.

## 실패하기 쉬운 문서를 먼저 시험해야 한다

MarkItDown의 가치가 가장 잘 드러나는 문서보다 실패 비용이 큰 문서를 먼저 넣어 보는 편이 낫습니다.

- 다단 PDF는 문장의 읽기 순서가 바뀌지 않는지 확인합니다.
- 병합 셀이 많은 Excel은 빈칸과 헤더가 잘못 연결되지 않는지 봅니다.
- 표·이미지·본문이 섞인 PPT는 슬라이드 경계와 순서를 검사합니다.
- 문서 유형별로 사람이 판정한 정답 샘플을 만들어 회귀 테스트에 씁니다.

특히 표의 숫자와 열 이름이 어긋나면 검색은 성공해도 답이 틀릴 수 있습니다. 변환 성공률만 집계하지 말고 구조 보존률과 근거 추적 가능성도 품질 지표로 두는 이유입니다.

## 도입 판단은 변환 이후 단계까지 포함한다

파일 형식을 하나의 마크다운 인터페이스로 통일하려는 팀에는 MarkItDown이 유용한 시작점입니다. 반면 정교한 레이아웃 복원, 청크별 메타데이터, 인용 위치 보존이 핵심이라면 별도 파싱과 후처리를 예상해야 합니다.

실행 순서는 간단합니다. 대표 문서보다 어려운 문서 묶음으로 변환 품질을 측정하고, 형식별 실패 규칙을 만든 뒤, 헤더 기반 청킹과 출처 메타데이터를 붙입니다. 마지막으로 VLM을 켠 경우와 끈 경우의 정확도·지연·비용을 비교해야 합니다. 이 검증을 통과할 때 MarkItDown은 RAG의 “구원자”가 아니라 관리 가능한 변환 계층이 됩니다.
