# s2wkjb Pico W captive-portal lab
# --------------------------------
# A Raspberry Pi Pico W running MicroPython becomes a pocket lab:
# it broadcasts its own Wi-Fi, answers every DNS query with its own
# address, and serves the fingerprint + test-attempt page to the
# Switch's captive-portal browser (WifiWebAuthApplet).
#
# Copy this file to the Pico as main.py. It runs on boot.
# No laptop needed once MicroPython is flashed.
#
# What it does NOT do: no exploit payloads. The 12 Userland buttons
# are attempts to try, and they only log the tap on the page.
# The fingerprint decides which attempt to build for real first.

import network
import socket
import time
import machine

SSID = "WebHacks"
DNS_PORT = 53
HTTP_PORT = 80

PAGE = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Web Hacks - Fingerprint</title>
<style>
body{font-family:sans-serif;margin:16px;background:#111;color:#eee}
h1{font-size:30px;margin:8px 0}
h2{font-size:24px;margin-top:28px}
p{font-size:18px;line-height:1.4}
.label{font-size:15px;color:#999;margin-top:16px}
.big{font-size:22px;word-break:break-all;background:#222;padding:12px;border-radius:8px}
.val{font-size:20px;word-break:break-all}
button{display:block;width:100%;font-size:19px;padding:14px;margin:8px 0;border-radius:8px;border:1px solid #555;background:#1e2a38;color:#fff;text-align:left}
#log{font-size:17px;background:#222;padding:12px;border-radius:8px;min-height:44px}
.warn{background:#3a1d1d;border:1px solid #a33;padding:12px;border-radius:8px}
</style>
</head>
<body>
<h1>Web Hacks - Fingerprint</h1>
<p>Take a photo of this screen and send it to Sam. The portal closes after about 20 minutes, so snap it before then.</p>
<div class="label">USER AGENT - from this request</div>
<div class="big">{{UA}}</div>
<div class="label">USER AGENT - from JavaScript</div>
<div class="big" id="ua-js">loading...</div>
<div id="fp"></div>
<h2>Userland attempts - tap to try</h2>
<p>Attempts to try, not working exploits. Tap one. If it does nothing, try the next one.</p>
<div id="buttons"></div>
<div id="log">No attempt tapped yet.</div>
<h2>Danger - kernel</h2>
<p class="warn">Do NOT run these on your main Switch. Kernel tests are for spare consoles only. These are placeholders, not working exploits.</p>
<div id="danger"></div>
<script>
var attempts = ["Integer overflow","Use-after-free","Type confusion","Out-of-bounds buffer","Heap grooming","JIT bug","Font / CSS parsing","Media decoding","DOM use-after-free","Double free","N-day CVE test","Fuzzing"];
var danger = ["Privileged sysmodule escalation","Syscall bug","Kernel object use-after-free","TrustZone / secure monitor","Driver bug"];
document.getElementById("ua-js").textContent = navigator.userAgent;
var rows = [
["Platform", navigator.platform],
["Language", navigator.language],
["Languages", (navigator.languages || []).join(", ")],
["CPU cores", navigator.hardwareConcurrency],
["Touch points", navigator.maxTouchPoints],
["Cookies", navigator.cookieEnabled],
["Screen", screen.width + " x " + screen.height],
["Available", screen.availWidth + " x " + screen.availHeight],
["Color depth", screen.colorDepth],
["Pixel depth", screen.pixelDepth],
["Pixel ratio", window.devicePixelRatio],
["Window", window.innerWidth + " x " + window.innerHeight],
["Timezone offset", new Date().getTimezoneOffset()]
];
var html = "";
for (var i = 0; i < rows.length; i++) {
html += '<div class="label">' + rows[i][0] + '</div><div class="val">' + rows[i][1] + '</div>';
}
document.getElementById("fp").innerHTML = html;
function mk(list, parent) {
var p = document.getElementById(parent);
for (var i = 0; i < list.length; i++) {
(function(name) {
var b = document.createElement("button");
b.textContent = name;
b.onclick = function() {
document.getElementById("log").textContent = "Tapped: " + name + " - placeholder, logs only. If it does nothing, try the next one.";
};
p.appendChild(b);
})(list[i]);
}
}
mk(attempts, "buttons");
mk(danger, "danger");
</script>
</body>
</html>
"""


def html_escape(s):
    return (s.replace("&", "&amp;")
             .replace("<", "&lt;")
             .replace(">", "&gt;")
             .replace('"', "&quot;"))


def render_page(ua):
    safe = html_escape(ua) if ua else "(no User-Agent header received)"
    return PAGE.replace("{{UA}}", safe)


def build_dns_response(query, ip):
    # Minimal DNS responder: answers any A query with the Pico's IP.
    # Returns response bytes, or None if the query is not answerable.
    if len(query) < 12:
        return None
    tid = query[0:2]
    qdcount = (query[4] << 8) | query[5]
    if qdcount != 1:
        return None
    i = 12
    while i < len(query):
        ln = query[i]
        if ln == 0:
            i += 1
            break
        i += 1 + ln
    if i + 4 > len(query):
        return None
    qtype = (query[i] << 8) | query[i + 1]
    question = query[12:i + 4]
    ancount = 1 if qtype == 1 else 0
    header = (tid + b"\x81\x80" + b"\x00\x01" +
              (b"\x00\x01" if ancount else b"\x00\x00") +
              b"\x00\x00\x00\x00")
    resp = header + question
    if ancount:
        ipb = bytes(int(x) for x in ip.split("."))
        resp += (b"\xc0\x0c" + b"\x00\x01\x00\x01" +
                 b"\x00\x00\x00\x3c" + b"\x00\x04" + ipb)
    return resp


def handle_http_request(req):
    ua = ""
    try:
        text = req.decode("utf-8", "ignore")
        for line in text.split("\r\n"):
            if line.lower().startswith("user-agent:"):
                ua = line.split(":", 1)[1].strip()
                break
    except Exception:
        ua = ""
    body = render_page(ua).encode("utf-8")
    head = ("HTTP/1.1 200 OK\r\n"
            "Content-Type: text/html; charset=utf-8\r\n"
            "Cache-Control: no-store\r\n"
            "Content-Length: %d\r\n"
            "Connection: close\r\n\r\n" % len(body))
    return head.encode("utf-8") + body


def run():
    ap = network.WLAN(network.AP_IF)
    ap.active(True)
    ap.config(essid=SSID)
    while not ap.active():
        time.sleep(0.1)
    ip = ap.ifconfig()[0]
    print("WebHacks AP up:", ip)

    dns_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    dns_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    dns_sock.bind(("0.0.0.0", DNS_PORT))
    dns_sock.settimeout(0.05)

    http_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    http_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    http_sock.bind(("0.0.0.0", HTTP_PORT))
    http_sock.listen(5)
    http_sock.settimeout(0.05)

    led = machine.Pin("LED", machine.Pin.OUT)
    print("Serving captive portal. Join the WebHacks Wi-Fi.")
    n = 0
    while True:
        try:
            data, addr = dns_sock.recvfrom(512)
            resp = build_dns_response(data, ip)
            if resp:
                dns_sock.sendto(resp, addr)
        except OSError:
            pass
        try:
            conn, addr = http_sock.accept()
            conn.settimeout(2)
            try:
                req = b""
                while b"\r\n\r\n" not in req and len(req) < 8192:
                    chunk = conn.recv(1024)
                    if not chunk:
                        break
                    req += chunk
                conn.sendall(handle_http_request(req))
            except OSError:
                pass
            try:
                conn.close()
            except OSError:
                pass
        except OSError:
            pass
        n += 1
        if n % 20 == 0:
            led.value(not led.value())


if __name__ == "__main__":
    run()
