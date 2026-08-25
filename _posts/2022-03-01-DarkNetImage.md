---
layout: post
title:  "Darknet image.c에서 자주 틀리는 5가지: CHW 인덱싱·리사이즈·메모리 소유권"
summary: "Darknet의 image 구조체가 픽셀을 저장하고 복사·리사이즈·letterbox·증강·탐지 결과를 그리는 흐름을 코드 기준으로 해설합니다."
date:   2022-03-01 16:00 -0400
categories: DarkNet
image:
  path: /assets/img/thumb/DarkNetImage.jpg
  alt: DarkNet 시리즈 - Image 대표 이미지
tags:
  - Darknet소스분석
  - 이미지전처리
  - C메모리
math: true
---

Darknet의 `image.c`를 읽을 때 가장 먼저 잡아야 할 것은 **데이터가 CHW 순서의 1차원 `float` 배열이고, 함수마다 새 메모리를 만드는지 기존 포인터를 빌리는지가 다르다**는 점이다. 이 두 가지를 놓치면 색 채널이 뒤섞이거나 같은 버퍼를 두 번 해제하기 쉽다.

이 글은 수십 개 함수를 이름순으로 외우지 않는다. 픽셀 접근에서 시작해 메모리 소유권, 크기 변환, 색 증강, 탐지 결과 그리기까지 실제 호출 흐름으로 묶어 읽는다. 코드는 Darknet 내부 타입과 helper를 전제로 한 핵심 조각이며 단독 프로그램이 아니다.

## 1. 픽셀 주소는 왜 `c*h*w + y*w + x`인가

Darknet의 `image`는 채널 하나의 평면을 연속으로 놓은 뒤 다음 채널을 붙인다. 좌표 `(x, y, c)`의 위치는 다음 식으로 계산한다.

```c
static float get_pixel(image m, int x, int y, int c)
{
    assert(x < m.w && y < m.h && c < m.c);
    return m.data[c*m.h*m.w + y*m.w + x];
}
```

즉, RGB 이미지라면 `R 평면 → G 평면 → B 평면` 순서다. 이미지 파일을 읽은 직후의 interleaved 배열과 배치가 다르기 때문에 `load_image_stb`는 원본 인덱스와 목적 인덱스를 따로 계산한다.

```c
int dst_index = i + w*j + w*h*k;
int src_index = k + c*i + c*w*j;
im.data[dst_index] = (float)data[src_index]/255.;
```

경계 처리도 함수마다 다르다.

```c
static float get_pixel_extend(image m, int x, int y, int c)
{
    if(x < 0 || x >= m.w || y < 0 || y >= m.h) return 0;
    if(c < 0 || c >= m.c) return 0;
    return get_pixel(m, x, y, c);
}

static void set_pixel(image m, int x, int y, int c, float val)
{
    if(x < 0 || y < 0 || c < 0 ||
       x >= m.w || y >= m.h || c >= m.c) return;
    m.data[c*m.h*m.w + y*m.w + x] = val;
}
```

`get_pixel`은 범위를 벗어나면 assert가 발생하지만, `get_pixel_extend`는 0을 반환하고 `set_pixel`은 쓰기를 건너뛴다. 보간이나 캔버스 삽입 코드에서 바깥 영역이 검게 채워지는 이유가 여기에 있다.

이름만 보고 오해하기 쉬운 함수도 있다.

- `translate_image`는 좌표를 이동하지 않고 모든 픽셀 **값에** 상수 `s`를 더한다.
- `scale_image`는 크기를 바꾸지 않고 모든 픽셀 값에 `s`를 곱한다.
- `censor_image`는 영역을 검게 지우지 않고 32×32 블록의 첫 픽셀을 복제해 픽셀화한다.
- `border_image`는 바깥 픽셀을 `1`로 설정하므로 0~1 범위에서는 검정이 아니라 밝은 테두리다.

함수 설명보다 실제 대입식을 먼저 봐야 하는 이유다.

## 2. `image` 복사와 해제는 누가 책임지나

`make_empty_image`는 크기만 채우고 `data`를 할당하지 않는다. 실제 0 초기화 버퍼는 `make_image`가 `calloc`으로 만든다.

```c
image make_empty_image(int w, int h, int c)
{
    image out;
    out.data = 0;
    out.h = h;
    out.w = w;
    out.c = c;
    return out;
}

image make_image(int w, int h, int c)
{
    image out = make_empty_image(w, h, c);
    out.data = calloc(h*w*c, sizeof(float));
    return out;
}
```

반면 `float_to_image`는 새 배열을 만들지 않고 전달받은 포인터를 그대로 가리킨다.

```c
image float_to_image(int w, int h, int c, float *data)
{
    image out = make_empty_image(w, h, c);
    out.data = data;
    return out;
}
```

따라서 반환된 `image`를 수정하면 원래 `data`도 바뀐다. 이 view에 무조건 `free_image`를 호출하면 그 포인터의 실제 소유자와 충돌할 수 있다.

독립 복사가 필요할 때는 새 배열을 할당하는 `copy_image`를 쓴다.

```c
image copy_image(image p)
{
    image copy = p;
    copy.data = calloc(p.h*p.w*p.c, sizeof(float));
    memcpy(copy.data, p.data,
           p.h*p.w*p.c*sizeof(float));
    return copy;
}

void free_image(image m)
{
    if(m.data) free(m.data);
}
```

특히 `resize_max`와 `resize_min`은 크기가 이미 맞으면 입력 `image`를 그대로 반환하고, 다르면 새 이미지를 만든다. 호출부가 원본과 반환값을 둘 다 해제하면 같은 포인터를 두 번 해제할 가능성이 생긴다. 반환값이 항상 새 버퍼라고 가정하지 말고 `data` 소유권을 호출 경로별로 확인해야 한다.

## 3. crop·resize·letterbox는 결과가 어떻게 다른가

`crop_image`는 `(dx, dy)`에서 `w×h` 영역을 뽑고, 범위를 벗어난 좌표는 가장 가까운 경계로 제한한다.

```c
int r = constrain_int(j + dy, 0, im.h-1);
int c = constrain_int(i + dx, 0, im.w-1);
float val = get_pixel(im, c, r, k);
set_pixel(cropped, i, j, k, val);
```

`resize_image`는 먼저 가로 방향으로 보간한 중간 이미지 `part`를 만든 뒤 세로 방향을 보간한다. 임의 좌표를 읽는 기본 조각은 네 이웃을 섞는 bilinear interpolation이다.

```c
static float bilinear_interpolate(image im, float x, float y, int c)
{
    int ix = (int)floorf(x);
    int iy = (int)floorf(y);
    float dx = x - ix;
    float dy = y - iy;

    return (1-dy)*(1-dx)*get_pixel_extend(im, ix,   iy,   c) +
           dy    *(1-dx)*get_pixel_extend(im, ix,   iy+1, c) +
           (1-dy)*dx    *get_pixel_extend(im, ix+1, iy,   c) +
           dy    *dx    *get_pixel_extend(im, ix+1, iy+1, c);
}
```

원본 종횡비를 무시하고 목표 크기로 바로 resize하면 물체 모양이 늘어난다. `letterbox_image`는 종횡비를 유지한 새 크기를 구하고, 0.5로 채운 목표 캔버스 중앙에 삽입한다.

```c
if (((float)w/im.w) < ((float)h/im.h)) {
    new_w = w;
    new_h = (im.h * w)/im.w;
} else {
    new_h = h;
    new_w = (im.w * h)/im.h;
}

image resized = resize_image(im, new_w, new_h);
image boxed = make_image(w, h, im.c);
fill_image(boxed, .5);
embed_image(resized, boxed,
            (w-new_w)/2, (h-new_h)/2);
```

여기서 resize된 영상 좌표와 원본 좌표는 같지 않다. 탐지 상자를 원본에 다시 그릴 때는 resize 비율뿐 아니라 좌우·상하 여백도 되돌려야 한다. `letterbox`를 단순 resize로 취급하면 상자가 일정하게 밀린다.

## 4. 기하 변환과 색 변환은 어디서 이어지나

`random_augment_args`는 회전각, scale, aspect ratio, 이동량을 무작위로 만들고 `rotate_crop_image`가 출력 픽셀을 원본 좌표로 역매핑해 보간한다.

```c
augment_args a = random_augment_args(
    im, angle, aspect, low, high, w, h);
image crop = rotate_crop_image(
    im, a.rad, a.scale, a.w, a.h,
    a.dx, a.dy, a.aspect);
```

색 증강은 RGB를 HSV로 바꾼 뒤 saturation과 value 채널을 조절하고 hue를 순환시킨다.

```c
void distort_image(image im, float hue, float sat, float val)
{
    rgb_to_hsv(im);
    scale_image_channel(im, 1, sat);
    scale_image_channel(im, 2, val);
    int i;
    for(i = 0; i < im.w*im.h; ++i){
        im.data[i] += hue;
        if(im.data[i] > 1) im.data[i] -= 1;
        if(im.data[i] < 0) im.data[i] += 1;
    }
    hsv_to_rgb(im);
    constrain_image(im);
}
```

`random_distort_image`가 실제로 무작위 값을 만들고, `distort_image`는 전달된 값을 그대로 적용한다. 이름과 달리 후자 내부에는 난수 생성이 없다. 증강 재현성을 확인하려면 난수 생성 지점과 변환 지점을 구분해야 한다.

또한 이 함수들은 대부분 입력 버퍼를 직접 수정한다. 원본을 이후에도 써야 한다면 먼저 `copy_image`로 독립 사본을 만들어야 한다.

## 5. 탐지 결과를 그릴 때 무엇을 검증할까

`draw_detections`는 detection마다 threshold를 넘은 클래스 이름을 모으고, 첫 클래스를 기준으로 색을 고른 뒤 정규화된 box를 픽셀 좌표로 바꾼다.

```c
int left  = (b.x-b.w/2.)*im.w;
int right = (b.x+b.w/2.)*im.w;
int top   = (b.y-b.h/2.)*im.h;
int bot   = (b.y+b.h/2.)*im.h;

draw_box_width(im, left, top, right, bot,
               width, red, green, blue);
```

`draw_box`는 좌표를 이미지 경계로 자르고 CHW 배열의 네 변에 RGB 값을 직접 쓴다. alphabet이 있으면 문자 이미지를 이어 붙인 label을 그리고, mask가 있으면 14×14 mask를 box 크기로 resize한 뒤 0.5에서 threshold해 삽입한다.

결과가 이상할 때는 화면만 보지 말고 다음을 순서대로 확인한다.

1. 입력 `image`가 CHW이며 픽셀 값이 0~1 범위인가?
2. `bbox.x`, `bbox.y`, `bbox.w`, `bbox.h`가 정규화 좌표인가?
3. letterbox를 거쳤다면 여백과 scale을 되돌렸는가?
4. RGB와 BGR을 바꾸는 `rgbgr_image`가 중복 호출되지 않았는가?
5. 새 버퍼를 반환한 함수와 입력을 직접 수정한 함수를 구분했는가?
6. 임시 `image`를 정확히 한 번만 `free_image` 했는가?

`show_image`는 OpenCV로 컴파일됐으면 창을 띄우고, 아니면 같은 이름의 PNG를 저장한다. “창이 안 뜬다”는 현상만으로 이미지 생성 실패라고 판단하면 안 된다. 결국 `image.c`의 핵심은 개별 필터 이름이 아니라 **배열 배치, 좌표계, 값 범위, 버퍼 소유권이 다음 함수로 어떻게 전달되는지 추적하는 것**이다.
