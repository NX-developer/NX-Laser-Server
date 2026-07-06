"""Message handlers.

Current milestone: complete the pepper handshake and bounce the client with a
LoginFailed carrying a custom message. If the player sees that message in-game,
the crypto + framing are correct and we can move on to LoginOk + OwnHomeData.

Flip `SEND_LOGIN_OK = True` in config to attempt the (still WIP) home flow.
"""
from __future__ import annotations

from . import messages
from .stream import Reader, Writer


def parse_login(payload: bytes) -> dict:
    """Best-effort parse of the decrypted LoginMessage (10101) body."""
    r = Reader(payload)
    info = {}
    try:
        hi, lo = r.read_long()
        info["account_id"] = (hi, lo)
        info["pass_token"] = r.read_string()
        info["client_major"] = r.read_int()
        info["client_minor"] = r.read_int()
        info["client_build"] = r.read_int()
        info["resource_sha"] = r.read_string()
        info["device"] = r.read_string()
        info["lang"] = r.read_string() if r.remaining() else ""
    except Exception as e:
        info["parse_error"] = repr(e)
    return info


def build_login_failed(reason: str, error_code: int = 8) -> bytes:
    """LoginFailed (20103) — error_code 8 shows `reason` as a maintenance popup."""
    w = Writer()
    w.write_vint(error_code)
    w.write_string(None)          # resourceFingerprintData
    w.write_string(None)          # redirectDomain
    w.write_string(None)          # contentURL
    w.write_string(None)          # updateURL
    w.write_string(reason)        # <- text shown to the player
    w.write_vint(0)               # secondsUntilMaintenanceEnd
    w.write_bool(False)           # showContactSupportButton
    w.write_vint(0)               # compressedFingerprintDataLength
    return w.bytes()


async def handle(server, conn, mid, version, payload):
    if mid == messages.LOGIN:
        info = parse_login(payload)
        conn.log(f"    LoginMessage: {info}")
        reason = server.config.get("message",
                                   "NX Laser Server is online! Handshake OK.")
        if server.config.get("send_login_ok"):
            # TODO: implement LoginOk (20104) + OwnHomeData (24101)
            conn.log("    (send_login_ok set, but home flow not implemented yet)")
        conn.send(messages.LOGIN_FAILED, build_login_failed(reason))
        return

    if mid == messages.KEEP_ALIVE:
        conn.send(messages.KEEP_ALIVE_OK, b"")
        return

    conn.log(f"    (no handler for {messages.name(mid)})")
