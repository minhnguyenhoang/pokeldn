"""Title selection and exact link-code matching for the experimental Pi joiner.

Game-generic: each supported title contributes its communication id, scene id,
advertisement link-code parser, LDN passphrase and application version. Z-A and
Scarlet/Violet are hardware-verified; Legends Arceus is wired but not yet tested
on a Pi (docs: examples/raspberry_pi/README.md)."""
import os

SUPPORTED = ('za', 'sv', 'pla')


class HandedOff(RuntimeError):
    """The console's member wait ran out and it handed us the host role before the trade.

    It destroys that network and browses again, so the joiner should rescan and rejoin."""


class NoHost(RuntimeError):
    """No usable matching host right now, before any trade began; the joiner may rescan and rejoin.

    Raised when no session matches, and when the host stops answering authentication, association,
    the LDN handshake or the seat: a Scarlet/Violet host's 3 to 4 s member wait can end between them,
    taking the network with it, and a Z-A console refuses some seats while it settles."""


def game():
    value = os.environ.get('POKEPI_GAME', 'za')
    if value not in SUPPORTED:
        raise ValueError(f'POKEPI_GAME must be one of {", ".join(SUPPORTED)}')
    return value


def session_code(network):
    """-> the link code a session of the selected game advertises, or None for any other network."""
    g = game()
    if g == 'sv':
        from pokeldn import sv
        if (network.local_communication_id in (sv.COMM_ID_SCARLET, sv.COMM_ID_VIOLET)
                and network.scene_id == sv.SCENE_ID):
            return sv.link_code(network.application_data)
        return None
    if g == 'pla':
        from pokeldn import pla
        if (network.local_communication_id == pla.COMM_ID
                and network.scene_id == pla.SCENE_ID):
            try:
                return pla.parse_advertise_data(bytes(network.application_data))['code']
            except (ValueError, IndexError, KeyError):
                return None
        return None
    from pokeldn import za
    if network.local_communication_id != za.COMM_ID:
        return None
    try:
        return za.parse_advertise_data(bytes(network.application_data))['code']
    except (ValueError, IndexError, KeyError):
        return None


def wanted_code():
    """-> the link code this run joins; None joins any session of the game (Z-A and Legends
    Arceus default to this), '' for Scarlet/Violet keeps its exact-match default."""
    default = '' if game() == 'sv' else None
    return os.environ.get('POKEPI_CODE', default) or default


def matches(network):
    code = session_code(network)
    return code is not None and wanted_code() in (None, code)


def credentials():
    """-> (LDN passphrase, LDN application version) for the selected game. The application
    version is the value the console advertises; confirm a new title's against a live scan."""
    g = game()
    if g == 'sv':
        from pokeldn import sv
        return sv.PASSPHRASE, sv.APP_VERSION
    if g == 'pla':
        from pokeldn import pla
        return pla.PASSPHRASE, pla.SYS_COMM_VERSION
    from pokeldn import za
    return za.PASSPHRASE, 6
