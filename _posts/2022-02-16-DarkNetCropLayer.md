---
layout: post
title: "DarkNet Crop Layer는 학습과 추론에서 어디를 자르나"
summary: "DarkNet Crop Layer의 랜덤 크롭·좌우 반전, 추론 시 중앙 크롭, 값 범위 변환과 빈 역전파 구현을 코드 기준으로 점검합니다."
date:   2022-02-16 16:00 -0400
categories: DarkNet
image:
  path: /assets/img/thumb/DarkNetCropLayer.jpg
  alt: DarkNet 시리즈 - Crop Layer 대표 이미지
tags:
  - DarkNet
  - Crop
  - 데이터증강
  - 전처리
math: true
---

DarkNet의 Crop Layer는 학습 중에는 임의 위치를 자르고 선택적으로 좌우 반전하며, 추론 중에는 반전 없이 중앙 영역을 잘라냅니다.

## 학습 크롭은 배치 전체에 한 번 정해진다

`forward_crop_layer`는 출력 크기가 입력 안에 들어온다는 전제에서 세 값을 먼저 고릅니다.

~~~c
int flip = (l.flip && rand()%2);
int dh = rand()%(l.h - l.out_h + 1);
int dw = rand()%(l.w - l.out_w + 1);
~~~

`dh`와 `dw`는 가능한 시작 위치를 끝점까지 포함해 선택합니다. `flip`이 참이면 열 인덱스를 오른쪽에서 왼쪽으로 계산하고, 아니면 `j + dw`를 그대로 사용합니다.

이 세 값은 batch 반복문보다 앞에서 계산되므로 한 번의 호출에 들어온 모든 배치 항목이 같은 오프셋과 반전 여부를 공유합니다. 이미지마다 독립적인 랜덤 크롭을 기대했다면 이 코드의 동작과 다릅니다.

## 추론은 반전 없는 중앙 크롭이다

`net.train`이 거짓이면 앞에서 뽑은 난수를 덮어쓰고 중앙 위치를 사용합니다.

~~~c
if(!net.train){
    flip = 0;
    dh = (l.h - l.out_h)/2;
    dw = (l.w - l.out_w)/2;
}
~~~

입력은 `batch → channel → row → column` 순서로 순회하며, 출력에는 채널별 크롭 영역이 연속해서 저장됩니다. `get_crop_image`는 이 `output` 포인터를 `out_w × out_h × out_c` 이미지 뷰로 바꿉니다.

학습과 추론 결과가 다르게 보일 때는 모델보다 먼저 랜덤 위치·반전과 중앙 크롭의 차이를 확인해야 합니다.

## noadjust가 값 범위를 결정한다

기본값에서는 선택한 입력 값에 2를 곱하고 1을 뺍니다.

~~~c
float scale = 2;
float trans = -1;
if(l.noadjust){
    scale = 1;
    trans = 0;
}

l.output[count++] = net.input[index]*scale + trans;
~~~

입력이 0에서 1 사이라면 기본 경로의 출력은 -1에서 1 범위가 됩니다. `noadjust`가 켜져 있으면 값은 그대로 복사됩니다.

생성 함수가 `angle`, `saturation`, `exposure`를 구조체에 저장하기는 하지만, 이 글에 나온 `forward_crop_layer` 본문은 세 값을 사용하지 않습니다. 따라서 이 코드 조각만으로 회전·채도·노출 증강까지 수행한다고 해석해서는 안 됩니다.

## 실행 전 크기와 역전파 한계를 확인한다

출력 높이나 너비가 입력보다 크면 랜덤 오프셋의 나머지 연산이 유효하지 않습니다. 생성 또는 resize 직후 다음 조건을 먼저 확인해야 합니다.

- `out_h <= h`
- `out_w <= w`
- `batch × out_h × out_w × out_c`만큼 출력이 할당됐는지

`resize_crop_layer`는 생성 시 `crop_height / h`로 저장한 하나의 `scale`을 새 가로와 세로 모두에 적용합니다. 원래 크롭의 가로·세로 비율이 서로 달랐다면 resize 뒤 출력 크기가 처음 의도와 달라질 수 있습니다.

가장 큰 한계는 역전파 함수가 완전히 비어 있다는 점입니다.

~~~c
void backward_crop_layer(const crop_layer l, network net){}
~~~

크롭 층에 학습 파라미터가 없다는 사실과 입력 기울기를 전달할 필요가 없다는 판단은 같은 말이 아닙니다. 이 구현은 `net.delta`로 기울기를 돌려놓지 않으므로, Crop Layer 뒤까지 학습하려는 네트워크에 넣기 전 상위 구조의 사용 방식을 확인해야 합니다. 이 글의 코드는 DarkNet 내부 구현 조각이며 단독 실행 예제가 아닙니다.
