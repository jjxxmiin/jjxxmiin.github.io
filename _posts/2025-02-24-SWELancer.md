---
layout: post
title: "SWE-Lancer에서 AI는 100만 달러 중 얼마를 벌었나: $403K의 의미"
summary: "실제 Upwork 작업 1,488개를 코드 구현과 매니저 판단으로 나눈 SWE-Lancer, 최고 $403K 점수를 과대해석하지 않는 법"
image:
  path: /assets/img/thumb/SWELancer.jpg
  alt: "SWE-Lancer: LLM이 실제 소프트웨어 엔지니어링으로 돈을 벌 수 있을까? 대표 이미지"
date: 2025-02-24
categories: Paper
tags:
  - SWELancer
  - AI코딩
  - 소프트웨어평가
  - LLM
math: true
---

SWE-Lancer에서 가장 높은 결과는 100만 달러 중 40만 3천 달러에 해당했지만, 이는 AI가 실제로 취업해 받은 수입이 아니라 통과한 프리랜서 작업의 보상액을 합산한 벤치마크 점수입니다.

- [논문](https://arxiv.org/abs/2502.12115v2)
- [벤치마크 GitHub](https://github.com/openai/SWELancer-Benchmark)

![SWE-Lancer 작업 예시](/assets/img/post_img/swe_lancer/3.PNG)

## 실제 작업의 가격을 평가 가중치로 쓴다

SWE-Lancer는 Upwork에서 채택된 소프트웨어 작업 1,488개를 모았고, 작업에 걸린 보상액은 합계 100만 달러입니다. 개별 금액은 50달러부터 32,000달러까지 분포합니다. 모델이 해결한 작업의 원래 보상액을 더하면 “얼마를 벌 수 있었는가”라는 직관적인 점수가 됩니다.

다만 높은 가격의 과제 하나가 낮은 가격 과제 여러 개보다 총액에 더 큰 영향을 줍니다. 따라서 달러 점수와 작업 성공률은 함께 봐야 합니다. 이 수치에는 실제 고객과의 소통, 배포 뒤 유지보수, 모델 사용 비용과 작업 시간까지 포함되지 않습니다.

## 구현과 선택을 서로 다른 시험으로 나눈다

![IC SWE와 Manager 작업](/assets/img/post_img/swe_lancer/1.PNG)

SWE-Lancer에는 두 종류의 문제가 있습니다.

| 유형 | 모델이 해야 할 일 | 대표 사례 |
|---|---|---|
| IC SWE Tasks | 코드베이스를 이해하고 버그 수정이나 기능 추가를 구현 | API 중복 호출 수정, 앱 내 비디오 재생 추가 |
| SWE Manager Tasks | 여러 개발자의 해결책을 비교해 가장 나은 안을 선택 | 데이터베이스 최적화 방식 선택 |

IC 과제는 코드를 직접 바꾸고 end-to-end 테스트를 통과해야 합니다. Manager 과제는 이미 나온 대안 중 옳은 선택을 해야 합니다. 둘의 점수 차이는 “코드를 고르는 능력”과 “완성된 변경을 구현하는 능력”이 같지 않다는 점을 보여 줍니다.

공개된 Diamond Set은 전체 중 엄선된 502개로, IC 237개와 Manager 265개를 포함합니다. 보상액은 각각 236,300달러와 264,500달러, 합계 500,800달러입니다.

## $403K는 절반을 해결했다는 뜻이 아니다

![모델별 SWE-Lancer 결과](/assets/img/post_img/swe_lancer/4.PNG)

| 모델 | IC SWE 수행률 | SWE Manager 수행률 | 100만 달러 기준 점수 |
|---|---:|---:|---:|
| GPT-4o | 8.6% | 38.7% | $304K |
| o1 | 20.3% | 46.3% | $380K |
| Claude 3.5 Sonnet | **26.2%** | **47.0%** | **$403K** |

Claude 3.5 Sonnet이 세 모델 중 가장 높은 403,000달러를 기록했지만, IC 성공률은 26.2%입니다. 총액 40.3%와 구현 과제 40.3% 성공을 같은 뜻으로 읽으면 안 됩니다. 세 모델 모두 Manager 과제보다 IC 구현 과제에서 더 낮았다는 점도 중요합니다.

![작업 유형별 성능](/assets/img/post_img/swe_lancer/5.PNG)

이 결과는 “AI가 초급 개발자를 대체했다”는 직급 판정도 아닙니다. 벤치마크가 직접 보여 주는 것은 주어진 코드베이스와 평가 조건에서 어떤 작업을 통과하고 어떤 해결책을 선택했는지입니다.

## 재현 명령은 저장소를 받은 뒤의 일부 절차다

원문에 실린 uv 기반 환경 설정과 실행 흐름은 다음과 같습니다.

~~~bash
uv sync
source .venv/bin/activate
for proj in nanoeval alcatraz nanoeval_alcatraz; do
  uv pip install -e project/"$proj"
done

cp sample.env .env
uv run python run_swelancer.py
~~~

이 조각은 저장소를 이미 받은 상태를 전제로 하며, sample.env에 필요한 API 키와 환경 변수를 채우는 과정은 포함하지 않습니다. Docker 이미지를 빌드할 때도 Apple Silicon·ARM64용 Dockerfile과 x86_64·AMD64용 Dockerfile_x86이 다르고 SSH 에이전트를 전달하는 명령이 사용됩니다.

따라서 곧바로 복사해 실행하는 단일 설치법이라기보다 2025년 2월 저장소 구조를 설명하는 출발점으로 봐야 합니다. 재현할 때는 평가 모델 설정, 아키텍처에 맞는 이미지, 환경 변수, end-to-end 판정 기준을 고정해야 모델 간 달러 점수를 공정하게 비교할 수 있습니다.
