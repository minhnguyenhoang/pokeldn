#!/bin/bash
# Wrapper around the Pi radio trading scripts in examples/raspberry_pi/ that
# guarantees the stock Wi-Fi driver is reloaded after the run, so wlan0 / SSH
# come back even if the inner script's own restore did not finish the job.
#
# The trading scripts (run_trade.sh, run_session.sh, ...) already trap their
# restore on exit and arm a rollback timer, but this wrapper is a belt-and-
# suspenders single entry point: whatever happens to the inner script, the
# radio is put back to the stock driver before this script returns.
#
# Run as root. POKEPI_ROOT / POKEPI_KEYS are passed through to the inner script.
#
#   sudo POKEPI_ROOT=~/pokemon-pi POKEPI_KEYS=~/pokemon-pi/private/prod.keys \
#     scripts/run_with_wifi_restore.sh run_trade.sh /path/to/validated.offer.bin
#
# The first argument is a script in examples/raspberry_pi/ (bare name) or a
# path; the rest are passed through unchanged. Launch it detached (systemd-run
# / setsid) when driving over Wi-Fi, since the radio still drops wlan0 while it
# runs; this wrapper only guarantees Wi-Fi is back once the run ends.
set -uo pipefail   # not -e: the restore step must run even when the inner script fails

repo="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
examples="$repo/examples/raspberry_pi"

if [[ ${EUID:-$(id -u)} -ne 0 ]]; then
    echo 'run_with_wifi_restore.sh must run as root (modprobe/nmcli).' >&2
    exit 2
fi

restore_wifi() {
    local status=$?
    echo '[wrapper] ensuring the stock Wi-Fi driver is back'
    # Prefer the live session's own restore script when it is still present.
    if [[ -f /run/pokepi-radio/restore.sh ]]; then
        bash /run/pokepi-radio/restore.sh || true
    fi
    # If the radio is still in the patched state (custom firmware path set or
    # mon0 present), force a reload of the stock driver. Handle whichever
    # firmware-vendor submodule this board uses (brcmfmac_wcc or brcmfmac_cyw).
    if [[ -n "$(cat /sys/module/firmware_class/parameters/path 2>/dev/null)" ]] \
            || [[ -e /sys/class/net/mon0 ]]; then
        echo '[wrapper] radio still patched; forcing a stock reload'
        echo '' > /sys/module/firmware_class/parameters/path 2>/dev/null || true
        ip link set mon0 down 2>/dev/null || true
        iw dev mon0 del 2>/dev/null || true
        ip link set wlan0 down 2>/dev/null || true
        for vendor in brcmfmac_wcc brcmfmac_cyw; do
            modprobe -r "$vendor" 2>/dev/null || true
        done
        modprobe -r brcmfmac 2>/dev/null || true
        modprobe brcmfmac 2>/dev/null || true
        sleep 3
        nmcli device set wlan0 managed yes 2>/dev/null || true
    fi
    echo "[wrapper] Wi-Fi restore done (inner script exit status $status)"
    exit "$status"
}
trap restore_wifi EXIT

script="${1:?Usage: run_with_wifi_restore.sh <run_trade.sh|run_session.sh|...> [args...]}"
shift
case "$script" in
    */*) target="$script" ;;            # an explicit path
    *)   target="$examples/$script" ;;  # a bare name in examples/raspberry_pi/
esac
if [[ ! -f "$target" ]]; then
    echo "No such radio script: $target" >&2
    exit 2
fi

echo "[wrapper] running: $target $*"
bash "$target" "$@"
