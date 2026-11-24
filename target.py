#!/usr/bin/env python3
"""HTTP-стенд для замеров. Запускать на своём тестовом узле."""
import argparse
from pathlib import Path
import ssl
from threading import Thread
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PAYLOAD = bytes(range(256)) * 16_384


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        data = {"/ping": b"ok\n", "/download": PAYLOAD}.get(self.path)
        if data is None:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", "application/octet-stream")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        try:
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            pass  # Клиент мог прервать замер по таймауту.

    def log_message(self, *_):
        pass


class BenchmarkServer(ThreadingHTTPServer):
    request_queue_size = 128


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bind", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=18080)
    parser.add_argument("--lab-tls-dir", type=Path, help="Сертификат и ключ локальной TLS-цели")
    args = parser.parse_args()
    if args.lab_tls_dir:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.minimum_version = ssl.TLSVersion.TLSv1_3
        context.set_alpn_protocols(["http/1.1"])
        context.load_cert_chain(args.lab_tls_dir / "tls.crt", args.lab_tls_dir / "tls.key")
        tls_server = BenchmarkServer((args.bind, 18444), Handler)
        tls_server.socket = context.wrap_socket(tls_server.socket, server_side=True)
        Thread(target=tls_server.serve_forever, daemon=True).start()
    with BenchmarkServer((args.bind, args.port), Handler) as server:
        server.serve_forever()
