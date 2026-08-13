"""Minimal DHCP packet builders for protocol unit tests."""
from __future__ import annotations

import socket

MAGIC = b"\x63\x82\x53\x63"


def build_dhcp_packet(
    *,
    op: int = 1,
    xid: int = 0x12345678,
    mac: bytes = b"\xaa\xbb\xcc\xdd\xee\xff",
    options: list[tuple[int, bytes]] | None = None,
) -> bytes:
    if len(mac) != 6:
        raise ValueError("mac must be 6 bytes")
    pkt = bytearray(300)
    pkt[0] = op
    pkt[4:8] = xid.to_bytes(4, "big")
    pkt[28:34] = mac
    pkt[236:240] = MAGIC
    pos = 240
    for opt, value in options or []:
        pkt[pos : pos + 2 + len(value)] = bytes([opt, len(value)]) + value
        pos += 2 + len(value)
    pkt[pos] = 255
    return bytes(pkt[: pos + 1])


def discover_packet(*, xid: int = 0x12345678, mac: bytes = b"\xaa\xbb\xcc\xdd\xee\xff") -> bytes:
    return build_dhcp_packet(xid=xid, mac=mac, options=[(53, b"\x01")])


def request_packet_server_id(
    *,
    xid: int,
    mac: bytes,
    server_ip: str,
) -> bytes:
    return build_dhcp_packet(
        xid=xid,
        mac=mac,
        options=[(53, b"\x03"), (54, socket.inet_aton(server_ip))],
    )


def request_packet_requested_ip(
    *,
    xid: int = 0x12345678,
    mac: bytes = b"\xaa\xbb\xcc\xdd\xee\xff",
    requested_ip: str,
) -> bytes:
    return build_dhcp_packet(
        xid=xid,
        mac=mac,
        options=[(53, b"\x03"), (50, socket.inet_aton(requested_ip))],
    )


def decline_packet(*, mac: bytes = b"\xaa\xbb\xcc\xdd\xee\xff") -> bytes:
    return build_dhcp_packet(mac=mac, options=[(53, b"\x04")])
