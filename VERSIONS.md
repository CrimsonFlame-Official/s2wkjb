# s2wkjb version table

Fill this in only from actual fingerprint captures, not from guesses.

| Date | Firmware | Applet | User-Agent | WebKit version | Notes |
|------|----------|--------|------------|----------------|-------|
| 2026-11-20 | 23.0.1 or earlier (his report, 2026-11-12) | WifiWebAuthApplet | Mozilla/5.0 (Nintendo Switch; WifiWebAuthApplet) AppleWebKit/613.0 (KHTML, like Gecko) NF/7.0.3.12.11 NintendoBrowser/5.2.0.55481 | AppleWebKit/613.0 | First real fingerprint, captured live via the Pico W captive-portal lab. Photo of the Switch screen; he corrected the NF segment from the photo himself (7.0.3.12.11). JS fields: language en-US, 4 CPU cores, 0 touch points, cookies true, screen 1920x1080, available 1920x972, color/pixel depth 32, pixel ratio 1. |
|      |          |        |            |                |       |

## How to capture

1. Run `lab/captive_portal_lab.py` on a PC.
2. Point the Switch DNS at that PC.
3. Connect to the network, load the captive portal page.
4. Copy the User-Agent logged by the server into this table.
