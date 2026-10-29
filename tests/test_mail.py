from email.message import EmailMessage

from conftest import mail


def raw_with_attachments():
    m = EmailMessage()
    m["From"] = "Anna <anna@example.com>"
    m["To"] = "me@example.com"
    m["Subject"] = "Files"
    m.set_content("see attached")
    m.add_attachment(b"%PDF-1.4 one", maintype="application", subtype="pdf", filename="one.pdf")
    m.add_attachment(b"\x89PNG two", maintype="image", subtype="png", filename="twee foto.png")
    return m.as_bytes()


class FakeImap:
    def __init__(self, raw):
        self.raw = raw

    def uid(self, cmd, *args):
        assert cmd == "FETCH"
        return "OK", [(b"1 (UID 7 BODY[] {%d}" % len(self.raw), self.raw), b")"]

    def logout(self):
        pass


def test_get_attachment(monkeypatch):
    monkeypatch.setattr(mail, "connect", lambda cfg, folder: FakeImap(raw_with_attachments()))
    assert mail.get_attachment({}, "7", "INBOX", 0) == ("one.pdf", "application/pdf", b"%PDF-1.4 one")
    assert mail.get_attachment({}, "7", "INBOX", 1) == ("twee foto.png", "image/png", b"\x89PNG two")


def test_get_attachment_out_of_range(monkeypatch):
    monkeypatch.setattr(mail, "connect", lambda cfg, folder: FakeImap(raw_with_attachments()))
    try:
        mail.get_attachment({}, "7", "INBOX", 2)
    except mail.MailError as err:
        assert err.code == "not_found"
    else:
        raise AssertionError("expected not_found")


class FakeSmtp:
    sent = []

    def login(self, *a):
        pass

    def send_message(self, msg, from_addr, to_addrs):
        FakeSmtp.sent.append(msg)

    def quit(self):
        pass


def test_send_with_attachments(monkeypatch):
    monkeypatch.setattr(mail, "_smtp", lambda cfg: FakeSmtp())
    cfg = {"email": "me@example.com", "password": "x"}
    mail.send(cfg, "Me", ["anna@example.com"], [], "Hello", "Body text", None, "new", None,
              attachments=[("report.pdf", "application/pdf", b"%PDF data"), ("notes.txt", "text/plain", b"hello")])
    msg = FakeSmtp.sent[-1]
    files = {p.get_filename(): (p.get_content_type(), p.get_payload(decode=True)) for p in msg.iter_attachments()}
    assert files == {"report.pdf": ("application/pdf", b"%PDF data"), "notes.txt": ("text/plain", b"hello")}
    assert msg["Subject"] == "Hello"


class ListImap:
    """A folder with UIDs 101..100+n: answers FETCH by position and FETCH of headers by UID."""

    def __init__(self, n):
        self.exists, self.n, self.fetched = n, n, []

    def fetch(self, rng, what):
        a, b = (int(x) for x in rng.split(":"))
        self.fetched.append(rng)
        return "OK", [b"%d (UID %d FLAGS (%s))" % (i, 100 + i, b"\\Seen" if i % 2 else b"") for i in range(a, b + 1)]

    def uid(self, cmd, uids, what):
        assert cmd == "FETCH"
        out = []
        for u in uids.split(b","):
            raw = b"From: Anna <anna@example.com>\r\nSubject: m" + u + b"\r\n\r\nhi"
            out += [(b"1 (UID " + u + b" RFC822.SIZE 50 BODY[]<0> {%d}" % len(raw), raw), b")"]
        return "OK", out

    def logout(self):
        pass


def test_list_newest_by_position(monkeypatch):
    imap = ListImap(40000)
    monkeypatch.setattr(mail, "connect", lambda cfg, folder: imap)
    rows = mail.list_messages("A", {"imap_server": "imap.example.com"}, 50, None, {})
    assert imap.fetched == ["39951:40000"]  # no list of all 40.000 UIDs
    assert [r["uid"] for r in rows][:2] == ["40051", "40052"] and len(rows) == 50
    assert rows[-1]["subject"] == "m40100" and rows[-1]["seen"] is False and rows[-2]["seen"] is True


def test_list_small_and_empty_folder(monkeypatch):
    monkeypatch.setattr(mail, "connect", lambda cfg, folder: ListImap(3))
    assert len(mail.list_messages("A", {"imap_server": "x"}, 50, None, {})) == 3
    monkeypatch.setattr(mail, "connect", lambda cfg, folder: ListImap(0))
    assert mail.list_messages("A", {"imap_server": "x"}, 50, None, {}) == []


def test_cache_is_bounded(monkeypatch):
    monkeypatch.setattr(mail, "MAX_CACHE", 3)
    cache = {}
    for i in range(5):
        mail.remember(cache, ("A", "INBOX", str(i)), {"uid": str(i)})
    assert list(cache) == [("A", "INBOX", "2"), ("A", "INBOX", "3"), ("A", "INBOX", "4")]


def test_imap_since():
    assert mail.imap_since("2026-10-05") == "5-Oct-2026"
    assert mail.imap_since("") is None and mail.imap_since("2026-13-01") is None and mail.imap_since("x") is None


class SinceImap(ListImap):
    def uid(self, cmd, *args):
        if cmd == "SEARCH":
            self.searched = args
            return "OK", [b"40098 40099 40100" if "UNSEEN" not in args else b"40100"]
        return super().uid(cmd, *args)


def test_list_and_count_since(monkeypatch):
    imap = SinceImap(40000)
    monkeypatch.setattr(mail, "connect", lambda cfg, folder: imap)
    rows = mail.list_messages("A", {"imap_server": "x"}, 50, None, {}, "INBOX", "2026-10-15")
    assert imap.searched == (None, "SINCE", "15-Oct-2026") and [r["uid"] for r in rows] == ["40098", "40099", "40100"]
    assert mail.unseen_since({}, "2026-10-15") == 1 and imap.searched == (None, "UNSEEN", "SINCE", "15-Oct-2026")
