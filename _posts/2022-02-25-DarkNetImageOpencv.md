---
source_citations:
  - name: "Darknet image_opencv.cpp 고정 커밋 원본"
    url: "https://raw.githubusercontent.com/pjreddie/darknet/f6afaabcdf85f77e7aff2ec55c020c0e297c77f9/src/image_opencv.cpp"
layout: post
title: "DarkNet image와 OpenCV Mat 변환: 채널 순서, 스트림 설정 주의점"
summary: "DarkNet의 CHW float image와 OpenCV의 HWC 8비트 Mat를 오갈 때 생기는 RGB, BGR 변환, VideoCapture 속성 설정 오류와 이미지 로드 실패 처리를 점검합니다."
description: "DarkNet CHW float image와 OpenCV HWC byte Mat의 layout, RGB/BGR, stride 변환, stream 속성, 빈 frame, 안전한 실패 처리를 설명합니다."
date:   2022-02-25 16:00 -0400
categories: DarkNet
image:
  path: /assets/img/thumb/DarkNetImageOpencv.jpg
  alt: DarkNet 시리즈 - Image Opencv 대표 이미지
tags:
  - DarkNet
  - 경량화
  - 웹개발
math: true
faq:
  - question: "DarkNet image와 OpenCV Mat를 변환할 때 무엇이 동시에 바뀌나요?"
    answer: "CHW와 HWC memory layout, float 0~1과 8-bit 0~255 범위, 3채널에서는 RGB와 BGR 순서를 함께 맞춰야 합니다."
  - question: "원문 open_video_stream의 height와 FPS 설정은 왜 의심해야 하나요?"
    answer: "해당 property의 값으로 h와 fps가 아니라 w를 전달해 두 설정이 요청과 다르게 적용될 수 있기 때문입니다."
  - question: "이미지 로드 실패 때 10×10 대체 이미지를 반환하면 무엇이 위험한가요?"
    answer: "호출자가 실패를 정상 입력으로 학습, 추론할 수 있고, 원문 shell 명령 기록은 신뢰할 수 없는 filename에서 명령 주입과 buffer overflow 위험도 있습니다."
---

DarkNet `image`는 채널별 평면을 잇는 float 배열이고 OpenCV 이미지는 픽셀별 채널이 붙은 8비트 배열이므로, 변환할 때 메모리 배치와 RGB, BGR 순서를 모두 바꿔야 합니다. 여기에 0–1 float와 0–255 byte의 값 범위 변환도 함께 일어납니다. 결과의 색이나 밝기가 틀리면 layout, 채널 순서, scale을 한꺼번에 고치지 말고 단계별 왕복 변환으로 확인해야 합니다.

## CHW float와 HWC byte를 서로 옮긴다

`image_to_ipl`은 DarkNet 값을 다음 인덱스로 읽습니다.

~~~c
im.data[c*im.h*im.w + y*im.w + x]
~~~

이는 한 채널의 전체 `h × w` 평면 뒤에 다음 채널이 오는 CHW 배치입니다. OpenCV의 `IplImage`에는 `y × widthStep + x × channels + c`로 써서 한 픽셀의 채널이 붙어 있는 배열로 바꾸고, float 값에 255를 곱해 `unsigned char`로 저장합니다.

반대 방향인 `ipl_to_image`는 이 인덱스를 거꾸로 사용하고 255로 나눕니다.

~~~c
im.data[k*w*h + i*w + j] =
    data[i*step + j*c + k]/255.;
~~~

`widthStep`을 사용하므로 OpenCV 행 끝의 padding도 건너뜁니다. 다만 `image_to_ipl` 자체는 입력 float를 0에서 1로 제한하지 않습니다. 이 함수를 직접 호출한다면 범위를 벗어난 값이 8비트 형변환되기 전에 먼저 제한해야 합니다.

## Mat 변환에서 RGB와 BGR을 바꾼다

`image_to_mat`은 원본을 복사해 0에서 1로 제한하고, 3채널일 때 `rgbgr_image`로 채널을 바꾼 뒤 IplImage와 Mat로 변환합니다. `cvarrToMat(ipl, true)`의 두 번째 인자가 true라 Mat에는 복사본이 생기며, 바로 뒤에서 IplImage와 DarkNet 복사 이미지를 해제할 수 있습니다.

~~~c
image copy = copy_image(im);
constrain_image(copy);
if(im.c == 3) rgbgr_image(copy);

IplImage *ipl = image_to_ipl(copy);
Mat m = cvarrToMat(ipl, true);
~~~

반대 방향의 `mat_to_image`는 Mat를 IplImage 헤더로 본 뒤 DarkNet 배열로 복사하고 `rgbgr_image`를 호출합니다. 이 호출은 채널 수 조건 없이 실행되므로, 1채널 Mat에서 `rgbgr_image`가 무엇을 하는지는 사용 중인 소스의 구현과 함께 확인해야 합니다.

## VideoCapture 설정에는 인자 오사용이 있다

`open_video_stream`은 파일 경로 `f`가 있으면 비디오 파일을, 없으면 카메라 인덱스 `c`를 엽니다. 너비 설정은 인자를 올바르게 사용하지만 높이와 FPS 설정에는 각각 `h`, `fps`가 아니라 `w`가 전달됩니다.

~~~c
if(w)   cap->set(CV_CAP_PROP_FRAME_WIDTH, w);
if(h)   cap->set(CV_CAP_PROP_FRAME_HEIGHT, w);
if(fps) cap->set(CV_CAP_PROP_FPS, w);
~~~

따라서 요청한 높이와 FPS가 적용되지 않거나 둘 다 너비 숫자로 설정될 수 있습니다. 이 코드를 재사용한다면 두 번째 인자를 각각 `h`와 `fps`로 쓰는 버전인지 확인해야 합니다.

`get_image_from_stream`은 `VideoCapture >> Mat`으로 한 프레임을 받고, 비어 있으면 `0 × 0 × 0` empty image를 반환합니다. 호출자는 이 값을 스트림 종료나 읽기 실패로 처리해야 합니다. 이 조각에는 `new VideoCapture`로 만든 객체를 해제하는 함수가 보이지 않습니다.

## 이미지 로드 실패를 정상 입력처럼 넘기지 않는다

`load_image_cv`의 채널 플래그는 코드상 다음과 같습니다.

- `channels == 0`: `flag = -1`, 파일의 채널 설정을 그대로 읽음
- `channels == 1`: `flag = 0`, 회색조로 읽음
- `channels == 3`: `flag = 1`, 컬러로 읽음

그 밖의 값은 오류 문구를 출력하지만 flag는 -1인 채 계속 로드합니다. 파일을 읽지 못했을 때도 함수는 실패를 반환하지 않고 `10 × 10 × 3` 이미지를 만들어 돌려줍니다.

더 주의할 부분은 실패한 파일명을 셸 문자열에 직접 넣는 코드입니다.

~~~c
char buff[256];
sprintf(buff, "echo %s >> bad.list", filename);
system(buff);
return make_image(10,10,3);
~~~

파일명에 공백이나 셸 특수문자가 있으면 기록이 깨지거나 의도하지 않은 명령으로 해석될 수 있고, 긴 경로는 256바이트 버퍼를 넘을 수 있습니다. 신뢰할 수 없는 경로에는 이 구현을 사용하지 말고, 셸을 거치지 않는 파일 기록과 명시적 실패 처리가 있는지 확인해야 합니다.

화면 출력은 `image_to_mat → imshow → waitKey(ms)` 순서이며, 창 생성은 fullscreen 여부에 따라 속성 또는 크기를 설정합니다. 전체 코드는 `#ifdef OPENCV` 안의 오래된 C/C++ 연동 조각이므로, 현재 OpenCV API와 그대로 호환되는 완전한 실행 예제로 보아서는 안 됩니다.

## Layout 변환은 어떤 Pixel Pattern으로 검증하나요?

2×2 RGB image에서 각 위치와 channel에 모두 다른 값을 넣습니다. DarkNet 배열의 R 평면 네 값, G 평면, B 평면이 OpenCV의 각 pixel BGR 세 값으로 정확히 모이는지 표로 비교합니다. 정사각 image만 쓰면 width와 height를 바꿔 쓴 오류가 숨을 수 있으므로 2×3 사례도 추가합니다.

Mat row는 `width×channels`보다 큰 step을 가질 수 있어 다음 row를 단순 곱으로 읽으면 padding byte가 pixel로 섞입니다. 연속 Mat와 ROI처럼 연속이 아닐 수 있는 Mat를 각각 시험하고 실제 `step`을 사용합니다. Round-trip 뒤 각 pixel의 최대 오차는 8-bit 양자화 범위 안이어야 하며 channel swap은 오차로 허용하지 않습니다.

## 값 범위와 형변환은 어디서 제한하나요?

Float가 음수 또는 1보다 큰 상태에서 255를 곱해 unsigned char로 바꾸면 clipping 대신 wrap이나 구현 의존 결과가 생길 수 있습니다. `image_to_mat`은 copy에 constrain을 하지만 낮은 수준의 `image_to_ipl` 직접 호출은 그렇지 않으므로 API별 precondition을 문서화합니다. NaN과 Inf도 화면 변환 전에 처리 정책을 정합니다.

반대 방향은 byte를 255로 나눠 0~1 float를 만듭니다. Model이 -1~1이나 mean/std normalize를 기대한다면 이 함수 뒤 별도 전처리를 한 번만 적용해야 합니다. 이미 normalize된 DarkNet image를 화면에 보이려고 역정규화하지 않고 constrain만 하면 색이 왜곡될 수 있으므로 추론 입력과 표시 copy를 분리합니다.

## Channel 수가 1, 3이 아닐 때 무엇을 해야 하나요?

RGB/BGR swap은 적어도 세 channel이 있다는 전제가 있습니다. Grayscale Mat에 무조건 `rgbgr_image`를 적용하는 경로가 channel index를 어떻게 처리하는지 사용 source를 확인하고, 안전하지 않으면 `c==3` 조건을 둡니다. Alpha를 가진 4채널 input은 alpha를 버릴지 보존할지 명시적으로 정합니다.

Loader의 요청 channels와 실제 Mat channels가 같은지 변환 직전에 검사합니다. OpenCV가 color flag에 따라 gray를 3채널로 바꾸거나 반대로 읽을 수 있으므로 filename 확장자로 추정하지 않습니다. Empty Mat는 channel query와 data 접근 전에 실패로 반환합니다.

## VideoCapture 설정은 실제 적용값을 어떻게 확인하나요?

Width, height와 FPS를 set한 뒤 get으로 실제 값을 다시 읽어 로그에 남깁니다. Camera backend가 요청값을 지원하지 않으면 set이 실패하거나 가까운 mode를 고를 수 있어 코드 인자를 고친 것만으로 보장되지 않습니다. 파일 source에서는 FPS를 바꾸는 property가 capture 속도와 같은 의미가 아닐 수도 있습니다.

첫 frame의 실제 Mat 크기와 설정값을 비교하고 network letterbox가 이 크기를 사용하도록 합니다. Height와 FPS에 w를 전달하는 원문 오류를 수정할 때는 각 property가 각각 h와 fps를 받는 단위 test를 둡니다. 0 인자는 property를 설정하지 않는 의미인지도 유지합니다.

## Stream의 빈 Frame은 어떻게 처리하나요?

0×0×0 image는 end-of-file, camera disconnect 또는 일시적 read 실패를 나타낼 수 있습니다. 그대로 resize하거나 network에 넣지 말고 source 유형에 따라 종료, 제한된 재시도와 재연결을 선택합니다. 반복 실패에서 busy loop가 되지 않도록 로그 빈도와 대기 정책을 정하지만 장시간 block으로 UI 종료를 막지 않습니다.

Capture object 수명은 성공과 실패 경로 모두에서 해제해야 합니다. 새 stream을 열 때 이전 object를 닫고, 프로그램 종료 전 read thread가 끝난 뒤 release합니다. Frame을 다른 thread가 읽는 동안 Mat backing memory가 재사용되지 않도록 copy와 소유권도 확인합니다.

## 실패 파일 기록을 안전하게 바꾸는 기준

Filename을 shell command 문자열에 삽입하지 말고 파일 API로 `bad.list`를 열어 한 줄을 기록합니다. 고정 크기 sprintf buffer 대신 길이를 검사하는 방식과 encoding, newline 정책을 사용합니다. 공격자가 조작할 수 있는 경로뿐 아니라 공백, 따옴표와 아주 긴 정상 경로도 시험합니다.

대체 image를 자동 반환하기보다 호출자에게 명확한 failure 상태를 전달하면 학습에서 skip 수를 세고 허용 한도를 넘을 때 중단할 수 있습니다. 호환성 때문에 placeholder가 필요하다면 label과 함께 유효 mask를 전달해 정상 sample로 loss에 들어가지 않게 합니다.

## 자주 남는 질문

### DarkNet image와 OpenCV Mat를 변환할 때 무엇이 동시에 바뀌나요?

CHW와 HWC memory layout, float 0~1과 8-bit 0~255 범위, 3채널에서는 RGB와 BGR 순서를 함께 맞춰야 합니다.

### 원문 open_video_stream의 height와 FPS 설정은 왜 의심해야 하나요?

해당 property의 값으로 h와 fps가 아니라 w를 전달해 두 설정이 요청과 다르게 적용될 수 있기 때문입니다.

### 이미지 로드 실패 때 10×10 대체 이미지를 반환하면 무엇이 위험한가요?

호출자가 실패를 정상 입력으로 학습, 추론할 수 있고, 원문 shell 명령 기록은 신뢰할 수 없는 filename에서 명령 주입과 buffer overflow 위험도 있습니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [Darknet image_opencv.cpp 고정 커밋 원본](https://raw.githubusercontent.com/pjreddie/darknet/f6afaabcdf85f77e7aff2ec55c020c0e297c77f9/src/image_opencv.cpp)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [Darknet col2im에서 픽셀값을 덮어쓰지 않고 +=로 더하는 이유]({% post_url 2022-02-10-DarkNetCol2im %}) — Darknet col2im_cpu가 column buffer의 값을 원본 feature map 위치로 되돌릴 때 겹치는 kernel 기여를 누적하는 이유를 index 계산과 padding 경계 처리로 설명합니다.
- [Darknet image.c에서 자주 틀리는 5가지: CHW 인덱싱, 리사이즈, 메모리 소유권]({% post_url 2022-03-01-DarkNetImage %}) — Darknet의 image 구조체가 픽셀을 저장하고 복사, 리사이즈, letterbox, 증강, 탐지 결과를 그리는 흐름을 코드 기준으로 해설합니다.
- [DarkNet Demo 실시간 파이프라인: 3개 버퍼와 3프레임 평균]({% post_url 2022-02-19-DarkNetDemo %}) — DarkNet OpenCV 데모가 캡처, 추론, 표시를 세 버퍼로 겹쳐 처리하고 최근 세 예측을 평균한 뒤 NMS와 박스 그리기를 수행하는 흐름을 풀이합니다.
<!-- internal-links:end -->
