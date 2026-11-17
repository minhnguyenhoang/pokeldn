"""Run upstream's Legends Arceus joiner on the Pi's encrypted Ethernet bridge.

EXPERIMENTAL / not yet tested on a Pi. Modelled on raw_sv.py and bin/pla_join.py's
run_session; it drives upstream's complete PLA joiner over the userspace IP stack
the radio layer bridges. The record must be prepared (validated) beforehand, as
for Z-A and Scarlet/Violet: PLA's own main() validates with PKHeX, which the Pi
does not run. See examples/raspberry_pi/README.md.
"""
from pi_paths import DATA_ROOT
import os
import socket
import struct
import time
import trio
from ldn import wlan
import raw_profile
from pokeldn import pla
from pokeldn.ldn import userspace_ip
from pokeldn.pla import data_exchange


async def trade(interface, local_ip, host_ip):
    try:
        import pla_join as upstream
    except ImportError:
        import pla_join_upstream as upstream
    args = upstream.build_parser().parse_args([])
    local_ip, host_ip = str(local_ip), str(host_ip)
    args.our_ip, args.host_ip = local_ip, host_ip
    args.name = os.environ.get('POKEPI_TRAINER', 'PI-TEST')
    args.hold = 240
    args.fresh_pid = False  # validated and optionally regenerated on the desktop
    args.offer = [os.environ['POKEPI_TRADE_OFFER']]
    destination = DATA_ROOT / 'private/received'
    destination.mkdir(mode=0o700, exist_ok=True)
    args.offer_out = os.environ.get('POKEPI_RECEIVED') or str(
        destination / (time.strftime('%Y%m%d-%H%M%S') + '.pa8'))

    # Build the trade identity and the offer with PLA's own helpers (no PKHeX).
    exchange = data_exchange.build_record(player_id=bytes.fromhex(args.player_id),
                                          name=args.name.encode())
    offer = upstream.build_offer(args, exchange)

    keys = pla.session_keys(interface.target.ssid)
    our_mac = b'\x02\x00' + socket.inet_aton(local_ip)
    session = None

    def record(**row):
        pass  # upstream run_session logs [pla] lines and writes received records itself

    async with userspace_ip.userspace_port('pokepi-raw', interface.source) as port:
        await port.add_address(local_ip, local_ip.rsplit('.', 1)[0] + '.255')
        await port.add_neighbor(host_ip, interface.target.address)

        async def receive(protocol, payload):
            frame = (bytes(interface.source) + bytes(interface.target.address)
                     + struct.pack('!H', protocol) + payload)
            await port.write(frame)

        async def reader():
            while True:
                event = await interface.next_event()
                if isinstance(event, wlan.DisassociationEvent):
                    raise RuntimeError('Switch disconnected from the Pi')

        async def writer():
            while True:
                frame = await port.read()
                destination_mac = wlan.MACAddress(':'.join(f'{b:02x}' for b in frame[:6]))
                await interface.send_payload(interface.target.address,
                    int.from_bytes(frame[12:14], 'big'), frame[14:], destination_mac)

        interface.on_data = receive
        # bind_ip=None so pia_socket returns the userspace stack's socket on our bridge,
        # not a kernel socket (userspace_ip.pia_socket).
        sock = userspace_ip.pia_socket('pokepi-raw', pla.PIA_PORT, None, broadcast=False)
        try:
            async with trio.open_nursery() as nursery:
                nursery.start_soon(reader)
                nursery.start_soon(writer)
                session = await upstream.run_session(args, keys, sock, host_ip, local_ip,
                                                     our_mac, offer, exchange, record)
                nursery.cancel_scope.cancel()
        finally:
            interface.on_data = None
            try:
                sock.close()
            except Exception:
                pass
    if not getattr(session, 'traded', False):
        raise RuntimeError('Legends Arceus session ended without a completed trade')
