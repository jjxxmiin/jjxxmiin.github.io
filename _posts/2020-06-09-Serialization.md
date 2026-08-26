---
layout: post
title:  "JSON과 Protobuf, 무엇을 골라야 하나: 직렬화 구조와 Python 예제"
summary: "데이터 구조를 저장·전송 가능한 형태로 바꾸는 직렬화의 목적과 JSON·Protocol Buffers의 차이를 주소록 예제로 설명합니다."
description: "JSON과 Protocol Buffers를 사람 가독성·스키마 계약·과거 데이터 호환성으로 비교하고 Python 주소록의 round-trip 검증과 실패 조건을 설명합니다."
image:
  path: /assets/img/thumb/Serialization.jpg
  alt: Serialization 끄적이기 대표 이미지
date:   2020-06-09 09:10 -0400
categories: Basics
tags:
  - 파이썬
  - AI코딩
faq:
  - question: "JSON과 Protobuf 중 사람이 직접 읽기 쉬운 형식은 무엇인가요?"
    answer: "JSON은 텍스트라 파일을 열어 key와 값을 확인하기 쉽습니다. Protobuf는 `.proto` 스키마와 생성된 코드를 기준으로 프로그램끼리 명확한 field 계약을 관리하는 데 초점이 있습니다."
  - question: "직렬화가 성공하면 데이터 의미도 올바른가요?"
    answer: "아닙니다. Byte나 문자열이 만들어져도 필수 값 누락, 단위 오류, 잘못된 반복 field가 남을 수 있습니다. 저장 후 다시 읽어 원본 의미와 비교하는 round-trip test가 필요합니다."
  - question: "형식을 고를 때 파일 크기만 비교하면 되나요?"
    answer: "안 됩니다. 사람이 수정할 필요, schema와 생성 코드 운영, 과거 데이터 호환, 오류 디버깅과 사용하는 언어·runtime까지 함께 판단해야 합니다."
---

사람이 직접 읽고 간단히 교환할 데이터라면 JSON이 편하고, **필드 구조를 `.proto` 스키마로 합의해 프로그램끼리 주고받으려면 Protobuf를 검토**할 수 있다. 둘의 공통 목적은 메모리 안의 데이터 구조를 파일이나 네트워크에서 다룰 수 있는 형태로 바꾸는 것이다.

선택의 핵심은 어느 형식이 절대적으로 우월한지가 아니라 보내는 쪽과 받는 쪽이 어떤 계약을 유지할 수 있는가다. 직렬화·역직렬화·validation·과거 데이터 읽기를 한 흐름으로 시험해야 한다.

```text
데이터 구조 --직렬화--> 저장·전송 형태 --역직렬화--> 데이터 구조
```

## 직렬화에서 먼저 합의할 것

직렬화는 단순히 파일 확장자를 고르는 문제가 아니다. 보내는 쪽과 받는 쪽이 다음을 같은 의미로 해석해야 한다.

- 어떤 필드가 있는가?
- 각 필드의 자료형은 무엇인가?
- 하나의 값인가, 여러 값인가?
- 값이 없을 때 어떻게 처리하는가?

JSON은 key와 value를 텍스트로 직접 표현한다. Protobuf는 `.proto` 파일에 이 계약을 먼저 적고, `protoc`로 언어별 코드를 생성해 사용한다.

## Protobuf 주소록 스키마 읽기

원문의 주소록 예제는 [공식 Python tutorial](https://developers.google.com/protocol-buffers/docs/pythontutorial)을 따른다.

```proto
syntax = "proto2";

package tutorial;

message Person {
  required string name = 1;
  required int32 id = 2;
  optional string email = 3;

  enum PhoneType {
    MOBILE = 0;
    HOME = 1;
    WORK = 2;
  }

  message PhoneNumber {
    required string number = 1;
    optional PhoneType type = 2 [default = HOME];
  }

  repeated PhoneNumber phones = 4;
}

message AddressBook {
  repeated Person people = 1;
}
```

`required`는 값이 반드시 필요하고, `optional`은 없을 수 있으며, `repeated`는 같은 형태의 값이 여러 번 들어갈 수 있다는 뜻이다. 각 필드 뒤의 `1`, `2`, `3`, `4`도 직렬화 형식의 일부이므로 단순한 표시 번호로 보면 안 된다.

Python 코드를 생성하는 당시 명령은 다음과 같다.

```text
protoc -I=. --python_out=. ./addressbook.proto
```

이 명령은 `protoc`가 설치되어 있고 현재 디렉터리에 `addressbook.proto`가 있다는 전제의 **실행 형태 예시**다. Windows 설치 파일과 환경 변수 등록은 [Protobuf releases](https://github.com/protocolbuffers/protobuf/releases)에서 운영체제에 맞는 배포본을 확인한 뒤 진행해야 한다.

## Python에서 저장하고 다시 읽는 흐름

생성된 `addressbook_pb2` 모듈을 import하면 `.proto`에 선언한 메시지를 Python 객체처럼 채울 수 있다.

```python
import addressbook_pb2

address_book = addressbook_pb2.AddressBook()
person = address_book.people.add()
person.id = 1
person.name = 'JJM'
person.email = 'jjm@example.com'

phone = person.phones.add()
phone.number = '010-0000-0000'
phone.type = addressbook_pb2.Person.PhoneType.MOBILE

with open('person.data', 'wb') as file:
    file.write(address_book.SerializeToString())
```

읽을 때는 같은 스키마에서 생성된 클래스를 만들고 byte를 파싱한다.

```python
import addressbook_pb2

address_book = addressbook_pb2.AddressBook()

with open('person.data', 'rb') as file:
    address_book.ParseFromString(file.read())

for person in address_book.people:
    print('Person ID:', person.id)
    print('Name:', person.name)
    if person.HasField('email'):
        print('E-mail:', person.email)

    for phone in person.phones:
        print('Phone:', phone.number)
```

원문의 `writing.py`와 `reading.py`는 명령행에서 파일 경로를 받아 주소록 전체를 읽고 한 사람을 추가한 뒤 다시 저장하는 구조였다. 핵심은 text 모드가 아니라 `rb`·`wb`로 열고, `SerializeToString`과 `ParseFromString`을 서로 짝지어 쓰는 것이다.

이 코드는 `addressbook_pb2.py`가 이미 생성됐다는 전제의 핵심 예제다. 스키마가 다른 코드로 같은 파일을 읽을 수 있다고 가정하면 안 된다. 값을 추가하기 전에 어떤 `.proto`에서 생성한 코드인지 함께 관리해야 한다.

## JSON은 무엇이 단순하고 무엇을 조심해야 하나

JSON object는 중괄호, array는 대괄호를 사용한다.

```json
{
  "name": "JJM",
  "age": 26,
  "phones": [
    {"type": "mobile", "number": "010-0000-0000"},
    {"type": "work", "number": "02-0000-0000"}
  ]
}
```

JavaScript에서는 객체를 문자열로 만들 때 `JSON.stringify`, 문자열을 객체로 되돌릴 때 `JSON.parse`를 사용한다.

```javascript
const person = {
  name: 'JJM',
  age: 26
};

const jsonText = JSON.stringify(person);
const restored = JSON.parse(jsonText);
```

JSON은 내용을 바로 읽기 쉽지만, 문서 자체만으로 모든 필드의 필수 여부와 타입 규칙을 강제하는 것은 아니다. Protobuf는 스키마가 명시적이지만 `.proto` 작성, 코드 생성, 스키마 관리 단계가 추가된다.

선택할 때는 “어느 형식이 무조건 더 좋은가”보다 다음을 묻는 편이 낫다.

- 사람이 파일을 자주 열어 확인하고 수정해야 하는가?
- 보내는 쪽과 받는 쪽이 같은 스키마와 생성 코드를 관리할 수 있는가?
- 필드가 없거나 여러 번 들어오는 상황을 어디에서 검증할 것인가?
- 저장된 과거 데이터를 새 코드에서도 읽어야 하는가?

직렬화 성공은 byte나 문자열이 만들어졌다는 뜻일 뿐, 의미가 올바르다는 보장은 아니다. 저장 후 즉시 역직렬화해 필수 필드와 반복 필드를 확인하는 round-trip 테스트가 가장 작은 안전장치다.

## 주소록 예제로 데이터 계약을 적는 법

먼저 한 사람을 표현하는 field와 주소록에서 여러 사람이 반복되는 구조를 문장으로 적는다. 이름·ID·이메일처럼 각 값의 타입과 필수 여부, 빈 값 처리, 중복 허용 여부를 정한다. 코드부터 쓰면 형식은 맞아도 업무 규칙이 서로 다를 수 있다.

Protobuf에서는 `.proto`를 계약의 출발점으로 두고 사용하는 언어의 코드를 생성한다. 생성된 class의 field에 값을 넣고 주소록 message에 추가한 뒤 binary로 저장한다. 읽는 쪽도 같은 schema 계열에서 생성된 코드를 사용해야 각 field를 같은 의미로 해석할 수 있다.

JSON에서는 object와 array로 같은 구조를 표현하고 key 이름과 값 type을 합의한다. 텍스트라 사람이 읽기 쉽지만 오타 난 key나 예상하지 않은 type을 형식 자체가 모두 막아 주는 것은 아니다. Parsing 성공 뒤 별도 validation이 필요한 이유다.

## Round-trip test에 무엇을 넣어야 하나

가장 작은 정상 주소록을 저장한 뒤 다시 읽어 사람 수와 각 field가 같은지 비교한다. 빈 주소록, 선택 값이 없는 사람, 여러 전화번호처럼 경계 사례도 넣는다. 직렬화 byte가 생성된 사실이 아니라 원래 의미가 복구되는지가 성공 기준이다.

잘린 파일, 잘못된 type, 알 수 없는 field를 받았을 때 프로그램 동작을 정한다. 예외를 내고 거부할지, 기본값으로 처리할지, 일부 레코드만 건너뛸지를 보내는 쪽과 받는 쪽이 합의해야 한다. 조용히 빈 값으로 바꾸면 데이터 손실을 늦게 발견할 수 있다.

파일에 version이나 생성 주체를 식별할 정보가 필요한지도 본다. Schema가 바뀐 뒤 과거 파일을 읽어야 한다면 새 코드로 이전 fixture를 계속 round-trip하는 회귀 test를 둔다. 새 파일만 통과하는 test로는 호환성을 알 수 없다.

## JSON이 더 단순한 경우와 위험한 경우

설정 파일이나 사람이 자주 확인하는 소규모 교환에서는 JSON의 투명성이 장점이다. Log와 diff에서 값을 직접 보고 다른 언어에서도 쉽게 구조를 만들 수 있다. 그러나 key spelling, 숫자와 문자열의 혼용, 날짜·단위 같은 의미 규칙은 별도 문서와 validation이 필요하다.

큰 object를 수동으로 수정할 때 쉼표나 중첩 오류가 날 수 있고, parsing 성공과 업무상 유효성은 다르다. 필수 key, 허용 범위, 추가 key 처리 정책을 test로 남긴다. 사람이 읽을 수 있다는 이유만으로 아무 값이나 안전하게 교환되는 것은 아니다.

## Protobuf가 맞는 경우와 운영 비용

여러 프로그램이 동일한 field 번호와 type을 장기간 공유하고 생성 코드를 관리할 수 있다면 명시적 schema가 도움이 된다. 반면 단순 파일 하나를 사람이 자주 수정해야 하는 작업에서는 binary 확인과 code generation이 추가 부담일 수 있다.

Schema 변경은 보내는 쪽만 바꾸고 끝나지 않는다. 받는 서비스의 배포 순서와 과거 message를 어떻게 읽을지 고려한다. Field 이름이 비슷하다는 이유로 type과 의미를 임의로 바꾸지 않고 호환 test를 먼저 만든다.

## 성능 비교를 공정하게 하는 법

같은 데이터 수와 field, 같은 언어 환경에서 serialize·parse 시간과 결과 크기를 잰다. 파일 I/O와 변환 시간, 첫 초기화와 반복 실행을 구분한다. 작은 샘플 한 번으로 전체 시스템의 선택을 결론 내리지 않는다.

성능 차이가 있어도 디버깅, schema 배포와 사람 검토 비용을 함께 본다. 형식 변환이 전체 요청 시간의 작은 일부라면 더 단순한 운영이 중요할 수 있고, 대량 message가 병목이라면 측정 결과의 비중이 커질 수 있다.

벤치마크는 같은 의미의 데이터를 같은 횟수로 encode와 decode하고, 준비 시간과 실제 직렬화 시간을 구분합니다. 작은 예제 하나의 파일 크기만으로 결론 내리지 말고 반복되는 메시지 크기와 읽기·쓰기 비율을 실제 사용 조건에 맞춥니다. 스키마 변경 뒤 오래된 데이터를 읽는 호환성 시험이 빠지면 빠른 형식도 운영에서는 선택하기 어렵습니다.

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [PPT Master: AI가 슬라이드 통이미지 대신 진짜 수정 가능한 파워포인트를 만드는 방법]({% post_url 2026-08-13-PPT-Master-Generating-Natively-Editable-PowerPoint-Presentations-with-AI %}) — PPT Master는 PDF, 마이그레이션 문서, 텍스트 등을 수정 가능한 고품질 파워포인트(.pptx) 파일로 변환해 주는 오픈소스 AI 프레젠테이션 자동화 도구입니다. 기존 AI 도구들이 슬라이드를 수정 불가능한 통이미지로 만들던…
- [PEP 8, 어디까지 지켜야 하나: 코드 리뷰에서 자주 걸리는 12가지 규칙]({% post_url 2019-12-20-pep8 %}) — 들여쓰기와 줄바꿈부터 import, 공백, 이름, 조건문까지 Python 코드를 읽기 쉽게 만드는 PEP 8 핵심을 예제로 정리합니다.
- [Python 데코레이터와 매직 메서드 차이: 함수 실행과 연산자를 바꾸는 법]({% post_url 2020-01-07-DecoratorMagicMethod %}) — @decorator가 중복 실행 로직을 감싸는 방식과 __add__ 같은 매직 메서드가 연산자의 동작을 정하는 원리를 예제로 비교합니다.
<!-- internal-links:end -->

## 자주 묻는 질문

### JSON과 Protobuf 중 사람이 직접 읽기 쉬운 형식은 무엇인가요?

JSON은 텍스트라 파일을 열어 key와 값을 확인하기 쉽습니다. Protobuf는 `.proto` 스키마와 생성된 코드를 기준으로 프로그램끼리 명확한 field 계약을 관리하는 데 초점이 있습니다.

### 직렬화가 성공하면 데이터 의미도 올바른가요?

아닙니다. Byte나 문자열이 만들어져도 필수 값 누락, 단위 오류, 잘못된 반복 field가 남을 수 있습니다. 저장 후 다시 읽어 원본 의미와 비교하는 round-trip test가 필요합니다.

### 형식을 고를 때 파일 크기만 비교하면 되나요?

안 됩니다. 사람이 수정할 필요, schema와 생성 코드 운영, 과거 데이터 호환, 오류 디버깅과 사용하는 언어·runtime까지 함께 판단해야 합니다.
