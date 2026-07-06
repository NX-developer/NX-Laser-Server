<h1 align="center">⚡ NX Laser Server</h1>

<p align="center">
  <b>An open-source, educational private server for Brawl Stars 20.93</b><br>
  <sub>Written in pure Python · pepper (libsodium) crypto · no native code required to run</sub>
</p>

<p align="center">
  <img alt="game" src="https://img.shields.io/badge/game-Brawl%20Stars-yellow">
  <img alt="version" src="https://img.shields.io/badge/version-20.93%20(build%2085)-blue">
  <img alt="python" src="https://img.shields.io/badge/python-3.9%2B-green">
  <img alt="license" src="https://img.shields.io/badge/license-MIT-lightgrey">
  <img alt="status" src="https://img.shields.io/badge/status-WIP-orange">
</p>

---

## What is this?

**NX Laser Server** is a from-scratch re-implementation of the Brawl Stars game
server ("laser" is Supercell's internal codename for the game). It lets a
**modded Brawl Stars 20.93 client** connect to *your own* machine instead of
Supercell's official servers, so you can study the protocol, run the game
offline, and experiment with your own game logic.

It is built for **learning how mobile game networking works** — encryption
handshakes, message framing, and login flow — on a version that is many years
old and no longer serviced by the official servers.

> ⚠️ **Disclaimer.** This project is **not affiliated with, endorsed by, or
> connected to Supercell** in any way. "Brawl Stars" and "Supercell" are
> trademarks of Supercell Oy. This repository contains **no** Supercell code,
> assets, or binaries — only a clean-room server that speaks a wire protocol.
> It is provided **for educational and research purposes only.** Running a
> private server may violate the game's Terms of Service; use it only with
> content you own, on your own devices. You are responsible for how you use it.

---

## Current status

This is an early work in progress. The roadmap milestones:

| Milestone | State |
|-----------|-------|
| TCP listener + Supercell frame parsing (`:9339`) | ✅ done |
| Pepper (libsodium/curve25519) handshake | ✅ implemented — needs live verification |
| Verbose packet logging for reverse-engineering | ✅ done |
| **LoginFailed** with a custom in-game message (crypto proof) | ✅ implemented |
| `LoginOk` (20104) | 🚧 planned |
| `OwnHomeData` (24101) → reach the home screen | 🚧 planned |
| Battles / gameplay | ⛔ not started |

The **first goal** is simple and testable: the modded client connects, our
server completes the encryption handshake, and the client displays our custom
message. When you see that text in-game, the hard part (crypto + framing) works.

---

## Requirements

- Python **3.9+**
- [`PyNaCl`](https://pypi.org/project/PyNaCl/) (libsodium bindings)
- A **modded Brawl Stars 20.93** APK that points at your server (see below)

```bash
pip install -r requirements.txt
```

---

## Quick start

```bash
# 1. generate the server keypair
python3 gen_keys.py
#    -> prints your PUBLIC KEY (you'll need it for the client)

# 2. start the server
python3 server.py
#    -> listening on 0.0.0.0:9339
```

Edit `config.json` to change the port or the welcome message:

```json
{
  "host": "0.0.0.0",
  "port": 9339,
  "message": "Welcome to NX Laser Server!",
  "send_login_ok": false
}
```

---

## Connecting the client — the important part

The Brawl Stars client keeps **two critical secrets inside `libg.so`** (the
native library), *not* in the decompiled Java/resources:

1. the **server hostname** — `game.brawlstarsgame.com`
2. the **server's public key** — a 32-byte curve25519 key it uses for the
   handshake

To make the client trust *our* server, you must change **both** inside
`libg.so` (found in the original APK at `lib/arm64-v8a/libg.so`):

1. **Hostname** → replace `game.brawlstarsgame.com` with your server's IP or
   domain (keep the string the same length or shorter, pad with `\0`).
2. **Public key** → replace Supercell's baked-in key with the one printed by
   `gen_keys.py`.

Then repackage and sign the APK.

> 💡 A decompiled APK that **excludes `.so` files** (like the one this project
> was studied from) is enough to read game logic, but you **cannot repoint the
> client without the `.so`.** Grab `libg.so` from the original APK.

### Alternative: DNS redirect

Instead of editing the hostname, you can redirect `game.brawlstarsgame.com` to
your server's IP (via the device `hosts` file, a local DNS, or a proxy). You
**still** need the public-key patch for the handshake to succeed.

---

## Protocol notes (20.93)

- **Transport:** TCP, port **9339**.
- **Frame:** `type(2) | length(3) | version(2) | payload(length)`, big-endian.
- **Crypto:** Supercell "pepper" — the client sends its curve25519 public key,
  then a `crypto_box` opened with `nonce = blake2b(client_pk + server_pk, 24)`
  and key `box_beforenm(client_pk, server_sk)`. Session traffic then uses
  `secretbox` with incrementing nonces. See [`laser/crypto.py`](laser/crypto.py).
- **Encoding:** big-endian fixed ints, length-prefixed UTF-8 strings, and
  Supercell's zig-zag **VInt**. See [`laser/stream.py`](laser/stream.py).

---

## Project layout

```
NX-Laser-Server/
├── server.py            # asyncio TCP entry point
├── gen_keys.py          # generate the curve25519 keypair
├── config.json          # host / port / welcome message
├── laser/
│   ├── crypto.py        # pepper handshake + session crypto
│   ├── messaging.py     # frame read/write + per-connection loop
│   ├── messages.py      # message type IDs
│   ├── stream.py        # byte reader/writer (ints, VInt, strings)
│   └── logic.py         # message handlers (login -> reply)
└── keys/                # generated keys (gitignored)
```

---

## Contributing

The next big step is decoding **`OwnHomeData` (24101)** for 20.93 so a client
reaches the home screen. Packet captures and field maps are very welcome.

## License

[MIT](LICENSE) — for the server code in this repository only.
