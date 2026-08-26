---
source_citations:
  - name: "Darknet demo.c 고정 커밋 원본"
    url: "https://raw.githubusercontent.com/pjreddie/darknet/f6afaabcdf85f77e7aff2ec55c020c0e297c77f9/src/demo.c"
layout: post
title: "DarkNet Demo 실시간 파이프라인: 3개 버퍼와 3프레임 평균"
summary: "DarkNet OpenCV 데모가 캡처·추론·표시를 세 버퍼로 겹쳐 처리하고 최근 세 예측을 평균한 뒤 NMS와 박스 그리기를 수행하는 흐름을 풀이합니다."
description: "DarkNet Demo의 3-slot capture·detect·display pipeline, 원시 출력 3-frame 평균, NMS와 지연·초기 buffer·종료 자원 문제를 설명합니다."
date:   2022-02-19 16:00 -0400
categories: DarkNet
image:
  path: /assets/img/thumb/DarkNetDemo.jpg
  alt: DarkNet 시리즈 - Demo 대표 이미지
tags:
  - DarkNet
  - 웹개발
  - 컴퓨터비전
math: true
faq:
  - question: "DarkNet Demo 화면의 box는 현재 막 캡처한 frame 결과인가요?"
    answer: "아닙니다. capture·detect·display가 서로 다른 ring buffer slot을 사용하므로 화면에는 pipeline 지연이 있는 이전 frame 결과가 표시됩니다."
  - question: "3-frame 평균은 완성된 bounding box 좌표를 평균하나요?"
    answer: "아닙니다. 검출 layer의 원시 output을 세 slot에서 평균한 뒤 그 평균으로 box decode와 NMS를 수행합니다."
  - question: "Demo 시작 직후 confidence가 낮을 수 있는 이유는 무엇인가요?"
    answer: "아직 예측이 들어오지 않은 calloc 0 slot까지 처음부터 3분의 1 비율로 평균에 포함되기 때문입니다."
---

DarkNet Demo는 프레임 세 장을 원형 버퍼로 돌리면서 새 프레임 캡처와 이전 프레임 추론을 동시에 실행하고, 최근 세 번의 검출 출력을 평균해 화면에 그립니다. 현재 캡처하는 프레임, 추론하는 프레임, 표시하는 프레임의 버퍼 인덱스는 서로 다릅니다. 지연이나 잘못된 박스를 진단할 때는 속도만 재기보다 이 인덱스와 검출 평균의 시간 순서를 먼저 맞춰야 합니다.

## 세 버퍼가 캡처와 추론 충돌을 피한다

전역 배열 `buff[3]`에는 원본 프레임을, `buff_letter[3]`에는 네트워크 입력 크기로 letterbox한 프레임을 둡니다. 메인 루프는 `buff_index`를 하나씩 이동한 뒤 두 스레드를 만듭니다.

~~~c
buff_index = (buff_index + 1) % 3;
pthread_create(&fetch_thread, 0, fetch_in_thread, 0);
pthread_create(&detect_thread, 0, detect_in_thread, 0);
~~~

fetch 스레드는 현재 `buff_index` 위치의 예전 이미지를 해제하고 스트림에서 새 프레임을 읽습니다. detect 스레드는 `(buff_index + 2) % 3` 위치의 letterbox 데이터를 읽습니다. 서로 다른 슬롯을 사용하므로 캡처가 추론 입력을 덮지 않습니다.

화면에는 `(buff_index + 1) % 3` 슬롯을 보여 줍니다. 두 작업은 매 반복 끝에서 `pthread_join`으로 모두 끝난 뒤 다음 인덱스로 넘어갑니다. 이 코드는 캡처·추론·표시가 같은 프레임 번호를 즉시 공유하는 구조가 아니라, 각 단계가 한 슬롯씩 떨어진 파이프라인입니다.

## 평균화 대상은 마지막 검출층의 원시 출력이다

`size_network`는 네트워크에서 `YOLO`, `REGION`, `DETECTION` 타입 층의 `outputs`를 모두 더합니다. `remember_network`도 같은 층의 출력만 현재 `predictions[demo_index]`에 연속 복사합니다.

`avg_predictions`는 기본 세 슬롯의 값을 같은 비율로 더합니다.

~~~c
for(j = 0; j < demo_frame; ++j){
    axpy_cpu(demo_total, 1./demo_frame,
             predictions[j], 1, avg, 1);
}
~~~

평균을 다시 각 검출층의 `output`에 복사한 뒤 `get_network_boxes`를 호출합니다. 즉, 완성된 박스 좌표 목록을 평균하는 것이 아니라 박스로 변환하기 전 층 출력을 평균합니다.

초기 `predictions` 배열은 `calloc`으로 0에서 시작합니다. 첫 두 프레임에는 아직 채워지지 않은 슬롯도 3분의 1씩 평균에 포함되므로, 데모 시작 직후의 점수가 낮아질 수 있습니다.

## 검출 후 NMS와 표시가 이어진다

detect 스레드는 letterbox 입력으로 `network_predict`를 실행하고, 평균 출력으로 박스를 만든 다음 objectness 기준 NMS를 적용합니다. NMS 값은 함수 안에서 0.4로 고정돼 있습니다.

~~~c
float nms = .4;
if (nms > 0) {
    do_nms_obj(dets, nboxes, l.classes, nms);
}
~~~

FPS와 객체 제목을 터미널에 출력하고, 같은 오래된 슬롯의 원본 프레임에 `draw_detections`로 박스를 그립니다. 그 뒤 detection 배열을 해제하고 예측 ring index를 다음 칸으로 옮깁니다.

표시 함수는 키 코드 27이면 종료합니다. 82·84는 검출 threshold를 0.02씩 올리거나 내리고, 83·81은 hierarchy threshold를 조절합니다. 하한은 각각 0.02와 0입니다. 키 이름은 플랫폼의 OpenCV 키 코드 해석에 따라 달라질 수 있으므로 숫자만 보고 특정 문자라고 단정하지 않는 편이 안전합니다.

## 실행 전 컴파일 조건과 무시되는 인자를 본다

이 구현 전체는 `#ifdef OPENCV` 안에 있습니다. OpenCV 없이 빌드되면 같은 `demo` 함수가 실제 처리를 하지 않고 다음 메시지만 출력합니다.

~~~c
fprintf(stderr, "Demo needs OpenCV for webcam images.\n");
~~~

`filename`이 있으면 비디오 파일을 열고, 없으면 `cam_index`, `w`, `h`, `frames`로 카메라 스트림을 엽니다. 연결 실패 메시지는 입력이 파일이더라도 webcam이라고 표시됩니다.

원문 함수 인자와 실제 동작 사이에도 차이가 있습니다.

- `avg_frames`를 `demo_frame`에 넣는 줄이 주석이라 평균 길이는 전역 기본값 3으로 고정됩니다.
- `delay` 인자는 함수 본문에서 사용되지 않습니다.
- `prefix`가 있으면 창 대신 `(buff_index + 1) % 3` 프레임을 저장하므로, 검출 스레드가 그 순간 처리하는 `(buff_index + 2) % 3` 슬롯과 다릅니다.
- 루프 종료 뒤 네트워크, 예측 배열, 알파벳과 스트림을 정리하는 코드는 이 조각에 보이지 않습니다.

따라서 이 글의 소스는 완성된 현대식 실행법이 아니라 오래된 DarkNet OpenCV 데모의 파이프라인을 읽는 자료입니다. 프레임 지연이나 저장 결과가 예상과 다르면 모델보다 먼저 세 슬롯의 인덱스와 평균 버퍼가 채워진 시점을 확인해야 합니다.

## Frame 번호를 어떻게 추적해야 하나요?

각 capture 시점에 증가하는 frame id를 원본, letterbox, prediction과 display slot에 함께 저장합니다. 로그에는 현재 `buff_index`, fetch가 쓰는 slot, detect가 읽는 slot, display가 보여 주는 slot과 id를 한 줄로 남깁니다. Box가 사람보다 뒤따라오는 현상이 model latency인지 잘못된 slot pairing인지 이 표로 구분할 수 있습니다.

저장 경로도 display slot의 image와 어느 prediction으로 그렸는지 같은 id를 가져야 합니다. Prefix 저장이 다른 slot을 사용한다는 원문 조건에서는 화면에서 본 box와 저장 파일이 다를 수 있습니다. 단순히 filename 순번만 늘리면 이 불일치를 숨기므로 frame metadata를 함께 기록합니다.

## 평균화는 움직임과 Confidence에 어떤 영향을 주나요?

정지 장면에서는 세 raw output 평균이 순간적인 score 흔들림을 줄일 수 있지만 빠르게 움직이는 객체는 서로 다른 위치 예측이 섞입니다. Decode 전 tensor 위치가 같은 의미를 유지한다는 전제도 필요합니다. Anchor·grid output을 평균한 뒤 box가 중간 위치에 나타나거나 confidence가 낮아질 수 있으므로 smoothing과 추적은 같은 기능이 아닙니다.

시작 구간은 채워진 prediction 수만큼만 나누거나 warm-up 뒤 표시하는 방식과 원문 3-slot 고정 평균을 비교할 수 있습니다. 평균 frame 수를 바꾸려면 allocation, ring index와 분모가 모두 같은 값을 쓰는지 확인합니다. `avg_frames` 인자만 바꾸고 주석 처리된 대입을 그대로 두면 동작은 변하지 않습니다.

## Thread 안전성은 어떤 경계에서 확인하나요?

서로 다른 slot을 쓴다는 설계는 index 계산과 join 순서가 정확할 때만 안전합니다. Image 해제와 detect read가 같은 slot에서 겹치지 않는지, letterbox 생성이 완료되기 전에 network가 읽지 않는지 thread별 주소와 frame id를 기록합니다. 높은 카메라 FPS나 느린 network에서 반복 실행해 use-after-free를 sanitizer로 찾습니다.

전역 network output과 prediction ring도 한 detect thread만 수정한다는 전제가 있습니다. 복수 stream이나 비동기 detect를 추가하면 평균 buffer, NMS와 그리기 대상이 경쟁할 수 있으므로 stream별 state로 분리해야 합니다. FPS 출력 자체의 공유 변수도 측정 구간을 명확히 합니다.

## Threshold와 NMS를 튜닝할 때 무엇을 분리하나요?

키 입력으로 바뀌는 detection threshold는 평균 raw output에서 후보를 남기는 기준이고, 코드의 NMS 0.4는 겹친 box를 억제하는 IoU 기준입니다. Confidence가 낮다고 NMS를 높이는 식으로 서로 다른 역할을 섞지 않습니다. NMS 전 후보 수, 후 후보 수와 class별 score를 기록해 어느 단계가 객체를 지웠는지 봅니다.

Hierarchy threshold는 계층 class를 쓰지 않는 모델에서는 기대한 효과가 없을 수 있습니다. 키 코드는 OS와 OpenCV backend마다 다르므로 실제 반환값을 출력하고, threshold 하한뿐 아니라 지나치게 큰 상한도 관리합니다. 데모에서 즉석 조정한 값은 재현 가능한 평가 설정으로 별도 저장해야 합니다.

## 종료와 자원 정리는 무엇을 포함하나요?

Escape나 stream 종료 뒤 fetch·detect thread가 모두 join됐는지 확인하고 capture, 세 원본 image, letterbox image, prediction 배열, detection 임시 메모리와 window를 해제합니다. 루프 안에서 slot image를 교체할 때 이전 object와 underlying OpenCV frame의 소유권도 구분합니다. 장시간 실행에서 memory가 꾸준히 늘면 frame별 allocation 경로를 먼저 봅니다.

카메라 read 실패를 빈 frame으로 계속 처리하지 않고 루프 종료 또는 재연결 정책으로 연결해야 합니다. 파일 끝과 일시적인 webcam 실패는 다를 수 있으며, 오류 메시지에 실제 source 유형과 frame id를 담아야 원인을 찾기 쉽습니다.

## 자주 남는 질문

### DarkNet Demo 화면의 box는 현재 막 캡처한 frame 결과인가요?

아닙니다. capture·detect·display가 서로 다른 ring buffer slot을 사용하므로 화면에는 pipeline 지연이 있는 이전 frame 결과가 표시됩니다.

### 3-frame 평균은 완성된 bounding box 좌표를 평균하나요?

아닙니다. 검출 layer의 원시 output을 세 slot에서 평균한 뒤 그 평균으로 box decode와 NMS를 수행합니다.

### Demo 시작 직후 confidence가 낮을 수 있는 이유는 무엇인가요?

아직 예측이 들어오지 않은 calloc 0 slot까지 처음부터 3분의 1 비율로 평균에 포함되기 때문입니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [Darknet demo.c 고정 커밋 원본](https://raw.githubusercontent.com/pjreddie/darknet/f6afaabcdf85f77e7aff2ec55c020c0e297c77f9/src/demo.c)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [DarkNet Cost Layer에서 SSE·L1·MASKED가 실제로 갈리는 지점]({% post_url 2022-02-14-DarkNetCostLayer %}) — DarkNet Cost Layer의 문자열 파싱, L2·L1·Smooth L1 선택, 마스킹 처리와 delta 역전파를 코드가 실제 수행하는 범위 안에서 설명합니다.
- [DarkNet CRNN Layer의 state는 세 Convolution을 어떻게 순환하나]({% post_url 2022-02-15-DarkNetCRNNLayer %}) — DarkNet CRNN이 입력·순환·출력용 3×3 합성곱 세 개로 시퀀스 state를 만들고, 시간 역순으로 기울기를 전달하는 과정을 코드 기준으로 풀이합니다.
- [DarkNet image와 OpenCV Mat 변환: 채널 순서·스트림 설정 주의점]({% post_url 2022-02-25-DarkNetImageOpencv %}) — DarkNet의 CHW float image와 OpenCV의 HWC 8비트 Mat를 오갈 때 생기는 RGB·BGR 변환, VideoCapture 속성 설정 오류와 이미지 로드 실패 처리를 점검합니다.
<!-- internal-links:end -->
