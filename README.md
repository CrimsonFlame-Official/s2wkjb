# s2wkjb - Web Hack

Switch 2 WebKit research, focused on the captive portal applet.

This is research in progress. Nothing here is a jailbreak yet, and no
exploit is claimed. The goal is to test, in private, whether the
Switch 2 captive portal applet can be used as a WebKit entry point,
and to document what is actually found.

## The idea

The Switch 2 does not have a normal browser you can just open, but it
has several WebKit applets inside the system:

- LoginApplet: whitelisted, only select websites can be loaded.
- ShareApplet and LobbyApplet: whitelisted, locked to Nintendo and
  social sites.
- WebApplet: whitelisted, the launching title decides what it allows.
- WifiWebAuthApplet: the captive portal applet, the "Sign In" browser
  for networks like coffee shops. This one has no whitelist.

WifiWebAuthApplet is the same kind of entry used by PegaSwitch on the
original Switch, and the same entry pepsipu started with on Switch 2
before moving to SmileBASIC. This project revisits that entry, it does
not claim a new discovery of the applet itself.

## How the trigger works

When the Switch connects to a network, it pings
conntest.nintendowifi.net to check the connection. If that reply is
missing Nintendo's header, the Switch shows
"Registration is required to use this network" and opens the captive
portal applet.

Pointing the Switch's DNS at your own server and serving your own page
through that portal is the entry to test. Loading a page is not a
jailbreak on its own. A crash is not an escape.

## What still has to be done

1. Capture the applet's user agent to pin down the WebKit version.
2. Build a PC-only DNS lab (see `lab/`).
3. Test known WebKit bugs that match that version.
4. Get past PAC, CFI, and execute-only memory, then chain to something
   with real privileges, if that is possible at all.

Target firmware for now: 23.0.1.

## Lab

`lab/captive_portal_lab.py` is a simple, benign lab server for a PC on
the same network as the Switch. It answers DNS for
conntest.nintendowifi.net, serves a test page, and logs the user agent
that connects. It contains no exploit payload. It is for testing the
entry point only.

Run it on a PC, point the Switch's DNS at that PC, then trigger
"Connect to this Network" on the Switch.

## Status

Research in progress. No exploit found yet. Updates will be posted
here when something is actually tested, not before.

## More in this repo

- `RESEARCH.md`: full checklist, Userland and Danger / Kernel tabs,
  ban vs brick, tester plan, Switch 1 port notes.
- `lab/test_buttons.html`: test-buttons page structure, Userland
  and Danger tabs, placeholders only, no payloads yet.
- `VERSIONS.md`: version table, blank until a real fingerprint is captured.
- `TESTER_SAFETY.md`: safety sheet and checklist for any tester,
  especially for kernel tests.
