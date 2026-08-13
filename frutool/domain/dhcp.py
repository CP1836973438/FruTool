"""Minimal DHCP server for BMC address assignment."""
from __future__ import annotations

import re
import socket
import subprocess
import sys
import threading
import time
from typing import Callable, Optional

from frutool.config import LogCallback
from frutool.infrastructure.network import NetworkConfig, _startup_flags, _subnet_broadcast_addr

_UDP67_OCCUPANT_RE = re.compile(
    r"^\s*UDP\s+(\S+):67\s+\S+(?:\s+\S+)*\s+(\d+)\s*$",
    re.I,
)
_DHCP_BIND_HINTS = (
    "VMware 虚拟网卡 / VMnet DHCP（vmnat.exe、vmnetdhcp.exe）",
    "Hyper-V 虚拟交换机 DHCP",
    "Windows ICS（Internet 连接共享）",
    "其它占用 UDP 67 的 DHCP 服务或产测工具",
)
_LEASE_SECONDS = 43200
_PENDING_SECONDS = 30


def _is_bind_permission_error(exc: BaseException) -> bool:
    if isinstance(exc, PermissionError):
        return True
    if isinstance(exc, OSError):
        if getattr(exc, "winerror", None) == 10013:
            return True
        if getattr(exc, "errno", None) in (13, 10013):
            return True
    msg = str(exc).lower()
    return "permission denied" in msg or "access is denied" in msg or "拒绝访问" in msg


def _is_udp67_in_use_error(exc: BaseException) -> bool:
    if isinstance(exc, OSError):
        if getattr(exc, "winerror", None) == 10048:
            return True
        if getattr(exc, "errno", None) in (10048, 98):
            return True
    msg = str(exc).lower()
    return "already in use" in msg or "address already in use" in msg or "只允许使用一次" in msg


def _lookup_process_name(pid: str) -> str:
    if sys.platform != "win32" or not pid.isdigit():
        return ""
    try:
        result = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
            capture_output=True,
            text=True,
            errors="replace",
            timeout=5,
            creationflags=_startup_flags(),
        )
        if result.returncode != 0:
            return ""
        line = (result.stdout or "").strip()
        if not line or line.startswith("INFO:"):
            return ""
        parts = line.split(",")
        if parts:
            return parts[0].strip('"')
    except Exception:
        pass
    return ""


def _diagnose_udp67_occupants() -> list[tuple[str, str, str]]:
    """Return (local_addr, pid, process_name) for each UDP :67 listener found via netstat."""
    if sys.platform != "win32":
        return []
    seen: set[tuple[str, str]] = set()
    occupants: list[tuple[str, str, str]] = []
    for cmd in (["netstat", "-ano", "-p", "udp"], ["netstat", "-ano"]):
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                errors="replace",
                timeout=8,
                creationflags=_startup_flags(),
            )
        except Exception:
            continue
        if result.returncode != 0:
            continue
        for line in (result.stdout or "").splitlines():
            match = _UDP67_OCCUPANT_RE.match(line)
            if not match:
                continue
            local_addr, pid = match.group(1), match.group(2)
            key = (local_addr, pid)
            if key in seen:
                continue
            seen.add(key)
            process = _lookup_process_name(pid)
            occupants.append((local_addr, pid, process))
        if occupants:
            break
    return occupants


def _log_dhcp_bind_failure(log_cb: LogCallback, exc: BaseException):
    if _is_bind_permission_error(exc):
        log_cb("error", "Cannot bind UDP 67. Run this program as administrator.")
        return
    if not _is_udp67_in_use_error(exc):
        log_cb("error", f"DHCP startup failed: {exc}")
        return
    log_cb("error", f"Cannot bind UDP 67: port already in use ({exc})")
    occupants = _diagnose_udp67_occupants()
    if occupants:
        for local_addr, pid, process in occupants:
            if process:
                log_cb("warning", f"UDP 67 occupant: {process} (PID {pid}, bind {local_addr}:67)")
            else:
                log_cb("warning", f"UDP 67 occupant: PID {pid} (bind {local_addr}:67)")
    else:
        log_cb("info", "netstat did not list a UDP :67 listener; conflict may be at driver/filter level")
    log_cb("info", "DHCP bind failure — possible causes:")
    for hint in _DHCP_BIND_HINTS:
        log_cb("info", f"  - {hint}")
    log_cb(
        "info",
        "DHCP: close the conflicting service or process, then refresh the network adapter or restart this tool.",
    )


class DHCPServer(threading.Thread):
    MAGIC = b"\x63\x82\x53\x63"

    def __init__(
        self,
        log_cb: LogCallback,
        network_provider: Callable[[], NetworkConfig],
        on_ack_sent: Optional[Callable[[str, str], None]] = None,
    ):
        super().__init__(daemon=True)
        self.log_cb = log_cb
        self.network_provider = network_provider
        self.on_ack_sent = on_ack_sent
        self._stop_event = threading.Event()
        self.sock: Optional[socket.socket] = None
        self.pending_leases: dict = {}
        self.active_leases: dict = {}

    def stop(self):
        self._stop_event.set()
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass

    def run(self):
        try:
            net = self.network_provider()
            bind_ip = (net.local_ip or "").strip()
            if not bind_ip:
                self.log_cb("error", "DHCP startup failed: local_ip is empty")
                return
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            self.sock.settimeout(2.0)
            # Initial DHCP Discover targets 255.255.255.255 from 0.0.0.0. On Windows,
            # a socket bound to one unicast address can miss that limited broadcast.
            # Listen on all local addresses, but bind every reply to the gated NIC below.
            self.sock.bind(("", 67))
            self.log_cb("success", f"DHCP server started on 0.0.0.0:67; reply NIC {bind_ip}")
        except Exception as exc:
            _log_dhcp_bind_failure(self.log_cb, exc)
            return
        while not self._stop_event.is_set():
            try:
                data, addr = self.sock.recvfrom(1024)
            except socket.timeout:
                continue
            except Exception as exc:
                self.log_cb("warning", f"DHCP recv loop stopped: {exc}")
                break
            try:
                self._handle_dhcp_packet(data)
            except Exception as exc:
                self.log_cb("warning", f"DHCP handler error: {exc}")

    def _handle_dhcp_packet(self, data: bytes):
        if len(data) < 240 or data[0] != 1:
            return
        magic_pos = data.find(self.MAGIC, 236)
        if magic_pos == -1:
            return

        now = time.time()
        expired = [x for x, v in self.pending_leases.items() if v["expire"] < now]
        for x in expired:
            entry = self.pending_leases[x]
            self.log_cb("info", f"DHCP pending lease expired: {entry['mac']} (xid={x:#010x})")
            del self.pending_leases[x]

        options_raw = data[magic_pos + 4 :]
        parsed = self._parse_options(options_raw)
        msg_type = self._option_byte(parsed, 53)
        if msg_type is None:
            return

        xid = self._xid_int(data)
        chaddr = data[28:34]
        mac = ":".join(f"{byte:02X}" for byte in chaddr)
        net = self.network_provider()

        if msg_type == 1:
            self._handle_discover(data, xid, mac, net, now)
        elif msg_type == 3:
            self._handle_request(data, xid, mac, net, parsed, now)
        elif msg_type == 4:
            self._handle_decline(mac)

    def _handle_discover(self, data: bytes, xid: int, mac: str, net: NetworkConfig, now: float):
        self.log_cb("info", f"DHCP Discover from MAC: {mac}")
        if xid in self.pending_leases:
            old = self.pending_leases[xid]
            self.log_cb("info", f"DHCP Discover reuses xid={xid:#010x}, overwriting pending lease for {old['mac']}")
        self.pending_leases[xid] = {
            "mac": mac,
            "bmc_ip": net.bmc_ip,
            "expire": now + _PENDING_SECONDS,
        }
        payload = self._build_reply(data, net, net.bmc_ip, 2)
        broadcast = _subnet_broadcast_addr(net.local_ip, net.prefix_length)
        result = self._send_dhcp_reply(payload, net.local_ip, broadcast)
        if result:
            self.log_cb("info", f"DHCP OFFER {net.bmc_ip} to {mac} via {result}")
        else:
            self.log_cb("warning", f"DHCP OFFER send failed for {mac} (target {net.bmc_ip})")

    def _handle_request(
        self,
        data: bytes,
        xid: int,
        mac: str,
        net: NetworkConfig,
        parsed: dict[int, bytes],
        now: float,
    ):
        self.log_cb("info", f"DHCP Request from MAC: {mac}")
        option_50 = parsed.get(50)
        option_54 = parsed.get(54)
        broadcast = _subnet_broadcast_addr(net.local_ip, net.prefix_length)

        if option_54 is not None:
            pending = self.pending_leases.get(xid)
            if not pending:
                self.log_cb(
                    "warning",
                    f"DHCP Request from {mac}: no pending lease for xid={xid:#010x} (option 54), ignored",
                )
                return
            bmc_ip = pending["bmc_ip"]
            del self.pending_leases[xid]
            self.active_leases[mac] = {"ip": bmc_ip, "expire": now + _LEASE_SECONDS}
            payload = self._build_reply(data, net, bmc_ip, 5)
            self._send_reply_and_log(payload, net.local_ip, broadcast, mac, bmc_ip, is_ack=True)
            return

        if option_50 is not None:
            requested_ip = socket.inet_ntoa(option_50[:4])
            if requested_ip == net.bmc_ip:
                self.log_cb("info", f"DHCP INIT-REBOOT: {mac} 请求地址匹配 {net.bmc_ip}，直接 ACK")
                self.active_leases[mac] = {"ip": net.bmc_ip, "expire": now + _LEASE_SECONDS}
                payload = self._build_reply(data, net, net.bmc_ip, 5)
                self._send_reply_and_log(payload, net.local_ip, broadcast, mac, net.bmc_ip, is_ack=True)
            else:
                self.log_cb(
                    "warning",
                    f"DHCP INIT-REBOOT: {mac} 请求 {requested_ip}，"
                    f"当前推导地址为 {net.bmc_ip}，发送 NAK 强制重新 Discover",
                )
                payload = self._build_reply(data, net, "0.0.0.0", 6)
                sent_via = self._send_dhcp_reply(payload, net.local_ip, broadcast)
                if sent_via:
                    self.log_cb("info", f"DHCP NAK sent to {mac} via {sent_via}")
                else:
                    self.log_cb("warning", f"DHCP NAK send failed for {mac}")
            return

        self.log_cb(
            "warning",
            f"DHCP Request from {mac}: 既无 option_54 也无 option_50，协议异常，仍直接分配 ACK",
        )
        self.active_leases[mac] = {"ip": net.bmc_ip, "expire": now + _LEASE_SECONDS}
        payload = self._build_reply(data, net, net.bmc_ip, 5)
        self._send_reply_and_log(payload, net.local_ip, broadcast, mac, net.bmc_ip, is_ack=True)

    def _handle_decline(self, mac: str):
        released_ip = self.active_leases.pop(mac, {}).get("ip", "unknown")
        self.log_cb(
            "warning",
            f"DHCP Decline from MAC: {mac}, released IP: {released_ip}，可能存在 IP 冲突，建议检查网络拓扑或重启 BMC",
        )

    def _send_reply_and_log(
        self,
        payload: bytes,
        local_ip: str,
        subnet_broadcast: str,
        mac: str,
        bmc_ip: str,
        *,
        is_ack: bool,
    ):
        sent_via = self._send_dhcp_reply(payload, local_ip, subnet_broadcast)
        if sent_via:
            if is_ack:
                self.log_cb("success", f"Assigned {bmc_ip} to {mac}; local IP {local_ip} via {sent_via}")
                if self.on_ack_sent is not None:
                    self.on_ack_sent(mac, bmc_ip)
        else:
            self.log_cb("warning", f"DHCP reply send failed for {mac}")

    def _build_reply(
        self,
        data: bytes,
        net: NetworkConfig,
        yiaddr: str,
        dhcp_msg_type: int,
    ) -> bytes:
        reply = bytearray(300)
        reply[0] = 2
        reply[1] = data[1]
        reply[2] = data[2]
        reply[3] = data[3]
        reply[4:8] = data[4:8]
        reply[10:12] = b"\x80\x00"
        reply[16:20] = socket.inet_aton(yiaddr)
        reply[20:24] = socket.inet_aton(net.local_ip)
        reply[28:34] = data[28:34]
        reply[236:240] = self.MAGIC
        p = 240
        p = self._put_option(reply, p, 53, bytes([dhcp_msg_type]))
        p = self._put_option(reply, p, 54, socket.inet_aton(net.local_ip))
        if dhcp_msg_type != 6:
            p = self._put_option(reply, p, 51, bytes([0, 1, 81, 128]))
            p = self._put_option(reply, p, 1, socket.inet_aton(net.subnet_mask))
            p = self._put_option(reply, p, 3, socket.inet_aton(net.local_ip))
            p = self._put_option(reply, p, 6, socket.inet_aton(net.local_ip))
        reply[p] = 255
        p += 1
        return bytes(reply[:p])

    def _send_dhcp_reply(self, payload: bytes, local_ip: str, subnet_broadcast: str) -> Optional[str]:
        sock = None
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.bind((local_ip, 0))
        except Exception as e:
            self.log_cb("warning", f"DHCP reply socket bind failed ({local_ip}): {e}")
            if sock:
                try:
                    sock.close()
                except Exception:
                    pass
            self.log_cb(
                "warning",
                "DHCP reply suppressed because the selected NIC could not be bound; "
                "refusing an unrestricted fallback",
            )
            return None
        try:
            sent_to = []
            for dest in (subnet_broadcast, "255.255.255.255"):
                try:
                    sock.sendto(payload, (dest, 68))
                    sent_to.append(dest)
                except Exception:
                    continue
            return sent_to[0] if sent_to else None
        finally:
            try:
                sock.close()
            except Exception:
                pass

    @staticmethod
    def _xid_int(data: bytes) -> int:
        return int.from_bytes(data[4:8], "big")

    @staticmethod
    def _parse_options(options: bytes) -> dict[int, bytes]:
        parsed: dict[int, bytes] = {}
        i = 0
        while i < len(options):
            opt = options[i]
            if opt == 255:
                break
            if opt == 0:
                i += 1
                continue
            if i + 1 >= len(options):
                break
            length = options[i + 1]
            if i + 2 + length > len(options):
                break
            parsed[opt] = options[i + 2 : i + 2 + length]
            i += 2 + length
        return parsed

    @staticmethod
    def _option_byte(parsed: dict[int, bytes], opt: int) -> Optional[int]:
        value = parsed.get(opt)
        if value is None or len(value) != 1:
            return None
        return value[0]

    @staticmethod
    def _put_option(reply: bytearray, pos: int, opt: int, value: bytes) -> int:
        reply[pos : pos + 2 + len(value)] = bytes([opt, len(value)]) + value
        return pos + 2 + len(value)
