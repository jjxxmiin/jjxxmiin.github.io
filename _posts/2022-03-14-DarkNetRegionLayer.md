---
source_citations:
  - name: "Darknet region_layer.c 고정 커밋 원본"
    url: "https://raw.githubusercontent.com/pjreddie/darknet/f6afaabcdf85f77e7aff2ec55c020c0e297c77f9/src/region_layer.c"
layout: post
title:  "Darknet Region Layer 학습이 멈추는 이유: 빈 backward와 objectness delta 추적"
date:   2022-03-14 16:00 -0400
categories: DarkNet
image:
  path: /assets/img/thumb/DarkNetRegionLayer.jpg
  alt: DarkNet 시리즈 - Region Layer 대표 이미지
tags:
  - DarkNet
  - 컴퓨터비전
summary: "Darknet region_layer의 출력 인덱스와 박스 좌표, 학습 delta 할당 순서를 따라가며 비어 있는 backward, truth 경계, 마스크 scale 형 변환, 추론 출력 변경을 점검합니다."
description: "Darknet Region Layer의 plane output·anchor decode·delta overwrite를 따라 빈 CPU backward, truth sentinel·mask scale·in-place flip 실패를 설명합니다."
math: true
faq:
  - question: "제시된 CPU Region Layer는 forward delta를 이전 layer로 보내나요?"
    answer: "아닙니다. Backward 본문이 주석 처리돼 있어 보이는 코드만으로는 net.delta에 누적되지 않습니다."
  - question: "Region truth에서 x가 0인 box는 어떻게 해석되나요?"
    answer: "Truth 목록 종료 표지로 사용되므로 중심 x가 정확히 0인 유효 box와 구분할 수 없습니다."
  - question: "get_region_detections를 같은 output에 반복 호출해도 같나요?"
    answer: "Batch 2 flip 평균 경로가 l.output을 직접 바꾸므로 두 번째 호출이 최초 상태와 다를 수 있습니다."
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

학습 초반 `*net.seen`이 12800 미만일 때는 모든 박스가 셀 중심과 bias 크기를 향하도록 `0.01` 스케일의 좌표 delta도 추가됩니다. 실제 truth에 선택된 박스의 좌표 스케일은 `coord_scale * (2 - truth.w*truth.h)`입니다.

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

## Synthetic Truth로 어떤 Delta를 확인하나요?

빈 truth에서는 모든 anchor objectness 음성 delta와 0인 class·coordinate delta를 확인합니다. Box 하나를 중앙 cell에 두고 모양이 다른 anchor를 만들면 best anchor 하나만 coordinate와 positive objectness를 받아야 합니다. Rescore와 background를 하나씩 켜 최종 대입 순서가 예상 target을 만드는지 봅니다.

Width·height 0, x 경계 0과 1, class 범위 밖 label을 loader에서 거부합니다. Empty batch의 metric 분모와 mask scale 0.5가 int conversion으로 0이 되는지도 별도 시험합니다.

## entry_index는 작은 숫자로 손계산합니다

### batch·anchor·entry·공간 위치를 따로 고정합니다

`w=2`, `h=2`, `n=2`, `coords=4`, `classes=2`인 예를 만들면 anchor 하나의 entry 수는 7이고 각 entry 평면은 원소 4개입니다. batch 0의 anchor 0, x entry는 처음 네 원소이고 y entry는 그 다음 네 원소입니다. anchor 1의 시작은 anchor 0이 사용하는 `7×4`개 뒤입니다. batch 1은 `l.outputs`만큼 더 이동해야 합니다.

배열을 0부터 증가하는 연속 값으로 채우고 `entry_index`가 반환한 index를 표로 적으면 anchor마다 `[x,y,w,h,obj,class...]`가 연속인 interleaved layout과 쉽게 구분됩니다. 두 layout은 전체 원소 수가 같아 shape assert만으로 오류를 찾을 수 없습니다. 포팅한 tensor transpose가 있다면 entry별 평면을 비교한 뒤에만 decode를 실행합니다.

### stride가 w×h인지 끝까지 확인합니다

`get_region_box`는 x, y, w, h를 `stride` 간격으로 읽습니다. stride를 1로 넘기면 같은 공간 위치의 네 entry가 아니라 한 평면의 이웃 셀 값을 박스 하나로 읽게 됩니다. 셀마다 서로 다른 패턴을 넣고 디코딩한 중심과 크기를 손계산하면 이런 오류가 시각화 전에 드러납니다.

## 두 번의 forward 순회를 분리해 delta를 봅니다

### 첫 순회는 모든 anchor의 음성 상태를 만듭니다

빈 truth 배치에서 objectness delta만 채워지고 box·class delta는 0인지 확인합니다. 실제 truth와 IoU가 `thresh`보다 큰 후보는 no-object delta가 0으로 지워지는지 봅니다. 이 단계의 목적은 정답 anchor를 확정하는 것이 아니라 명확한 음성을 만들고 truth와 충분히 겹친 예측을 무시하는 데 있으므로 두 역할을 로그에서 구분합니다.

각 셀·anchor마다 obj index, 원래 output, best IoU와 첫 순회 뒤 delta를 남기면 `entry_index` 오류와 threshold 분기를 함께 찾을 수 있습니다. 평균 no-object 값만 보면 특정 anchor의 잘못된 index가 다른 값에 묻힐 수 있습니다.

### 둘째 순회는 truth별 best anchor를 양성으로 덮습니다

하나의 truth와 모양이 다른 두 bias를 두어 어떤 anchor가 선택될지 먼저 계산합니다. 선택된 anchor에만 좌표·class와 양성 objectness delta가 들어가고, 같은 셀의 나머지 anchor는 첫 순회 결과를 유지해야 합니다. truth 두 개가 같은 셀과 anchor를 선택하는 경우에는 마지막 대입이 앞 delta를 덮는지 또는 누적하는지 원문 코드 순서로 확인합니다.

`rescore`와 `background`가 독립된 `if`로 이어지므로 둘 다 켜면 마지막 `background` 할당이 최종 objectness 목표가 됩니다. 설정 이름을 조합해 의도를 추측하지 말고 각 옵션을 하나씩 켠 결과와 동시 조건을 표로 남깁니다. class-only 분기의 무조건 0 대입도 같은 방식으로 마지막 쓰기 위치를 추적해야 합니다.

## backward 연결은 함수 포인터부터 추적합니다

### 보이는 CPU 함수만 호출된다면 delta가 멈춥니다

제시된 `backward_region_layer`의 실행 본문은 비어 있으므로 `forward`가 만든 `l.delta`는 이 함수만으로 `net.delta`에 더해지지 않습니다. 학습 loss 로그가 변해도 이전 convolution weight가 갱신되지 않을 수 있습니다. 한 입력 원소에 대한 finite difference와 이전 layer delta norm을 함께 보면 손실 계산과 gradient 전달을 분리할 수 있습니다.

네트워크 실행부에서 이 layer의 `backward` 함수 포인터가 무엇으로 설정되는지, CPU 경로가 실제로 호출되는지 로그를 남깁니다. backward 호출 직전 `l.delta`가 유한하고 nonzero인데 직후 `net.delta`가 그대로라면 optimizer보다 연결 문제를 먼저 봅니다.

### 다른 build와 GPU 경로는 별도 근거가 필요합니다

다른 Darknet fork나 GPU 구현이 역전파를 제공할 수 있지만, 이 코드 조각만으로 그 경로가 존재하거나 같은 delta 규칙을 쓴다고 단정할 수 없습니다. 빌드 플래그, layer 생성 시 등록한 함수 포인터와 실제 링크된 소스를 확인해야 합니다. CPU와 GPU 결과를 비교할 때는 같은 입력·truth·bias·옵션에서 entry별 delta와 이전 layer delta를 각각 대조합니다.

구현을 보완한다면 주석 속 코드를 무조건 활성화하기보다 logistic gradient가 forward 표현과 맞는지, `axpy_cpu` 길이와 batch stride가 현재 layout에 맞는지 검증합니다. 수정 뒤에는 손실 감소만 보지 말고 수치 미분과 작은 overfit 테스트로 gradient 방향을 확인합니다.

## resize는 크기와 메타데이터를 함께 갱신해야 합니다

### 재할당 성공만으로 shape 전파가 끝나지 않습니다

`resize_region_layer`는 `w`, `h`, `inputs`, `outputs`, `output`과 `delta`를 바꾸지만 보이는 코드에서는 `out_w`·`out_h`를 갱신하지 않습니다. 다음 layer나 detection API가 어느 필드를 읽는지에 따라 실제 buffer 크기와 metadata가 달라질 수 있습니다. resize 전후에 모든 shape 필드와 할당 byte 수를 한 줄로 출력해 비교합니다.

`realloc`은 실패 시 원래 포인터를 잃지 않도록 임시 변수로 처리하는 편이 안전합니다. 커진 영역은 자동으로 0이 되지 않으므로 forward가 전 범위를 덮는지 확인합니다. resize 뒤 오래된 `l.output` view를 외부가 보관하고 있다면 재할당으로 use-after-free가 생길 수 있어 pointer 수명도 함께 점검합니다.

### 여러 크기를 왕복하는 테스트가 필요합니다

작은 크기→큰 크기→다시 작은 크기로 바꾸고 forward, decode와 free를 반복합니다. 각 단계에서 `outputs` 식, `truths`, bias 수와 detection allocation이 맞는지 봅니다. spatial 크기가 바뀌어도 anchor bias를 같은 단위로 해석하는지 cfg와 resize 호출부에서 확인해야 합니다.

## 추론 함수의 in-place 변경을 어떻게 통제할까

batch 2 flip 경로는 두 번째 출력의 좌우를 제자리에서 바꾸고 첫 배치 출력에 평균을 다시 씁니다. 따라서 같은 `l.output`으로 검출 함수를 두 번 호출하는 API는 순수 함수가 아닙니다. 호출 전 output 사본을 만들고 첫 호출·두 번째 호출의 byte 차이를 비교하면 반복성 문제를 확인할 수 있습니다.

NMS나 임계값만 바꿔 같은 raw output을 여러 번 디코딩하려면 변환 함수가 입력을 변경하지 않도록 별도 작업 buffer를 쓰거나 호출마다 원본을 복원해야 합니다. `zero_objectness`처럼 batch 0만 대상으로 계산하는 보조 함수도 다중 batch에서 의도한 범위를 확인합니다. 속도 최적화를 위해 in-place를 유지한다면 API 문서에 한 번만 호출할 수 있다는 수명 계약을 명시합니다.

letterbox 보정과 `relative` 변환도 단계별 출력으로 나눕니다. raw normalized box, letterbox 제거 뒤 box, pixel 변환 뒤 box를 기록하면 좌표 오류와 in-place 평균 오류를 구분할 수 있습니다. map 경로의 고정 200개 순회는 class 수, `map`과 `prob` allocation 전제를 parser에서 검사합니다.

## 입력 경계와 로그를 어떤 순서로 디버깅할까

먼저 loader에서 truth의 x·y가 열린 구간 안인지, w·h와 bias가 양수인지, class가 범위 안인지 검사합니다. x가 0인 유효 박스는 sentinel과 충돌하므로 데이터 정책으로 이동하거나 다른 종료 표현을 써야 합니다. x가 1이면 셀 index가 w가 될 수 있어 배열 접근 전에 거부합니다.

다음으로 NaN이 처음 생기는 위치를 분리합니다. `log(truth_w*w/bias_w)` 입력, `exp`가 큰 raw width·height, 빈 batch 통계의 0 나눗셈과 실제 delta의 NaN을 각각 봅니다. 통계 출력만 NaN인데 delta와 cost가 유한한 경우와 gradient 자체가 오염된 경우는 대응이 다릅니다.

마지막으로 sanitizer와 synthetic tensor를 함께 사용합니다. AddressSanitizer는 map 범위와 cell index 같은 메모리 오류를 찾지만 유효한 다른 anchor를 선택한 논리 오류는 찾지 못합니다. 손으로 계산한 index, IoU, best anchor와 delta 배열을 기준으로 둬야 두 종류의 실패를 모두 다룰 수 있습니다.

## 이 글의 출처 범위는 어떻게 해석해야 하나

이 설명은 제시된 CPU Region Layer 코드의 배열과 대입 순서를 분석한 것입니다. 다른 시점의 Darknet, fork와 GPU 소스에서는 backward, resize, truth 형식과 detection 후처리가 달라졌을 수 있습니다. 동일한 `REGION` 이름만 보고 여기의 빈 backward나 200 class 전제를 모든 버전에 적용하면 안 됩니다.

포팅 대상 저장소의 커밋에서 layer 생성 함수, parser, CPU·GPU 함수 포인터, network backward 호출과 detection API를 한 묶음으로 읽습니다. 이 글은 “어디를 확인할지”에 대한 디버깅 기준선이며 완성된 최신 학습 절차나 정확도 보장을 제공하지 않습니다. 소스 차이가 발견되면 그 버전의 실제 실행 순서를 우선합니다.

## 자주 남는 질문

### 제시된 CPU Region Layer는 forward delta를 이전 layer로 보내나요?

아닙니다. Backward 본문이 주석 처리돼 있어 보이는 코드만으로는 net.delta에 누적되지 않습니다.

### Region truth에서 x가 0인 box는 어떻게 해석되나요?

Truth 목록 종료 표지로 사용되므로 중심 x가 정확히 0인 유효 box와 구분할 수 없습니다.

### get_region_detections를 같은 output에 반복 호출해도 같나요?

Batch 2 flip 평균 경로가 l.output을 직접 바꾸므로 두 번째 호출이 최초 상태와 다를 수 있습니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [Darknet region_layer.c 고정 커밋 원본](https://raw.githubusercontent.com/pjreddie/darknet/f6afaabcdf85f77e7aff2ec55c020c0e297c77f9/src/region_layer.c)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [DarkNet GRU Layer는 학습 가능한가: 6개 Connected와 빈 backward]({% post_url 2022-02-23-DarkNetGRULayer %}) — DarkNet GRU 순전파의 update·reset·candidate 계산을 여섯 완전연결층으로 추적하고, 비어 있는 역전파 때문에 이 소스만으로 학습할 수 없는 한계를 짚습니다.
- [Darknet Maxpool 역전파가 index -1로 깨지는 경우: padding과 argmax 추적]({% post_url 2022-03-09-DarkNetMaxpool %}) — Darknet maxpool layer의 출력 크기, padding offset, 최댓값 인덱스 저장과 backward scatter 과정을 따라가며 경계 오류를 점검합니다.
- [Darknet Normalize Layer 역전파가 정확하지 않은 이유: 채널 정규화와 delta 덮어쓰기]({% post_url 2022-03-11-DarkNetNormalizeLayer %}) — Darknet normalization_layer의 채널별 순방향 계산을 코드로 추적하고, 원본 주석이 밝힌 근사 역전파와 net.delta 덮어쓰기 문제를 점검합니다.
<!-- internal-links:end -->
