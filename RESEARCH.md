# s2wkjb research notes - Web Hack

Status: research in progress. No exploit found yet. No jailbreak claimed.
This file is a checklist, not a payload. Nothing here is tested on
Switch 2 yet.

## Entry point

- Target applet: WifiWebAuthApplet, the captive portal applet.
- Why: no whitelist, unlike LoginApplet, ShareApplet, LobbyApplet,
  and WebApplet.
- Trigger: Switch pings conntest.nintendowifi.net on connect. If the
  reply is missing Nintendo's header, the Switch shows
  "Registration is required to use this network" and opens the applet.
- Delivery: point the Switch DNS at a PC lab server (see `lab/`),
  serve an HTTP page. No cable, no cartridge, no delisted app.
- Target firmware for now: 23.0.1.

## Step 1: fingerprint first

Before any exploit test, capture what the applet actually is:

- User-Agent header and JS navigator.userAgent
- Platform, language, screen size, devicePixelRatio
- Any other JS navigator info the page is allowed to see

That version determines which known WebKit bugs are even plausible.
The lab server in `lab/` already logs this on first connect.

## Userland tab - test ideas

Goal: code execution inside WebKit / as a userland sysmodule.
This is enough for homebrew, modding, and save backups, as ns2jb
shows. Kernel access is not required for userland to be useful.
A crash is not an escape. A repeatable crash is a lead.

1. Integer overflow / underflow in array lengths, counts, offsets.
2. Use-after-free, including CSSFontFace-style object reuse.
3. Type confusion, including addrof / fakeobj primitives.
4. Out-of-bounds read/write via typed arrays and buffers.
5. Heap grooming / spray, as a setup helper for the above.
6. JIT optimization bugs, where the optimizer guesses a type wrong.
7. Font / CSS parsing bugs.
8. Image / media decoding bugs.
9. DOM use-after-free, including teardown / reflow triggers.
10. Double free, corrupting the allocator free list.
11. Known n-day CVEs matching the exact WebKit version found in
    fingerprinting, tested first before inventing new bugs.
12. Fuzzing: mutated JS, DOM, and CSS inputs, watching for crashes.

## Danger / Kernel tab - research directions only

Goal: kernel access, which can then be used to install persistence.
Kernel access alone is not automatically permanent. Persistence
requires installing something from kernel, which then lasts until
the original OS is flashed back.

WARNING: kernel tests can cause bans, soft bricks, data loss, and
hard bricks. Do not run kernel tests on a primary Switch, a primary
account, or a Switch with saves you care about. Back up first,
stay offline while testing, and get informed consent from any
tester before they run anything.

1. Privileged sysmodule to kernel escalation via IPC.
2. Kernel syscall argument validation bugs.
3. Kernel object use-after-free / double free.
4. TrustZone / secure monitor attacks - highest brick risk.
5. Driver / peripheral bugs reachable from userland.

No public Switch 2 kernel exploit exists yet. These are directions
to research, not working exploits.

## Tethered vs untethered

- Web Hack entry needs no cable, just Wi-Fi. In that everyday
  sense it is untethered.
- In the strict jailbreak sense, WebKit code execution does not
  survive a reboot. You must re-run the page after reboot.
- True untethered means a persistent install that fires on boot.
  That requires kernel-level install, not just a WebKit page.

## Ban vs brick

- Account ban: that account loses online access. Switching accounts
  on the same console does not fix a console ban.
- Console ban: the device itself is flagged. No account on that
  console can go online on it, even a new or alternate account.
- Soft brick: console will not boot normally, often fixable by
  recovery or reflashing the original OS, with possible save loss.
- Hard brick: boot chain / NAND corrupted, console may not boot
  at all. This is the main risk in the Danger tab.

Using an alternate account protects a primary account from an
account-only ban. It does not protect the console from a console
ban. Staying offline while testing is the main protection for
the console itself.

## Tester plan

- Userland tests: developer's own Switch first.
- Kernel tests: only volunteers with a spare Switch 2 they can
  afford to lose, with full warning, backup, and offline testing.
- No tester should run a kernel test blind, and no tester should
  be pressured to run a test they do not understand.

## Switch 1 port - later, not automatic

Many Switch 2 userland exploits are also Switch 1 exploits, because
Switch 2 runs Switch 1 software through backward compatibility.
SmileBASIC 4 is the example: a Switch 1 app, a Switch 1 bug, used
on Switch 2.

If Web Hack works on Switch 2, porting to Switch 1 is the next
project, not a free result. Firmware, addresses, and sysmodule
versions differ, and Switch 2 mitigations like PAC / CFI / XOM
are stronger in some places.

If a persistent version ever worked on Switch 1, it would matter
for patched units that never had a jig softmod: V2 (Mariko),
Switch OLED, and Switch Lite, all of which currently need a
hardmod chip for custom firmware. V1 launch units already have
the RCM / jig route.

## Roadmap

1. Fingerprint the captive portal applet.
2. Get a userland primitive in WebKit.
3. Chain to a privileged service, like the fs bug ns2jb used.
4. Only then, research kernel escalation and persistence.
5. Only then, port to Switch 1 patched units.
