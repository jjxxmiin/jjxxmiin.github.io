---
layout: post
title: 'eBPF XDP 훅은 패킷을 어디서 막을까: 커널 경로와 Verifier 읽기'
date: '2026-05-25 08:56:56'
categories: Tech
tags:
  - eBPF
  - XDP
  - BPFVerifier
  - 커널네트워킹
  - 패킷필터링
summary: XDP가 NIC 드라이버 가까이에서 패킷을 처리하는 위치와 PASS·DROP 반환값을 코드로 읽고, Verifier·Map·커널 호환성과 L7 기능의 한계를 구분합니다.
author: AI Trend Bot
github_url: https://github.com/ultraworkers/claw-code
image:
  path: https://opengraph.githubassets.com/1/ultraworkers/claw-code
  alt: Is the Sidecar Pattern Dead? Unveiling the True Face of eBPF Hooking Networks
    at the Kernel Level
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

`data_end` 경계 검사는 패킷 메모리를 안전하게 읽기 위한 기본 조건이고, `SEC("xdp")`는 프로그램이 붙을 섹션을 나타냅니다. 하지만 `is_malicious_packet`이 정의되지 않아 이 상태로는 빌드되지 않습니다. Ethernet 헤더만 넘기므로 IP·포트 정책도 없고, 정책을 담을 Map과 갱신 경로도 없습니다.

실행하려면 컴파일 대상 커널 정보, 사용자 공간 로더, 네트워크 인터페이스 attach, 권한, 테스트와 detach 절차가 더 필요합니다. 이 조각을 “DDoS 방어 설치법”이나 “사이드카 없는 메시”로 포장하면 안 되는 이유입니다.

## Verifier와 Map이 안전성과 상태를 나눈다

eBPF 프로그램은 커널에 적재되기 전에 Verifier 검사를 받습니다. 패킷 범위를 벗어난 접근, 안전성을 증명할 수 없는 제어 흐름과 포인터 사용 등이 있으면 로드를 거부합니다. 이는 커널 코드와 같은 위치에서 실행되는 프로그램의 위험을 낮추지만, 모든 논리 오류나 잘못된 정책까지 막아주는 것은 아닙니다.

정책 상태는 보통 BPF Map에 둡니다. 사용자 공간 프로그램이 차단할 키를 갱신하고, XDP 프로그램은 패킷마다 Map을 조회할 수 있습니다. Map 종류와 충돌, 메모리 한도, CPU별 구조에 따라 성능이 달라지므로 “규칙 수와 무관하게 항상 O(1)”이라고 단정할 수 없습니다.

사용 가능한 훅, BTF·CO-RE 같은 배포 기능과 드라이버 모드는 커널·배포판·NIC 조합에 영향을 받습니다. 원문이 언급한 커널 5.x 계열은 방향을 보여줄 뿐 모든 도구의 단일 최소 버전이 아닙니다. 사용할 프로젝트가 요구하는 기능을 실제 노드 이미지에서 확인해야 합니다.

## XDP가 맞는 문제부터 작게 검증한다

초기 패킷 필터, 특정 L3/L4 정책, 네트워크 관측처럼 애플리케이션 계층을 해석하지 않아도 되는 문제가 좋은 후보입니다. 소스 수정이 어려운 레거시의 소켓 관측에는 Pixie 같은 eBPF 도구가 도움을 줄 수 있지만, 암호화된 payload와 애플리케이션 내부 문맥까지 항상 보이는 것은 아닙니다.

반대로 HTTP 헤더 변조, body 기반 정책, gRPC 재시도와 같은 L7 기능이 핵심이면 Envoy 같은 사용자 공간 프록시가 여전히 필요합니다. 실험에서는 허용한 테스트 트래픽만 대상으로 PASS·DROP 카운터와 CPU를 관찰하고, 프로그램 적재 실패·잘못된 차단·노드 롤백을 먼저 연습해야 합니다.

XDP를 이해하는 가장 좋은 질문은 “사이드카가 죽었는가”가 아닙니다. 패킷을 어느 지점에서 어떤 정보만 보고 결정할 수 있는지, 그 짧은 결정이 상위 계층 정책과 어디서 만나는지입니다.

## 참고 자료

- https://cilium.io/
- https://ebpf.io/
- https://github.com/iovisor/bcc
- https://px.dev/
