"""Message type IDs used by Brawl Stars 20.93 (Supercell "laser" protocol).

Client -> Server messages are 1xxxx, Server -> Client are 2xxxx.
Only the ones we currently handle/emit are listed; add more as we implement.
"""

# --- Client -> Server ---
CLIENT_HELLO = 10100
LOGIN = 10101
KEEP_ALIVE = 10108
CLIENT_CAPABILITIES = 10107

# --- Server -> Client ---
SERVER_HELLO = 20100
LOGIN_FAILED = 20103
LOGIN_OK = 20104
KEEP_ALIVE_OK = 20108
OWN_HOME_DATA = 24101

NAMES = {
    10100: "ClientHello",
    10101: "Login",
    10107: "ClientCapabilities",
    10108: "KeepAlive",
    20100: "ServerHello",
    20103: "LoginFailed",
    20104: "LoginOk",
    20108: "KeepAliveOk",
    24101: "OwnHomeData",
}


def name(mid: int) -> str:
    return NAMES.get(mid, f"Unknown({mid})")
