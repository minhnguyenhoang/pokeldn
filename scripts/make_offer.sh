#!/bin/bash
# Convert a Pokemon record into the offer its trade launcher consumes, using the
# project's own framing (pokeldn.pokemon.offer_bytes). Per game:
#   za    -> 354-byte framed Z-A offer (input must be a 344-byte party record)
#   lgpe  -> 232-byte offer (first 232 bytes of the record)
#   frlg, bdsp, pla, sv, swsh -> the entity record itself; the launcher frames it
#                                on the wire, so this normalizes and copies it.
# It does NOT check legality: the record must already be legal for the game.
#
#   scripts/make_offer.sh <game> <input> [output]
#   game: frlg lgpe swsh bdsp pla sv za
#
# Default output: $POKEPI_ROOT/offers/<input-name>.<game>.offer
set -euo pipefail
repo="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
root="${POKEPI_ROOT:-$HOME/pokemon-pi}"
python="$root/runtime/bin/python"
[[ -x "$python" ]] || python="$(command -v python3)"

game="${1:?Usage: make_offer.sh <game> <input> [output]  (game: frlg lgpe swsh bdsp pla sv za)}"
in="${2:?Usage: make_offer.sh <game> <input> [output]}"
test -f "$in"
out="${3:-$root/offers/$(basename "${in%.*}").$game.offer}"
mkdir -p "$(dirname "$out")"

PYTHONPATH="$repo" "$python" - "$game" "$in" "$out" <<'PY'
import sys
from pokeldn.pokemon import offer_bytes, entity_bytes, EXTENSIONS
game, inp, outp = sys.argv[1], sys.argv[2], sys.argv[3]
valid = sorted(set(EXTENSIONS) | {"za"})
if game not in valid:
    sys.exit(f"error: unknown game {game!r}; choose from {valid}")
rec = entity_bytes(game, open(inp, "rb").read())
try:
    offer = offer_bytes(game, rec)
except Exception as e:
    sys.exit(f"error: {inp}: {e}")
open(outp, "wb").write(offer)
kind = "reframed" if len(offer) != len(rec) else "entity record (framed on the wire by the launcher)"
print(f"wrote {outp} ({len(rec)} -> {len(offer)} bytes, {kind})")
PY
