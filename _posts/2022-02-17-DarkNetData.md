---
layout: post
title: "DarkNet data.c 읽는 법: 이미지 경로가 X, y 배치가 되기까지"
summary: "DarkNet data.c의 경로 샘플링, 이미지, 라벨 동시 증강, 데이터 유형별 로더 분기와 멀티스레드 병합을 메모리 소유권 주의점까지 연결해 설명합니다."
description: "DarkNet data.c의 복원 경로 sampling, image, label 동시 증강, loader 분기와 thread 병합을 shape, 재현성, 메모리 소유권 기준으로 설명합니다."
date:   2022-02-17 16:00 -0400
categories: DarkNet
image:
  path: /assets/img/thumb/DarkNetData.jpg
  alt: DarkNet 시리즈 - Data 대표 이미지
tags:
  - DarkNet
  - 컴퓨터비전
math: true
faq:
  - question: "DarkNet get_random_paths는 한 batch에서 같은 이미지를 다시 뽑을 수 있나요?"
    answer: "네. 선택한 index를 제외하지 않는 복원 추출이므로 같은 경로가 한 batch에 여러 번 포함될 수 있습니다."
  - question: "Detection 증강에서 image만 변환하면 왜 안 되나요?"
    answer: "Resize, offset, flip이 적용된 image와 같은 값으로 box 좌표를 보정하지 않으면 객체 위치와 truth가 서로 어긋나기 때문입니다."
  - question: "concat_datas의 shallow flag는 왜 중요한가요?"
    answer: "병합된 data와 임시 thread data 중 누가 실제 행 메모리를 해제할지 정해 double free와 leak을 막는 소유권 표시이기 때문입니다."
---

DarkNet의 `data.c`는 경로 목록에서 표본을 고르고, 이미지와 정답에 같은 변환을 적용해 `data.X`와 `data.y`를 만든 뒤 스레드별 결과를 하나의 배치로 합칩니다. 데이터 오류는 경로 문자열 치환, label 매핑, 이미지와 좌표 변환의 불일치에서 자주 생깁니다. 로더가 끝났다는 사실만 보지 말고 같은 표본의 `X`와 `y`, 스레드별 행 범위가 함께 맞는지 확인해야 합니다.

## 경로 선택에서 이미 표본 구성이 정해진다

`get_paths`는 텍스트 파일을 한 줄씩 읽어 문자열 리스트를 만듭니다. 그 목록에서 `get_random_paths`가 `n`개를 고를 때는 이미 뽑은 경로를 제외하지 않습니다.

~~~c
for(i = 0; i < n; ++i){
    int index = rand()%m;
    random_paths[i] = paths[index];
}
~~~

따라서 한 배치 안에 같은 이미지가 여러 번 들어갈 수 있는 복원 추출입니다. 뮤텍스는 여러 로더 스레드가 동시에 `rand()`를 호출하는 구간을 감싸지만, 경로 파일을 읽는 `get_paths` 자체를 잠그지는 않습니다.

라벨 경로는 별도 매핑 테이블보다 문자열 치환에 의존합니다. 검출 로더는 `images`나 `JPEGImages`를 `labels`로, 마스크 로더는 `mask`로 바꾸고 확장자를 `.txt`로 바꿉니다. 디렉터리명이나 확장자 대소문자가 예상 패턴과 다르면 잘못된 경로가 만들어질 수 있습니다.

분류용 `fill_truth`는 파일 경로 안에 label 문자열이 포함되는지를 검사합니다. 레이블 이름이 다른 디렉터리명이나 파일명 일부와 겹치면 둘 이상이 동시에 선택될 수 있으므로, `Too many or too few labels` 메시지를 데이터 오류 신호로 봐야 합니다.

## 이미지와 정답에는 같은 공간 변환이 필요하다

검출 데이터의 핵심 순서는 이미지 변환과 박스 보정이 한 쌍으로 움직인다는 점입니다. `load_data_detection`은 원본 비율에 jitter를 넣고, 회색 값 0.5로 채운 `w × h` 캔버스에 크기와 위치를 달리해 이미지를 놓습니다. 이후 색조, 채도, 노출 변형과 좌우 반전을 적용합니다.

같은 `dx`, `dy`, `nw/w`, `nh/h`, `flip`이 `fill_truth_detection`으로 전달됩니다.

~~~c
fill_truth_detection(random_paths[i], boxes, d.y.vals[i],
    classes, flip, -dx/w, -dy/h, nw/w, nh/h);
~~~

`correct_boxes`는 박스의 left, right, top, bottom에 scale과 offset을 적용하고, 반전이면 `left = 1 - right` 관계로 바꿉니다. 좌표를 0과 1 사이로 제한한 뒤 다시 중심 `x, y`와 크기 `w, h`로 환산합니다. 너무 작은 박스는 제외되고, detection 정답 한 항목은 `x, y, w, h, class id` 다섯 값입니다.

데이터 유형마다 `y`의 뜻은 달라집니다.

- `REGION_DATA`: 셀마다 object 여부, 클래스 one-hot, 셀 내부 좌표와 박스 크기
- `INSTANCE_DATA`: 박스 네 값, 고정 크기로 줄인 마스크, 클래스 id
- `SEGMENTATION_DATA`: RLE 마스크를 클래스 채널 이미지로 복원한 픽셀 정답
- `COMPARE_DATA`: 두 이미지를 6채널로 붙이고 클래스별 두 IoU를 비교한 쌍 정답
- `CLASSIFICATION_DATA`: 경로에서 찾은 클래스와 선택적인 계층 부모 정답
- `SUPER_DATA`: 큰 랜덤 크롭이 정답이고, 이를 줄인 이미지가 입력

증강을 추가하거나 수정할 때는 `X`만 바꾸지 말고 해당 유형의 `fill_truth_*`가 같은 기하 변환을 받는지 확인해야 합니다.

## load_args가 로더와 스레드 수를 연결한다

`load_thread`는 `load_args.type`에 따라 실제 로더를 고르는 중앙 분기입니다. exposure, saturation, aspect가 0이면 각각 1로 바꾼 뒤 분류, 회귀, 초해상도, 검출, 분할, 비교, 이미지, letterbox 등 서로 다른 함수를 호출합니다.

단일 비동기 로드는 `load_data_in_thread`가 `load_args`를 복사해 pthread 하나를 생성합니다. 여러 스레드를 쓰는 `load_data`의 흐름은 한 단계 더 있습니다.

$$
load_data
\rightarrow load_threads
\rightarrow load_data_in_thread
\rightarrow load_thread
$$

`load_threads`는 전체 `n`을 스레드 수로 나누며 나머지도 정수 구간식으로 분배합니다.

~~~c
args.n = (i+1) * total/args.threads
       - i * total/args.threads;
~~~

각 스레드가 만든 `data`는 `concat_datas`가 행 포인터 배열로 이어 붙입니다. 결합 결과가 실제 행 메모리를 소유하도록 `out->shallow = 0`으로 바꾸고, 임시 buffer는 `shallow = 1`로 표시해 행 데이터가 아닌 포인터 배열만 해제합니다.

이 소유권 규칙은 `free_data`와 함께 읽어야 합니다. `shallow == 0`이면 X와 y 행렬의 행 데이터까지 해제하고, 1이면 `vals` 포인터 배열만 해제합니다.

## 새 데이터 유형을 붙이기 전 확인할 위험 지점

원문 코드는 다양한 실험용 로더를 한 파일에 모은 오래된 내부 구현 조각입니다. 그대로 재사용하기 전에 다음 조건을 점검해야 합니다.

- `get_random_paths`는 `rand() % m`을 사용하므로 `m`은 0보다 커야 합니다. 일부 로더는 `if(m)`으로 보호하지만 detection, region, segmentation 계열은 곧바로 이 함수를 호출합니다.
- 라벨 파일 열기 실패 처리가 일관되지 않습니다. 태그 로더는 없는 파일을 건너뛰지만, 회귀 라벨과 Compare 라벨 코드는 `fopen` 결과를 확인하지 않고 `fscanf`를 호출합니다.
- RLE 마스크의 클래스 `id`는 `or_image`의 대상 채널 인덱스로 바로 사용됩니다. `id`가 0 이상이고 `classes`보다 작은지 검증하는 코드는 이 조각에 보이지 않습니다.
- instance mask 로더는 `fill_truth_mask(..., 14, 14)`로 마스크 크기를 고정합니다. 설정의 `coords`와 실제 `4 + 14×14 + 1` 구성이 맞는지 확인해야 합니다.
- `load_data_captcha_encode`는 `d.y = d.X`로 같은 행렬을 공유하면서 `d.shallow = 0`을 유지합니다. 여기에 나온 `free_data`를 그대로 호출하면 X와 y를 각각 해제하려 하므로 소유권 충돌 가능성이 있습니다.
- `get_next_batch`와 여러 좌표 보정 함수에는 입력 범위 검사가 없습니다. offset과 batch 크기, 박스 수, 클래스 id가 할당 범위 안인지 호출자가 보장해야 합니다.

새 로더를 추가할 때는 먼저 `X.rows/cols`와 `y.rows/cols`를 명시하고, 이미지 변환과 truth 변환을 같은 인자로 묶은 다음, `load_thread` 분기와 shallow 소유권까지 연결해 보는 것이 안전합니다. 이 글은 전체 실행법이 아니라 기존 DarkNet `data.c`를 추적하기 위한 지도입니다.

## Loader를 최소 Batch로 어떻게 검증하나요?

이미지 두 장에 서로 다른 고정 색과 알려진 box를 넣고 augmentation을 끈 batch부터 만듭니다. `X.rows=n`, 각 row 길이가 `w×h×c`, `y`의 row와 column이 loader type의 계약과 같은지 출력합니다. 경로 순서, class id와 좌표를 원본 파일과 대조한 뒤 flip 하나, resize 하나를 차례로 켭니다. 여러 변환을 동시에 켜면 label이 어긋난 원인을 찾기 어렵습니다.

Detection은 변환 후 image 위에 보정된 box를 그려 모든 sample을 확인하고, segmentation은 mask의 class channel과 image 경계가 함께 움직이는지 봅니다. 없는 label, 빈 box, 범위 밖 class와 너무 작은 image도 넣어 loader가 실패를 알리는지 확인합니다. 조용히 0 label을 만드는 처리는 실제 배경과 파일 오류를 구분하기 어렵게 합니다.

## 멀티스레드 결과는 무엇이 같아야 하나요?

같은 경로와 같은 난수 선택을 고정했을 때 thread 수 1과 여러 개에서 X, y shape와 sample 수가 같아야 합니다. 전역 `rand()` 호출 순서는 thread scheduling에 따라 달라질 수 있으므로 완전한 값 재현이 목표라면 thread별 난수 상태와 seed 정책이 필요합니다. Mutex가 race를 막는 것과 실행마다 같은 augmentation을 보장하는 것은 다른 문제입니다.

전체 `n`이 thread 수보다 작거나 나누어떨어지지 않는 경우도 시험합니다. 일부 thread의 `args.n`이 0일 수 있고, concat 뒤 행 순서가 학습에서 의미가 있는지 확인해야 합니다. Free 전에는 병합 data와 임시 data의 row pointer를 비교해 실제 행을 한 번만 해제하는지 sanitizer로 검증합니다.

## 표본 하나를 끝까지 추적하면 무엇을 기록해야 하나

한 이미지 경로를 골라 `random_paths[i]`부터 `d.X.vals[i]`와 `d.y.vals[i]`까지 같은 식별자를 붙인다. 원본 너비, 높이, jitter로 만든 비율, `dx`, `dy`, flip, 색 변환 인자와 최종 tensor shape를 한 줄에 기록하면 이미지와 label이 어디서 갈라졌는지 찾을 수 있다. Detection이라면 변환 전 box와 `correct_boxes` 이후 box를 함께 남기고, 최종 이미지에 새 box를 그려 수치와 화면을 동시에 확인한다.

예를 들어 원본 중앙에 있는 box를 오른쪽으로 이동시킨 이미지라면 새 중심 x도 같은 방향으로 변해야 한다. 좌우 반전을 적용했을 때 중심은 반대편으로 옮겨지고 너비는 유지되어야 한다. Crop 밖으로 일부 나간 box는 clip 뒤 폭과 높이가 줄어들 수 있으며, 완전히 사라진 box는 정답에서 제외되어야 한다. 이 세 경우를 고정된 작은 fixture로 만들면 augmentation을 바꿀 때 회귀를 바로 찾을 수 있다.

분류는 경로 문자열에서 label을 찾는 방식이므로 경로와 선택된 one-hot index를 저장한다. 비슷한 label 문자열 둘이 동시에 일치하거나 하나도 일치하지 않는 fixture를 넣어 오류가 드러나는지 확인한다. Segmentation과 instance mask는 class id별 픽셀 수를 변환 전후에 비교하고, 이미지와 mask 경계를 겹쳐 본다. 로더 유형마다 `y`의 의미가 다르므로 공통 검사는 shape와 유한값까지, 의미 검사는 유형별로 나눈다.

## 속도, 다양성, 재현성 가운데 무엇을 우선할까

복원 추출은 구현이 단순하고 작은 데이터셋에서도 원하는 batch 크기를 채울 수 있지만, 같은 이미지가 반복되면 한 batch의 유효 다양성이 줄어든다. 중복이 허용되는지부터 결정하고, 허용하더라도 batch별 고유 경로 수를 측정하면 실제 반복 정도를 알 수 있다. 중복 없는 epoch 순회가 필요하다면 index 배열을 섞어 소비하는 방식처럼 다른 sampler가 필요하며, 이는 `get_random_paths` 한 줄 수정이 아니라 epoch 경계와 thread 분배 정책까지 바꾸는 일이다.

여러 스레드는 로딩 지연을 숨길 수 있지만 전역 난수 호출 순서와 메모리 소유권을 복잡하게 만든다. 정확한 재현이 중요한 디버깅에서는 thread 수 1, augmentation off로 기준 결과를 만든다. 그다음 augmentation을 하나씩 켜고 마지막에 thread 수를 늘린다. 운영 처리량을 높일 때는 초당 이미지 수뿐 아니라 중복 표본 수, 로딩 실패 수, 빈 label 수와 메모리 사용량을 함께 본다.

성능 때문에 파일 오류를 조용히 0 label로 바꾸는 선택은 신중해야 한다. 실제 배경 이미지와 라벨 파일 누락이 같은 `y`가 되면 모델은 데이터 장애를 정상 정답으로 학습한다. 필수 label이 없는 표본은 실패로 집계하고, 허용 가능한 비율과 중단 기준을 설정한다. 문제가 있는 경로를 별도 목록으로 남기면 전체 학습을 다시 시작하기 전에 데이터셋을 고칠 수 있다.

## 장애 증상별 점검 순서

학습 loss가 갑자기 나빠졌다면 모델 설정 전에 변환된 이미지와 정답 overlay를 본다. Box가 일정한 방향으로 밀리면 `dx`, `dy`의 부호와 정규화 분모를 확인하고, flip에서만 어긋나면 left, right 교환 순서를 확인한다. 특정 파일에서만 실패하면 문자열 치환으로 만든 label 경로와 파일 존재 여부, class id 범위를 확인한다.

thread 수를 늘렸을 때만 crash가 난다면 스레드별 `args.n`, 임시 `data`의 `shallow` 값, concat 뒤 포인터 소유자를 기록한다. Double free는 종료나 다음 batch에서 늦게 나타날 수 있으므로 crash 위치만으로 원인을 단정하지 않는다. AddressSanitizer 같은 메모리 검사 결과와 X, y 행 포인터 목록을 함께 보면 같은 행이 두 번 해제되는지, 아예 해제되지 않는지 구분할 수 있다.

실행마다 batch가 달라지는 것은 random loader의 정상 동작일 수 있다. 그러나 같은 seed와 단일 thread에서도 첫 batch가 달라진다면 경로 목록 순서, seed 설정 시점과 다른 `rand()` 호출을 찾는다. 여러 thread에서 값까지 동일해야 하는 요구가 있다면 전역 난수에 의존하는 현재 구조가 그 요구를 충족하는지 별도 검증해야 한다.

## 출처와 버전 한계

이 글은 [pjreddie Darknet의 data.c](https://github.com/pjreddie/darknet/blob/master/src/data.c)에 있는 loader 분기, 좌표 보정과 thread 병합 구조를 기준으로 읽었다. 원본 파일은 여러 데이터 실험을 한곳에 모은 특정 구현이며, 모든 Darknet fork나 최신 학습 파이프라인의 공통 규격은 아니다. AlexeyAB 계열이나 자체 fork를 사용한다면 같은 함수 이름이라도 인자, 오류 처리와 메모리 소유권이 달라졌는지 commit 단위로 비교해야 한다.

코드 조각만으로는 데이터셋 디렉터리 규칙, parser가 채운 `load_args`, 호출자가 `data`를 해제하는 시점이 모두 드러나지 않는다. 따라서 이 글의 위험 지점은 점검 목록이지 특정 환경에서 crash가 반드시 난다는 주장으로 읽으면 안 된다. 재현 보고서에는 저장소 URL과 commit, loader type, thread 수, seed, 입력 경로 목록과 X, y shape를 함께 남겨 해설의 적용 범위를 고정한다.

## 자주 남는 질문

### DarkNet get_random_paths는 한 batch에서 같은 이미지를 다시 뽑을 수 있나요?

네. 선택한 index를 제외하지 않는 복원 추출이므로 같은 경로가 한 batch에 여러 번 포함될 수 있습니다.

### Detection 증강에서 image만 변환하면 왜 안 되나요?

Resize, offset, flip이 적용된 image와 같은 값으로 box 좌표를 보정하지 않으면 객체 위치와 truth가 서로 어긋나기 때문입니다.

### concat_datas의 shallow flag는 왜 중요한가요?

병합된 data와 임시 thread data 중 누가 실제 행 메모리를 해제할지 정해 double free와 leak을 막는 소유권 표시이기 때문입니다.

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [Darknet image.c에서 자주 틀리는 5가지: CHW 인덱싱, 리사이즈, 메모리 소유권]({% post_url 2022-03-01-DarkNetImage %}) — Darknet의 image 구조체가 픽셀을 저장하고 복사, 리사이즈, letterbox, 증강, 탐지 결과를 그리는 흐름을 코드 기준으로 해설합니다.
- [Darknet 연결 리스트가 한 번 pop 뒤 깨지는 이유: front, back과 메모리 소유권]({% post_url 2022-03-05-DarkNetList %}) — Darknet list 구현의 삽입, pop 불변식과 node, val, array를 각각 누가 해제해야 하는지 코드로 추적합니다.
- [DarkNet GEMM 인자 읽는 법: TA, TB, lda, BETA]({% post_url 2022-02-22-DarkNetGEMM %}) — DarkNet GEMM 호출을 C=βC+αop(A)op(B)로 해석하고, 네 가지 전치 분기와 leading dimension이 실제 메모리 인덱스에 미치는 영향을 설명합니다.
<!-- internal-links:end -->
