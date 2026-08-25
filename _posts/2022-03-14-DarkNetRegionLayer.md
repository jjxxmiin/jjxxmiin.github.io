---
layout: post
title:  "Darknet Region Layer 학습이 멈추는 이유: 빈 backward와 objectness delta 추적"
date:   2022-03-14 16:00 -0400
categories: DarkNet
image:
  path: /assets/img/thumb/DarkNetRegionLayer.jpg
  alt: DarkNet 시리즈 - Region Layer 대표 이미지
tags:
  - DarkNet
  - Region Layer
  - Object Detection
summary: "Darknet region_layer의 출력 인덱스와 박스 좌표, 학습 delta 할당 순서를 따라가며 비어 있는 backward, truth 경계, 마스크 scale 형 변환, 추론 출력 변경을 점검합니다."
math: true
---

이 소스의 Region Layer는 `forward`에서 손실용 `delta`를 만들지만 `backward_region_layer`가 전부 주석 처리되어 있어, 보이는 CPU 코드만으로는 그 기울기가 이전 레이어에 전달되지 않습니다. 학습이 진행되지 않는다면 수식보다 이 연결부터 확인해야 합니다.

## 출력 배열은 box·objectness·class가 평면별로 놓인다

레이어 하나의 채널 수는 anchor마다 `coords + classes + 1`이고 전체 원소 수는 다음과 같습니다.

$$
outputs = w \\times h \\times n \\times (coords + classes + 1)
$$

`entry_index`는 배치, anchor, entry, 공간 위치를 1차원 인덱스로 바꿉니다. 한 박스의 값들이 연속으로 붙어 있는 구조가 아니라, 같은 entry의 `w*h` 값이 한 평면을 이룹니다.

```c
int entry_index(layer l, int batch, int location, int entry)
{
    int n = location / (l.w*l.h);
    int loc = location % (l.w*l.h);
    return batch*l.outputs
         + n*l.w*l.h*(l.coords + l.classes + 1)
         + entry*l.w*l.h
         + loc;
}
```

박스 디코딩은 셀 안의 오프셋 `x, y`와 anchor에 대한 로그 크기 `w, h`를 사용합니다.

```c
box get_region_box(float *x, float *biases, int n, int index,
                   int i, int j, int w, int h, int stride)
{
    box b;
    b.x = (i + x[index + 0*stride]) / w;
    b.y = (j + x[index + 1*stride]) / h;
    b.w = exp(x[index + 2*stride]) * biases[2*n] / w;
    b.h = exp(x[index + 3*stride]) * biases[2*n+1] / h;
    return b;
}
```

반대로 학습 목표는 다음 형태로 바뀝니다.

$$
t_x = truth_x w-i,\\quad
t_y = truth_y h-j
$$

$$
t_w = \\log\\frac{truth_w w}{bias_w},\\quad
t_h = \\log\\frac{truth_h h}{bias_h}
$$

`delta_region_box`는 이 목표와 원시 출력의 차이를 `delta`에 기록하고, 디코딩한 박스와 truth의 IoU를 반환합니다. 따라서 truth의 너비·높이와 bias가 양수라는 전제가 필요합니다. 0이나 음수가 들어오면 로그 계산부터 유효하지 않습니다.

## forward는 추론과 학습에서 하는 일이 크게 다르다

함수 시작은 입력을 출력으로 복사하고 `delta`를 0으로 만드는 것입니다. 추론이면 여기서 바로 반환합니다.

```c
memcpy(l.output, net.input, l.outputs*l.batch*sizeof(float));
memset(l.delta, 0, l.outputs*l.batch*sizeof(float));
if(!net.train) return;
```

즉, 이 함수의 추론 경로는 박스나 확률을 최종 검출 형식으로 만들지 않습니다. `get_region_detections`가 나중에 `l.output`을 해석합니다.

학습 경로는 두 번의 큰 순회를 합니다.

1. 모든 셀과 anchor를 훑으며 가장 가까운 truth와의 IoU를 구합니다. 기본 objectness 목표는 0이고, `background`일 때는 1입니다. 가장 좋은 IoU가 `thresh`보다 크면 이 음성 delta를 0으로 지웁니다.
2. truth를 하나씩 읽고, 중심이 속한 셀에서 모양 IoU가 가장 큰 anchor를 고릅니다. 그 anchor에 좌표, objectness, class, 필요하면 mask delta를 씁니다.

학습 초반 `*net.seen < 12800`에는 모든 박스가 셀 중심과 bias 크기를 향하도록 `0.01` 스케일의 좌표 delta도 추가됩니다. 실제 truth에 선택된 박스의 좌표 스케일은 `coord_scale * (2 - truth.w*truth.h)`입니다.

objectness는 기본적으로 1을 목표로 하지만 옵션에 따라 달라집니다.

```c
l.delta[obj_index] =
    l.object_scale * (1 - l.output[obj_index]);

if(l.rescore){
    l.delta[obj_index] =
        l.object_scale * (iou - l.output[obj_index]);
}
if(l.background){
    l.delta[obj_index] =
        l.object_scale * (0 - l.output[obj_index]);
}
```

이 세 문장은 독립된 `if`이므로 둘 이상의 옵션이 켜지면 아래쪽 할당이 위 결과를 덮어씁니다. 최종 target을 판단할 때 설정 이름만 보지 말고 실행 순서를 봐야 합니다.

## truth 경계와 delta 덮어쓰기에는 네 가지 함정이 있다

첫째, truth는 배치마다 최대 30개를 읽고 `truth.x == 0`을 목록 끝으로 사용합니다.

```c
for(t = 0; t < 30; ++t){
    box truth = float_to_box(
        net.truth + t*(l.coords + 1) + b*l.truths, 1);
    if(!truth.x) break;
    /* ... */
}
```

생성 함수의 `l.truths = 30*(l.coords + 1)`도 이 규약과 맞물립니다. 중심 x가 정확히 0인 유효 박스는 종료 표식과 구분되지 않으며, `truth.x * l.w`가 정확히 `l.w`가 되는 값도 셀 범위를 벗어납니다. 이 코드는 정규화된 중심이 열린 경계 안에 있다는 입력 전제를 둡니다.

둘째, 계층형 분류의 class-only truth 분기에는 objectness delta를 계산한 직후 무조건 0으로 만드는 문장이 있습니다.

```c
if(l.output[obj_index] < .3) {
    l.delta[obj_index] =
        l.object_scale * (.3 - l.output[obj_index]);
}else{
    l.delta[obj_index] = 0;
}
l.delta[obj_index] = 0;
```

결과적으로 앞의 조건 계산과 무관하게 이 경로의 objectness delta는 항상 0입니다. 의도한 동작인지 판단하기 전에는 마지막 대입을 놓치면 안 됩니다.

셋째, mask 함수의 `scale` 매개변수 형은 `int`입니다.

```c
void delta_region_mask(float *truth, float *x, int n, int index,
                       float *delta, int stride, int scale)
{
    for(int i = 0; i < n; ++i){
        delta[index + i*stride] =
            scale * (truth[i] - x[index + i*stride]);
    }
}
```

호출부는 `l.mask_scale`을 넘기므로 이 필드가 실수라면 함수 진입 시 정수로 변환됩니다. 예를 들어 1보다 작은 양의 scale은 0이 될 수 있습니다. 실수 스케일을 유지하려는 코드라면 매개변수 형부터 맞춰야 합니다.

넷째, 통계 출력은 실제 truth가 하나도 없을 때도 `count`와 `class_count`로 나눕니다.

```c
*(l.cost) = pow(mag_array(l.delta, l.outputs*l.batch), 2);
printf("Region Avg IOU: %f, Class: %f, Obj: %f, "
       "No Obj: %f, Avg Recall: %f, count: %d\n",
       avg_iou/count, avg_cat/class_count, avg_obj/count,
       avg_anyobj/(l.w*l.h*l.n*l.batch), recall/count, count);
```

빈 라벨 배치에서는 비용 계산과 별개로 로그 값이 유효하지 않을 수 있습니다. 진단 로그를 신뢰하려면 분모가 0인지 먼저 처리해야 합니다.

## backward와 resize는 완성된 학습 경로로 볼 수 없다

보이는 역전파 함수는 실행 코드가 없습니다.

```c
void backward_region_layer(const layer l, network net)
{
    /*
    int b;
    int size = l.coords + l.classes + 1;
    for(b = 0; b < l.batch*l.n; ++b){
        int index = (b*size + 4)*l.w*l.h;
        gradient_array(
            l.output + index, l.w*l.h, LOGISTIC, l.delta + index);
    }
    axpy_cpu(l.batch*l.inputs, 1, l.delta, 1, net.delta, 1);
    */
}
```

주석 속 마지막 `axpy_cpu`가 실행되지 않으므로 `l.delta`는 `net.delta`에 더해지지 않습니다. 다른 빌드나 GPU 경로가 이를 보완하는지 별도로 확인하지 않았다면, 이 조각을 완전한 학습 구현이라고 소개할 수 없습니다.

리사이즈 함수도 `w`, `h`, `inputs`, `outputs`와 두 버퍼만 바꿉니다.

```c
void resize_region_layer(layer *l, int w, int h)
{
    l->w = w;
    l->h = h;
    l->outputs = h*w*l->n*(l->classes + l->coords + 1);
    l->inputs = l->outputs;
    l->output =
        realloc(l->output, l->batch*l->outputs*sizeof(float));
    l->delta =
        realloc(l->delta, l->batch*l->outputs*sizeof(float));
}
```

생성 시 설정한 `out_w`와 `out_h`는 여기서 갱신하지 않습니다. 동적 입력 크기를 쓰는 네트워크라면 다음 레이어가 어떤 필드를 참조하는지 확인해야 합니다. `realloc` 실패 처리도 없고, 커진 영역은 0 초기화되지 않습니다.

생성 함수는 bias와 bias update를 anchor당 2개씩 할당하고 bias를 모두 0.5로 채웁니다. `cost`, `output`, `delta`도 별도 소유하며 마지막에 `srand(0)`을 호출합니다. 레이어 생성이 프로세스 전역 난수 상태까지 초기화한다는 점은 다른 무작위 연산과 순서를 재현할 때 고려해야 합니다.

## 검출 변환은 l.output을 직접 바꿀 수 있다

`get_region_detections`는 각 셀·anchor의 박스를 디코딩하고, objectness가 임계값을 넘을 때 클래스 확률을 채운 뒤 letterbox 보정을 적용합니다. `relative == 0`이면 마지막에 원본 이미지 픽셀 단위로 바꿉니다.

배치가 정확히 2이면 두 번째 출력을 수평으로 뒤집고 첫 번째 출력과 평균냅니다.

```c
if(l.batch == 2){
    float *flip = l.output + l.outputs;
    /* flip 버퍼의 좌우를 제자리 교환하고 x 항의 부호를 반전 */
    for(i = 0; i < l.outputs; ++i){
        l.output[i] = (l.output[i] + flip[i]) / 2.;
    }
}
```

이 과정은 별도 임시 출력이 아니라 `l.output`과 두 번째 배치 내용을 직접 수정합니다. 같은 출력에 대해 함수를 두 번 호출하면 최초 상태와 같은 계산이 아닐 수 있습니다.

계층형 softmax에서 `map`이 있으면 코드가 고정적으로 200개 항목을 순회합니다.

```c
if(map){
    for(j = 0; j < 200; ++j){
        int class_index = entry_index(
            l, 0, n*l.w*l.h + i, l.coords + 1 + map[j]);
        float prob = scale*predictions[class_index];
        dets[index].prob[j] = (prob > thresh) ? prob : 0;
    }
}
```

따라서 `map`과 `prob`가 최소 200개이며 각 `map[j]`가 클래스 범위 안이라는 전제가 필요합니다. `zero_objectness` 역시 batch 인덱스를 항상 0으로 계산하므로 첫 배치의 objectness만 0으로 만듭니다.

Region Layer를 점검할 때는 출력 모양만 맞추는 것으로 충분하지 않습니다. `entry_index`의 배치·anchor·entry 순서, truth의 종료 규약, 여러 옵션이 같은 delta를 덮어쓰는 순서, 그리고 최종 delta가 실제 이전 레이어로 누적되는지를 함께 확인해야 합니다.
