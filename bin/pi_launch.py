"""Start the desktop app on its Pi page with the Raspberry Pi radio chosen; `Start pokeldn Pi.cmd` runs it.

The connection profile is the one Settings already has, else POKEPI_CONNECTION, else pi-connection.json in the
app's data folder. The profile stays where it is, outside the checkout."""
import argparse
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pokeldn.app import paths, settings  # noqa: E402


def main():
    argparse.ArgumentParser(description=__doc__.splitlines()[0]).parse_args()
    chosen = settings.load()
    for candidate in (chosen.pi_connection, os.environ.get('POKEPI_CONNECTION', ''),
                      str(paths.DATA / 'pi-connection.json')):
        if candidate and os.path.isfile(os.path.expanduser(candidate)):
            chosen.pi_connection = candidate
            break
    # Without a profile the Pi page says to choose one in Settings.
    chosen.radio = 'raspberry-pi'
    chosen.save()
    os.environ['POKELDN_START_PAGE'] = 'pi'
    from gui.main import run
    run()


if __name__ == '__main__':
    main()
