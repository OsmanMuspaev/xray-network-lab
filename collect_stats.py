#!/usr/bin/env python3
"""Пишет CPU и память одного Docker-контейнера с временными метками UTC."""
import argparse
import csv
from datetime import datetime, timezone
import json
import re
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("container", help="ID или имя контейнера")
    parser.add_argument("--output", default="resources.csv")
    args = parser.parse_args()
    subprocess.run(["docker", "inspect", "--type", "container", args.container],
                   stdout=subprocess.DEVNULL, check=True)
    with open(args.output, "x", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(["timestamp_utc", "cpu_percent", "memory_used", "memory_limit"])
        with subprocess.Popen(
            ["docker", "stats", "--format", "{{json .}}", args.container],
            stdout=subprocess.PIPE, text=True,
        ) as sampler:
            try:
                for line in sampler.stdout:
                    row = re.sub(r"\x1b\[[0-9;]*[HJK]", "", line).strip()
                    if not row:
                        continue
                    sample = json.loads(row)
                    used, limit = sample["MemUsage"].split(" / ")
                    timestamp = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
                    writer.writerow([timestamp, sample["CPUPerc"].rstrip("%"), used, limit])
                    stream.flush()
            except KeyboardInterrupt:
                pass
            finally:
                if sampler.poll() is None:
                    sampler.terminate()


if __name__ == "__main__":
    main()
