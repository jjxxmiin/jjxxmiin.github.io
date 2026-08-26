---
layout: post
title: "DarkNet Crop Layer는 학습과 추론에서 어디를 자르나"
summary: "DarkNet Crop Layer의 랜덤 크롭·좌우 반전, 추론 시 중앙 크롭, 값 범위 변환과 빈 역전파 구현을 코드 기준으로 점검합니다."
description: "DarkNet Crop Layer의 batch 공유 random crop·flip, 중앙 crop, 값 범위 변환과 빈 backward가 학습·추론에 미치는 영향을 설명합니다."
date:   2022-02-16 16:00 -0400
categories: DarkNet
image:
  path: /assets/img/thumb/DarkNetCropLayer.jpg
  alt: DarkNet 시리즈 - Crop Layer 대표 이미지
tags:
  - DarkNet
  - 컴퓨터비전
math: true
faq:
  - question: "DarkNet Crop Layer는 batch 이미지마다 다른 위치를 자르나요?"
    answer: "아닙니다. flip·dh·dw를 batch loop 밖에서 한 번 선택하므로 같은 forward의 모든 이미지가 같은 crop 위치와 반전을 공유합니다."
  - question: "Crop Layer의 noadjust는 무엇을 바꾸나요?"
    answer: "기본 경로의 2x-1 값 변환을 끄고 선택된 input 값을 scale 1, translation 0으로 그대로 복사합니다."
  - question: "Backward 함수가 비어 있어도 Crop Layer 뒤쪽 학습은 가능한가요?"
    answer: "뒤 layer 파라미터는 학습할 수 있지만 crop 이전으로 input gradient가 전달되지 않으므로 앞부분까지 end-to-end 학습하려면 문제가 됩니다."
---

DarkNet의 Crop Layer는 학습 중에는 임의 위치를 자르고 선택적으로 좌우 반전하며, 추론 중에는 반전 없이 중앙 영역을 잘라냅니다. 이 구현은 한 번의 순전파 호출에서 뽑은 crop 위치와 반전 여부를 배치 전체에 공유합니다. 학습과 추론 결과가 예상보다 다르면 `train` 상태, 입력·출력 크기, 배치 단위 난수 선택을 순서대로 확인해야 합니다.

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

- 출력 높이 `out_h`는 입력 높이 `h` 이하여야 한다.
- 출력 너비 `out_w`는 입력 너비 `w` 이하여야 한다.
- `batch × out_h × out_w × out_c`만큼 출력이 할당됐는지

`resize_crop_layer`는 생성 시 `crop_height / h`로 저장한 하나의 `scale`을 새 가로와 세로 모두에 적용합니다. 원래 크롭의 가로·세로 비율이 서로 달랐다면 resize 뒤 출력 크기가 처음 의도와 달라질 수 있습니다.

가장 큰 한계는 역전파 함수가 완전히 비어 있다는 점입니다.

~~~c
void backward_crop_layer(const crop_layer l, network net){}
~~~

크롭 층에 학습 파라미터가 없다는 사실과 입력 기울기를 전달할 필요가 없다는 판단은 같은 말이 아닙니다. 이 구현은 `net.delta`로 기울기를 돌려놓지 않으므로, Crop Layer 뒤까지 학습하려는 네트워크에 넣기 전 상위 구조의 사용 방식을 확인해야 합니다. 이 글의 코드는 DarkNet 내부 구현 조각이며 단독 실행 예제가 아닙니다.

## Crop 좌표는 어떤 Pattern으로 검증하나요?

입력 각 위치에 `row×10+col`처럼 고유 값을 넣고 channel마다 큰 offset을 더합니다. 지정한 `dh,dw`에서 output의 왼쪽 위 값과 마지막 값이 예상 좌표인지 보면 row·column과 channel stride 오류를 찾을 수 있습니다. Flip을 켜면 같은 crop 영역의 열 순서만 반대가 되고 row와 channel은 유지돼야 합니다.

현재 코드는 난수를 함수 안에서 뽑으므로 재현 시험에서는 seed를 고정하거나 crop 계산을 분리해 알려진 offset을 주는 harness가 필요합니다. Batch 두 장을 서로 다른 pattern으로 채우면 같은 `dh,dw,flip`이 적용되되 sample 값이 섞이지 않는지도 확인할 수 있습니다. 추론에서는 홀수 차이 `(h-out_h)/2`가 정수 나눗셈으로 어느 쪽 pixel을 더 버리는지 명시합니다.

## Image와 Detection Label을 함께 Crop하려면 무엇이 더 필요한가요?

이 layer의 forward는 image tensor만 자르고 정답 box를 고치는 코드는 보이지 않습니다. Detection 학습 전처리로 쓰려면 원본 좌표에서 crop offset을 빼고 새 크기로 정규화하며, crop 밖 box를 제거하거나 잘린 경계를 clip해야 합니다. Image만 바꾸고 label을 그대로 두면 모델은 다른 위치의 객체를 정답으로 받습니다.

Flip도 box 중심 `x`를 새 너비 기준으로 반전해야 하고 segmentation mask에는 동일한 pixel 변환을 적용해야 합니다. 이 책임이 data loader에 이미 있다면 layer에서 중복 적용하지 않습니다. Crop Layer가 feature map 안에서 쓰이는지 원본 image 전처리에 쓰이는지에 따라 label 보정 필요가 달라지므로 graph 위치를 먼저 정합니다.

## 값 범위 변환이 중복되면 어떤 현상이 생기나요?

Input이 이미 -1과 1로 정규화됐는데 기본 `2x-1`을 다시 적용하면 출력은 의도한 범위를 벗어납니다. 반대로 network가 -1~1 입력으로 학습됐는데 `noadjust`를 켜 0~1을 넣으면 모든 첫 layer activation 분포가 바뀝니다. Crop 전 값의 최소·최대와 crop 후 범위를 batch마다 기록해 중복 normalize를 찾습니다.

Mean·standard deviation 정규화를 별도 단계에서 쓴다면 이 affine 변환과 적용 순서를 고정해야 합니다. 같은 이미지에서 학습 mode와 추론 mode는 crop 위치만 달라지고 값 변환은 같아야 합니다. 값 범위 차이를 crop randomness 탓으로 오해하지 않도록 중앙 crop을 양 mode에서 강제로 비교할 수 있습니다.

## 빈 Backward를 보완한다면 어떤 Gradient가 필요한가요?

Crop은 선택된 output 위치의 delta를 대응하는 input 위치에 scatter-add하고 crop 밖에는 0을 보냅니다. Flip이 있으면 forward에서 뒤집어 읽은 index로 다시 보내야 하고, `2x-1` 변환을 썼다면 local derivative 2도 반영해야 합니다. 단순 복사만 하면 noadjust 경로에는 맞아도 기본 경로 gradient 크기가 절반이 됩니다.

같은 input 위치가 output에 한 번만 대응하므로 일반 crop에서는 겹침이 없지만 기존 `net.delta`에 다른 branch 기여가 있을 수 있어 누적 계약을 확인합니다. 구현 전에는 실제 network가 crop을 고정된 입력 전처리 경계로만 쓰는지 확인해야 합니다. 필요 없는 backward를 추가하는 것과 end-to-end graph의 끊긴 gradient를 고치는 것은 다른 결정입니다.

## Resize의 하나의 Scale이 왜 위험한가요?

생성 시 높이 비율 하나만 저장해 새 width와 height 모두에 적용하면 원래 `crop_width/w`와 `crop_height/h`가 달랐던 직사각 crop의 비율이 보존되지 않습니다. Resize 전후의 상대 crop 가로·세로 비율을 각각 계산하고 output이 input 안에 드는지 다시 검사합니다. 반올림 때문에 0 또는 input보다 한 칸 큰 크기가 생기지 않게 경계도 정합니다.

Resize 뒤에는 output과 delta buffer 크기, `out_c`, inputs와 outputs metadata도 일치해야 합니다. Shape가 바뀐 frame 사이에서 이전 output pointer를 이미지 view가 계속 참조하지 않는지 소유권까지 확인합니다.

최소 시험에는 원본과 같은 크기의 crop도 넣어 offset 0, flip off에서 값이 그대로인지 확인합니다.

## 작은 행렬 예제로 인덱스를 먼저 확정한다

입력 높이 4, 너비 5에서 높이 2, 너비 3을 자르고 `dh=1`, `dw=2`라고 가정해 보자. 반전이 꺼져 있으면 출력 왼쪽 위는 입력의 1행 2열이고, 출력 오른쪽 아래는 2행 4열이다. 각 입력 값을 `100×channel + 10×row + column`로 채우면 출력 숫자만 보고도 channel·row·column 중 어느 stride가 틀렸는지 구분할 수 있다. 단순한 모두 0 또는 모두 1 입력은 잘못된 위치를 읽어도 같은 결과가 나와 좌표 검증에 적합하지 않다.

반전을 켰을 때 주의할 점은 전체 입력을 뒤집은 뒤 같은 `dw`에서 자른다고 막연히 생각하지 않는 것이다. 실제 index 식이 어떤 열을 가리키는지 코드 그대로 계산해 예상 배열을 만든다. 출력 열 순서가 반대여야 하지만 행 순서와 channel 구분은 그대로여야 한다. Batch 두 장에는 서로 다른 천 단위 offset을 주어 같은 crop 파라미터가 공유되면서도 sample 메모리가 섞이지 않는지 확인한다.

중앙 크롭도 짝수 차이와 홀수 차이를 나눠 시험한다. 입력 너비와 출력 너비의 차이가 홀수이면 C 정수 나눗셈이 나머지를 버리므로 한쪽에서 한 픽셀을 더 제거한다. 이것은 메모리 오류가 아니라 현재 식이 정한 규칙이다. 학습 전처리와 별도 추론 프로그램이 서로 다른 중앙 정렬 규칙을 쓰면 같은 사진도 한 픽셀씩 이동하므로, 예상 좌표를 테스트에 고정해야 한다.

## Crop Layer를 어디에 둘지 결정하는 기준

원본 이미지 증강이 목적이라면 데이터 로더에서 이미지와 detection box·segmentation mask를 함께 변환하는 구조가 이해하기 쉽다. 이 경우 Crop Layer는 학습 그래프의 일부가 아니라 입력을 만들기 전 단계가 되며, 빈 backward가 앞쪽 모델 학습을 끊는 문제도 생기지 않는다. 대신 학습과 추론 프로그램이 같은 값 범위와 중앙 crop 규칙을 공유하도록 전처리 함수를 한곳에서 관리해야 한다.

중간 feature map을 선택하기 위한 layer라면 label 좌표를 직접 고칠 필요는 없을 수 있지만 gradient 전달 여부가 중요해진다. Crop 이전 convolution까지 학습해야 하는데 backward가 비어 있다면 이전 계층의 가중치는 이 branch에서 신호를 받지 못한다. 다른 loss branch가 같은 계층에 연결돼 있다면 일부 업데이트가 일어나 문제를 숨길 수 있으므로, crop 전후 계층의 gradient norm을 따로 확인한다.

배치 전체에 같은 random crop을 쓰는 현재 정책은 항상 오류라는 뜻은 아니다. 같은 변환을 공유하도록 의도한 학습일 수 있고, 난수 호출 횟수도 적다. 다만 이미지마다 독립적인 다양성을 기대한 경우에는 요구와 구현이 어긋난다. 정책을 바꾸려면 `dh`, `dw`, `flip`을 batch loop 안으로 옮기는 것만으로 끝내지 말고, seed 재현성, label 변환, CPU 비용과 테스트 기대값도 함께 갱신한다.

`noadjust` 역시 편의 옵션이 아니라 앞뒤 layer의 수치 계약이다. Crop 입력이 0~1인지, 이미 -1~1인지, 또는 평균과 표준편차로 정규화됐는지 먼저 기록한다. 첫 convolution의 학습 가중치가 기대한 입력 범위가 무엇인지 확인한 뒤 옵션을 정한다. 모델 파일만 같고 전처리 범위가 다르면 inference 결과를 모델 회귀로 잘못 판단할 수 있다.

## 실패 증상에서 원인을 좁히는 순서

프로그램이 `rand() % 0` 부근에서 실패한다면 `out_h > h` 또는 `out_w > w`인지 가장 먼저 본다. Resize 뒤에만 발생한다면 생성 당시의 단일 `scale`이 새 가로·세로에 만든 `out_h`, `out_w`를 출력한다. 버퍼 손상처럼 보일 때는 실제 output 할당량과 `batch × out_h × out_w × out_c` 계산이 같은 타입과 값인지 확인한다.

학습 결과가 실행마다 크게 달라지면 난수 seed 하나만 기록해서는 부족할 수 있다. Crop 호출 순서가 달라지면 전역 `rand()`에서 꺼내는 값의 위치도 달라진다. 데이터 로더 스레드나 다른 증강이 같은 난수 상태를 공유하는지 확인하고, 재현이 필요하면 crop 파라미터를 로그에 남긴다. 재현 로그에는 batch index와 `dh`, `dw`, `flip`, `train`, 입력·출력 shape가 함께 있어야 같은 호출을 찾을 수 있다.

추론 정확도만 떨어지고 학습 평가는 정상이라면 `net.train` 설정과 추론 전처리의 중복 crop을 확인한다. 외부 프로그램에서 이미 중앙 crop한 이미지를 넣고 layer가 다시 중앙 crop하면 시야가 예상보다 좁아진다. 반대로 추론에서도 실수로 `train`이 참이면 같은 이미지가 호출할 때마다 다른 영역으로 들어갈 수 있다. 두 경로의 crop 결과 이미지를 저장해 픽셀 단위로 비교하면 모델 추론 전에 차이를 확인할 수 있다.

출력의 밝기나 activation만 비정상이라면 공간 좌표보다 값 변환을 먼저 분리한다. 같은 좌표에서 `noadjust`를 켠 결과와 끈 결과가 정확히 `2x-1` 관계인지 작은 입력으로 검사한다. NaN이 이미 입력에 있었다면 crop은 그대로 전달하므로, 최소·최대뿐 아니라 유한값 여부도 확인한다. 빈 backward가 원인인 경우에는 crop 이전 계층의 gradient가 계속 0이고 crop 이후 계층은 변할 수 있다는 구분 가능한 징후가 있다.

## 배포 전 최소 테스트와 중단 조건

단위 테스트는 전체 크기 crop, 모서리 crop, 중앙 crop, 좌우 반전, batch 두 장, channel 두 개와 `noadjust` 두 경로를 포함한다. 각 경우에 예상 output을 손으로 만든 배열과 완전 일치 비교한다. 이어서 출력보다 한 픽셀 작은 입력, 0 크기, 큰 batch처럼 계약을 위반한 값이 조용히 진행되지 않고 구성 단계에서 거부되는지 확인한다.

통합 테스트에서는 실제 network의 학습·추론 mode를 각각 한 번 실행하고 crop 전후 이미지 또는 feature map의 shape와 통계를 남긴다. 원본 이미지 전처리에 사용한다면 같은 변환을 거친 label을 화면에 겹쳐 본다. 학습 그래프 안에 사용한다면 crop 이전과 이후 parameter의 gradient를 확인한다. 검사 없이 정확도만 비교하면 좌표·값 범위·gradient 중 무엇이 바뀌었는지 알기 어렵다.

출력 크기가 입력을 넘거나, detection label이 같은 변환을 받지 않거나, 앞 계층 학습이 필요한데 backward가 비어 있으면 배포를 중단해야 한다. 학습과 추론의 crop 규칙이 다르다는 사실 자체는 설계일 수 있지만, 두 규칙을 평가하지 않았다면 역시 중단 조건이다. 입력 shape와 전처리 계약이 명시되고 최소 배열 테스트를 통과한 뒤에만 성능 실험으로 넘어간다.

## 원본 소스가 보장하는 범위

이 글은 pjreddie Darknet의 `crop_layer.c`에 나타난 순전파·resize·빈 역전파 구조를 해설한 것이다. [원본 저장소의 crop_layer.c](https://github.com/pjreddie/darknet/blob/master/src/crop_layer.c)는 특정 시점의 구현을 보여 주지만, 이후 fork의 수정이나 별도 CUDA 전처리, 독자의 network 설정까지 설명하지 않는다. 사용하는 저장소와 commit이 다르면 함수 본문과 구조체 필드를 다시 대조해야 한다.

또한 여기에 제시한 코드 조각은 parser가 어떤 옵션을 넘기는지, 입력 tensor가 누가 소유하는지, label을 어느 단계에서 고치는지까지 포함하지 않는다. 정확한 동작을 재현하려면 `crop_layer.c`만 떼어 보지 말고 layer 생성 호출부, network의 `train` 설정, data loader와 메모리 해제 경로를 함께 기록한다. 이 한계를 명시해야 코드 설명이 특정 버전의 사실인지 일반적인 crop 연산의 성질인지 구분할 수 있다.

## 자주 남는 질문

### DarkNet Crop Layer는 batch 이미지마다 다른 위치를 자르나요?

아닙니다. flip·dh·dw를 batch loop 밖에서 한 번 선택하므로 같은 forward의 모든 이미지가 같은 crop 위치와 반전을 공유합니다.

### Crop Layer의 noadjust는 무엇을 바꾸나요?

기본 경로의 2x-1 값 변환을 끄고 선택된 input 값을 scale 1, translation 0으로 그대로 복사합니다.

### Backward 함수가 비어 있어도 Crop Layer 뒤쪽 학습은 가능한가요?

뒤 layer 파라미터는 학습할 수 있지만 crop 이전으로 input gradient가 전달되지 않으므로 앞부분까지 end-to-end 학습하려면 문제가 됩니다.

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [Darknet BatchNorm은 학습과 추론에서 왜 다른 Mean을 쓸까?]({% post_url 2022-02-07-DarkNetBatchnormLayer %}) — Darknet batchnorm_layer의 forward·backward 코드를 따라 mini-batch mean·variance와 rolling statistics, scale·bias, standalone layer의 복사…
- [DarkNet GRU Layer는 학습 가능한가: 6개 Connected와 빈 backward]({% post_url 2022-02-23-DarkNetGRULayer %}) — DarkNet GRU 순전파의 update·reset·candidate 계산을 여섯 완전연결층으로 추적하고, 비어 있는 역전파 때문에 이 소스만으로 학습할 수 없는 한계를 짚습니다.
- [Darknet Logistic Layer의 cost가 batch마다 달라지는 이유: sigmoid·cross entropy 흐름]({% post_url 2022-03-06-DarkNetLogisticLayer %}) — Darknet LOGXENT layer가 입력을 sigmoid 출력으로 바꾸고 truth가 있을 때만 loss와 delta를 계산하는 과정을 추적합니다.
<!-- internal-links:end -->
