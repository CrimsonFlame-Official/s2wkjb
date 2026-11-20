"""Fallback test for s2wkjb/pico/code.py (CircuitPython).

When the DHCP port is already taken (as it is when the firmware's
built-in DHCP server holds port 67), run() must still start and
serve HTTP instead of crashing.

The fake socket exposes only socketpool's real API (recvfrom_into /
recv_into, no recv / recvfrom), so a call to the wrong method fails
here exactly like on the Pico.
"""
import importlib.util
import os
import sys
import types

os.chdir("/tmp")

wifi = types.ModuleType("wifi")


class FakeRadio:
    def __init__(self):
        self.ipv4_address_ap = "192.168.4.1"

    def start_ap(self, ssid=None, password=None, **k):
        pass


wifi.radio = FakeRadio()
sys.modules["wifi"] = wifi

socketpool = types.ModuleType("socketpool")
import socket as _socket


class FakeSocket:
    def __init__(self, real):
        self._real = real

    def bind(self, addr):
        return self._real.bind(addr)

    def listen(self, backlog):
        return self._real.listen(backlog)

    def accept(self):
        conn, addr = self._real.accept()
        return FakeSocket(conn), addr

    def close(self):
        return self._real.close()

    def settimeout(self, value):
        return self._real.settimeout(value)

    def setblocking(self, flag):
        return self._real.setblocking(flag)

    def recvfrom_into(self, buf):
        return self._real.recvfrom_into(buf)

    def recv_into(self, buf, bufsize=0):
        if bufsize:
            return self._real.recv_into(buf, bufsize)
        return self._real.recv_into(buf)

    def send(self, data):
        return self._real.send(data)

    def sendall(self, data):
        return self._real.sendall(data)

    def sendto(self, data, addr):
        return self._real.sendto(data, addr)

    def setsockopt(self, level, optname, value):
        return self._real.setsockopt(level, optname, value)


class FakePool:
    AF_INET = _socket.AF_INET
    SOCK_DGRAM = _socket.SOCK_DGRAM
    SOCK_STREAM = _socket.SOCK_STREAM
    SOL_SOCKET = _socket.SOL_SOCKET
    SO_REUSEADDR = _socket.SO_REUSEADDR

    def __init__(self, radio):
        pass

    def socket(self, family, type):
        return FakeSocket(_socket.socket(family, type))


socketpool.SocketPool = FakePool
sys.modules["socketpool"] = socketpool

board = types.ModuleType("board")
board.LED = "LED"
sys.modules["board"] = board

digitalio = types.ModuleType("digitalio")


class FakeDirection:
    OUTPUT = 1


class FakeDIO:
    def __init__(self, pin):
        self.direction = None
        self.value = False


digitalio.DigitalInOut = FakeDIO
digitalio.Direction = FakeDirection
sys.modules["digitalio"] = digitalio

spec = importlib.util.spec_from_file_location(
    "pico_code", "/home/hatch/workspace/s2wkjb/pico/code.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

import threading
import time
import urllib.request

# Occupy the DHCP port first, like the firmware's built-in DHCP server.
blocker = _socket.socket(_socket.AF_INET, _socket.SOCK_DGRAM)
blocker.bind(("127.0.0.1", 53667))

mod.HTTP_PORT = 8082
mod.DNS_PORT = 53537
mod.DHCP_PORT = 53667
t = threading.Thread(target=mod.run, daemon=True)
t.start()
time.sleep(4)  # 5 x 0.3s DHCP retries + startup

req = urllib.request.Request("http://127.0.0.1:8082/",
                             headers={"User-Agent": "FallbackTest/1.0"})
with urllib.request.urlopen(req, timeout=5) as f:
    body = f.read().decode()
    assert "FallbackTest/1.0" in body, "HTTP must still serve with DHCP busy"
print("fallback HTTP OK")

with open("/tmp/status.txt") as f:
    assert "built-in" in f.read(), "status must say the built-in DHCP is in use"
os.remove("/tmp/status.txt")
print("fallback status OK")
print("FALLBACK TEST PASSED")
