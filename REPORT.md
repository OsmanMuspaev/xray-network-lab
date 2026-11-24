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

## Remote benchmark procedure

1. Check that the test node is reachable directly and through the tunnel. Record the date, region, ISP, connection type, VPS specs, Xray version, and workload.
2. Run three trials for each of 1, 4, and 16 workers. Alternate the order of the two routes between trials. Add higher concurrency levels if capacity remains at 16.
3. Match trial timestamps to server CPU and RAM samples. Report median throughput, per-trial p95 with successful sample counts, and errors.
4. If a timeout occurs, repeat the direct control request and inspect server logs, CPU, and network conditions. Record an unknown cause when the evidence is inconclusive.

Remote throughput, ISP reachability, and profile import in third-party clients remain unverified.

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
