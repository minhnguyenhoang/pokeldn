# Experimental Raspberry Pi 4 / 5 radio alternative

This fork adds a Pi-only experimental transport to Decryptu's pokeldn. It uses
the Pi 4's or Pi 5's built-in BCM43455 Wi-Fi, Nexmon firmware, a matching patched
brcmfmac driver, and userspace CCMP/IP/Pia. It does not require an ESP32 or USB Wi-Fi adapter.
The upstream game engine, Pokémon builder, and reference messages do the game work.

## Verified result

On October 21, 2026, a Raspberry Pi 4 Model B / 2 GB completed a Legends Z-A
local trade with a stock Switch 2. The user confirmed Genesect arrived; the Pi
saved the received Litwick. A separate 45-second session and clean departure
also passed. On October 22, 2026, the same Pi completed Scarlet simulated-gift
trades (shiny Koraidon, then shiny Miraidon from the GUI). These are single
hardware/game combinations, not general compatibility.

## Running from the GUI

Pick **Raspberry Pi 4 (Ethernet / SSH)** as the radio in Settings and choose a
Pi connection profile: a private JSON file with `host`, `user`, `identity` (SSH
key), `known_hosts`, `root` (the data directory below), `sudo_password_file`,
and optionally `host_key_alias`, `keys` and `repo` (default `<root>/repo`).
Supported: Z-A Trade (Join), Scarlet/Violet Trade (Join) and Mystery Gift -
Simulated, one Pokémon per run.

Each run starts by syncing this checkout's `pokeldn/`, `bin/`,
`examples/raspberry_pi/` and `vendor/LDN` to `repo` on the Pi, only when their
content changed and never while a radio session is running. The Pi always runs
the code on the desktop, uncommitted edits included. To sync without trading:

```sh
POKEPI_CONNECTION=/path/to/pi-connection.json python bin/pi_remote.py --sync
```

Then, once per Pi (and after kernel updates), as the login user on the Pi:

```sh
POKEPI_ROOT=~/pokemon-pi bash ~/pokemon-pi/repo/examples/raspberry_pi/setup-pi.sh
```

It creates `private/`, builds `runtime/` when missing, checks the firmware,
the driver's kernel version, the keys and the system tools, and runs the offline
checks. It does not build Nexmon or the driver. It also checks that the kernel
packages are held: the patched driver only loads on the kernel it was built for,
so hold them once (`sudo apt-mark hold linux-image-rpi-v8 linux-image-rpi-2712
linux-headers-rpi-v8 linux-headers-rpi-2712`) and `apt upgrade` keeps it.

A Mystery Gift whose card gives the receiver's own trainer (Mew, Darkrai and
others; the GUI turns on Made for the receiving player for them) is made again
on the desktop before the run, for the save the newest received Scarlet/Violet
Pokémon was caught in. The trade host remakes it mid-trade from the console's
offer, but PKHeX runs only on the desktop and the Pi joins instead of hosting.
With no earlier trade, or after switching saves, it goes with the trainer from
Settings until one Pokémon from that save has been traded.

A join that fails before any trade begins is retried: the Pi rescans and
rejoins for up to `POKEPI_RETRY_SECONDS` (150). That covers no matching session
yet, no answer to authentication, association, the LDN handshake or the seat,
and, for Scarlet/Violet, whose search hosts for only 3 to 4 s, the console
handing over the host role. A link code mismatch is reported at once instead,
naming the code the console searches with.

If the patched firmware crashes, the radio restore retries unloading the driver
while its crash recovery holds it, then reloads the stock driver; if it never
frees, the 360-second rollback timer tries again.

### The Pi page

With the Pi radio chosen, the app shows a **Pi** page: a light per check (SSH,
driver against the kernel, Nexmon firmware, kernel hold, code in sync, stock or
patched Wi-Fi driver), each red one saying what to do, and a warning when the
profile's host is the Pi's Wi-Fi address, which a trade takes down. Its buttons
sync the code, run `setup-pi.sh` and restore the stock Wi-Fi driver, and wait
while a trade runs; its log shows the running trade's output with the `[pi]`
lines picked out. Everything goes over the profile's SSH connection. The same
actions from a shell:

```sh
POKEPI_CONNECTION=/path/to/pi-connection.json python bin/pi_remote.py --status   # JSON
POKEPI_CONNECTION=/path/to/pi-connection.json python bin/pi_remote.py --check    # setup-pi.sh
POKEPI_CONNECTION=/path/to/pi-connection.json python bin/pi_remote.py --restore-radio
```

On Windows, `Start pokeldn Pi.cmd` in the checkout starts the app on the Pi
page with the Pi radio and the saved profile chosen (else `POKEPI_CONNECTION`,
else `pi-connection.json` in the app's data folder). It uses a `gui-venv` and
`gui-data` beside the checkout when present; `POKELDN_PYTHON` and
`POKELDN_DATA` override them.

Tested OS: Raspberry Pi OS Bookworm Lite 64-bit, kernel
`6.12.109+rpt-rpi-v8`; Nexmon BCM43455c0 firmware `7_45_206`; Python 3.13.16,
Trio 0.33.0, python-netlink 0.0.15, pycryptodome 3.23.0, zstandard 0.25.0,
and this checkout's vendored LDN (0.0.17).

## Status and prerequisites

This is an advanced source integration. Only joining Legends Z-A and Scarlet
were tested. Violet, other games, Pi models, kernels, hosting, and repeated
unattended trades have not been validated. Some received frames were
rejected during testing; the current counter combines parse and integrity failures.

Raspberry Pi 5 / kernel 6.18 / Debian 13 (Trixie) is supported by this fork,
short of a completed live trade — see
[Running on a Raspberry Pi 5](#running-on-a-raspberry-pi-5-kernel-618--debian-13).
The patched `brcmfmac` driver builds and loads on 6.18, the Nexmon firmware
(from Kali's `firmware-nexmon`) loads, `mon0` monitor mode comes up, and the
stock Wi-Fi driver restores cleanly; `setup-pi.sh` and the offline checks pass.
A full Z-A trade on a Pi 5 has not been completed yet.

Keep Ethernet connected. Radio setup temporarily unloads the normal Wi-Fi driver
and creates `mon0`; it restores the stock driver on exit. Do not run it through
a Wi-Fi-only SSH connection. The scripts expect NetworkManager, systemd, iw, ip,
rfkill, ethtool, flock, and matching kernel headers/build tools.

Prepare a data directory outside the checkout, referred to as `$POKEPI_ROOT`:

* `nexmon/`: build [seemoo-lab/nexmon](https://github.com/seemoo-lab/nexmon),
  specifically `patches/bcm43455c0/7_45_206/nexmon`, and `utilities/nexutil`.
  The firmware must exist at that patch directory's `brcmfmac43455-sdio.bin`.
  On a Pi 5 / Debian 13 the from-source Nexmon build fails (its 2016-era 32-bit
  ARM toolchain needs `libisl.so.10`/`libmpfr.so.4`, which Trixie no longer
  ships); use Kali's prebuilt firmware instead, see
  [Running on a Raspberry Pi 5](#running-on-a-raspberry-pi-5-kernel-618--debian-13).
* `driver/`: the Kali brcmfmac-nexmon-dkms sources at commit
  `b3b2a8622a361cc8929fa3e153f4a87020361472` (tag `kali/6.12.2`). Apply
  `kernel-compat.patch` with `git apply`, then build against the running kernel:
  `make -C /lib/modules/$(uname -r)/build M="$PWD" -j2`.
  The resulting module must be `driver/brcmfmac.ko`. `kernel-compat.patch` is
  version-guarded for both the tested Pi 4 kernel (`6.12.109`) and the Pi 5's
  6.18 line: it applies to the same pinned commit and builds cleanly against
  `6.18.50+rpt-rpi-2712` on Debian 13 (compile-verified on a Pi 5; the radio
  has not been live-traded there). Kernels outside those two lines may still
  need work.
* `runtime/`: a Python 3.13 virtual environment with the dependencies above and
  this repository's `vendor/LDN` installed. Run from a full source checkout.
* `private/`: mode 0700, for persistent CCMP counters and received Pokémon files.

`setup-pi.sh` checks these, but the firmware and driver builds are still manual.
The original successful build needed ARM compiler compatibility libraries. No firmware
binary, compiled module, SDK, or Nintendo key is redistributed in this addition.

Use your own keys file outside the checkout. Never commit it. Set absolute paths
explicitly when running through sudo:

```sh
sudo env POKEPI_ROOT=/path/to/pi-data POKEPI_KEYS=/path/to/private/prod.keys \
  bash examples/raspberry_pi/run_session.sh 45
```

Start Z-A local Link Trade searching before running. Session tests do not trade.
They disconnect at the end, which may end the console's search.

## Running on a Raspberry Pi 5 (kernel 6.18 / Debian 13)

The Pi 5 keeps the Pi 4's BCM43455 Wi-Fi chip, so the same Nexmon approach
works. Three things differ from the Pi 4, all handled by this fork:

**Driver.** `kernel-compat.patch` is version-guarded and builds the patched
`brcmfmac.ko` on the Pi 5's 6.18 kernel as well as the Pi 4's 6.12 (the kernel
timer API was renamed in 6.16, and three `cfg80211` ops gained a radio/link
index in 6.17). Build it as in [Status and prerequisites](#status-and-prerequisites)
into `$POKEPI_ROOT/driver/brcmfmac.ko`.

**Firmware.** The from-source Nexmon build does not work on Debian 13. Use the
prebuilt Nexmon firmware from Kali's `firmware-nexmon` package — the same build
Kali ships for the Pi 5. Its `cyfmac43455-sdio-standard.bin` is the Nexmon-patched
`7.45.206` blob the repo expects:

```sh
curl -fsSLO https://http.kali.org/kali/pool/non-free-firmware/f/firmware-nexmon/firmware-nexmon_0.2_all.deb
dpkg-deb -x firmware-nexmon_0.2_all.deb fw
install -D fw/usr/lib/firmware/cypress/cyfmac43455-sdio-standard.bin \
  "$POKEPI_ROOT/nexmon/patches/bcm43455c0/7_45_206/nexmon/brcmfmac43455-sdio.bin"
```

Build `nexutil` natively from the Nexmon checkout (`make` in `utilities/nexutil`,
no special toolchain) into `$POKEPI_ROOT/nexmon/utilities/nexutil/nexutil`.
`setup-pi.sh` then reports the radio ready.

**Vendor module.** On Pi 5 / newer kernels the stock driver's firmware-vendor
submodule is `brcmfmac_cyw`, not the Pi 4's `brcmfmac_wcc`, and it holds
`brcmfmac` open. `test-radio.sh` and `pi_remote.py` now unload whichever is
present before `brcmfmac`, and stage the firmware under the running board's name
(`raspberrypi,5-model-b`). Without this the radio could neither come up nor
restore.

Verified on a Pi 5 Model B: the driver binds, the Nexmon `7.45.206` firmware
loads, `mon0` monitor mode comes up, and the stock Wi-Fi driver restores. A full
trade has not been run on a Pi 5 yet.

### Testing without Ethernet

The radio uses the built-in Wi-Fi, so on a Wi-Fi-only Pi the radio session drops
`wlan0` — and your SSH — while it runs: the one radio cannot be both your SSH
link and the trade radio. Run the session **detached** so it survives the
disconnect; its `trap … EXIT` restore and the detached `systemd-run` rollback
timer (≤360 s) bring the stock Wi-Fi back on their own, and SSH returns. Keep
physical access to power-cycle as a last resort (a reboot reloads the stock
driver). A self-test that loads the stack, creates `mon0`, then restores,
without trading (replace the paths):

```sh
sudo systemd-run --unit=pokepi-selftest --collect \
  --setenv=POKEPI_ROOT=$HOME/pokemon-pi --setenv=POKEPI_ROLLBACK_SECONDS=60 \
  bash -c 'bash $HOME/pokeldn-pi/examples/raspberry_pi/test-radio.sh \
    > $HOME/pokemon-pi/selftest.log 2>&1'
```

Reconnect after ~90 s, then read `selftest.log` and
`$POKEPI_ROOT/radio-capabilities.txt`.

### One trade, then Wi-Fi back

`scripts/run_with_wifi_restore.sh` wraps any radio script and guarantees the
stock Wi-Fi driver is reloaded when it ends, even if the inner restore did not
finish (it reloads whichever vendor module the board uses). Launch it detached
the same way:

```sh
sudo systemd-run --unit=pokepi-trade --collect \
  --setenv=POKEPI_ROOT=$HOME/pokemon-pi \
  --setenv=POKEPI_KEYS=$HOME/pokemon-pi/private/prod.keys \
  bash -c 'bash $HOME/pokeldn-pi/scripts/run_with_wifi_restore.sh \
    run_trade.sh /path/to/validated.offer.bin > $HOME/pokemon-pi/trade.log 2>&1'
```

Start the Switch's Z-A Link Trade search before launching, confirm the exchange
on the console during the run, then reconnect and read `trade.log` and
`$POKEPI_ROOT/private/received/`.

## Trading

Prepare and validate a Z-A Pokémon through the upstream builder. The runner takes
a **354-byte framed Z-A offer**, not a raw `.pa9` file. Upstream
`pokeldn.pokemon.offer_bytes('za', decrypted_party_bytes)` creates this framing.
Validate the record before framing; the runner does not perform a legality check.
`scripts/make_za_offer.sh <file.pa9>` (or `scripts/make_offer.sh <game> <file>`
for any supported game) runs that framing from a prepared record.

```sh
sudo env POKEPI_ROOT=/path/to/pi-data POKEPI_KEYS=/path/to/private/prod.keys \
  bash examples/raspberry_pi/run_trade.sh /path/to/validated.offer.bin
```

The partner appears as PI-TEST. Choose and confirm the exchange on the Switch.
The adapter uses upstream `bin/za_join.py` GameStreams, permits one completed
trade per run, and saves the received record under `$POKEPI_ROOT/private/received`.
The process is bounded to 300 seconds, with a separate 360-second radio rollback.
Completion in the log records the engine sending its final step; verify arrival
on the console. A disconnect during a trade requires checking the console's state
before attempting another exchange.

### Other games on the shell path

The joiner is game-generic (`raw_profile.py` is a per-title table). Select the
title with `POKEPI_GAME`:

| `POKEPI_GAME` | title | status |
|---|---|---|
| `za` (default) | Legends Z-A | hardware-verified (Pi 4) |
| `sv` | Scarlet/Violet | hardware-verified (Pi 4) |
| `pla` | Legends Arceus | **wired, experimental — not yet tested on a Pi** |

Legends Arceus joining reuses upstream's complete `pla_join` engine
(`raw_pla.py`) over the same userspace-IP bridge. Run it like the Z-A trade with
`POKEPI_GAME=pla` and a prepared `.pa8` record (framing is a pass-through for
PLA, so the record itself is the offer). Two values can only be confirmed
against a live console: the LDN application version (set to PLA's
`SYS_COMM_VERSION`) and host-handoff handling (PLA is treated like Z-A, which
has no handoff). Sword/Shield and BDSP are **not** wired: their upstream
`*_join.py` are LDN association probes with no trade engine (and BDSP also uses
Pia 5), so each needs its join-trade path built first.

## Offline check

```sh
POKEPI_ROOT=/path/to/pi-data /path/to/pi-data/runtime/bin/python \
  examples/raspberry_pi/test_raw_pia.py
```

Tests cover encrypted ACK round trips, both reliable stream formats, cumulative
ACK progression, IPv4 checksums, nonce progression, and Z-A join serialization.
They do not replace a live hardware test.

## How a trade works

A Switch "local wireless" trade is a full network stack over raw Wi-Fi; the Pi
impersonates a second console by speaking every layer in software. Bottom to
top:

1. **Radio.** The host console transmits raw 802.11 frames. The Nexmon-patched
   firmware and driver give the Pi two abilities a normal Wi-Fi card lacks:
   monitor mode (hear every frame on the channel, via `mon0`) and frame
   injection (transmit arbitrary frames). This is the layer the Pi 5 self-test
   validates.
2. **LDN** — Nintendo's local-wireless layer ([docs/ldn.md](../../docs/ldn.md)).
   The host beacons an advertisement; a joiner authenticates and associates with
   a shared **LDN passphrase** (Z-A reuses Sword/Shield's), then frames are
   CCMP-encrypted. Reading the advertisement needs `prod.keys`. Code:
   `vendor/LDN`, `raw_ldn.py`.
3. **Pia** — Nintendo's peer-to-peer session middleware ([docs/pia.md](../../docs/pia.md)),
   above LDN: reliable sequenced encrypted datagrams with emulated IP/UDP. The
   session key derives from the 16-byte **Pia game key** and a session id in the
   SSID. Code: `raw_pia.py` (what `test_raw_pia.py` exercises).
4. **The game's trade protocol** — on Pia's reliable streams, Z-A runs its trade
   state machine ([docs/za.md](../../docs/za.md)): the sides exchange offered
   Pokémon, preview, confirm and swap. Driver: `bin/za_join.py`.

The Pi is the **joiner**: it scans for the console's Link Trade session (matched
by link code), associates (appearing as `PI-TEST`), offers the prepared Pokémon,
waits for you to confirm on the Switch, completes exactly one trade, saves what
the console sent, and leaves — then Wi-Fi is restored.

## How Pokémon files work

**One file is one Pokémon.** Each generation has a fixed-size record: `.pa9`
(Legends Z-A), `.pk9` (Scarlet/Violet), `.pa8`/`.pk8` (Gen 8), `.pb7`/`.pb8`
(Let's Go / BDSP), `.pk3` (Gen 3), and so on.

**Stored vs. party form** (`pokeldn/gen9.py`): the *stored* record (`0x148`, 328
bytes for Gen 9) holds the permanent data — species, PID, encryption constant,
IVs/EVs, moves, nature, ability, original trainer, ball; the *party* record
(`0x158`, 344 bytes) adds battle stats. **Trades move the party form.**

**Encryption is not `prod.keys`.** On the console each record is encrypted and
block-shuffled by its own PID — a Pokémon-format scheme unrelated to the Switch.
PKHeX and pokeldn work on the decrypted record (the "entity bytes").
`prod.keys` are Switch keys for the wireless layer only.

**Legal Pokémon are built, not required as input.** The pinned PKHeX service
(`services/pkhex/`, `pokeldn/pokemon.py`) generates a record from a real
encounter so it passes legality analysis — correct met location, legal moves,
valid PID/shiny correlations — from a species plus options, or from a
Pokémon Showdown set. Illegal requests are refused with the reason. See
[docs/architecture.md](../../docs/architecture.md) → *Pokémon preparation*.

**Framing for the trade.** The runner takes a **354-byte framed Z-A offer**, not
a raw `.pa9`. `prepare_offer` (`pokeldn/pokemon.py`) runs the record through
`entity_bytes` → PKHeX's legality check → `offer_bytes('za', …)`, which wraps the
decrypted party bytes in the game's on-wire trade envelope. (Scarlet/Violet's
envelope is a 4-byte `bc 81 58 01` prefix plus the 344-byte party = 348 bytes.)

**The received Pokémon.** On completion the console sends its record; the Pi
decrypts it and `save_received` writes it under `$POKEPI_ROOT/private/received/`
as a `.pa9`. Receiving can rewrite friendship and the handling trainer — whether
the received Pokémon keeps original-trainer status depends on your trainer
settings matching (see [docs/za.md](../../docs/za.md) and
[docs/architecture.md](../../docs/architecture.md) → friendship table).

## Credits and license

This is a fork of [Decryptu/pokeldn](https://github.com/Decryptu/pokeldn), retaining
its AGPL-3.0 license and upstream attribution. Pi integration developed with Codex
and tested by SeanC28. Nexmon and the Kali driver remain separate upstream
projects with their own licensing; obtain and build them from their sources.
