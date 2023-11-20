# This module will be the initial forwarding plane implementation for our software router
import asyncio
import ipaddress
import logging
import random
import time
from typing import Type, Optional

import anyio
import dpkt
import socket

log = logging.getLogger(__name__)


class ForwardingPlane:
    def __init__(self, *, sock: Type[socket.socket] = socket.socket):
        self._sock = sock

    @staticmethod
    def get_local_ip() -> str:
        try:
            # Create a new socket using the Internet address family
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            # Try to connect to an IP outside the local network (doesn't actually establish a connection)
            s.connect(("8.8.8.8", 80))
            ip_address = s.getsockname()[0]
            s.close()
            return ip_address
        except Exception:
            return "127.0.0.1"

    def _send_ping(self, dest_ip: str, timeout_seconds: int) -> float:
        icmp_echo = dpkt.icmp.ICMP.Echo()
        icmp_echo.id = random.randint(0, 65535)
        icmp_echo.seq = random.randint(0, 65535)
        icmp_echo.data = b""

        icmp = dpkt.icmp.ICMP()
        icmp.type = dpkt.icmp.ICMP_ECHO
        icmp.data = icmp_echo

        sock = self._sock(socket.AF_INET, socket.SOCK_RAW, dpkt.ip.IP_PROTO_ICMP)
        sock.connect((dest_ip, 1))
        sock.settimeout(1)
        # sock.sendto(bytes(icmp), (dest_ip, 1))
        start = time.time()
        sock.send(bytes(icmp))
        buf = sock.recv(1024)
        rtt = time.time() - start
        sock.close()
        return rtt

    def ping(self, dest_ip: str, timeout_seconds: int = 1) -> float:
        return self._send_ping(dest_ip, timeout_seconds)

    def send_udp(
        self, data: bytes, dest_ip: str, dest_port: int, src_port: Optional[int] = None
    ) -> int:
        udp = dpkt.udp.UDP()
        if src_port is None:
            src_port = random.randint(1024, 65535)

        udp.sport = src_port
        udp.dport = dest_port
        udp.data = data
        udp.ulen = len(udp)

        with self._sock(socket.AF_INET, socket.SOCK_RAW, dpkt.ip.IP_PROTO_UDP) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.sendto(bytes(udp), (dest_ip, dest_port))

        return src_port

    async def listen_udp(self, src_port: int, callback: callable):
        log.info(f"listen_udp: src_port={src_port}")
        async with await anyio.create_udp_socket(
            local_port=src_port, local_host="0.0.0.0", reuse_port=True
        ) as sock:
            async for packet, (host, port) in sock:
                log.info(f"received {packet} from {host}:{port}, calling callback")
                await callback(packet, (host, port))

    async def listen_udp_timed(
        self, src_port: int, callback: callable, timeout_seconds: int
    ):
        try:
            await asyncio.wait_for(self.listen_udp(src_port, callback), timeout_seconds)
        except asyncio.TimeoutError:
            log.info(f"listen_udp_timed: timeout_seconds={timeout_seconds}")
