---
layout: post
title: 'eBPF XDP 훅은 패킷을 어디서 막을까: 커널 경로와 Verifier 읽기'
date: '2026-05-25 08:56:56'
categories: Tech
tags:
  - 인프라
  - AI트렌드
summary: XDP가 NIC 드라이버 가까이에서 패킷을 처리하는 위치와 PASS, DROP 반환값을 코드로 읽고, Verifier, Map, 커널 호환성과 L7 기능의 한계를 구분합니다.
description: XDP 프로그램이 NIC 드라이버 가까이에서 패킷을 처리하는 위치, 안전한 헤더 파싱과 Verifier, Map 동작을 코드로 읽고 테스트, 배포, 롤백 기준까지 설명합니다.
faq:
  - question: XDP_DROP을 반환하면 방화벽 규칙과 로그도 자동으로 남나요?
    answer: 아닙니다. 패킷은 일찍 폐기되지만 이유와 카운터를 남기려면 별도의 BPF Map, 이벤트 수집과 사용자 공간 관측기를 설계해야 합니다.
  - question: Verifier를 통과한 XDP 프로그램은 논리적으로도 안전한가요?
    answer: 아닙니다. Verifier는 메모리 접근과 종료 가능성 같은 안전성을 검사하지만 잘못된 IP를 차단하는 정책 오류까지 판별하지는 않습니다.
  - question: XDP 프로그램은 어떻게 안전하게 배포하나요?
    answer: 일반 모드에서 관측만 한 뒤 테스트 인터페이스와 canary 노드로 범위를 넓히고, 허용 트래픽 오차와 detach, 이전 경로 복구 시간을 검증해야 합니다.
github_url: https://github.com/ultraworkers/claw-code
image:
  path: https://opengraph.githubassets.com/1/ultraworkers/claw-code
  alt: "ultraworkers/claw-code GitHub 저장소 대표 이미지"
---

XDP는 NIC 드라이버 가까운 지점에서 패킷을 통과시키거나 버릴 수 있지만, 이 짧은 훅 하나가 서비스 메시 전체 기능을 대신하는 것은 아닙니다.

## XDP는 네트워크 스택의 앞단에서 결정한다

전통적인 사용자 공간 프록시는 커널이 받은 패킷을 애플리케이션 영역으로 올려 정책을 적용한 뒤 다시 커널 경로로 보냅니다. XDP 프로그램은 더 이른 수신 지점에 붙어 `XDP_PASS`, `XDP_DROP` 같은 반환값으로 다음 경로를 결정할 수 있습니다. 불필요한 패킷을 일찍 버리는 필터에서는 이 위치가 중요합니다.

여기서 “커널 훅”과 “커널 우회”를 구분해야 합니다. `XDP_PASS`를 반환하면 패킷은 이후 정상 네트워크 스택으로 진행합니다. `XDP_DROP`은 해당 패킷을 버릴 뿐 HTTP 의미나 사용자 인증을 이해하지 않습니다. XDP가 빠른 위치에 있다는 사실만으로 사용자 공간 왕복과 프록시 기능이 모두 사라지지는 않습니다.

## 코드가 보여주는 것과 숨기는 것

원문의 코드는 반환값의 원리를 보여주는 불완전한 핵심 조각입니다.

```c
#include <linux/bpf.h>
#include <bpf/bpf_helpers.h>
#include <linux/if_ether.h>

SEC("xdp")
int xdp_drop_ddos(struct xdp_md *ctx) {
    void *data_end = (void *)(long)ctx->data_end;
    void *data = (void *)(long)ctx->data;
    struct ethhdr *eth = data;

    if (data + sizeof(struct ethhdr) > data_end)
        return XDP_PASS;

    if (is_malicious_packet(eth)) {
        return XDP_DROP;
    }

    return XDP_PASS;
}

char _license[] SEC("license") = "GPL";
```

`data_end` 경계 검사는 패킷 메모리를 안전하게 읽기 위한 기본 조건이고, `SEC("xdp")`는 프로그램이 붙을 섹션을 나타냅니다. 하지만 `is_malicious_packet`이 정의되지 않아 이 상태로는 빌드되지 않습니다. Ethernet 헤더만 넘기므로 IP, 포트 정책도 없고, 정책을 담을 Map과 갱신 경로도 없습니다.

실행하려면 컴파일 대상 커널 정보, 사용자 공간 로더, 네트워크 인터페이스 attach, 권한, 테스트와 detach 절차가 더 필요합니다. 이 조각을 “DDoS 방어 설치법”이나 “사이드카 없는 메시”로 포장하면 안 되는 이유입니다.

## Verifier와 Map이 안전성과 상태를 나눈다

eBPF 프로그램은 커널에 적재되기 전에 Verifier 검사를 받습니다. 패킷 범위를 벗어난 접근, 안전성을 증명할 수 없는 제어 흐름과 포인터 사용 등이 있으면 로드를 거부합니다. 이는 커널 코드와 같은 위치에서 실행되는 프로그램의 위험을 낮추지만, 모든 논리 오류나 잘못된 정책까지 막아주는 것은 아닙니다.

정책 상태는 보통 BPF Map에 둡니다. 사용자 공간 프로그램이 차단할 키를 갱신하고, XDP 프로그램은 패킷마다 Map을 조회할 수 있습니다. Map 종류와 충돌, 메모리 한도, CPU별 구조에 따라 성능이 달라지므로 “규칙 수와 무관하게 항상 O(1)”이라고 단정할 수 없습니다.

사용 가능한 훅, BTF, CO-RE 같은 배포 기능과 드라이버 모드는 커널, 배포판, NIC 조합에 영향을 받습니다. 원문이 언급한 커널 5.x 계열은 방향을 보여줄 뿐 모든 도구의 단일 최소 버전이 아닙니다. 사용할 프로젝트가 요구하는 기능을 실제 노드 이미지에서 확인해야 합니다.

## XDP가 맞는 문제부터 작게 검증한다

초기 패킷 필터, 특정 L3/L4 정책, 네트워크 관측처럼 애플리케이션 계층을 해석하지 않아도 되는 문제가 좋은 후보입니다. 소스 수정이 어려운 레거시의 소켓 관측에는 Pixie 같은 eBPF 도구가 도움을 줄 수 있지만, 암호화된 payload와 애플리케이션 내부 문맥까지 항상 보이는 것은 아닙니다.

반대로 HTTP 헤더 변조, body 기반 정책, gRPC 재시도와 같은 L7 기능이 핵심이면 Envoy 같은 사용자 공간 프록시가 여전히 필요합니다. 실험에서는 허용한 테스트 트래픽만 대상으로 PASS, DROP 카운터와 CPU를 관찰하고, 프로그램 적재 실패, 잘못된 차단, 노드 롤백을 먼저 연습해야 합니다.

XDP를 이해하는 가장 좋은 질문은 “사이드카가 죽었는가”가 아닙니다. 패킷을 어느 지점에서 어떤 정보만 보고 결정할 수 있는지, 그 짧은 결정이 상위 계층 정책과 어디서 만나는지입니다.

## 패킷 파서는 경계를 확인한 만큼만 읽을 수 있다

XDP에서 `data`와 `data_end` 사이의 메모리는 일반 애플리케이션 버퍼처럼 자유롭게 읽을 수 없습니다. Ethernet 헤더를 읽기 전에 그 크기가 범위 안인지 확인하고, 다음 헤더로 이동할 때마다 다시 경계를 검사해야 합니다. VLAN 태그가 있으면 IPv4 헤더가 예상 위치에 없을 수 있고, IPv6와 확장 헤더도 별도 분기가 필요합니다.

IP 헤더 길이와 TCP, UDP 헤더도 고정값으로 가정하면 옵션이 있는 패킷에서 잘못된 offset을 읽습니다. fragment를 어떻게 처리할지 정하지 않으면 첫 조각에만 포트 정보가 있고 나머지 조각에는 없는 상황을 놓칠 수 있습니다. 파서가 이해하지 못한 패킷은 무조건 DROP하기보다 정책에 따라 PASS하고 상위 계층에서 처리하도록 하는 보수적 기본값이 필요합니다.

`is_malicious_packet` 같은 함수 이름은 정책을 설명하지 않습니다. 어떤 필드와 목록을 보고 차단했는지, byte order를 어디서 변환했는지, allowlist와 denylist 충돌 때 무엇이 우선인지 코드와 테스트로 드러내야 합니다. 짧은 C 코드라도 네트워크 입력을 다루는 순간 충분한 test vector가 필요한 이유입니다.

## Verifier는 정책의 옳고 그름을 보증하지 않는다

BPF Verifier는 프로그램의 가능한 실행 경로를 분석해 범위를 벗어난 메모리 접근, 초기화되지 않은 값, 종료가 증명되지 않는 반복과 허용되지 않은 helper 호출을 거부합니다. 이 덕분에 임의 커널 모듈보다 안전한 실행 경계를 만들지만, 운영 정책이 맞는지는 알 수 없습니다. 정상 고객 IP를 denylist에 넣어도 메모리 안전하면 적재될 수 있습니다.

적재 실패를 고칠 때 verifier 로그를 단순히 우회할 대상으로 보면 안 됩니다. 어느 register가 packet pointer인지, 경계 검사가 어떤 분기에서 사라졌는지 로그와 컴파일된 명령을 연결해 봐야 합니다. verifier를 통과시키려고 검사를 제거하거나 모든 예외를 PASS로 바꾸면 보안 목적이 달라질 수 있습니다.

커널 버전별 verifier 기능과 허용 helper 차이도 있습니다. 개발 노트북의 최신 커널에서 성공한 object가 오래된 운영 노드에서 적재되지 않을 수 있으므로 지원 행렬과 실제 노드 이미지에서 테스트해야 합니다. 프로그램과 loader, libbpf, clang 버전을 한 묶음으로 기록하면 문제를 재현하기 쉽습니다.

## Map에는 정책뿐 아니라 동기화 실패도 존재한다

IP 차단 목록을 BPF Map에 넣으면 프로그램을 다시 컴파일하지 않고 사용자 공간에서 정책을 바꿀 수 있습니다. 하지만 컨트롤 플레인이 일부 노드만 갱신하거나 오래된 항목을 지우지 못하면 동일한 요청이 노드마다 다르게 처리됩니다. Map schema와 최대 항목 수, update 원자성, 만료와 마지막 동기화 시각을 운영 지표로 관리해야 합니다.

패킷마다 사용자 공간 로그를 직접 보내면 성능과 유실 문제가 생길 수 있습니다. 우선 Map counter로 PASS, DROP 수를 집계하고, 자세한 사건은 ring buffer 등 제한된 채널로 샘플링하는 구성이 현실적입니다. 로그가 가득 찼을 때 패킷 처리까지 막지 않도록 데이터 경로와 관측 경로의 실패 정책을 분리합니다.

정책 변경에는 버전을 붙이고 canary 노드에서 예상한 test packet이 같은 결과를 내는지 확인합니다. 배포 뒤에는 노드별 정책 버전과 Map 항목 수를 비교해 drift를 찾습니다. 삭제된 정책이 실제 Map에서 사라졌는지도 점검해야 오래된 차단이 남지 않습니다.

## 성능 평가는 native, generic, offload 모드를 구분한다

XDP가 실행되는 방식은 드라이버 지원에 따라 달라질 수 있습니다. native 모드, 일반 네트워크 스택에 가까운 generic 모드, 지원 NIC의 offload 모드를 같은 ‘XDP 결과’로 합치면 비교가 왜곡됩니다. attach 모드와 NIC, 드라이버, queue 설정, CPU affinity를 결과 옆에 기록해야 합니다.

테스트에서는 packet per second만 보지 말고 허용 트래픽 지연, CPU 사용량, drop 정확도와 관측 유실률을 함께 봅니다. 작은 고정 패킷으로 만든 최대 처리량이 실제 혼합 트래픽의 성능을 대표하지 않습니다. IPv4, IPv6, VLAN, fragment, 잘린 패킷과 경계 크기의 입력을 넣어 파서가 안전한 기본 경로를 택하는지 확인합니다.

운영 확대 전에는 잘못된 정책을 적용해 canary 노드에서만 탐지, 롤백하는 연습을 합니다. 프로그램을 detach했을 때 정상 네트워크 경로로 돌아오는지, loader 장애 뒤 재부팅 시 어떤 버전이 붙는지, SSH 같은 관리 트래픽을 보존하는 비상 allowlist가 있는지도 확인해야 합니다.

## XDP와 상위 계층 정책을 연결하는 방법

XDP는 수신 초기에 명확히 불필요한 패킷을 줄이는 데 집중시키고, 연결 상태, 애플리케이션 신원, HTTP 문맥이 필요한 판단은 TC, socket 계층이나 사용자 공간으로 넘기는 편이 이해하기 쉽습니다. 같은 정책을 여러 훅에 중복 구현하면 어느 지점에서 차단됐는지 찾기 어려워집니다.

정책 문서에는 각 결정에 필요한 정보와 담당 훅을 적습니다. 출발지 주소와 프로토콜만으로 충분한 대량 차단은 XDP 후보이고, 사용자 권한이나 요청 경로가 필요하면 L7 계층의 일입니다. 이 경계를 지키면 XDP의 빠른 위치를 활용하면서도 커널 코드에 애플리케이션 규칙을 과도하게 넣지 않을 수 있습니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [공식 GitHub 저장소](https://github.com/ultraworkers/claw-code)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [Cilium eBPF로 kube-proxy를 바꿀 때: iptables 병목, Hubble, L7 경계]({% post_url 2026-05-25-The-End-of-the-Sidecar-Era-How-eBPF-is-Rewiring-Kubernetes-Networking-from-the-Kernel-Up %}) — Kubernetes 서비스, 정책 경로를 Cilium eBPF 데이터 플레인으로 옮길 때의 Map, 소켓 경로와 Hubble 관측성을 살펴보고, L7 프록시와 커널 운영 조건을 점검합니다.
- [eBPF 프로그램을 운영에 올리려면: 훅 선택, CO-RE, 런타임 보안]({% post_url 2026-05-28-The-End-of-the-Sidecar-Pattern-A-10-Year-Engineers-Deep-Dive-into-eBPF-and-Kernel-Level-Revolution %}) — XDP, 시스템 콜 추적, 런타임 보안처럼 목적이 다른 eBPF 훅을 구분하고, Verifier, JIT, CO-RE, 커널 호환성과 운영 롤백을 하나의 수명주기로 정리합니다.
- [eBPF를 처음 도입할 때 무엇을 확인할까: 훅, Verifier, Map 입문]({% post_url 2026-05-27-Hacking-the-Kernel-without-Reboot-A-10-Year-Backend-Engineers-Deep-Dive-into-the-Insane-Potential-of-eBPF %}) — eBPF 프로그램이 커널 훅에서 실행되고 Verifier를 거쳐 BPF Map으로 유저 공간과 통신하는 원리를 살펴본 뒤 직접 개발과 도구 도입의 경계를 정리합니다.
<!-- internal-links:end -->

## 자주 묻는 질문

### XDP_DROP을 반환하면 방화벽 규칙과 로그도 자동으로 남나요?

아닙니다. 패킷은 일찍 폐기되지만 이유와 카운터를 남기려면 별도의 BPF Map, 이벤트 수집과 사용자 공간 관측기를 설계해야 합니다.

### Verifier를 통과한 XDP 프로그램은 논리적으로도 안전한가요?

아닙니다. Verifier는 메모리 접근과 종료 가능성 같은 안전성을 검사하지만 잘못된 IP를 차단하는 정책 오류까지 판별하지는 않습니다.

### XDP 프로그램은 어떻게 안전하게 배포하나요?

일반 모드에서 관측만 한 뒤 테스트 인터페이스와 canary 노드로 범위를 넓히고, 허용 트래픽 오차와 detach, 이전 경로 복구 시간을 검증해야 합니다.

## 참고 자료

- [cilium.io 원문](https://cilium.io/)
- [ebpf.io 원문](https://ebpf.io/)
- [GitHub 저장소](https://github.com/iovisor/bcc)
- [px.dev 원문](https://px.dev/)
