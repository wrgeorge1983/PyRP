# This module will be the initial forwarding plane implementation for our software router
import random
import time

import dpkt
import socket


class ForwardingPlane:
    def __init__(self, *, sock=socket.socket):
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


if __name__ == "__main__":
    fp = ForwardingPlane()
    rtt = fp.ping("8.8.8.8")

    print(f"RTT: {rtt * 1000:.2f}ms")
    print("omfg!")
