"""Instant new mail with IMAP IDLE: one connection per account that waits until the server says the inbox changed.

Needs Python 3.14+ (imaplib IDLE support) and a server that offers IDLE. Without it Home-mail keeps polling.
While IDLE works, the regular check runs only every 15 minutes as a safety net (fewer logins at the provider).
"""
from __future__ import annotations

import imaplib
import logging
import threading
from typing import TYPE_CHECKING

from . import mail

if TYPE_CHECKING:
    from .coordinator import HomemailCoordinator

_LOGGER = logging.getLogger(__name__)
IDLE_SECONDS = 9 * 60  # RFC 2177 allows 29 minutes, but routers often drop a connection that is quiet for ~10
CHANGES = {"EXISTS", "EXPUNGE", "FETCH", "RECENT"}


def supported() -> bool:
    return hasattr(imaplib.IMAP4, "idle")


def wait_for_change(m: imaplib.IMAP4, seconds: float) -> bool:
    """IDLE on the selected mailbox for at most `seconds`. True when the server reported a change
    (new message, flags changed by another app, message removed)."""
    with m.idle(duration=seconds) as idler:
        for typ, _data in idler:
            if typ in CHANGES:  # not keep-alive chatter like "* OK still here"
                return True
    return False


class IdleWatcher:
    """Runs in its own thread so it never blocks Home Assistant."""

    def __init__(self, coordinator: HomemailCoordinator) -> None:
        self.co = coordinator
        self.state = "off"  # off | starting | on | unsupported | error
        self.error = ""
        self._stop = threading.Event()
        self._conn: imaplib.IMAP4 | None = None
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if not supported():
            self.state = "unsupported"
            return
        self.state = "starting"
        self._thread = threading.Thread(target=self._run, name=f"homemail idle {self.co.cfg['email']}", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        m = self._conn
        if m is not None:
            try:
                m.shutdown()  # wakes the thread up from its wait
            except Exception:  # noqa: BLE001
                pass

    def _to_loop(self, func, *args) -> None:
        self.co.hass.loop.call_soon_threadsafe(func, *args)

    def _run(self) -> None:
        delay = 30
        while not self._stop.is_set():
            m = None
            try:
                m = self._conn = mail.connect(self.co.cfg, "INBOX")
                if "IDLE" not in m.capabilities:
                    self.state = "unsupported"
                    self._to_loop(self.co.set_push, False)
                    return
                self.state, self.error, delay = "on", "", 30
                self._to_loop(self.co.set_push, True)
                while not self._stop.is_set():
                    if wait_for_change(m, IDLE_SECONDS):
                        self._to_loop(self.co.push_refresh)
            except Exception as err:  # noqa: BLE001
                if self._stop.is_set():
                    break
                self.state, self.error = "error", f"{type(err).__name__}: {err}"[:200]
                _LOGGER.debug("IDLE for %s stopped, trying again in %s s: %s", self.co.cfg["email"], delay, err)
                self._to_loop(self.co.set_push, False)
                self._stop.wait(delay)
                delay = min(delay * 2, 900)
            finally:
                self._conn = None
                if m is not None:
                    mail.close(m)
        self.state = "off"
