# This module will be the initial forwarding plane implementation for our software router
import ipaddress
import random
import time
from typing import Type, Optional

import dpkt
import socket


class ForwardingPlane:
    def __init__(self, *, sock: Type[socket.socket]=socket.socket):
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

    def _send_udp(self, dest_ip: str, data: bytes, dest_port: int, src_port: Optional[int] = None):
        udp = dpkt.udp.UDP()
        if src_port is not None:
            udp.sport = src_port
        udp.dport = dest_port
        udp.data = data
        udp.ulen = len(udp)


        with self._sock(socket.AF_INET, socket.SOCK_RAW, dpkt.ip.IP_PROTO_UDP) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.sendto(bytes(udp), (dest_ip, dest_port))



if __name__ == "__main__":
    fp = ForwardingPlane()
    # fp._send_udp('10.1.1.1', "hello".encode(), 520, 520)

    rip = dpkt.rip.RIP()
    rip.cmd = dpkt.rip.RESPONSE
    rip.v = 1

    rte = dpkt.rip.RTE()
    rte.family = 2
    rte.addr = int(ipaddress.ip_address('10.0.0.0'))
    rte.next_hop = int(ipaddress.ip_address('0.0.0.0'))
    rte.metric = 1
    rip.rtes = [rte]
    rip.rsvd = 0
    rip.auth = None
    udp = dpkt.udp.UDP()
    udp.sport = 520
    udp.dport = 520
    udp.data = bytes(rip)
    while True:
        fp._send_udp('255.255.255.255', bytes(rip), 520, 520)
        time.sleep(10)
