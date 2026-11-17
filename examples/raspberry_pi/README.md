# Experimental Raspberry Pi 4 radio alternative

This fork adds a Pi-only experimental transport to Decryptu's pokeldn. It uses
the Pi 4's built-in BCM43455 Wi-Fi, Nexmon firmware, a matching patched brcmfmac
driver, and userspace CCMP/IP/Pia. It does not require an ESP32 or USB Wi-Fi adapter.
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

Raspberry Pi 5 / kernel 6.18 / Debian 13 (Trixie) is a work in progress: the
patched `brcmfmac` driver now builds cleanly there (see `kernel-compat.patch`),
but the Nexmon firmware for the Pi 5 is not built yet and no radio session or
trade has been run on a Pi 5. The software runtime and offline checks
(`setup-pi.sh`) do pass on it.

Keep Ethernet connected. Radio setup temporarily unloads the normal Wi-Fi driver
and creates `mon0`; it restores the stock driver on exit. Do not run it through
a Wi-Fi-only SSH connection. The scripts expect NetworkManager, systemd, iw, ip,
rfkill, ethtool, flock, and matching kernel headers/build tools.

Prepare a data directory outside the checkout, referred to as `$POKEPI_ROOT`:

* `nexmon/`: build [seemoo-lab/nexmon](https://github.com/seemoo-lab/nexmon),
  specifically `patches/bcm43455c0/7_45_206/nexmon`, and `utilities/nexutil`.
  The firmware must exist at that patch directory's `brcmfmac43455-sdio.bin`.
  On the Pi 5 (same BCM43455 chip, Cypress firmware `7.45.265`), Nexmon's
  compatibility table lists `7_45_234` as the bcm43455c0 patch; the Pi 5
  firmware has not yet been built or verified in this fork.
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

## Trading

Prepare and validate a Z-A Pokémon through the upstream builder. The runner takes
a **354-byte framed Z-A offer**, not a raw `.pa9` file. Upstream
`pokeldn.pokemon.offer_bytes('za', decrypted_party_bytes)` creates this framing.
Validate the record before framing; the runner does not perform a legality check.

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

## Offline check

```sh
POKEPI_ROOT=/path/to/pi-data /path/to/pi-data/runtime/bin/python \
  examples/raspberry_pi/test_raw_pia.py
```

Tests cover encrypted ACK round trips, both reliable stream formats, cumulative
ACK progression, IPv4 checksums, nonce progression, and Z-A join serialization.
They do not replace a live hardware test.

## Credits and license

This is a fork of [Decryptu/pokeldn](https://github.com/Decryptu/pokeldn), retaining
its AGPL-3.0 license and upstream attribution. Pi integration developed with Codex
and tested by SeanC28. Nexmon and the Kali driver remain separate upstream
projects with their own licensing; obtain and build them from their sources.
