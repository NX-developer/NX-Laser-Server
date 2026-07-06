#!/usr/bin/env python3
"""Generate the server's curve25519 keypair.

The PUBLIC key printed here must be the one the client trusts. Patch it into
libg.so (replacing Supercell's key) so your modded APK talks to this server.
"""
import os
from nacl.public import PrivateKey

BASE = os.path.dirname(os.path.abspath(__file__))
KEYS = os.path.join(BASE, "keys")
os.makedirs(KEYS, exist_ok=True)

sk = PrivateKey.generate()
priv = bytes(sk)
pub = bytes(sk.public_key)

with open(os.path.join(KEYS, "server_private.key"), "wb") as f:
    f.write(priv)
with open(os.path.join(KEYS, "server_public.key"), "wb") as f:
    f.write(pub)

print("server_private.key written (keep secret)")
print("server_public.key  written")
print()
print("PUBLIC KEY (patch this into libg.so):")
print(pub.hex())
