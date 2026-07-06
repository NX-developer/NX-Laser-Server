#!/usr/bin/env python3
"""NX Laser Server — entry point.

Listens on TCP :9339 and speaks the Brawl Stars 20.93 protocol.
Run:  python3 server.py
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import time

from laser import logic
from laser.messaging import Connection

BASE = os.path.dirname(os.path.abspath(__file__))


def load_key(path: str) -> bytes:
    with open(path, "rb") as f:
        return f.read().strip()


class Server:
    def __init__(self, config: dict):
        self.config = config
        self.server_sk = load_key(os.path.join(BASE, "keys", "server_private.key"))
        self.server_pk = load_key(os.path.join(BASE, "keys", "server_public.key"))
        if len(self.server_sk) != 32 or len(self.server_pk) != 32:
            raise SystemExit("keys must be 32 raw bytes each — run: python3 gen_keys.py")

    def log(self, msg: str):
        print(f"{time.strftime('%H:%M:%S')} {msg}", flush=True)

    async def handle(self, conn, mid, version, payload):
        await logic.handle(self, conn, mid, version, payload)

    async def on_client(self, reader, writer):
        await Connection(reader, writer, self).run()

    async def serve(self):
        host = self.config.get("host", "0.0.0.0")
        port = self.config.get("port", 9339)
        srv = await asyncio.start_server(self.on_client, host, port)
        self.log("=" * 52)
        self.log(f" NX Laser Server  —  Brawl Stars 20.93 (build 85)")
        self.log(f" listening on {host}:{port}")
        self.log(f" server public key: {self.server_pk.hex()}")
        self.log("=" * 52)
        async with srv:
            await srv.serve_forever()


def main():
    cfg_path = os.path.join(BASE, "config.json")
    config = {}
    if os.path.exists(cfg_path):
        with open(cfg_path) as f:
            config = json.load(f)
    try:
        asyncio.run(Server(config).serve())
    except KeyboardInterrupt:
        print("\nbye")


if __name__ == "__main__":
    main()
