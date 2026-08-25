---
layout: post
title: "DarkNet Demo 실시간 파이프라인: 3개 버퍼와 3프레임 평균"
summary: "DarkNet OpenCV 데모가 캡처·추론·표시를 세 버퍼로 겹쳐 처리하고 최근 세 예측을 평균한 뒤 NMS와 박스 그리기를 수행하는 흐름을 풀이합니다."
date:   2022-02-19 16:00 -0400
categories: DarkNet
image:
  path: /assets/img/thumb/DarkNetDemo.jpg
  alt: DarkNet 시리즈 - Demo 대표 이미지
tags:
  - DarkNet
  - YOLO
  - OpenCV
  - 실시간추론
math: true
---

DarkNet Demo는 프레임 세 장을 원형 버퍼로 돌리면서 새 프레임 캡처와 이전 프레임 추론을 동시에 실행하고, 최근 세 번의 검출 출력을 평균해 화면에 그립니다.

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
