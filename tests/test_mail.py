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
