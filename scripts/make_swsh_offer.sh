#!/bin/bash
# Convenience wrapper: make a Sword/Shield trade offer.
# Thin delegate to make_offer.sh; see it for details and options.
#   scripts/make_swsh_offer.sh <input> [output]
exec "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/make_offer.sh" swsh "$@"
