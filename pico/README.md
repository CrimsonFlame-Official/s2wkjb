# Pico W captive-portal lab (s2wkjb)

A pocket version of the s2wkjb lab: a Raspberry Pi Pico W running MicroPython
broadcasts its own Wi-Fi, answers all DNS with itself, and serves the
fingerprint + test-attempt page to the Switch's captive-portal browser
(WifiWebAuthApplet). No laptop needed once MicroPython is on the Pico.

## What you need

- Raspberry Pi Pico W (the W version, it has Wi-Fi)
- MicroPython already flashed (hold BOOTSEL, drag the UF2 over — one time,
  needs a computer)
- USB cable + power (phone, power bank, or charger)

## Install

1. Plug the Pico into your phone (USB OTG). It shows up as a USB drive.
2. Copy `main.py` onto it, replacing the one that's there.
3. Unplug the Pico and plug it back in (or press reset). It runs `main.py`
   on boot.
4. The Pico broadcasts an open Wi-Fi network called `WebHacks`.

## Use it

1. On the Switch: Settings > Internet > connect to `WebHacks`.
2. The Switch says "Registration is required to use this network" — tap it.
3. The portal opens with the fingerprint page: user agent + device details
   in big text.
4. Take a photo of the screen and send it to Sam. The portal closes after
   about 20 minutes.
5. The 12 Userland attempt buttons are on the same page. They are attempts
   to try, not working exploits — tap one, and if it does nothing, try the
   next one.

## Notes

- The page shows the user agent twice: once from the request itself, once
  from JavaScript. They should match.
- Nothing is uploaded anywhere. The Pico only serves the page on its own
  little network.
- The Danger section is placeholders only, same as the repo's test page.
- No exploit payloads live here. The fingerprint decides which attempt to
  build for real first.
