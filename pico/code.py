# s2wkjb Pico W captive-portal lab - CircuitPython version
# --------------------------------------------------------
# Same pocket lab as pico/main.py (MicroPython), rewritten for
# CircuitPython, which is what is actually on this Pico
# (the drive shows up as CIRCUITPY).
#
# The Pico broadcasts its own Wi-Fi, hands out IP addresses (DHCP),
# answers every DNS query with its own address, and serves the
# fingerprint + test-attempt page to the Switch's captive-portal
# browser (WifiWebAuthApplet).
#
# Copy this file to the Pico as code.py. CircuitPython runs code.py
# on boot (and reloads it when the file changes). On this Pico 2 W
# the file that actually runs has been boot.py, so use that name
# there if code.py does not take.
# No laptop needed once CircuitPython is on the Pico.
#
# What it does NOT do: no exploit payloads. The 12 Userland buttons
# are attempts to try, and they only log the tap on the page.
# The fingerprint decides which attempt to build for real first.
#
# If this file crashes on startup, the reason is written to
# error.txt on the CIRCUITPY drive. Send that file to Sam.

import sys
import time

import board
import digitalio
import socketpool
import wifi

SSID = "WebHacks"
DNS_PORT = 53
HTTP_PORT = 80
DHCP_PORT = 67
SERVER_IP = "192.168.4.1"
LEASE_TIME = 3600

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


# --- Minimal DHCP server ---
# Without this the Switch joins the Wi-Fi but never gets an IP
# address, so its connection test fails with 2110-1100 before it
# ever asks for the portal page. This hands out 192.168.4.x,
# gateway + DNS 192.168.4.1 (the Pico itself).

_leases = {}   # client MAC bytes -> IP string
_next_host = [2]


def _ip_bytes(s):
    return bytes(int(x) for x in s.split("."))


def _parse_dhcp_options(pkt):
    opts = {}
    i = 240
    while i + 1 < len(pkt):
        code = pkt[i]
        if code == 0:
            i += 1
            continue
        if code == 255:
            break
        ln = pkt[i + 1]
        opts[code] = pkt[i + 2:i + 2 + ln]
        i += 2 + ln
    return opts


def _build_dhcp_reply(req, msg_type, yiaddr):
    xid = req[4:8]
    flags = req[10:12]
    chaddr = req[28:44]
    yiaddr_b = _ip_bytes(yiaddr)
    siaddr_b = _ip_bytes(SERVER_IP)
    header = (b"\x02\x01\x06\x00" + xid + b"\x00\x00" + flags +
              b"\x00\x00\x00\x00" + yiaddr_b + siaddr_b +
              b"\x00\x00\x00\x00" + chaddr + b"\x00" * 64 + b"\x00" * 128)
    opts = (b"\x63\x82\x53\x63" +
            b"\x35\x01" + bytes([msg_type]) +
            b"\x36\x04" + siaddr_b +
            b"\x33\x04" + LEASE_TIME.to_bytes(4, "big") +
            b"\x01\x04" + b"\xff\xff\xff\x00" +
            b"\x03\x04" + siaddr_b +
            b"\x06\x04" + siaddr_b +
            b"\xff")
    pkt = header + opts
    if len(pkt) < 300:
        pkt += b"\x00" * (300 - len(pkt))
    return pkt


def _offer_ip(chaddr):
    if chaddr in _leases:
        return _leases[chaddr]
    host = _next_host[0]
    _next_host[0] = host + 1 if host < 100 else 2
    ip = "192.168.4.%d" % host
    _leases[chaddr] = ip
    return ip


def handle_dhcp_request(pkt):
    # Returns (reply_bytes, yiaddr) or None.
    if len(pkt) < 240:
        return None
    if pkt[236:240] != b"\x63\x82\x53\x63":
        return None
    if pkt[0] != 1:
        return None
    opts = _parse_dhcp_options(pkt)
    msg = opts.get(53)
    if not msg:
        return None
    mtype = msg[0]
    chaddr = bytes(pkt[28:34])
    if mtype == 1:  # DISCOVER -> OFFER
        ip = _offer_ip(chaddr)
        return _build_dhcp_reply(pkt, 2, ip), ip
    if mtype == 3:  # REQUEST -> ACK
        req_ip = opts.get(50)
        if req_ip and len(req_ip) == 4:
            ip = "%d.%d.%d.%d" % (req_ip[0], req_ip[1], req_ip[2], req_ip[3])
            if ip.startswith("192.168.4."):
                _leases[chaddr] = ip
            else:
                ip = _offer_ip(chaddr)
        else:
            ip = _offer_ip(chaddr)
        return _build_dhcp_reply(pkt, 5, ip), ip
    return None


def _arm_socket(sock):
    # Prefer a short timeout; fall back to non-blocking mode if the
    # firmware's socket does not offer settimeout.
    try:
        sock.settimeout(0.05)
    except (AttributeError, NotImplementedError, OSError):
        sock.setblocking(False)


def run():
    wifi.radio.start_ap(ssid=SSID)
    ip = str(wifi.radio.ipv4_address_ap)
    print("WebHacks AP up:", ip)

    pool = socketpool.SocketPool(wifi.radio)

    dns_sock = pool.socket(pool.AF_INET, pool.SOCK_DGRAM)
    dns_sock.bind(("0.0.0.0", DNS_PORT))
    _arm_socket(dns_sock)

    dhcp_sock = pool.socket(pool.AF_INET, pool.SOCK_DGRAM)
    dhcp_sock.bind(("0.0.0.0", DHCP_PORT))
    _arm_socket(dhcp_sock)

    http_sock = pool.socket(pool.AF_INET, pool.SOCK_STREAM)
    http_sock.bind(("0.0.0.0", HTTP_PORT))
    http_sock.listen(5)
    _arm_socket(http_sock)

    try:
        with open("status.txt", "w") as f:
            f.write("WebHacks AP is up. SSID: " + SSID + " IP: " + ip + "\n")
    except OSError:
        pass

    led = digitalio.DigitalInOut(board.LED)
    led.direction = digitalio.Direction.OUTPUT
    print("Serving captive portal. Join the WebHacks Wi-Fi.")
    n = 0
    while True:
        try:
            data, addr = dhcp_sock.recvfrom(1024)
            out = handle_dhcp_request(data)
            if out:
                reply, yiaddr = out
                try:
                    dhcp_sock.sendto(reply, ("255.255.255.255", 68))
                except OSError:
                    dhcp_sock.sendto(reply, (yiaddr, 68))
        except OSError:
            pass
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
            led.value = not led.value
        time.sleep(0.05)


def main():
    try:
        run()
    except Exception as e:
        try:
            with open("error.txt", "w") as f:
                f.write("code.py crashed. Send this file to Sam:\n")
                f.write(repr(e) + "\n")
                try:
                    sys.print_exception(e, f)
                except Exception:
                    try:
                        import traceback
                        traceback.print_exception(
                            type(e), e, e.__traceback__, file=f)
                    except Exception:
                        pass
        except Exception:
            pass
        raise


if __name__ == "__main__":
    main()
