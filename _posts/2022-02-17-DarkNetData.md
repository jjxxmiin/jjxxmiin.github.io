---
layout: post
title: "DarkNet data.c 읽는 법: 이미지 경로가 X·y 배치가 되기까지"
summary: "DarkNet data.c의 경로 샘플링, 이미지·라벨 동시 증강, 데이터 유형별 로더 분기와 멀티스레드 병합을 메모리 소유권 주의점까지 연결해 설명합니다."
date:   2022-02-17 16:00 -0400
categories: DarkNet
image:
  path: /assets/img/thumb/DarkNetData.jpg
  alt: DarkNet 시리즈 - Data 대표 이미지
tags:
  - DarkNet
  - DataLoader
  - YOLO
  - 멀티스레드
math: true
---

DarkNet의 `data.c`는 경로 목록에서 표본을 고르고, 이미지와 정답에 같은 변환을 적용해 `data.X`와 `data.y`를 만든 뒤 스레드별 결과를 하나의 배치로 합칩니다.

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

검출 데이터의 핵심 순서는 이미지 변환과 박스 보정이 한 쌍으로 움직인다는 점입니다. `load_data_detection`은 원본 비율에 jitter를 넣고, 회색 값 0.5로 채운 `w × h` 캔버스에 크기와 위치를 달리해 이미지를 놓습니다. 이후 색조·채도·노출 변형과 좌우 반전을 적용합니다.

같은 `dx`, `dy`, `nw/w`, `nh/h`, `flip`이 `fill_truth_detection`으로 전달됩니다.

~~~c
fill_truth_detection(random_paths[i], boxes, d.y.vals[i],
    classes, flip, -dx/w, -dy/h, nw/w, nh/h);
~~~

`correct_boxes`는 박스의 left·right·top·bottom에 scale과 offset을 적용하고, 반전이면 `left = 1 - right` 관계로 바꿉니다. 좌표를 0과 1 사이로 제한한 뒤 다시 중심 `x, y`와 크기 `w, h`로 환산합니다. 너무 작은 박스는 제외되고, detection 정답 한 항목은 `x, y, w, h, class id` 다섯 값입니다.

데이터 유형마다 `y`의 뜻은 달라집니다.

- `REGION_DATA`: 셀마다 object 여부, 클래스 one-hot, 셀 내부 좌표와 박스 크기
- `INSTANCE_DATA`: 박스 네 값, 고정 크기로 줄인 마스크, 클래스 id
- `SEGMENTATION_DATA`: RLE 마스크를 클래스 채널 이미지로 복원한 픽셀 정답
- `COMPARE_DATA`: 두 이미지를 6채널로 붙이고 클래스별 두 IoU를 비교한 쌍 정답
- `CLASSIFICATION_DATA`: 경로에서 찾은 클래스와 선택적인 계층 부모 정답
- `SUPER_DATA`: 큰 랜덤 크롭이 정답이고, 이를 줄인 이미지가 입력

증강을 추가하거나 수정할 때는 `X`만 바꾸지 말고 해당 유형의 `fill_truth_*`가 같은 기하 변환을 받는지 확인해야 합니다.

## load_args가 로더와 스레드 수를 연결한다

`load_thread`는 `load_args.type`에 따라 실제 로더를 고르는 중앙 분기입니다. exposure, saturation, aspect가 0이면 각각 1로 바꾼 뒤 분류·회귀·초해상도·검출·분할·비교·이미지·letterbox 등 서로 다른 함수를 호출합니다.

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

- `get_random_paths`는 `rand() % m`을 사용하므로 `m`은 0보다 커야 합니다. 일부 로더는 `if(m)`으로 보호하지만 detection·region·segmentation 계열은 곧바로 이 함수를 호출합니다.
- 라벨 파일 열기 실패 처리가 일관되지 않습니다. 태그 로더는 없는 파일을 건너뛰지만, 회귀 라벨과 Compare 라벨 코드는 `fopen` 결과를 확인하지 않고 `fscanf`를 호출합니다.
- RLE 마스크의 클래스 `id`는 `or_image`의 대상 채널 인덱스로 바로 사용됩니다. `0 <= id < classes` 검증은 이 조각에 보이지 않습니다.
- instance mask 로더는 `fill_truth_mask(..., 14, 14)`로 마스크 크기를 고정합니다. 설정의 `coords`와 실제 `4 + 14×14 + 1` 구성이 맞는지 확인해야 합니다.
- `load_data_captcha_encode`는 `d.y = d.X`로 같은 행렬을 공유하면서 `d.shallow = 0`을 유지합니다. 여기에 나온 `free_data`를 그대로 호출하면 X와 y를 각각 해제하려 하므로 소유권 충돌 가능성이 있습니다.
- `get_next_batch`와 여러 좌표 보정 함수에는 입력 범위 검사가 없습니다. offset과 batch 크기, 박스 수, 클래스 id가 할당 범위 안인지 호출자가 보장해야 합니다.

새 로더를 추가할 때는 먼저 `X.rows/cols`와 `y.rows/cols`를 명시하고, 이미지 변환과 truth 변환을 같은 인자로 묶은 다음, `load_thread` 분기와 shallow 소유권까지 연결해 보는 것이 안전합니다. 이 글은 전체 실행법이 아니라 기존 DarkNet `data.c`를 추적하기 위한 지도입니다.
