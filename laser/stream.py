"""Byte stream helpers for the Supercell/Brawl Stars wire format.

Supercell games use big-endian fixed-width integers plus a variable-length
"VInt" (zig-zag) encoding for many fields, and length-prefixed UTF-8 strings.
These readers/writers are the primitives every message is built from.
"""
from __future__ import annotations


class Reader:
    def __init__(self, data: bytes):
        self.buf = data
        self.offset = 0

    def _take(self, n: int) -> bytes:
        chunk = self.buf[self.offset:self.offset + n]
        self.offset += n
        return chunk

    def remaining(self) -> bytes:
        return self.buf[self.offset:]

    def read_byte(self) -> int:
        return self._take(1)[0]

    def read_bool(self) -> bool:
        return self.read_byte() != 0

    def read_int(self) -> int:
        return int.from_bytes(self._take(4), "big", signed=True)

    def read_short(self) -> int:
        return int.from_bytes(self._take(2), "big", signed=True)

    def read_long(self) -> tuple[int, int]:
        return self.read_int(), self.read_int()

    def read_vint(self) -> int:
        """Supercell zig-zag VInt."""
        result = 0
        shift = 0
        while True:
            b = self.read_byte()
            if shift == 0:
                # first byte: bit6 is the "more" flag, bit7 keeps going
                result |= (b & 0x3F)
                if (b & 0x40) != 0:
                    sign = -1
                else:
                    sign = 1
                if (b & 0x80) == 0:
                    return result * sign
                shift = 6
            else:
                result |= (b & 0x7F) << shift
                shift += 7
                if (b & 0x80) == 0:
                    return result * (sign)

    def read_string(self) -> str:
        length = self.read_int()
        if length <= 0 or length > (1 << 20):
            return ""
        return self._take(length).decode("utf-8", "replace")


class Writer:
    def __init__(self):
        self.buf = bytearray()

    def write_byte(self, v: int):
        self.buf.append(v & 0xFF)

    def write_bool(self, v: bool):
        self.write_byte(1 if v else 0)

    def write_int(self, v: int):
        self.buf += int(v).to_bytes(4, "big", signed=True)

    def write_short(self, v: int):
        self.buf += int(v).to_bytes(2, "big", signed=True)

    def write_long(self, high: int, low: int):
        self.write_int(high)
        self.write_int(low)

    def write_vint(self, value: int):
        # zig-zag style VInt matching Supercell's LogicMessage.writeVInt
        v = value
        if v < 0:
            temp = (v & 0x3F) | 0x40
            v >>= 6
            if v != 0:
                self.write_byte(temp | 0x80)
                while True:
                    if (v >> 7) != -1 and (v >> 7) != 0:
                        self.write_byte((v & 0x7F) | 0x80)
                    else:
                        self.write_byte(v & 0x7F)
                        break
                    v >>= 7
            else:
                self.write_byte(temp)
        else:
            temp = (v & 0x3F)
            v >>= 6
            if v != 0:
                self.write_byte(temp | 0x80)
                while True:
                    if (v >> 7) != 0:
                        self.write_byte((v & 0x7F) | 0x80)
                    else:
                        self.write_byte(v & 0x7F)
                        break
                    v >>= 7
            else:
                self.write_byte(temp)

    def write_string(self, s: str | None):
        if s is None:
            self.write_int(-1)
            return
        raw = s.encode("utf-8")
        self.write_int(len(raw))
        self.buf += raw

    def bytes(self) -> bytes:
        return bytes(self.buf)
