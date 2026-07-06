"""Supercell "pepper" crypto (libsodium / curve25519) for Brawl Stars.

Brawl Stars 20.93 negotiates a session with the classic Supercell pepper
handshake:

  * The client ships with the SERVER's public key baked into libg.so.
  * On connect it sends message 10101 (Login). The payload is:
        [ client_public_key : 32 bytes ][ crypto_box(...) ]
    where the box is opened with nonce = blake2b(client_pk + server_pk, 24)
    and the shared key k = box_beforenm(client_pk, server_sk).
  * The decrypted blob is:  session_nonce(24) + client_nonce(24) + login_payload
  * All later traffic uses secretbox with key = session_nonce-derived shared
    key and monotonically incrementing nonces.

IMPORTANT: for the client to accept us, the public key inside its libg.so must
match `keys/server_public.key` here. Either patch libg.so with our public key,
or drop in the key extracted from the original .so. See the README.
"""
from __future__ import annotations

from nacl.bindings import (
    crypto_box_beforenm,
    crypto_box_open_afternm,
    crypto_box_afternm,
)
from nacl.hash import blake2b
from nacl.encoding import RawEncoder

NONCE_LEN = 24


def _increment_nonce(nonce: bytearray) -> None:
    # little-endian +2 increment, matching Supercell's session nonce stepping
    c = 2
    for i in range(len(nonce)):
        c += nonce[i]
        nonce[i] = c & 0xFF
        c >>= 8


class PepperSession:
    """Handshake + symmetric session state for a single connection."""

    def __init__(self, server_sk: bytes, server_pk: bytes, log):
        self.server_sk = server_sk
        self.server_pk = server_pk
        self.log = log
        self.handshake_done = False
        self.shared_key: bytes | None = None
        self.client_pk: bytes | None = None
        self.encrypt_nonce: bytearray | None = None  # server -> client
        self.decrypt_nonce: bytearray | None = None  # client -> server

    # ---- client -> server ----
    def decrypt(self, msg_id: int, payload: bytes) -> bytes:
        if not self.handshake_done:
            if len(payload) < 32:
                raise ValueError(f"login payload too short: {len(payload)} bytes")
            self.client_pk = payload[:32]
            box = payload[32:]
            nonce = blake2b(
                self.client_pk + self.server_pk,
                digest_size=NONCE_LEN,
                encoder=RawEncoder,
            )
            self.shared_key = crypto_box_beforenm(self.client_pk, self.server_sk)
            decrypted = crypto_box_open_afternm(box, nonce, self.shared_key)

            session_nonce = decrypted[:NONCE_LEN]
            client_nonce = decrypted[NONCE_LEN:NONCE_LEN * 2]
            login_payload = decrypted[NONCE_LEN * 2:]

            # session key = blake2b(client_nonce + client_pk + shared_key)[:32]
            self.session_key = blake2b(
                bytes(client_nonce) + self.client_pk + self.shared_key,
                digest_size=32,
                encoder=RawEncoder,
            )
            self.encrypt_nonce = bytearray(session_nonce)
            self.decrypt_nonce = bytearray(client_nonce)
            self.handshake_done = True
            self.log(f"    handshake OK  client_pk={self.client_pk.hex()[:16]}...  "
                     f"login_payload={len(login_payload)}B")
            return login_payload

        # symmetric phase
        from nacl.bindings import crypto_secretbox_open
        _increment_nonce(self.decrypt_nonce)
        return crypto_secretbox_open(payload, bytes(self.decrypt_nonce), self.session_key)

    # ---- server -> client ----
    def encrypt(self, msg_id: int, payload: bytes) -> bytes:
        if not self.handshake_done or self.encrypt_nonce is None:
            # pre-handshake responses (rare) go out in the clear
            return payload
        from nacl.bindings import crypto_secretbox
        _increment_nonce(self.encrypt_nonce)
        return crypto_secretbox(payload, bytes(self.encrypt_nonce), self.session_key)
