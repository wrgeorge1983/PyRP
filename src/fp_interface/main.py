# This module will be the initial forwarding plane implementation for our software router
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
        self, dest_ip: str, data: bytes, dest_port: int, src_port: Optional[int] = None
    ):
        udp = dpkt.udp.UDP()
        if src_port is not None:
            udp.sport = src_port
        udp.dport = dest_port
        udp.data = data
        udp.ulen = len(udp)

        with self._sock(socket.AF_INET, socket.SOCK_RAW, dpkt.ip.IP_PROTO_UDP) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.sendto(bytes(udp), (dest_ip, dest_port))

    async def listen_udp(self, src_port: int, callback: callable):
        log.info(f"listen_udp: src_port={src_port}")
        async with await anyio.create_udp_socket(
            local_port=src_port, local_host="0.0.0.0", reuse_port=True
        ) as sock:
            async for packet, (host, port) in sock:
                log.info(f"received {packet} from {host}:{port}, calling callback")
                callback(packet, (host, port))

        # anyio.run(self._listen_udp, src_port, callback)

        # with self._sock(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        #     sock.bind(("0.0.0.0", src_port))
        #     while True:
        #         data, addr = sock.recvfrom(1024)
        #         callback(data, addr)


# if __name__ == "__main__":
# import socket
# listen_addr = "0.0.0.0"
# listen_port = 520
# sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
# sock.bind((listen_addr, listen_port))
# print('asdf')
# while True:
#     data, addr = sock.recvfrom(1024)
#     print(f"Received {data} from {addr}")
#     time.sleep(10)
#     sock.sendto(data, addr)
