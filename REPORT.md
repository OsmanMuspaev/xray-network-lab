# Network Benchmarks

English · [Русский](REPORT.ru.md)

[Setup and usage](README.md)

## Local benchmark

On November 24, 2026, the lab ran Xray 26.11.9 in OrbStack on an arm64 Mac. Both Xray configurations passed `xray run -test`. The first run reached a public HTTPS endpoint through SOCKS, but Xray's outbound policy blocked traffic to the private test container. The [initial CSV](local-results.csv) records that failure.

The working lab uses a local TLS target and a scoped rule for TCP traffic to the HTTP test service. The direct route reaches the service through its published loopback port. The tunneled route reaches the same service through SOCKS and both Xray containers.

Each route ran three five-second trials at each concurrency level. Download workers requested a fixed 4 MiB file while a separate worker sent short HTTP probes. Throughput is the median of the three trials. Probe p95 and sample counts are listed in trial order. CPU and RAM values are the highest sampled server-container values during tunneled trials. In Docker, 100% CPU corresponds to one logical core.

| Workers | Route | Median, Mibit/s | p95, ms | Successful probes per trial | Completed downloads | Errors | Peak CPU, % | Peak RAM, MiB |
| ---: | --- | ---: | --- | --- | ---: | ---: | ---: | ---: |
| 1 | Direct | 2087.81 | 2.45 / 1.94 / 2.20 | 24 / 24 / 24 | 1015 | 0 | — | — |
| 1 | Tunnel | 1270.32 | 11.87 / 9.04 / 12.10 | 23 / 23 / 23 | 602 | 0 | 23.52 | 15.40 |
| 4 | Direct | 6132.57 | 3.16 / 2.82 / 3.32 | 23 / 23 / 23 | 2957 | 0 | — | — |
| 4 | Tunnel | 2822.27 | 25.18 / 20.71 / 24.58 | 22 / 22 / 22 | 1349 | 0 | 70.47 | 23.16 |
| 16 | Direct | 6251.53 | 34.54 / 31.83 / 215.31 | 20 / 20 / 19 | 2994 | 0 | — | — |
| 16 | Tunnel | 3965.13 | 98.10 / 113.05 / 121.84 | 18 / 16 / 16 | 1911 | 0 | 158.64 | 27.93 |

All trials completed without recorded request errors. At 16 download workers, latency increased on both paths and direct throughput largely plateaued. The test service, client, and server share one host, so this run does not isolate the bottleneck or establish the maximum supported concurrency. It also provides no evidence about filtering on ISP networks.

Raw data: [18 trials](lab-results.csv) and [185 resource samples](lab-resources.csv). Total benchmark runtime was about 93 seconds.

## VPS benchmark

On November 24, 2026, Xray 26.11.9 ran on an Ubuntu 24.04 VPS in the Netherlands with 1 vCPU and about 2 GiB RAM. A client on a Mac reached a public HTTPS endpoint through the deployed tunnel. The request returned HTTP 200 before and after the benchmark.

The load target was a temporary HTTP service on the VPS itself. The Mac reached it directly and through the Xray listener. Each workload ran three trials per route with a five-second window for starting requests and a four-second timeout per request. Requests already in progress could extend the measured interval. The throughput calculation includes only complete 4 MiB downloads.

| Workers | Route | Median, Mibit/s | p95, ms per trial | Successful probes per trial | Download errors | Probe errors |
| ---: | --- | ---: | --- | --- | ---: | ---: |
| 1 | Direct | 13.70 | 421.53 / 363.41 / 371.70 | 9 / 9 / 9 | 0 | 0 |
| 1 | Tunnel | 7.26 | 767.67 / 754.92 / 717.57 | 6 / 4 / 6 | 2 | 1 |
| 4 | Direct | 36.64 | 372.93 / 420.36 / 381.60 | 9 / 9 / 9 | 3 | 0 |
| 4 | Tunnel | 38.31 | 749.05 / 766.92 / 966.97 | 6 / 6 / 6 | 4 | 0 |
| 16 | Direct | 71.03 | 630.49 / 1478.26 / 2347.63 | 8 / 8 / 5 | 45 | 0 |
| 16 | Tunnel | 63.46 | 898.73 / 1068.44 / 936.37 | 5 / 5 / 5 | 45 | 0 |

Xray's sampled peak during tunneled trials was 14.35% CPU and 54.87 MiB RAM. At 16 workers each route recorded 45 download errors. The benchmark groups timeouts, HTTP failures, and unexpected response sizes into one counter, so the error counts do not establish the cause. With the target on the VPS, this run measures the client-to-VPS path and tunnel overhead under this workload. It does not measure forwarding to a separate origin, establish a reliable concurrency limit, or test ISP filtering. The temporary HTTP listener was removed after testing.

Raw data: [18 VPS trials](vps-results.csv) and [656 resource samples](vps-resources.csv). The VPS trial sequence lasted about 136 seconds. I estimate I spent about five hours actively working on the assignment, much of it troubleshooting connectivity to the initial VPS IP address. I waited about a day and a half before I could change the IP. That wait is excluded from the five-hour estimate.

### Longer timeout retest

A follow-up used the same target with two trials on each route at 4, 8, and 16 workers. The request-start window was seven seconds and the per-request timeout was 12 seconds. At 16 workers the direct route recorded two download errors and the tunnel recorded eight. Across all 12 trials, the short probes completed without errors. The repeat still showed download failures, so no error-free capacity limit was established. The changed run settings and network conditions prevent attributing the improvement to the timeout alone.

A route check on the Mac after the retest showed that traffic to the VPS used an existing system tunnel interface. The direct baseline here means direct at the benchmark's application layer. These runs cannot establish access from a native ISP route. [Follow-up CSV](vps-retest.csv)

### Phone connectivity check

On November 24, 2026, the tester reported that the control page loaded on the phone with Xray disconnected and failed to load with Xray enabled in Happ. The network type and provider were not recorded. A concurrent server check recorded no accepted Xray requests. The incoming TCP packets could not be attributed to the phone. The cause remains undetermined.

On November 26, after changing the VPS IP address, I tested the VLESS profile in Happ on an iPhone over Wi-Fi in Crimea. The test page loaded. The benchmarks above were run before the address changed. I could not determine why the initial IP was unreachable.

## Remote benchmark procedure

1. Check that the test node is reachable directly and through the tunnel. Record the date, region, ISP, connection type, VPS specs, Xray version, and workload.
2. Run three trials for each of 1, 4, and 16 workers. Alternate the order of the two routes between trials. Add higher concurrency levels if capacity remains at 16.
3. Match trial timestamps to server CPU and RAM samples. Report median throughput, per-trial p95 with successful sample counts, and errors.
4. If a timeout occurs, repeat the direct control request and inspect server logs, CPU, and network conditions. Record an unknown cause when the evidence is inconclusive.

A separate public origin, identified fixed-line and mobile networks, and profile import in third-party clients remain unverified. No traffic-volume threshold for filtering was measured.

## Protocol and network considerations

DPI can classify flows using IP addresses, protocol signatures, or traffic patterns. SNI in a conventional TLS ClientHello exposes the server name. A TLS failure on its own is inconclusive. [Censored Planet](https://ensa.fi/papers/tspu-imc22.pdf) · [OONI measurements](https://labs.ooni.io/ru/post/2024-russia-report/) · [OONI interpretation guide](https://ooni.org/support/interpreting-ooni-data/)

Mobile allowlists can prevent access to the server IP regardless of the tunnel protocol. Cloudflare reported transfers cutting off at around 16 KB on some Russian networks in June 2025. That observation is specific to the routes and infrastructure measured. Check the assigned VPS IP from both fixed-line and mobile connections. [Mobile access restrictions](https://aks-rus.ru/wp-content/uploads/2026/04/%D0%97%D0%B0%D0%BF%D1%80%D0%BE%D1%81_%D0%9C%D0%B8%D0%BD%D1%86%D0%B8%D1%84%D1%80%D1%8B_white.pdf) · [Cloudflare measurements](https://blog.cloudflare.com/russian-internet-users-are-unable-to-access-the-open-internet/)

| Protocol | Evidence and limitations |
| --- | --- |
| WireGuard | Reports from 2023–2024 document connectivity issues in Russian networks, including mobile networks. |
| OpenVPN | The same reports document connectivity issues. A USENIX study also identified OpenVPN using flow characteristics and server responses. |
| Legacy Shadowsocks | Researchers demonstrated detection through traffic heuristics in China. The result does not establish behavior on Russian networks. |
| AmneziaWG | The developers describe changes after blocks in summer 2026. Comparable measurements are still needed. |
| Xray VLESS / REALITY / Vision | The lab confirms that the generated client and server work together. Reachability depends on the server IP, ISP, and TLS target. |

Sources: [Roskomsvoboda](https://roskomsvoboda.org/en/analysis/vpn-russia-2023-eng/) · [OpenVPN fingerprinting](https://www.usenix.org/system/files/sec22-xue-diwen.pdf) · [Encrypted traffic detection](https://www.usenix.org/conference/usenixsecurity23/presentation/wu-mingshi) · [AmneziaWG](https://docs.amnezia.org/documentation/amnezia-wg/) · [REALITY configuration](https://xtls.github.io/en/config/transports/reality.html)

## Development note

Codex assisted with the configuration generator, benchmark scripts, documentation, and local verification.
