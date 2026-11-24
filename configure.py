#!/usr/bin/env python3
"""Создаёт конфигурации сервера и клиента. Ключи остаются в private/."""
import argparse
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
from urllib.parse import urlencode
from uuid import uuid4

ROOT = Path(__file__).resolve().parent
LAB_TARGET_IP = "172.30.184.10"
LAB_TARGET_PORT = 18080


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("server", nargs="?", help="Публичное имя или IPv4 сервера")
    parser.add_argument("target", nargs="?", help="Имя TLS-сервиса для REALITY")
    parser.add_argument("--port", type=int, default=443)
    parser.add_argument("--lab", action="store_true", help="Локальные конфигурации для compose.lab.yaml")
    args = parser.parse_args()
    if args.lab:
        if args.server or args.target or args.port != 443:
            parser.error("Для лаборатории используй только --lab")
        args.server, args.target = "172.30.184.20", "lab.invalid"
    if not 1 <= args.port <= 65535 or not all(
        host and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.-]*", host)
        for host in (args.server, args.target)
    ):
        parser.error("Нужны корректные имена хостов и TCP-порт")
    target = f"{LAB_TARGET_IP}:18444" if args.lab else f"{args.target}:443"
    private = ROOT / ("private-lab" if args.lab else "private")
    if private.exists():
        parser.error(f"{private.name}/ уже существует. Сохрани её перед выпуском нового профиля.")

    compose = ["docker", "compose", "-f", str(ROOT / "compose.yaml")]
    image = subprocess.check_output(
        [*compose, "config", "--images", "tunnel"], text=True
    ).strip()
    key_output = subprocess.check_output(
        ["docker", "run", "--rm", image, "x25519"], text=True
    )
    key = next(line.split(": ", 1)[1] for line in key_output.splitlines() if line.startswith("PrivateKey: "))
    public = next(line.split(": ", 1)[1] for line in key_output.splitlines() if line.startswith("Password"))
    client_id, short_id = str(uuid4()), secrets.token_hex(8)
    flow = "xtls-rprx-vision"
    server = {
        "log": {"loglevel": "warning"},
        "inbounds": [{
            "port": 443, "protocol": "vless",
            "settings": {"clients": [{"id": client_id, "flow": flow}], "decryption": "none"},
            "streamSettings": {
                "network": "raw", "security": "reality",
                "realitySettings": {
                    "target": target, "serverNames": [args.target],
                    "privateKey": key, "shortIds": [short_id],
                },
            },
        }],
        "outbounds": [{"protocol": "freedom"}],
    }
    if args.lab:
        server["outbounds"][0]["settings"] = {
            "finalRules": [{
                "action": "allow", "network": "tcp",
                "ip": [LAB_TARGET_IP], "port": LAB_TARGET_PORT,
            }],
        }
    client = {
        "log": {"loglevel": "warning"},
        "inbounds": [{"listen": "0.0.0.0", "port": 1080, "protocol": "socks"}],
        "outbounds": [{
            "protocol": "vless",
            "settings": {"vnext": [{
                "address": args.server, "port": args.port,
                "users": [{"id": client_id, "encryption": "none", "flow": flow}],
            }]},
            "streamSettings": {
                "network": "raw", "security": "reality",
                "realitySettings": {
                    "serverName": args.target, "fingerprint": "chrome",
                    "password": public, "shortId": short_id,
                },
            },
        }],
    }
    query = urlencode({
        "type": "tcp", "security": "reality", "encryption": "none", "flow": flow,
        "sni": args.target, "fp": "chrome", "pbk": public, "sid": short_id,
    })
    os.umask(0o077)
    private.mkdir(mode=0o700)
    if args.lab:
        subprocess.run([
            "openssl", "req", "-new", "-x509", "-newkey", "ec",
            "-pkeyopt", "ec_paramgen_curve:P-256", "-nodes", "-days", "30",
            "-subj", f"/CN={args.target}",
            "-keyout", str(private / "tls.key"), "-out", str(private / "tls.crt"),
        ], check=True)
    for name, config in (("server.json", server), ("client.json", client)):
        (private / name).write_text(json.dumps(config, indent=2) + "\n")
    (private / "profile.txt").write_text(
        f"vless://{client_id}@{args.server}:{args.port}?{query}#Xray%20Network%20Lab\n"
    )
    print(f"Созданы server.json, client.json и profile.txt в {private.name}/")


if __name__ == "__main__":
    main()
