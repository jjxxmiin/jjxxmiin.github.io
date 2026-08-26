---
layout: post
title: '사이드카를 없애도 될까: eBPF 서비스 메시의 경계와 선택 기준'
date: '2026-05-29 08:55:23'
categories: Tech
tags:
  - 인프라
  - 튜토리얼
  - AI에이전트
summary: 'eBPF·Cilium이 파드별 프록시의 L3/L4 역할을 어디까지 줄일 수 있는지 살펴보고, mTLS·L7 라우팅·관측 요구에 따라 사이드카 유지 여부를 판단합니다.'
description: 'eBPF 서비스 메시가 사이드카의 L3/L4 기능을 대체하는 범위와 mTLS·L7 프록시가 남는 조건을 비교해 워크로드별 선택 기준과 파일럿 지표를 정리합니다.'
github_url: https://github.com/Hmbown/CodeWhale
faq:
  - question: 'eBPF를 도입하면 Envoy 같은 프록시를 완전히 없앨 수 있나요?'
    answer: '항상 그렇지는 않습니다. L3/L4 라우팅과 정책은 커널 경로로 옮길 수 있지만 HTTP 헤더 라우팅, 일부 mTLS·L7 관측에는 사용자 공간 프록시가 남을 수 있습니다.'
  - question: '사이드카가 많은 클러스터는 바로 eBPF 메시로 바꾸는 게 좋나요?'
    answer: '현재 병목과 필요한 L7 기능을 먼저 측정해야 합니다. 대표 서비스에서 자원·지연·정책 동등성과 장애 대응을 비교한 뒤 워크로드별로 점진 적용하세요.'
  - question: '사이드카 없는 메시의 가장 큰 운영 위험은 무엇인가요?'
    answer: '패킷 경로와 정책 상태가 커널·BPF Map으로 이동해 기존 도구만으로 장애를 보기 어려워지는 점입니다. 새 관측 도구와 우회·복귀 절차를 먼저 준비해야 합니다.'
image:
  path: https://opengraph.githubassets.com/1/Hmbown/CodeWhale
  alt: "Hmbown/CodeWhale GitHub 저장소 대표 이미지"
---

eBPF 기반 네트워킹은 파드마다 프록시를 두는 비용을 줄일 수 있지만, 서비스 메시의 모든 기능을 커널로 옮기는 것은 아닙니다. L3/L4 전달·정책은 eBPF가 잘 맡고, HTTP 의미를 해석하는 L7 기능은 사용자 공간 프록시가 남을 수 있습니다. 따라서 ‘사이드카 종말’보다 워크로드별 기능 경계를 먼저 그려야 합니다.

이 글은 [Cilium 문서](https://cilium.io/docs/), [eBPF 소개](https://ebpf.io/)와 [Linux BPF 문서](https://docs.kernel.org/bpf/index.html)를 바탕으로 아키텍처 선택 기준을 정리합니다. 구체적인 지원 기능과 커널 요구 조건은 설치하려는 Cilium·Linux 버전에서 다시 확인해야 합니다.

## 사이드카는 왜 있었고 어떤 비용을 만드는가?

사이드카 프록시는 애플리케이션을 수정하지 않고도 서비스 발견, mTLS, 재시도, L7 라우팅과 관측을 동일한 데이터 플레인에서 적용합니다. 각 파드와 함께 배포되므로 정책 버전과 프록시 생명주기를 워크로드에 가깝게 관리할 수 있습니다. 이 격리와 일관성은 단순한 낭비가 아니라 패턴의 장점입니다.

비용은 파드 수에 따라 복제됩니다. 프록시 프로세스의 메모리와 CPU, 애플리케이션과 프록시 사이의 소켓·커널 경로, 시작·종료 순서와 readiness가 운영 대상이 됩니다. 트래픽이 적은 파드도 기본 자원을 예약하고, 프록시가 준비되지 않으면 애플리케이션이 떠 있어도 통신이 지연될 수 있습니다. 다만 실제 오버헤드는 프록시 설정, 연결 수, 암호화와 관측 수준에 따라 달라 고정 수치로 일반화하면 안 됩니다.

먼저 파드별 sidecar RSS·CPU, 요청 p50·p95·p99 지연, 재시작과 readiness 지연, 프록시 관련 오류를 분리해 측정하세요. 애플리케이션 자체가 병목인데 프록시만 제거하면 복잡성은 늘고 성능은 거의 바뀌지 않을 수 있습니다.

## eBPF가 대체하는 경로와 남는 L7 경계는?

eBPF 프로그램은 검증을 거쳐 커널의 네트워크 hook에서 실행되고 BPF Map을 통해 정책·엔드포인트 상태를 조회할 수 있습니다. Cilium 같은 구현은 이 능력으로 서비스 로드밸런싱, L3/L4 네트워크 정책과 관측의 일부를 파드별 프록시보다 앞선 경로에서 처리합니다. 데이터 플레인 상태를 노드 수준에서 공유하므로 같은 기능을 모든 파드에 복제하는 비용을 줄일 수 있습니다.

그러나 HTTP path·header 기반 라우팅, 복잡한 gRPC 처리와 일부 mTLS 동작은 암호화된 애플리케이션 프로토콜을 이해해야 합니다. 이런 기능은 커널의 빠른 packet path만으로 완결되지 않고 node-level 또는 다른 형태의 사용자 공간 프록시를 사용할 수 있습니다. ‘sidecarless’는 프록시가 완전히 사라진다는 뜻이 아니라 프록시 배치와 통과 조건이 달라진다는 뜻으로 읽어야 합니다.

| 요구 기능 | eBPF 경로의 적합성 | 별도 프록시를 검토할 조건 |
| :--- | :--- | :--- |
| 서비스 전달·L4 정책 | 엔드포인트·identity 기반 처리에 적합 | 특수 네트워크 장비와 호환이 필요할 때 |
| HTTP header·path 라우팅 | 정책에 따라 일부 연계 가능 | 고급 L7 변환·필터·재시도가 핵심일 때 |
| mTLS | 구현의 암호화 경계 확인 필요 | 워크로드 identity·인증서 동작이 기존 메시와 달라질 때 |
| 관측 | flow·drop 이유 파악에 유용 | 애플리케이션 내부 span·비즈니스 의미가 필요할 때 |

기능 목록의 체크 표시만 비교하지 말고 실패 의미를 확인합니다. 재시도와 circuit breaking의 위치가 달라지면 장애 때 트래픽 증폭과 timeout이 달라지고, node-level 프록시의 장애 범위는 pod-level 프록시와 다릅니다.

## XDP 예시는 서비스 메시 코드가 아닌 이유는?

원문에 있던 다음 조각은 XDP에서 packet 경계를 확인하고 Map 후보를 조회하는 개념용 의사코드입니다. `ip_header`와 Map 선언 등이 생략돼 그대로 빌드할 수 없으며, 특정 IP drop은 서비스 메시 전체 동작을 구현하지 않습니다.

```c
SEC("xdp")
int xdp_drop_ddos(struct xdp_md *ctx) {
    // 1. 패킷 데이터의 시작과 끝 포인터 확보
    void *data_end = (void *)(long)ctx->data_end;
    void *data = (void *)(long)ctx->data;
    struct ethhdr *eth = data;

    // 2. 메모리 바운더리 유효성 검증
    if (data + sizeof(*eth) > data_end) {
        return XDP_PASS;
    }

    // 3. 실제 프로그램에는 IP 파싱과 Map 정의가 더 필요함
    __u32 *is_malicious = bpf_map_lookup_elem(&blacklisted_ips, &ip_header->saddr);
    if (is_malicious) {
        return XDP_DROP;
    }

    return XDP_PASS;
}
```

Verifier는 메모리 범위와 제어 흐름을 검사해 허용하지 않는 프로그램의 적재를 거부하지만, 통과한 로직이 운영 정책상 옳다는 뜻은 아닙니다. 잘못된 IP key, 오래된 Map 또는 과도한 drop 조건도 안전하게 빠르게 실행될 수 있습니다. 프로그램 검증, 정책 테스트와 배포 승인을 별도로 둬야 합니다.

서비스 메시에서는 XDP 하나보다 여러 hook, user-space agent, control plane과 프록시가 함께 작동합니다. 장애 조사 때 어느 계층이 packet을 처리했는지 확인할 수 있어야 하며, 단순 코드 예시의 빠른 경로를 전체 서비스 지연 수치로 확대해서는 안 됩니다.

## 워크로드별로 어떤 선택이 합리적인가?

L4 내부 API, 높은 파드 밀도와 단순한 네트워크 정책이 중심이면 eBPF 경로의 이점이 큽니다. 반대로 header 변환, 복잡한 traffic shaping과 애플리케이션별 proxy filter가 핵심이면 기존 sidecar 또는 node-level L7 프록시가 더 명확할 수 있습니다. 같은 클러스터에서도 두 유형을 나누는 혼합 구성이 가능합니다.

판단표에는 현재 기능을 ‘사용 중’과 ‘설치만 됨’으로 구분하세요. 기존 메시가 제공하지만 실제 어떤 팀도 쓰지 않는 기능 때문에 전환을 막을 필요는 없고, 반대로 소수 결제 서비스가 의존하는 재시도·mTLS 동작을 평균 사용량으로 지워서는 안 됩니다. 서비스별로 인증, routing, telemetry, resilience와 정책 소유자를 적습니다.

운영 인력도 기능입니다. `iptables`와 Envoy log에는 익숙하지만 `bpftool`, Cilium 상태와 flow 관측을 해석할 수 없다면 장애 평균 복구 시간이 늘 수 있습니다. 파일럿 전에 runbook, 권한, 대시보드와 escalation 경로를 준비하고 온콜 훈련에서 drop·Map 불일치·node agent 장애를 재현하세요.

## 파일럿은 무엇을 같은 조건에서 비교해야 하는가?

대표적인 L4 중심 서비스와 L7 기능을 많이 쓰는 서비스를 하나씩 고릅니다. 동일한 요청·연결 수, 정책과 암호화 조건에서 기존 sidecar와 후보 구성을 비교합니다. 애플리케이션 CPU와 별도로 proxy·node agent CPU, pod·node 메모리, 첫 연결과 p99 지연, policy update 반영 시간, error·retry를 기록합니다.

기능 동등성 시험에는 허용·거부 traffic, 인증서 교체, pod scale-out, node drain, control plane 단절과 proxy/agent 재시작을 포함합니다. 평균 정상 traffic만 재면 데이터 플레인 전환의 가장 비싼 실패를 놓칩니다. 관측 화면에서 한 요청이 왜 허용 또는 drop됐는지 온콜 담당자가 설명할 수 있는지도 합격 조건입니다.

새 구성이 빠르더라도 필요한 L7 정책이 빠지거나 장애 격리가 나빠지면 전환하지 않습니다. 전체 클러스터의 ‘sidecar 0개’를 목표로 삼기보다 기능과 비용이 맞는 workload부터 선택하고, sidecar가 필요한 예외를 공식적으로 지원하세요. 그래야 eBPF가 새 교리가 아니라 실제 비용을 줄이는 도구가 됩니다.

비교 결과는 서비스 유형별 결정 기록으로 남깁니다. 어떤 traffic이 커널 경로를 쓰고 어떤 요청이 L7 proxy를 통과하는지, mTLS의 인증서와 identity를 어느 component가 책임지는지, 장애 때 우회 가능한 경로를 함께 그립니다. 팀이 ‘sidecarless’라는 이름만 보고 모든 요청이 같은 빠른 경로를 탄다고 가정하지 않게 하는 문서입니다.

비용도 pod resource 감소만 계산하지 않습니다. node agent와 proxy의 여유 자원, flow 저장소, 새 dashboard·교육과 game day 시간을 포함하고 현재 sidecar 운영비와 같은 기간으로 비교하세요. 작은 파드가 많은 cluster에서는 절감이 클 수 있지만 L7 traffic이 집중된 node에서는 node-level proxy 증설이 필요할 수 있습니다. 절감이 특정 peak나 장애 격리를 희생해 얻어진 것은 아닌지 함께 확인합니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [공식 GitHub 저장소](https://github.com/Hmbown/CodeWhale)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [Istio 사이드카를 없애도 될까: eBPF 서비스 메시와 L7 하이브리드 조건]({% post_url 2026-05-26-Time-to-Ditch-the-Sidecar-How-eBPF-is-Disrupting-Service-Mesh %}) — 파드별 Istio·Envoy 비용을 eBPF와 노드 단위 프록시로 줄일 수 있는 조건을 살펴보고, mTLS·재시도·HTTP 라우팅 때문에 남는 L7 기능과 안전한 전환 기준을 정리합니다.
- [Cilium으로 사이드카를 줄여도 될까: L4·L7 경계와 마이그레이션]({% post_url 2026-05-27-Is-the-Sidecar-Pattern-Dead-Why-eBPF-and-Cilium-Devoured-K8s-Networking %}) — Cilium이 eBPF로 쿠버네티스 네트워크와 정책을 처리하는 구조를 살펴보고, 사이드카 없는 L4 경로와 L7 프록시가 남는 지점을 구분해 이관 기준을 정리합니다.
- [eBPF는 사이드카를 어디까지 대체할까: XDP·Sockmap과 운영 비용의 경계]({% post_url 2026-05-24-The-End-of-the-Sidecar-Era-How-eBPF-Hacks-the-Kernel-to-Dominate-Infrastructure %}) — 사이드카의 사용자 공간 경로를 eBPF의 XDP·Sockmap·BPF Map으로 옮길 때 줄어드는 비용과 그대로 남는 L7 기능, 커널·검증기·운영 역량의 교환을 설명합니다.
<!-- internal-links:end -->

## 자주 묻는 질문

### eBPF를 도입하면 Envoy 같은 프록시를 완전히 없앨 수 있나요?

항상 그렇지는 않습니다. L3/L4 라우팅과 정책은 커널 경로로 옮길 수 있지만 HTTP 헤더 라우팅, 일부 mTLS·L7 관측에는 사용자 공간 프록시가 남을 수 있습니다.

### 사이드카가 많은 클러스터는 바로 eBPF 메시로 바꾸는 게 좋나요?

현재 병목과 필요한 L7 기능을 먼저 측정해야 합니다. 대표 서비스에서 자원·지연·정책 동등성과 장애 대응을 비교한 뒤 워크로드별로 점진 적용하세요.

### 사이드카 없는 메시의 가장 큰 운영 위험은 무엇인가요?

패킷 경로와 정책 상태가 커널·BPF Map으로 이동해 기존 도구만으로 장애를 보기 어려워지는 점입니다. 새 관측 도구와 우회·복귀 절차를 먼저 준비해야 합니다.

## References

- [공식 문서](https://cilium.io/docs/)
- [ebpf.io 원문](https://ebpf.io/)
- [공식 문서](https://docs.kernel.org/bpf/index.html)
