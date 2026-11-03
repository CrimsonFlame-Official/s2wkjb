#!/usr/bin/env python3
"""
s2wkjb lab server - benign captive portal test only.

Answers DNS queries for conntest.nintendowifi.net with this PC's IP,
serves a simple test page over HTTP, and logs the User-Agent of
anything that connects. No exploit payload is included.

Usage (on a PC on the same network as the Switch):
    sudo python3 captive_portal_lab.py --ip <this-PC-IP>

Then on the Switch, set the Wi-Fi DNS to <this-PC-IP> and use
"Connect to this Network". The Switch should show
"Registration is required to use this network" and load the test page.

Requires root/admin only because DNS uses UDP port 53 and HTTP
uses TCP port 80.
"""
import argparse
import http.server
import socket
import socketserver
import struct
import threading

PAGE = b"""<!doctype html>
<html><head><meta charset="utf-8"><title>s2wkjb lab</title></head>
<body><h1>s2wkjb lab page loaded</h1>
<p>If you see this on the Switch, the captive portal entry works.</p>
<script>document.write('<p>User-Agent: ' + navigator.userAgent + '</p>');</script>
</body></html>
"""


class DNSHandler(socketserver.BaseRequestHandler):
    def handle(self):
        data, sock = self.request
        if len(data) < 12:
            return
        tid, flags, qdcount = struct.unpack(">HHH", data[:6])
        # Only answer the first question, for any name, with our IP.
        # The Switch only asks for conntest.nintendowifi.net here.
        question = data[12:]
        # Build a minimal response: 1 answer, A record, TTL 60.
        header = struct.pack(">HHHHHH", tid, 0x8180, qdcount, 1, 0, 0)
        # Answer: pointer to question name (0xc00c), type A, class IN,
        # TTL 60, length 4, then the IP bytes.
        answer = struct.pack(">HHHIH", 0xC00C, 1, 1, 60, 4) + socket.inet_aton(self.server.ip)
        sock.sendto(header + question + answer, self.client_address)


class HTTPHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        ua = self.headers.get("User-Agent", "(no user agent)")
        print(f"[http] {self.client_address[0]} UA: {ua}", flush=True)
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(PAGE)))
        self.end_headers()
        self.wfile.write(PAGE)

    def log_message(self, *args):
        pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ip", required=True, help="IP of this PC on the Switch network")
    args = ap.parse_args()

    dns = socketserver.UDPServer(("0.0.0.0", 53), DNSHandler)
    dns.ip = args.ip
    threading.Thread(target=dns.serve_forever, daemon=True).start()
    print(f"[dns] answering with {args.ip} on UDP 53", flush=True)
    print("[http] serving lab page on TCP 80", flush=True)
    print("Point the Switch DNS at this PC, then Connect to this Network.", flush=True)
    http.server.HTTPServer(("0.0.0.0", 80), HTTPHandler).serve_forever()


if __name__ == "__main__":
    main()
