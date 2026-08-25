---
layout: post
title: "DarkNet image와 OpenCV Mat 변환: 채널 순서·스트림 설정 주의점"
summary: "DarkNet의 CHW float image와 OpenCV의 HWC 8비트 Mat를 오갈 때 생기는 RGB·BGR 변환, VideoCapture 속성 설정 오류와 이미지 로드 실패 처리를 점검합니다."
date:   2022-02-25 16:00 -0400
categories: DarkNet
image:
  path: /assets/img/thumb/DarkNetImageOpencv.jpg
  alt: DarkNet 시리즈 - Image Opencv 대표 이미지
tags:
  - DarkNet
  - OpenCV
  - 이미지포맷
  - VideoCapture
math: true
---

DarkNet `image`는 채널별 평면을 잇는 float 배열이고 OpenCV 이미지는 픽셀별 채널이 붙은 8비트 배열이므로, 변환할 때 메모리 배치와 RGB·BGR 순서를 모두 바꿔야 합니다.

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
