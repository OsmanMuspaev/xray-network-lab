#!/usr/bin/env python3
"""Замеряет прямой маршрут и SOCKS-маршрут до одного тестового сервиса."""
import argparse
import csv
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import math
import subprocess
from time import monotonic, sleep

FIELDS = [
    "route", "parallel", "downloads_ok", "downloads_failed", "probe_ok",
    "probe_failed", "mibit_per_second", "ping_p95_ms", "probe_samples",
    "repeat", "started_utc", "finished_utc",
]


def transfer(url, proxy, timeout, expected_bytes):
    result = subprocess.run(
        ["curl", "-q", "--globoff", "--proxy", proxy, "--noproxy", "", "--fail",
         "--silent", "--show-error", "--max-time", str(timeout),
         "--output", "/dev/null", "--write-out", "%{size_download}\t%{time_total}", "--", url],
        capture_output=True, text=True,
    )
    if result.returncode:
        return None
    size, seconds = result.stdout.split("\t")
    if int(size) != expected_bytes:
        return None
    return int(size), float(seconds)


def worker(url, proxy, deadline, timeout):
    downloads = failed = total = 0
    while monotonic() < deadline:
        result = transfer(url + "/download", proxy, timeout, 4 * 2**20)
        if result is None:
            failed += 1
        else:
            downloads += 1
            total += result[0]
    return downloads, failed, total


def trial(url, proxy, parallel, duration, timeout):
    started = monotonic()
    deadline = started + duration
    failures = 0
    latencies = []
    with ThreadPoolExecutor(max_workers=parallel) as pool:
        jobs = [pool.submit(worker, url, proxy, deadline, timeout) for _ in range(parallel)]
        while monotonic() < deadline:
            result = transfer(url + "/ping", proxy, timeout, 3)
            if result is None:
                failures += 1
            else:
                latencies.append(result[1] * 1000)
            sleep(0.2)
    elapsed = monotonic() - started
    ok, failed, total = map(sum, zip(*(job.result() for job in jobs)))
    latencies.sort()
    p95 = round(latencies[math.ceil(0.95 * len(latencies)) - 1], 2) if latencies else ""
    return [parallel, ok, failed, len(latencies), failures,
            round(total * 8 / 2**20 / elapsed, 2), p95, len(latencies) + failures]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url", help="Базовый URL тестового сервиса")
    parser.add_argument("--proxy", default="socks5h://127.0.0.1:1080")
    parser.add_argument("--local-tunnel-url", help="Тот же сервис под другим адресом в локальном Docker")
    parser.add_argument("--parallel", type=int, nargs="+", default=[1, 4, 16])
    parser.add_argument("--duration", type=int, default=15)
    parser.add_argument("--timeout", type=int, default=5)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--output", default="results.csv")
    args = parser.parse_args()
    if min(*args.parallel, args.duration, args.timeout, args.repeats) < 1:
        parser.error("Длительность, таймаут и параллельность должны быть положительными")
    routes = [("direct", args.url, ""), ("tunnel", args.local_tunnel_url or args.url, args.proxy)]
    for name, url, proxy in routes:
        for path, size in (("/ping", 3), ("/download", 4 * 2**20)):
            if transfer(url.rstrip("/") + path, proxy, args.timeout, size) is None:
                parser.error(f"{name}: не прошла проверка {path}. Проверь маршрут до замеров.")
    with open(args.output, "x", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(FIELDS)
        for parallel in args.parallel:
            for repeat in range(1, args.repeats + 1):
                order = routes if repeat % 2 else reversed(routes)
                for name, url, proxy in order:
                    started = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
                    metrics = trial(url.rstrip("/"), proxy, parallel, args.duration, args.timeout)
                    finished = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
                    row = [name, *metrics, repeat, started, finished]
                    writer.writerow(row)
                    stream.flush()
                    print(*row, sep=" | ", flush=True)


if __name__ == "__main__":
    main()
