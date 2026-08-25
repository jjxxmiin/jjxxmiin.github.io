---
layout: post
title:  "Darknet utils.c 이름만 믿으면 틀리는 7곳: mse_array는 MSE가 아니다"
summary: "Darknet utils.c의 CLI 파서·문자열·파일·CSV·난수·배열 helper를 기능별로 정리하고, 함수 이름과 실제 동작이 다른 부분과 범위·0 나눗셈·입력 변경 위험을 짚습니다."
date:   2022-03-22 16:00 -0400
categories: DarkNet
image:
  path: /assets/img/thumb/DarkNetUtils.jpg
  alt: DarkNet 시리즈 - Utils 대표 이미지
tags:
  - DarkNet
  - C언어
  - 아키텍처분석
  - 컴퓨터비전
math: true
---

Darknet `utils.c`를 포팅할 때는 함수 이름보다 배열을 직접 바꾸는지, 범위와 0을 검사하는지부터 봐야 하며, 특히 `mse_array`는 MSE가 아니라 root mean square를 반환합니다.

원문은 수십 개 helper를 사전처럼 나열하지만 실제 문제는 짧은 코드의 숨은 전제에서 생깁니다. 이 글은 CLI, 문자열·파일, CSV, 배열·난수로 묶어 코드에서 바로 확인되는 위험 지점을 추립니다. 모든 조각은 Darknet의 list·error helper와 C runtime을 전제로 하며 독립 라이브러리가 아닙니다.

## CLI Parser는 argv를 읽기만 하지 않습니다

`find_arg`, `find_int_arg`, `find_float_arg`, `find_char_arg`는 값을 찾은 뒤 `del_arg`로 해당 항목을 제거합니다. `argc` 자체는 줄이지 않고 배열을 앞으로 당긴 뒤 마지막을 null로 둡니다.

```c
if(0==strcmp(argv[i], arg)){
    def = atoi(argv[i+1]);
    del_arg(argc, argv, i);
    del_arg(argc, argv, i);
    break;
}
```

같은 `argv`를 두 parser가 순서대로 볼 때 첫 parser가 배열을 바꿨다는 점을 고려해야 합니다. 값이 필요한 option은 `argc-1`까지만 순회해 끝의 dangling option을 피하지만, 문자열을 `atoi/atof`로 바꿀 때 유효성 검사를 하지 않습니다.

`read_intlist`도 쉼표 개수로 배열 크기를 정한 뒤 `atoi`와 `strchr`를 사용합니다. 잘못된 쉼표 형식이나 숫자가 아닌 값에 대한 명시적 오류가 없고, 기본 branch는 int 배열인데 `sizeof(float)`로 할당합니다. 흔한 환경에서 크기가 같더라도 타입 계약은 잘못 적혀 있습니다.

더 직접적인 인덱스 문제는 `random_index_order`입니다. 배열은 `max-min`개만 할당하지만 loop는 `inds[i]`에 `i=min...max-1`로 씁니다. `min=0`이 아닐 때 시작부터 배열 offset과 맞지 않으므로 이 조각을 그대로 일반 구간 shuffle로 사용하면 안 됩니다.

## 문자열·파일 Helper는 소유권과 종료 코드를 봅니다

`split_str`은 구분자를 null 문자로 바꾸므로 입력 문자열 자체를 훼손하고, 반환 list의 항목은 그 원본 buffer 안을 가리킵니다. 반면 `copy_string`과 `fgetl`은 새 메모리를 반환하므로 호출자가 해제해야 합니다. 비슷한 문자열 반환 함수라도 소유권이 다릅니다.

`find_replace`는 4096 byte 고정 buffer와 `sprintf`를 사용하고 첫 번째 일치 항목만 바꿉니다. 긴 입력과 output buffer 크기를 검사하지 않습니다. `basecfg`는 마지막 점이 아니라 basename에서 처음 만난 점부터 잘라내므로 점이 여러 개인 파일명은 예상보다 짧아질 수 있습니다.

파일 오류 처리도 일관적이지 않습니다. `error`와 `malloc_error`는 실패 코드로 종료하지만 `file_error`는 파일을 열지 못해도 `exit(0)`을 호출합니다. 자동화에서는 성공으로 오인될 수 있습니다. `write_int`가 쓰기 실패 시 `"read failed"` 메시지를 내는 것도 진단 로그를 헷갈리게 합니다.

## CSV Parser는 완전한 CSV 구현이 아닙니다

`parse_csv_line`은 큰따옴표 안의 쉼표를 건너뛰지만 quote를 제거하거나 escaped quote를 처리하는 코드는 없습니다. 구분 쉼표를 null로 바꾸며 field 문자열을 복사해 list에 넣습니다.

`parse_fields`는 각 field를 `strtod`로 바꾸고 빈 값이나 남은 문자가 있으면 NaN으로 둡니다. DOS 줄끝의 `\r`만 예외로 인정합니다. 하지만 실제 field 개수가 인자 `n`보다 많은지 검사하지 않고 `field[count]`를 계속 씁니다. 먼저 `count_fields` 결과와 할당 크기를 맞춰야 합니다.

이 함수들도 입력 line의 쉼표를 null로 바꾸므로 같은 문자열을 다시 파싱하려면 복사본이 필요합니다. “parse”가 원본을 보존한다는 가정을 버리는 편이 안전합니다.

## 배열 함수는 0과 범위를 호출자가 보장합니다

이름이 가장 오해를 부르는 코드는 다음과 같습니다.

```c
float mse_array(float *a, int n)
{
    int i;
    float sum = 0;
    for(i = 0; i < n; ++i) sum += a[i]*a[i];
    return sqrt(sum/n);
}
```

제곱 평균에 제곱근까지 취하므로 RMS입니다. 두 배열의 prediction error를 받는 함수도 아니며, 모든 값이 같은 nonzero 상수라고 0이 되지도 않습니다. `normalize_array`는 표준편차가 0일 때 나눗셈을 막지 않고, `mean_array`는 `n=0`을 검사하지 않습니다.

`sample_array`는 합으로 배열 전체를 나눠 확률화하므로 입력 `a`를 직접 변경합니다. 합이 0이거나 음수 값이 섞인 경우를 검사하지 않습니다. `one_hot_encode`도 `(int)a[i]`가 `0...k-1`인지 확인하지 않고 바로 index로 씁니다.

`rand_int`와 `rand_uniform`은 min·max 순서가 반대면 교환하지만 암호학적 난수 함수가 아닙니다. `rand_normal`은 Box–Muller 변환의 두 번째 값을 static 변수에 보관합니다. 재현성과 동시 접근 요구가 있다면 외부 seed와 호출 모델까지 함께 관리해야 합니다.

실용적인 검증 순서는 mutation, bounds, empty input, allocation ownership입니다. 각 helper에 정상값 하나만 넣는 대신 `min!=0`, `n=0`, 합이 0인 배열, 너무 긴 문자열, field 수 초과를 넣어야 이름 뒤에 숨은 전제가 드러납니다.
