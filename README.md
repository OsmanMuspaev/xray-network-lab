# Xray Network Lab

English · [Русский](README.ru.md)

A Docker Compose lab for Xray with VLESS, REALITY, and Vision. Compare direct and tunneled traffic to the same HTTP service and measure throughput, latency, and server resource usage.

[Benchmark methodology and results](REPORT.md)

## Run the lab locally

Install Docker Compose 2.24.4 or later, Python 3, OpenSSL, and curl. Make sure the Docker subnet `172.30.184.0/24` is available. Once the images are downloaded, the lab uses a local TLS target and can run offline.

```sh
python3 configure.py --lab
docker compose -f compose.yaml -f compose.lab.yaml --profile client up -d
```

The lab stores credentials and the TLS certificate in `private-lab/`. Xray's server port stays inside Docker. The host can reach the SOCKS proxy at `127.0.0.1:1080` and the HTTP target at `127.0.0.1:18080`. The lab configuration permits TCP traffic to the test service at `172.30.184.10:18080`.

Start the resource collector in one terminal.

```sh
container_id=$(docker compose -f compose.yaml -f compose.lab.yaml --profile client ps -q tunnel)
python3 collect_stats.py "$container_id" --output lab-resources-new.csv
```

Run the benchmark in a second terminal.

```sh
python3 benchmark.py http://127.0.0.1:18080 \
  --local-tunnel-url http://172.30.184.10:18080 \
  --parallel 1 4 16 --duration 5 --repeats 3 --output lab-results-new.csv
```

Stop the collector with Ctrl+C and remove the lab containers when finished.

```sh
docker compose -f compose.yaml -f compose.lab.yaml --profile client down
```

## Deploy to a VPS

Install Docker with Compose and Python 3. Allow inbound TCP 443. Replace `SERVER_IP` with the server's public address and `TLS_HOST` with a TLS hostname reachable from the server.

```sh
python3 configure.py SERVER_IP TLS_HOST
docker compose run --rm tunnel tls ping TLS_HOST
docker compose up -d tunnel
docker compose logs --tail 20 tunnel
```

On a native Linux Docker host, the pinned image runs as UID 65532. If Xray reports permission denied for the generated mode-0600 config, run `sudo chown 65532 private/server.json` and retry. Keep the `private/` directory at mode 0700.

For a different public port, pass the same number to `configure.py --port` and Compose's `PORT` environment variable. Keep `private/server.json` on the VPS because it contains the server's private key. Share `private/profile.txt` only with authorized clients.

To run the Docker client, copy `compose.yaml` and `private/client.json` to the client machine. Run `docker compose --profile client up -d client` to expose the loopback SOCKS proxy.

## Benchmark a remote deployment

Deploy `target.py` to a separate HTTP test node reachable by both the VPS and the client. Restrict access to the test port to those machines.

```sh
# On the test node
python3 target.py --bind TEST_HOST_IP

# On the client machine
python3 benchmark.py http://TEST_HOST_IP:18080 --parallel 1 4 16 --duration 30 --repeats 3

# On the VPS, while the benchmark runs
python3 collect_stats.py "$(docker compose ps -q tunnel)" --output resources.csv
```

The benchmark records throughput from completed downloads, p95 latency for short requests made during downloads, and errors. Synchronize the client and VPS clocks to match resource samples with the trial intervals. Use a fresh CSV filename for each run.
