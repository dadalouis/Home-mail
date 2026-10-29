"""IMAP IDLE against a tiny fake IMAP server (needs Python 3.14+, like Home Assistant 2026)."""
import imaplib
import socket
import threading
import time

import pytest

from conftest import idle

pytestmark = pytest.mark.skipif(not idle.supported(), reason="imaplib IDLE needs Python 3.14+")


def fake_server(push_after: float | None):
    """Minimal IMAP server: login, select, IDLE. When push_after is set it reports new mail after that delay."""
    srv = socket.socket()
    srv.bind(("127.0.0.1", 0))
    srv.listen(1)

    def run():
        try:
            serve()
        except OSError:  # the client hung up (the watcher was stopped)
            pass

    def serve():
        conn, _ = srv.accept()
        f = conn.makefile("rwb", buffering=0)
        f.write(b"* OK [CAPABILITY IMAP4rev1 IDLE] ready\r\n")
        while line := f.readline():
            tag, _, rest = line.decode().strip().partition(" ")
            cmd = rest.split(" ")[0].upper()
            if cmd == "CAPABILITY":
                f.write(b"* CAPABILITY IMAP4rev1 IDLE\r\n" + f"{tag} OK done\r\n".encode())
            elif cmd in ("LOGIN", "LOGOUT", "NOOP"):
                f.write(f"{tag} OK done\r\n".encode())
                if cmd == "LOGOUT":
                    break
            elif cmd == "EXAMINE" or cmd == "SELECT":
                f.write(b"* 3 EXISTS\r\n" + f"{tag} OK [READ-ONLY] done\r\n".encode())
            elif cmd == "IDLE":
                f.write(b"+ idling\r\n")
                f.write(b"* OK still here\r\n")  # keep-alive: must not count as a change
                if push_after is not None:
                    time.sleep(push_after)
                    f.write(b"* 4 EXISTS\r\n")
                done = f.readline()
                assert done.strip().upper() == b"DONE"
                f.write(f"{tag} OK IDLE done\r\n".encode())
        conn.close()
        srv.close()

    threading.Thread(target=run, daemon=True).start()
    m = imaplib.IMAP4("127.0.0.1", srv.getsockname()[1], timeout=30)
    m.login("me", "pw")
    m.select("INBOX", readonly=True)
    return m


def test_idle_reports_new_mail():
    m = fake_server(push_after=0.2)
    start = time.monotonic()
    assert idle.wait_for_change(m, 10) is True
    assert time.monotonic() - start < 5  # at once, not after the full wait
    m.logout()


def test_idle_times_out_quietly():
    m = fake_server(push_after=None)
    start = time.monotonic()
    assert idle.wait_for_change(m, 1) is False
    assert 0.8 < time.monotonic() - start < 5
    m.logout()


class FakeCoordinator:
    def __init__(self):
        self.cfg = {"email": "me@example.com"}
        self.push = []
        self.refreshed = threading.Event()
        self.hass = type("H", (), {"loop": type("L", (), {"call_soon_threadsafe": staticmethod(lambda f, *a: f(*a))})()})()

    def set_push(self, ok):
        self.push.append(ok)

    def push_refresh(self):
        self.refreshed.set()


def test_watcher_refreshes_on_new_mail_and_stops(monkeypatch):
    monkeypatch.setattr(idle.mail, "connect", lambda cfg, folder: fake_server(push_after=0.2))
    co = FakeCoordinator()
    w = idle.IdleWatcher(co)
    w.start()
    assert co.refreshed.wait(5), "no refresh after the server reported new mail"
    assert w.state == "on" and co.push[0] is True
    w.stop()
    w._thread.join(5)
    assert not w._thread.is_alive()
