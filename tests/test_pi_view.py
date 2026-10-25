"""The Pi page's status lights and bin/pi_remote.py's --status report, without a Pi."""
import importlib.util
from pathlib import Path
import subprocess
from types import SimpleNamespace

from gui.views import pi

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("pi_remote", ROOT / "bin" / "pi_remote.py")
pi_remote = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pi_remote)

CFG = {"host": "192.168.1.50", "root": "/home/pi/pokemon-pi"}
READY = ("kernel=6.12.1\ndriver_kernel=6.12.1\nfirmware=1\nunheld=\nsync_hash={hash}\nfirmware_path=\n"
         "addr_eth0=192.168.1.50\naddr_wlan0=\n")


def fake_ssh(stdout="", error=None):
    def ssh(command, **kwargs):
        if error:
            raise error
        return SimpleNamespace(stdout=stdout.encode())
    return ssh


def test_a_ready_pi_reports_every_check_green(monkeypatch):
    monkeypatch.setattr(pi_remote, "checkout_archive", lambda: ("ab" * 32, b""))
    report = pi_remote.status(CFG, fake_ssh(READY.format(hash="ab" * 32)))
    assert report["reachable"] and report["driver_matches"] and report["firmware"] and report["kernel_held"]
    assert report["code_current"] and not report["radio_patched"] and not report["host_on_wifi"]
    assert {state for state, _, _ in pi.lights(report)} == {pi.GREEN}


def test_an_unreachable_pi_reports_ssh_s_reason(monkeypatch):
    monkeypatch.setattr(pi_remote, "checkout_archive", lambda: ("ab" * 32, b""))
    error = subprocess.CalledProcessError(255, "ssh", stderr=b"ssh: connect to host x port 22: Connection timed out\n")
    report = pi_remote.status(CFG, fake_ssh(error=error))
    assert report == {"reachable": False, "host": CFG["host"], "local_code": "ab" * 6,
                      "error": "ssh: connect to host x port 22: Connection timed out"}
    [(state, title, detail)] = pi.lights(report)
    assert state == pi.RED and "Ethernet" in detail


def test_a_new_kernel_an_unheld_package_and_a_wifi_host_each_name_their_fix(monkeypatch):
    monkeypatch.setattr(pi_remote, "checkout_archive", lambda: ("ab" * 32, b""))
    facts = READY.format(hash="old").replace("driver_kernel=6.12.1", "driver_kernel=6.12.0").replace(
        "unheld=", "unheld=linux-image-rpi-v8").replace("addr_wlan0=", "addr_wlan0=192.168.1.50")
    report = pi_remote.status(CFG, fake_ssh(facts + "monitor=1\n"))
    rows = {title: (state, detail) for state, title, detail in pi.lights(report)}
    assert rows["Kernel changed: rebuild the driver"][0] == pi.RED
    assert "apt-mark hold linux-image-rpi-v8" in rows["Kernel packages not held"][1]
    assert rows["Connection profile uses the Pi's Wi-Fi address"][0] == pi.RED
    assert rows["Code on the Pi differs from this checkout"][0] == pi.AMBER
    assert rows["The patched Wi-Fi driver is still loaded"][0] == pi.AMBER


def test_check_and_restore_pass_the_pi_s_exit_status_back(tmp_path):
    password = tmp_path / "sudo"
    password.write_text("secret\n")
    failing = fake_ssh(error=subprocess.CalledProcessError(3, "ssh"))
    assert pi_remote.check(CFG, failing) == 3
    assert pi_remote.restore_radio(dict(CFG, sudo_password_file=str(password)), failing) == 3
    sent = []
    pi_remote.restore_radio(dict(CFG, sudo_password_file=str(password)),
                            lambda command, **kwargs: sent.append((command, kwargs["input"])))
    assert sent[0][1] == b"secret\n" and "secret" not in sent[0][0]


def test_the_pi_page_shows_games_runs_only_with_the_pi_radio_and_restarts_its_log_per_run():
    app = SimpleNamespace(page=None, settings=SimpleNamespace(radio="raspberry-pi", ot="X", private_logs=False),
                          run_listeners=[], process=None, ui=lambda fn: None)
    view = pi.PiView(app)
    shown, cleared = [], []
    view.log = SimpleNamespace(add=shown.append, clear=lambda: cleared.append(1), list=None)
    first, second = object(), object()
    for process, line in ((first, "[pi] one"), (first, "two"), (second, "[pi] three")):
        app.run_listeners[0](process, line)
    assert shown == ["[app] Trade started on the Games page", "[pi] one", "two",
                     "[app] Trade started on the Games page", "[pi] three"]
    assert len(cleared) == 2
    app.settings.radio = ""
    app.run_listeners[0](second, "board line")
    assert shown[-1] == "[pi] three"


def test_entering_the_pi_page_updates_nothing_before_the_shell_adds_it_to_the_page(tmp_path):
    later = []
    app = SimpleNamespace(page=None, settings=SimpleNamespace(radio="raspberry-pi", ot="X", private_logs=False,
                                                              pi_connection=str(tmp_path / "missing.json")),
                          run_listeners=[], process=None, ui=later.append)
    view = pi.PiView(app)
    view.enter()     # a control.update() here raised "Control must be added to the page first"
    view.leave()
    assert later[0] == view.refresh   # after the page update; the watcher may queue its buttons too
