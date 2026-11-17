"""Sword/Shield on the Pi — STAGE 1: confirm the LDN seat only; the trade is not wired yet.

The retail console hosts a Link Trade network (comm id 0100abf008968000, scene 60001) which the Pi
joins with the same LDN layer that seats it in Scarlet/Violet. Stage 2 will set up the userspace-IP
bridge and run the Pia-4 trade from bin/swsh_connect.py here (it needs that engine refactored to
expose a trade-over-socket entry). docs/swsh_session.md, docs/swsh_trade.md.
"""
import time


async def trade(interface, local_ip, host_ip):
    print(f'[swsh] LDN SEAT REACHED on the Pi: us={local_ip} host={host_ip}', flush=True)
    print('[swsh] Stage 1: the Sword/Shield join + seat work; the Pia-4 trade is not wired yet.',
          flush=True)
    # Hold the seat briefly so the result is visible, then leave cleanly (no trade).
    try:
        await _hold(2.0)
    finally:
        print('[swsh] releasing the seat (Stage 1 complete)', flush=True)


async def _hold(seconds):
    import trio
    with trio.move_on_after(seconds):
        await trio.sleep_forever()
