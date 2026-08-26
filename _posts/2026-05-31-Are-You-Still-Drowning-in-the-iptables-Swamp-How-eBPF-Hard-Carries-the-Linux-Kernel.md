---
layout: post
title: 'eBPF를 이 노드에 올릴 수 있을까: 커널·BTF·Verifier 사전 점검'
date: '2026-05-31 07:08:56'
categories: Tech
tags:
  - 인프라
  - AI에이전트
summary: 'eBPF 도입 전 Linux 커널 버전만 보지 않고 필요한 hook·helper·BTF, JIT, 권한, NIC mode와 Verifier 적재를 노드별로 확인하는 절차를 정리합니다.'
description: 'eBPF 프로그램을 배포하기 전 커널 hook·helper·BTF·JIT·NIC 지원, Verifier 로그, 권한과 배포판 backport를 노드별 preflight로 확인하는 방법입니다.'
github_url: https://github.com/EveryInc/compound-engineering-plugin
faq:
  - question: 'Linux 커널 버전만 알면 eBPF 지원 여부를 판단할 수 있나요?'
    answer: '아닙니다. 배포판 backport와 build config, 필요한 hook·helper·BTF·JIT, NIC driver와 보안 정책이 달라 실제 노드에서 기능 probe와 적재 시험을 해야 합니다.'
  - question: 'Verifier를 통과하면 eBPF 프로그램이 안전한가요?'
    answer: '메모리·제어 흐름 등 커널이 검사하는 조건을 통과했다는 뜻이지 정책 로직이 옳다는 보장은 아닙니다. test packet, 범위 제한과 canary·detach 절차가 필요합니다.'
  - question: 'BCC 예제는 모든 서버에서 그대로 실행되나요?'
    answer: '아닙니다. 커널 header·compiler·BCC와 권한, 함수·interface 이름이 필요합니다. 배포판과 노드 image에 맞춰 의존성과 attach mode를 확인해야 합니다.'
image:
  path: https://opengraph.githubassets.com/1/EveryInc/compound-engineering-plugin
  alt: "EveryInc/compound-engineering-plugin GitHub 저장소 대표 이미지"
---

eBPF 도입 가능 여부는 ‘커널 5.x 이상’ 같은 한 줄로 판정할 수 없습니다. 사용할 hook과 helper, BTF·JIT, 배포판 backport, NIC driver와 보안 권한을 실제 노드에서 확인해야 합니다. Verifier 적재 시험과 안전한 detach까지 통과해야 같은 node image에 배포할 근거가 생깁니다.

이 글은 [eBPF](https://ebpf.io/), [Cilium](https://cilium.io/)과 [BCC](https://github.com/iovisor/bcc)를 참고해 kernel prerequisite와 검증 순서를 정리합니다. 특정 기능의 최소 버전은 프로젝트·배포판 문서를 확인해야 하며, 원문의 예제는 production drop 프로그램이 아니라 학습용 조각으로 읽어야 합니다.

## 커널 버전보다 어떤 기능을 먼저 목록화할까?

도입할 제품이 사용하는 program type과 attach point를 적습니다. XDP, tc, cgroup socket, tracepoint, kprobe·uprobe는 필요한 kernel 기능과 실패 영향이 다릅니다. 사용 helper, Map type, BTF·CO-RE, ring buffer와 JIT 의존성도 버전별 기능표로 만듭니다. ‘eBPF 지원’이라는 넓은 체크 하나로는 실제 프로그램 적재를 예측할 수 없습니다.

배포판 kernel은 upstream 버전 숫자가 같아도 patch와 backport가 다를 수 있습니다. 반대로 오래된 base version에 일부 기능이 backport됐을 수도 있습니다. `/boot/config` 또는 제공되는 kernel config, BTF 파일 존재, lockdown·LSM과 unprivileged BPF 설정을 node image별로 확인합니다. managed Kubernetes라면 provider가 허용하는 kernel flag와 agent 권한도 별도입니다.

NIC와 driver는 XDP mode에 영향을 줍니다. native driver mode, generic fallback 또는 hardware offload 중 무엇을 사용할지 확인하고 실제 interface·bond·virtual device에서 attach probe를 실행합니다. 기능은 동작하지만 fallback 때문에 기대한 성능이 나오지 않는 경우를 ‘지원’으로만 표시해서는 안 됩니다.

| 점검 영역 | 확인할 항목 | 실패 시 선택 |
| :--- | :--- | :--- |
| Kernel | program·Map·helper, config, JIT | 기능 축소, node image upgrade |
| Portability | BTF, CO-RE, 배포판 backport | image별 artifact 또는 재컴파일 |
| Network | NIC driver, XDP mode, MTU | tc/generic 경로 또는 지원 제외 |
| Security | capability, lockdown, LSM, seccomp | 전용 agent와 최소 권한 설계 |
| Operations | attach 목록, logs, detach·rollback | canary 전 runbook 보완 |

## eBPF 프로그램은 어떤 단계를 거쳐 적재되는가?

C나 Rust source는 compiler를 거쳐 eBPF bytecode가 되고 user-space loader가 `bpf()` system call 등으로 kernel에 요청합니다. Verifier는 register 상태, pointer 범위, stack과 제어 흐름을 분석해 허용할 수 없는 접근이 있으면 적재를 거부합니다. 통과한 program은 설정에 따라 JIT된 native code로 실행되고 지정 hook에 attach됩니다.

‘컴파일 성공’과 ‘Verifier 성공’, ‘attach 성공’을 분리해 기록하세요. compiler가 만든 object가 있어도 target kernel의 type·helper가 없으면 load가 실패하고, load돼도 interface 이름이나 권한이 맞지 않으면 attach할 수 없습니다. 각 단계의 error log와 kernel version, object hash를 수집하면 node 간 차이를 찾기 쉽습니다.

Verifier는 program의 업무 의도를 알지 못합니다. 모든 packet을 drop하는 유한한 program도 메모리 규칙을 지키면 적재될 수 있습니다. 따라서 unit·VM test, test namespace와 synthetic packet으로 정책 정확성을 검증하고 attach scope·canary node를 제한해야 합니다.

## 원문의 XDP·BCC 예제에서 특히 위험한 부분은?

다음 XDP 조각은 들어오는 모든 packet을 `XDP_DROP`으로 반환합니다. `bpf_printk` 문자열에 ‘악성’이라고 적혀 있어도 IP 판별 로직은 없습니다. 운영 interface에 attach하면 정상 traffic도 차단할 수 있으므로 격리된 veth·test namespace에서만 원리를 확인해야 합니다.

```c
#include <linux/bpf.h>
#include <bpf/bpf_helpers.h>

SEC("xdp")
int drop_malicious_ip(struct xdp_md *ctx) {
    // 학습용 조각: 현재 코드는 모든 패킷을 드롭합니다.
    bpf_printk("Drop packet at XDP hook\n");
    return XDP_DROP;
}

char _license[] SEC("license") = "GPL";
```

원문의 BCC loader 역시 `ebpf_c_code` 정의와 실제 함수 이름·오류 처리가 생략됐습니다. attach할 device를 하드코딩했고 종료 시 detach, 신호 처리와 기존 XDP program 충돌 검사도 없습니다.

```python
from bcc import BPF

# 1. 컴파일된 eBPF C 코드 바이트코드 로드
b = BPF(text=ebpf_c_code)

# 2. XDP 훅에 프로그램 부착 (테스트 인터페이스 예시)
b.attach_xdp(dev="eth0", fn=b.get_syscall_fnname("drop_malicious_ip"))

print("XDP eBPF 프로그램 적재 상태를 확인합니다.")
b.trace_print()
```

실제 loader는 기존 program ID와 attach mode를 확인하고, 실패하면 변경을 남기지 않으며, signal·timeout 때 확실히 detach해야 합니다. `eth0`가 관리 traffic interface일 수 있으므로 device 선택을 입력 검증과 승인 대상으로 둡니다. `trace_print`는 부하가 큰 경로의 production telemetry로 무제한 사용하지 않습니다.

## BTF와 CO-RE는 어떤 문제를 줄이고 무엇을 남기는가?

BTF는 kernel type 정보를 제공하고 CO-RE는 compile된 program이 target kernel 구조 차이에 맞게 relocation되는 데 도움을 줍니다. 여러 node image마다 source를 다시 빌드하는 부담을 줄일 수 있지만, target kernel에 필요한 type·field와 helper가 아예 없거나 의미가 바뀐 경우까지 해결하지는 않습니다.

build artifact에는 source commit, compiler·libbpf 버전, 요구 feature와 BTF 기준을 기록합니다. 지원하는 모든 node image의 VM 또는 실제 canary에서 load·attach·event test를 실행하고, kernel upgrade 때 회귀 suite를 다시 돌립니다. ‘한 번 compile해 어디서나’라는 문구를 기능 probe 대체로 사용하지 마세요.

BCC 방식은 runtime compile과 kernel header 의존성이 생길 수 있습니다. 학습·탐색에는 편리하지만 production agent에서는 build toolchain과 header 배포, startup 지연과 supply chain 범위를 고려해야 합니다. CO-RE object와 BCC 중 어느 방식을 쓰든 재현 가능한 artifact와 version pinning이 필요합니다.

## eBPF 권한은 어떻게 최소화할까?

program load·attach와 Map 접근에는 높은 권한이 필요할 수 있습니다. 모든 애플리케이션 pod에 넓은 capability나 host filesystem을 주지 말고 전용 node agent가 검증된 artifact만 관리하게 합니다. control plane API는 누가 어느 hook에 어떤 program을 배포할 수 있는지 RBAC와 승인으로 제한합니다.

Map에는 packet metadata, process 정보나 평문에 가까운 민감 데이터가 들어갈 수 있습니다. 수집 field와 보존 기간을 최소화하고 사용자 공간 exporter의 접근을 제한합니다. uprobe로 암호화 library 경계를 관찰할 수 있다는 가능성은 관측 장점인 동시에 기밀 노출 위험이므로 별도 보안·법적 검토가 필요합니다.

artifact 서명과 hash를 검증하고, 임의 source를 node에서 바로 compile·attach하지 않습니다. 허용 program·Map type과 interface를 정책으로 제한하며 load·attach·detach 사건을 감사 로그에 남깁니다. agent가 침해되면 kernel-level traffic과 관측이 영향을 받을 수 있으므로 node 보안 경계로 다룹니다.

## 노드 preflight와 canary 합격 기준은?

node pool별 대표 node에서 kernel config, BTF, helper·Map probe, JIT, attach mode와 권한을 자동 수집합니다. 이어서 read-only trace 또는 test interface의 pass program을 load·attach·detach해 각 단계 로그를 확인합니다. production interface의 drop·redirect program은 이 preflight에 사용하지 않습니다.

canary에서는 program load 실패, Verifier reject, Map allocation, agent restart, node reboot와 upgrade를 재현합니다. attach 뒤 network와 application health가 유지되고, agent를 제거했을 때 hook과 pinned Map이 의도한 상태로 정리되는지 봅니다. cleanup이 안 되면 이전 program이 남아 rollback 뒤에도 packet을 바꿀 수 있습니다.

노드 일부가 기능 probe에 실패하면 조용히 다른 datapath로 섞지 말고 scheduling label과 지원 matrix로 격리합니다. feature downgrade가 허용되는지, 성능과 정책이 달라지는지 명시하세요. 모든 지원 image가 load·attach·detach와 운영 관측을 통과했을 때만 전체 배포 후보가 됩니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [공식 GitHub 저장소](https://github.com/EveryInc/compound-engineering-plugin)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [eBPF 프로그램을 운영에 올리려면: 훅 선택·CO-RE·런타임 보안]({% post_url 2026-05-28-The-End-of-the-Sidecar-Pattern-A-10-Year-Engineers-Deep-Dive-into-eBPF-and-Kernel-Level-Revolution %}) — XDP·시스템 콜 추적·런타임 보안처럼 목적이 다른 eBPF 훅을 구분하고, Verifier·JIT·CO-RE·커널 호환성과 운영 롤백을 하나의 수명주기로 정리합니다.
- [eBPF XDP 훅은 패킷을 어디서 막을까: 커널 경로와 Verifier 읽기]({% post_url 2026-05-25-Is-the-Sidecar-Pattern-Dead-Unveiling-the-True-Face-of-eBPF-Hooking-Networks-at-the-Kernel-Level %}) — XDP가 NIC 드라이버 가까이에서 패킷을 처리하는 위치와 PASS·DROP 반환값을 코드로 읽고, Verifier·Map·커널 호환성과 L7 기능의 한계를 구분합니다.
- [eBPF를 처음 도입할 때 무엇을 확인할까: 훅·Verifier·Map 입문]({% post_url 2026-05-27-Hacking-the-Kernel-without-Reboot-A-10-Year-Backend-Engineers-Deep-Dive-into-the-Insane-Potential-of-eBPF %}) — eBPF 프로그램이 커널 훅에서 실행되고 Verifier를 거쳐 BPF Map으로 유저 공간과 통신하는 원리를 살펴본 뒤 직접 개발과 도구 도입의 경계를 정리합니다.
<!-- internal-links:end -->

## 자주 묻는 질문

### Linux 커널 버전만 알면 eBPF 지원 여부를 판단할 수 있나요?

아닙니다. 배포판 backport와 build config, 필요한 hook·helper·BTF·JIT, NIC driver와 보안 정책이 달라 실제 노드에서 기능 probe와 적재 시험을 해야 합니다.

### Verifier를 통과하면 eBPF 프로그램이 안전한가요?

메모리·제어 흐름 등 커널이 검사하는 조건을 통과했다는 뜻이지 정책 로직이 옳다는 보장은 아닙니다. test packet, 범위 제한과 canary·detach 절차가 필요합니다.

### BCC 예제는 모든 서버에서 그대로 실행되나요?

아닙니다. 커널 header·compiler·BCC와 권한, 함수·interface 이름이 필요합니다. 배포판과 노드 image에 맞춰 의존성과 attach mode를 확인해야 합니다.

## References

- [ebpf.io 원문](https://ebpf.io/)
- [cilium.io 원문](https://cilium.io/)
- [GitHub 저장소](https://github.com/iovisor/bcc)
