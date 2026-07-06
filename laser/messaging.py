"""Frame reading/writing and the per-connection message loop.

Supercell frame layout (all big-endian):
    message_type : 2 bytes
    length       : 3 bytes   (length of the encrypted payload)
    version      : 2 bytes
    payload      : `length` bytes
"""
from __future__ import annotations

import asyncio

from . import messages
from .crypto import PepperSession

HEADER_LEN = 7


def hexdump(data: bytes, limit: int = 128) -> str:
    """Compact hex dump for reverse-engineering the first packets."""
    out = []
    chunk = data[:limit]
    for i in range(0, len(chunk), 16):
        row = chunk[i:i + 16]
        hexpart = " ".join(f"{b:02x}" for b in row)
        asciipart = "".join(chr(b) if 32 <= b < 127 else "." for b in row)
        out.append(f"      {i:04x}  {hexpart:<47}  {asciipart}")
    if len(data) > limit:
        out.append(f"      ... (+{len(data) - limit} more bytes)")
    return "\n".join(out)


class Connection:
    def __init__(self, reader, writer, server):
        self.reader = reader
        self.writer = writer
        self.server = server
        self.peer = writer.get_extra_info("peername")
        self.session = PepperSession(server.server_sk, server.server_pk, self.log)
        self.frame_count = 0

    def log(self, msg: str):
        self.server.log(f"[{self.peer[0]}:{self.peer[1]}] {msg}")

    async def read_frame(self):
        header = await self.reader.readexactly(HEADER_LEN)
        mid = int.from_bytes(header[0:2], "big")
        length = int.from_bytes(header[2:5], "big")
        version = int.from_bytes(header[5:7], "big")
        payload = await self.reader.readexactly(length) if length else b""
        return mid, version, payload

    def send(self, mid: int, payload: bytes):
        enc = self.session.encrypt(mid, payload)
        header = (
            mid.to_bytes(2, "big")
            + len(enc).to_bytes(3, "big")
            + (0).to_bytes(2, "big")
        )
        self.writer.write(header + enc)
        self.log(f"  --> {messages.name(mid)} ({mid})  {len(enc)}B")

    async def run(self):
        self.log("connected")
        try:
            while True:
                mid, version, enc_payload = await self.read_frame()
                self.frame_count += 1
                self.log(f"<-- {messages.name(mid)} ({mid})  v{version}  {len(enc_payload)}B enc")

                # Dump the first two raw frames verbatim: this is what tells us
                # RC4 vs pepper and reveals the exact on-wire login structure.
                if self.frame_count <= 2:
                    self.log(f"    RAW frame #{self.frame_count} (id={mid}, {len(enc_payload)}B):\n"
                             + hexdump(enc_payload))

                try:
                    payload = self.session.decrypt(mid, enc_payload)
                except Exception as e:
                    self.log(f"    !! decrypt failed: {e!r}  raw={enc_payload[:48].hex()}")
                    # keep going so we can still study later frames
                    payload = enc_payload

                await self.server.handle(self, mid, version, payload)
        except asyncio.IncompleteReadError:
            self.log("disconnected")
        except Exception as e:
            self.log(f"error: {e!r}")
        finally:
            try:
                self.writer.close()
            except Exception:
                pass
