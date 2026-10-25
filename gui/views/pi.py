"""The Pi page, shown while Settings picks the Raspberry Pi radio: whether the Pi is ready, what it prints during a
trade, and the fixes bin/pi_remote.py offers (examples/raspberry_pi/README.md). Everything goes over the profile's
SSH connection; the Pi runs no server for it."""
import json
import os
import threading
import time

import flet as ft

from gui import theme as t
from gui.views.widgets import Log
from pokeldn.app import runner
from pokeldn.app.paths import SESSION

GUIDE = "see the Pi guide (examples/raspberry_pi/README.md)"
GREEN, AMBER, RED = "ok", "warn", "bad"


def lights(report: dict) -> list[tuple[str, str, str]]:
    """-> (state, title, what to do) rows for a `pi_remote.py --status` report."""
    if not report.get("reachable"):
        why = report.get("error") or "no answer"
        return [(RED, f"Pi not answering at {report.get('host', '?')}",
                 f"{why}. Check the Pi is powered and its Ethernet cable is plugged in.")]
    rows = [(GREEN, "Pi answers over SSH", f"Ethernet {report.get('eth0') or 'not connected'}")]
    if report.get("host_on_wifi"):
        rows.append((RED, "Connection profile uses the Pi's Wi-Fi address",
                     "A trade takes the Pi's Wi-Fi down, so the app would lose it mid-trade. Put the Ethernet "
                     f"address{' ' + report['eth0'] if report.get('eth0') else ''} in the profile."))
    if report.get("driver_matches"):
        rows.append((GREEN, "Patched driver matches the kernel", report.get("kernel", "")))
    elif report.get("driver_kernel"):
        rows.append((RED, "Kernel changed: rebuild the driver",
                     f"The driver was built for {report['driver_kernel']}, the Pi runs {report.get('kernel')}; {GUIDE}."))
    else:
        rows.append((RED, "Patched driver missing", f"Build driver/brcmfmac.ko; {GUIDE}."))
    rows.append((GREEN, "Nexmon firmware present", "") if report.get("firmware") else
                (RED, "Nexmon firmware missing", f"Build it; {GUIDE}."))
    rows.append((GREEN, "Kernel packages held", "") if report.get("kernel_held") else
                (RED, "Kernel packages not held", "An apt upgrade would replace the kernel the driver needs. On the "
                 f"Pi run: sudo apt-mark hold {' '.join(report.get('unheld_packages', []))}"))
    rows.append((GREEN, "Code on the Pi matches this checkout", report.get("local_code", "")) if report.get("code_current")
                else (AMBER, "Code on the Pi differs from this checkout",
                      "Sync code now, or let the next trade sync it."))
    if report.get("session_running"):
        rows.append((AMBER, "A radio session is running", "Fixes wait until it ends."))
    elif report.get("radio_patched"):
        rows.append((AMBER, "The patched Wi-Fi driver is still loaded", "Restore Wi-Fi brings the stock one back."))
    else:
        rows.append((GREEN, "Stock Wi-Fi driver loaded", ""))
    return rows


class PiLog(Log):
    """The session log, with the Pi's own `[pi]` lines picked out."""

    @staticmethod
    def _line(line: str) -> ft.Text:
        if line.startswith("[pi]"):
            return ft.Text(line, size=11, color=t.AMBER, font_family=t.MONO, selectable=True,
                           weight=ft.FontWeight.W_600)
        return Log._line(line)


class PiView:
    def __init__(self, app):
        self.app = app
        self.job = None            # the pi_remote.py maintenance run, if any
        self.job_lines: list[str] = []
        self.trade = None          # the trade process whose lines the log shows
        self.visible = False
        self.report: dict | None = None
        self.checked = t.text("", 12, t.FAINT)
        self.rows = ft.Column(spacing=10)
        self.refresh_button = t.icon_button("refresh", lambda e: self.refresh(), "Refresh")
        self.buttons = {
            "sync": t.secondary_button("Sync code", lambda e: self.run("--sync", "Sync code"), "upload"),
            "check": t.secondary_button("Run setup check", lambda e: self.run("--check", "Setup check"), "check"),
            "restore": t.secondary_button("Restore Wi-Fi", lambda e: self.run("--restore-radio", "Restore Wi-Fi"), "radio"),
        }
        self.state = t.text("", 12, t.MUTED)
        self.log = PiLog(app.page, "A trade's Pi output and these buttons' output appear here.",
                         private=lambda: [app.settings.ot] if app.settings.private_logs else None)
        app.run_listeners.append(self._trade_line)
        self.control = ft.Row([
            t.panel(ft.Column([
                t.panel_header("Raspberry Pi", self.refresh_button),
                ft.Container(ft.Column([self.checked, self.rows], spacing=12, scroll=ft.ScrollMode.AUTO),
                             padding=ft.Padding(18, 4, 18, 8), expand=True),
                ft.Container(ft.Column([ft.Row(list(self.buttons.values()), spacing=8, wrap=True), self.state],
                                       spacing=8), padding=ft.Padding(18, 8, 18, 18)),
            ], spacing=0, expand=True), expand=2),
            t.panel(ft.Column([
                t.panel_header("Pi output"),
                ft.Container(self.log.control, padding=ft.Padding(12, 0, 12, 12), expand=True),
            ], spacing=0, expand=True), expand=3),
        ], spacing=t.GAP, expand=True, vertical_alignment=ft.CrossAxisAlignment.STRETCH)

    def enter(self, **kwargs) -> None:
        # The shell adds self.control to the page after enter(): nothing here may update yet.
        self.render(update=False)
        self.visible = True
        if self.report is None or kwargs.get("refresh"):
            self.app.ui(self.refresh)
        threading.Thread(target=self._watch, daemon=True).start()

    def leave(self) -> None:
        self.visible = False

    def _watch(self) -> None:
        """A trade starts and ends on the Games page; the buttons follow it while this page shows."""
        busy = None
        while self.visible:
            now = self.trading()
            if now != busy:
                busy = now
                self.app.ui(self.render_buttons)
            time.sleep(1)

    def trading(self) -> bool:
        process = self.app.process
        return bool(process and process.running)

    def profile_problem(self) -> str:
        path = os.path.expanduser(self.app.settings.pi_connection)
        return "" if os.path.isfile(path) else "Choose the Pi connection file in Settings."

    def render(self, update: bool = True) -> None:
        if problem := self.profile_problem():
            self.rows.controls = [self._row(RED, "No Pi connection profile", problem)]
        elif self.report is None:
            self.rows.controls = [self._row(AMBER, "Checking the Pi", "Asking it over SSH.")]
        else:
            self.rows.controls = [self._row(*row) for row in lights(self.report)]
        self.render_buttons(update=False)
        if update and self.visible:
            self.control.update()

    def render_buttons(self, update: bool = True) -> None:
        idle = not self.trading() and not (self.job and self.job.running) and not self.profile_problem()
        for button in self.buttons.values():
            button.disabled = not idle
        self.refresh_button.disabled = bool(self.job and self.job.running) or bool(self.profile_problem())
        if self.trading():
            self.state.value = "A trade is running; the fixes wait until it ends."
        if update and self.visible:
            self.control.update()

    @staticmethod
    def _row(state: str, title: str, detail: str) -> ft.Control:
        color = {GREEN: t.GREEN, AMBER: t.AMBER, RED: t.RED}[state]
        light = ft.Container(width=10, height=10, border_radius=5, bgcolor=color, margin=ft.Margin(0, 4, 0, 0))
        text = [t.text(title, 13, weight=ft.FontWeight.W_600)]
        if detail:
            text.append(t.text(detail, 12, t.MUTED if state == GREEN else t.SOFT, selectable=True))
        return ft.Row([light, ft.Column(text, spacing=2, expand=True, tight=True)], spacing=10,
                      vertical_alignment=ft.CrossAxisAlignment.START)

    def _start(self, flag: str, on_exit) -> None:
        self.job_lines = []
        env = runner.base_env(self.app.settings, "raspberry-pi")
        self.job = runner.Process(["--run", "bin/pi_remote.py", flag], str(SESSION), env,
                                  self.job_lines.append if flag == "--status" else self._job_line, on_exit)
        self.render_buttons()

    def refresh(self) -> None:
        if self.profile_problem() or (self.job and self.job.running):
            self.render()
            return
        self.checked.value = "Checking…"
        if self.visible:
            self.checked.update()

        def done(code: int) -> None:
            try:
                report = json.loads("\n".join(self.job_lines))
            except ValueError:
                tail = self.job_lines[-1] if self.job_lines else f"exit code {code}"
                report = {"reachable": False, "host": "?", "error": tail}
            def show():
                self.report = report
                self.checked.value = f"Checked {time.strftime('%H:%M:%S')}"
                self.render()
            self.app.ui(show)
        self._start("--status", done)

    def run(self, flag: str, label: str) -> None:
        if self.trading() or (self.job and self.job.running):
            return
        self.log.add(f"[app] {label}")
        self.state.value = f"{label}…"

        def done(code: int) -> None:
            def show():
                self.state.value = f"{label}: {'done' if code == 0 else f'failed (exit code {code})'}"
                self.log.add(f"[app] {label} exited with code {code}.")
                self.job = None
                self.refresh()
            self.app.ui(show)
        self._start(flag, done)

    def _job_line(self, line: str) -> None:
        self.log.add(line)

    def _trade_line(self, process, line: str) -> None:
        """Every line of a Games-page run while the Pi radio is chosen; a new run starts a fresh log."""
        if self.app.settings.radio != "raspberry-pi":
            return
        if process is not self.trade:
            self.trade = process
            self.log.clear()
            self.log.add("[app] Trade started on the Games page")
            self.app.ui(lambda: self.log.list.update() if self.visible else None)
        self.log.add(line)
