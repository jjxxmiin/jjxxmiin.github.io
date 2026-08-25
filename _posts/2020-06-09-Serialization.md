---
layout: post
title:  "JSON과 Protobuf, 무엇을 골라야 하나: 직렬화 구조와 Python 예제"
summary: "데이터 구조를 저장·전송 가능한 형태로 바꾸는 직렬화의 목적과 JSON·Protocol Buffers의 차이를 주소록 예제로 설명합니다."
image:
  path: /assets/img/thumb/Serialization.jpg
  alt: Serialization 끄적이기 대표 이미지
date:   2020-06-09 09:10 -0400
categories: Basics
tags:
  - 직렬화
  - Protobuf
  - JSON
---

사람이 직접 읽고 간단히 교환할 데이터라면 JSON이 편하고, **필드 구조를 `.proto` 스키마로 합의해 프로그램끼리 주고받으려면 Protobuf를 검토**할 수 있다. 둘의 공통 목적은 메모리 안의 데이터 구조를 파일이나 네트워크에서 다룰 수 있는 형태로 바꾸는 것이다.

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
