---
source_citations:
  - name: "Darknet compare.c 고정 커밋 원본"
    url: "https://raw.githubusercontent.com/pjreddie/darknet/f6afaabcdf85f77e7aff2ec55c020c0e297c77f9/src/compare.c"
layout: post
title: "DarkNet Compare는 두 이미지를 어떻게 순위로 바꾸나"
summary: "DarkNet compare 코드의 쌍 비교 학습, 10분할 검증, qsort 정렬과 Elo 토너먼트 흐름을 실행 전 주의점과 함께 정리합니다."
description: "DarkNet Compare의 이미지 쌍 학습, 누적 검증, qsort와 Elo 순위 경로를 데이터 계약, 비교 일관성, 버퍼 안전성 기준으로 설명합니다."
date:   2022-02-11 16:00 -0400
categories: DarkNet
image:
  path: /assets/img/thumb/DarkNetCompare.jpg
  alt: DarkNet 시리즈 - Compare 대표 이미지
tags:
  - DarkNet
  - 컴퓨터비전
math: true
faq:
  - question: "DarkNet Compare는 한 이미지의 절대 점수를 직접 학습하나요?"
    answer: "아닙니다. 두 이미지를 함께 입력해 클래스마다 어느 쪽이 우세한지 쌍 비교 출력을 학습하고, 필요하면 비교 결과를 순위로 집계합니다."
  - question: "qsort 순위와 Elo 순위는 같은 방식인가요?"
    answer: "아닙니다. qsort 경로는 비교 함수를 이용해 한 class 기준으로 직접 정렬하고, Elo 경로는 반복 대결 결과로 class별 rating을 갱신합니다."
  - question: "원문 Compare 코드를 실행하기 전에 가장 먼저 확인할 것은 무엇인가요?"
    answer: "두 이미지를 담을 입력 buffer 크기, 고정된 목록, 백업 경로, 클래스 수와 실제 run_compare 명령 분기를 먼저 확인해야 합니다."
---

DarkNet의 Compare 모드는 두 이미지를 한 번에 네트워크에 넣어 클래스별 우열을 예측하고, 그 결과로 검증 정확도나 이미지 순위를 계산하는 코드입니다. 읽을 때는 학습용 이미지 쌍 구성, 한 쌍의 정방향 계산, 검증과 순위 산출을 나눠 봐야 합니다. 출력은 일반적인 이미지 유사도가 아니라 설정된 클래스별 비교 점수이므로 데이터 형식과 인덱스를 함께 확인해야 합니다.

## 학습 데이터는 이미지 쌍으로 읽는다

`train_compare`는 설정 파일로 네트워크를 만들고, 가중치가 지정되면 이어서 불러옵니다. 입력 목록은 `data/compare.train.list`, 데이터 형식은 `COMPARE_DATA`로 고정되어 있습니다.

~~~c
int imgs = 1024;
list *plist = get_paths("data/compare.train.list");

args.classes = 20;
args.n = imgs;
args.type = COMPARE_DATA;
~~~

로더 스레드가 현재 묶음을 읽는 동안 다음 묶음을 미리 요청하고, `train_network`가 반환한 손실을 지수 이동 평균으로 누적합니다. 100번 반복할 때마다 `minor` 가중치를 저장하고, `seen / N`이 다음 epoch로 넘어가면 epoch 가중치를 저장합니다. 22 epoch마다 학습률을 10분의 1로 낮추는 조건도 코드에 들어 있습니다.

이 구조를 다른 데이터에 적용하려면 클래스 수 20, 한 번에 읽는 이미지 수 1024, 목록 경로와 백업 경로를 먼저 자신의 환경에 맞춰야 합니다.

## 검증은 각 클래스의 두 출력 방향을 비교한다

`validate_compare`는 `data/compare.val.list`를 읽은 뒤 전체 크기의 절반을 `N`으로 잡고, 데이터를 10개 구간으로 나눠 예측합니다. 정답과 예측 모두 클래스마다 두 칸을 사용합니다.

~~~c
if(val.y.vals[j][k*2] != val.y.vals[j][k*2+1]){
    ++total;
    if((val.y.vals[j][k*2] < val.y.vals[j][k*2+1]) ==
       (pred.vals[j][k*2] < pred.vals[j][k*2+1])){
        ++correct;
    }
}
~~~

두 정답 값이 같지 않은 경우만 평가 대상으로 세고, 어느 쪽 값이 더 작은지에 대한 방향이 예측과 일치하면 `correct`를 올립니다. 출력되는 정확도는 각 분할만의 점수가 아니라, 앞에서 처리한 결과까지 누적한 `correct / total`입니다.

## qsort와 Elo는 서로 다른 순위 경로다

`SortMaster3000`은 `data/compare.sort.list`의 이미지를 `qsort`에 넘깁니다. 비교 함수는 이미지 두 장을 불러 네트워크 출력을 얻고, 고정된 클래스 7의 두 출력값을 비교합니다. 따라서 이 경로는 한 클래스 기준의 직접 정렬입니다.

`BattleRoyaleWithCheese`는 클래스 20개 각각에 Elo 점수를 둡니다. 모든 이미지는 1500에서 시작하고, 한 번의 대결 결과를 받은 `bbox_update`가 K값 32로 두 점수를 함께 갱신합니다.

~~~c
float EA = 1./(1+pow(10, (b->elos[class] - a->elos[class])/400.));
float SA = result ? 1 : 0;
a->elos[class] += 32*(SA - EA);
~~~

처음 네 라운드는 모든 클래스를 갱신합니다. 그다음 클래스별로 Elo 내림차순 정렬과 대결을 반복하며, 초기 20라운드에는 후보 수를 줄입니다. 최종 결과는 `results/battle_클래스번호.log` 형태로 기록됩니다.

## 그대로 실행하기 전에 세 가지를 확인한다

이 글의 코드는 완전한 실행 예제가 아니라 당시 DarkNet 소스의 핵심 흐름입니다. 특히 다음 항목은 원문 코드 그대로 실행하기 전에 확인해야 합니다.

- `run_compare`의 안내문에는 `train/test/valid`가 적혀 있지만 실제 분기는 `train`, `valid`, `sort`, `battle`입니다.
- 학습 목록, 검증 목록, 정렬 목록과 `/home/pjreddie/backup/`가 코드에 고정돼 있습니다.
- `bbox_comparator`와 `bbox_fight`는 `X`를 한 이미지 크기로 할당한 뒤 두 이미지 데이터를 연달아 복사합니다. 현재 보이는 코드만으로는 두 번째 복사가 할당 범위를 넘으므로, 사용 중인 소스 버전의 입력 버퍼 크기와 네트워크 입력 형식을 반드시 대조해야 합니다.

즉, 먼저 `train_compare`와 `validate_compare`로 쌍 데이터의 의미를 확인하고, 순위가 필요할 때만 직접 정렬 또는 Elo 토너먼트 중 목적에 맞는 경로를 선택하는 것이 안전합니다.

## 쌍 Label은 어떤 불변조건을 가져야 하나요?

한 class의 두 target 값은 이미지 A와 B의 방향을 나타내므로, 두 이미지를 바꾸면 target 방향도 함께 뒤집혀야 합니다. 같은 pair를 `(A,B)`와 `(B,A)`로 넣었는데 둘 다 같은 쪽이 우세하다고 학습되면 데이터 생성이나 출력 index가 잘못된 것입니다. 두 target 값이 같은 경우는 검증에서 제외되므로 tie가 많은 데이터에서는 표면적 sample 수보다 실제 평가 `total`이 훨씬 작을 수 있습니다.

Train, validation 사이에 같은 이미지가 다른 pair로 반복되면 개별 이미지 특징을 외워 검증 점수가 부풀 수 있습니다. Pair 행만 무작위로 나누기보다 원본 이미지 또는 대상 단위로 분할해야 합니다. 클래스마다 유효 pair 수와 방향 비율도 세어 한쪽 우세만 많은 label에서 단순 편향이 높은 정확도로 보이지 않게 합니다.

## 비교 함수가 정렬 조건을 만족하는지 어떻게 보나요?

`qsort`는 비교 결과가 일관된 순서를 이룬다고 기대합니다. 네트워크가 A>B, B>C, 그런데 C>A로 판단하는 순환 관계를 만들면 전역적으로 완벽한 순서가 존재하지 않습니다. 추론의 randomness나 입력 전처리 차이로 같은 두 이미지를 다시 비교할 때 결과가 바뀌어도 정렬은 불안정해집니다.

작은 이미지 세트에서 모든 pair 결과를 행렬로 만들고 대칭 방향, 자기 비교, 순환 횟수를 확인합니다. Comparator 안에서 매번 이미지를 읽고 network를 호출하면 정렬 과정의 비교 횟수만큼 비용이 들므로 feature나 결과 cache도 고려할 수 있지만, cache key에는 순서와 class를 정확히 포함해야 합니다. 정렬 결과를 절대적인 품질 척도로 부르기 전에 pairwise model의 일관성부터 보고해야 합니다.

## Elo 결과는 어떤 조건에 민감한가요?

Elo 갱신은 현재 rating 차이로 기대 승률을 만들고 실제 승패와 차이만큼 K값을 곱합니다. 같은 대결 집합이라도 순서와 반복 횟수, 초기 rating과 후보 sampling에 따라 중간 순위가 달라질 수 있습니다. 코드의 1500과 K=32는 보편적 최적값이 아니라 이 구현의 설정입니다.

모든 이미지가 충분히 연결된 대결 graph를 갖는지도 중요합니다. 일부 집단끼리만 싸우면 rating 숫자는 있어도 서로 비교할 근거가 약합니다. 여러 shuffle에서 상위 순위가 유지되는지, 대결 수가 적은 항목에 불확실성을 표시하는지 확인하고 단 한 번의 최종 log만 확정 순위로 해석하지 않습니다.

## 입력 Buffer와 전처리는 어떻게 검증하나요?

두 이미지 데이터를 연속 배치한다면 할당 크기는 적어도 `2×w×h×c`여야 하고 network가 기대하는 batch, inputs와 같아야 합니다. 두 번째 `memcpy`의 시작과 마지막 주소를 계산해 buffer 범위를 넘지 않는지 sanitizer로 확인합니다. 크기만 늘리고 network batch를 그대로 두면 두 번째 이미지가 모델 입력으로 읽히지 않을 수도 있습니다.

두 이미지에는 동일한 resize, channel 순서와 정규화를 적용해야 합니다. Comparator 호출 순서에 따라 augmentation이 달라지면 우열 대신 전처리 randomness를 학습하거나 평가할 수 있습니다. 고정된 두 synthetic image를 넣어 A/B 위치를 바꿨을 때 대응하는 출력 두 칸이 기대대로 바뀌는지부터 시험합니다.

검증의 10개 구간도 독립적인 10-fold 교차검증으로 오해하지 않아야 합니다. 한 validation 집합을 메모리와 처리 단위로 나누어 순서대로 예측하고 `correct`와 `total`을 누적하는 흐름입니다. 각 줄의 중간 accuracy는 이전 구간을 포함하므로 구간별 난이도를 비교하려면 별도 분자, 분모를 계산해야 합니다. 마지막 total이 0인 class나 전체 집합에서는 나눗셈과 결과 표시를 명시적으로 처리합니다.

결과 log에는 모델 weight, 목록 버전, class index와 pair 생성 규칙을 함께 남깁니다. 이미지 파일만 재정렬되어도 같은 rating 숫자를 재현하기 어려울 수 있기 때문입니다.

## 자주 남는 질문

### DarkNet Compare는 한 이미지의 절대 점수를 직접 학습하나요?

아닙니다. 두 이미지를 함께 입력해 클래스마다 어느 쪽이 우세한지 쌍 비교 출력을 학습하고, 필요하면 비교 결과를 순위로 집계합니다.

### qsort 순위와 Elo 순위는 같은 방식인가요?

아닙니다. qsort 경로는 비교 함수를 이용해 한 class 기준으로 직접 정렬하고, Elo 경로는 반복 대결 결과로 class별 rating을 갱신합니다.

### 원문 Compare 코드를 실행하기 전에 가장 먼저 확인할 것은 무엇인가요?

두 이미지를 담을 입력 buffer 크기, 고정된 목록, 백업 경로, 클래스 수와 실제 run_compare 명령 분기를 먼저 확인해야 합니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [Darknet compare.c 고정 커밋 원본](https://raw.githubusercontent.com/pjreddie/darknet/f6afaabcdf85f77e7aff2ec55c020c0e297c77f9/src/compare.c)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [YOLOv4 Bag of Freebies와 Specials, 무엇이 추론 비용을 늘릴까?]({% post_url 2022-02-04-DarkNetYOLOv4 %}) — YOLOv4의 Mosaic, SAT, CmBN 같은 학습 전용 기법과 SPP, PAN, SAM, Mish 같은 구조 변경을 구분하고, CSPDarknet-53 조합과 실험 결과를 읽는 법을 정리합니다.
- [Darknet avgpool은 일반 Average Pooling이 아니다: Global Average 코드 읽기]({% post_url 2022-02-06-DarkNetAvgpool %}) — Darknet avgpool_layer가 window와 stride 없이 채널마다 h×w 전체를 평균내는 Global Average Pooling인 이유와 backward에서 gradient를 균등 분배하는 방식을 설명합니다.
- [DarkNet Demo 실시간 파이프라인: 3개 버퍼와 3프레임 평균]({% post_url 2022-02-19-DarkNetDemo %}) — DarkNet OpenCV 데모가 캡처, 추론, 표시를 세 버퍼로 겹쳐 처리하고 최근 세 예측을 평균한 뒤 NMS와 박스 그리기를 수행하는 흐름을 풀이합니다.
<!-- internal-links:end -->
