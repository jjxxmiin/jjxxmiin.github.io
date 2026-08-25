---
layout: post
title: "DarkNet Compare는 두 이미지를 어떻게 순위로 바꾸나"
summary: "DarkNet compare 코드의 쌍 비교 학습, 10분할 검증, qsort 정렬과 Elo 토너먼트 흐름을 실행 전 주의점과 함께 정리합니다."
date:   2022-02-11 16:00 -0400
categories: DarkNet
image:
  path: /assets/img/thumb/DarkNetCompare.jpg
  alt: DarkNet 시리즈 - Compare 대표 이미지
tags:
  - DarkNet
  - YOLO
  - 쌍비교
  - Elo
math: true
---

DarkNet의 Compare 모드는 두 이미지를 한 번에 네트워크에 넣어 클래스별 우열을 예측하고, 그 결과로 검증 정확도나 이미지 순위를 계산하는 코드입니다.

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
