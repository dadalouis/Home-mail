"""IMAP/SMTP logic for Home-mail. Plain blocking Python (stdlib only); always run in an executor.

`cfg` is a dict with: email, password, imap_server, imap_port, smtp_server, smtp_port.
UIDs are real IMAP UIDs (stable), returned as strings. Nothing is stored or logged.
"""

from __future__ import annotations

import base64
import email
import html as htmllib
import imaplib
import re
import smtplib
import time
from email.header import decode_header, make_header
from email.message import EmailMessage
from email.utils import formataddr, formatdate, getaddresses, make_msgid, parsedate_to_datetime
from html.parser import HTMLParser
from typing import Any

MAX_INLINE = 3_000_000  # bytes of embedded (cid:) images per message
TIMEOUT = 30
MAX_CACHE = 3000  # message headers/previews kept in memory per account; the oldest go first


class MailError(Exception):
    """Error with a short code the frontend can translate."""

    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail


def q(name: str) -> str:
    return '"' + name.replace("\\", "\\\\").replace('"', '\\"') + '"'


def is_gmail(cfg: dict) -> bool:
    return "gmail" in cfg["imap_server"].lower()


def connect(cfg: dict, folder: str | None = "INBOX", readonly: bool = True) -> imaplib.IMAP4_SSL:
    m = imaplib.IMAP4_SSL(cfg["imap_server"], int(cfg["imap_port"]), timeout=TIMEOUT)
    m.login(cfg["email"], cfg["password"])
    if folder:
        typ, data = m.select(q(folder), readonly=readonly)
        if typ != "OK":
            close(m)
            raise MailError("folder_not_found", folder)
        m.exists = int(data[0]) if data and data[0] and data[0].isdigit() else None  # messages in the folder
    return m


MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
SINCE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")


def imap_since(since: str | None) -> str | None:
    """'2026-10-15' -> '15-Oct-2026' (IMAP SEARCH SINCE; English month names whatever the locale). None: no limit."""
    g = SINCE.match(since or "")
    if not g or not 1 <= int(g[2]) <= 12:
        return None
    return f"{int(g[3])}-{MONTHS[int(g[2]) - 1]}-{g[1]}"


def unseen_since(cfg: dict, since: str | None, folder: str = "INBOX") -> int:
    """Unread messages in a folder that arrived on or after `since` (the period a web app shows)."""
    m = connect(cfg, folder)
    try:
        return _unseen(m, since)
    finally:
        close(m)


def _unseen(m: imaplib.IMAP4, since: str | None) -> int:
    d = imap_since(since)
    _, data = m.uid("SEARCH", None, *(["UNSEEN", "SINCE", d] if d else ["UNSEEN"]))
    return len(data[0].split()) if data and data[0] else 0


def remember(cache: dict, key: tuple, row: dict) -> None:
    """Keep a message summary in memory, dropping the oldest ones above MAX_CACHE."""
    cache.pop(key, None)
    cache[key] = row
    while len(cache) > MAX_CACHE:
        cache.pop(next(iter(cache)))


def close(m: imaplib.IMAP4) -> None:
    try:
        m.logout()
    except Exception:  # noqa: BLE001
        pass


def header(msg: email.message.Message, key: str) -> str:
    try:
        return str(make_header(decode_header(msg.get(key, "") or ""))).strip()
    except Exception:  # noqa: BLE001
        return str(msg.get(key, "") or "").strip()


class _Text(HTMLParser):
    """HTML -> readable plain text (previews and quoting)."""

    BLOCK = {"p", "div", "br", "tr", "li", "h1", "h2", "h3", "h4", "table", "section", "blockquote"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.out: list[str] = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("style", "script", "head", "title"):
            self.skip += 1
        elif tag in self.BLOCK:
            self.out.append("\n")
        elif tag == "td":
            self.out.append(" ")

    def handle_endtag(self, tag):
        if tag in ("style", "script", "head", "title"):
            self.skip = max(0, self.skip - 1)
        elif tag in self.BLOCK:
            self.out.append("\n")

    def handle_data(self, data):
        if not self.skip:
            self.out.append(data)


def html_to_text(h: str) -> str:
    p = _Text()
    try:
        p.feed(h)
    except Exception:  # noqa: BLE001
        return re.sub(r"<[^>]+>", " ", h)
    t = "".join(p.out).replace("\xa0", " ").replace("‌", "").replace("͏", "")
    t = re.sub(r"[ \t]+", " ", t)
    return re.sub(r"\n\s*\n+", "\n\n", t).strip()


def part_text(p: email.message.Message) -> str:
    try:
        raw = p.get_payload(decode=True) or b""
    except Exception:  # noqa: BLE001
        raw = b""
    try:
        return raw.decode(p.get_content_charset() or "utf-8", "replace")
    except LookupError:
        return raw.decode("utf-8", "replace")


def preview(msg: email.message.Message) -> str:
    for kind in ("text/plain", "text/html"):
        for p in msg.walk():
            if p.get_content_type() == kind and not p.get_filename():
                t = part_text(p)
                if kind == "text/html":
                    t = html_to_text(t)
                t = re.sub(r"\s+", " ", t).strip()
                if t:
                    return t[:200]
    return ""


def sender(msg: email.message.Message) -> tuple[str, str]:
    adr = getaddresses([header(msg, "From")])
    name, address = adr[0] if adr else ("", "")
    return (name or address or "?").strip('" '), address.lower()


def date_iso(msg: email.message.Message) -> str:
    try:
        return parsedate_to_datetime(msg.get("Date")).isoformat()
    except Exception:  # noqa: BLE001
        return ""


def message_id(msg: email.message.Message) -> str:
    return " ".join((msg.get("Message-ID") or "").split())


def _flags(res) -> dict[str, str]:
    out = {}
    for r in res or []:
        r = r if isinstance(r, bytes) else (r[0] if isinstance(r, tuple) else b"")
        u = re.search(rb"UID (\d+)", r)
        f = re.search(rb"FLAGS \(([^)]*)\)", r)
        if u and f:
            out[u.group(1).decode()] = f.group(1).decode()
    return out


def _chunks(res) -> list[list[bytes]]:
    """FETCH response -> [info, body, trailer]; the UID can be in info or in the trailer."""
    parts: list[list[bytes]] = []
    for r in res or []:
        if isinstance(r, tuple):
            parts.append([r[0], r[1], b""])
        elif isinstance(r, bytes) and parts:
            parts[-1][2] += r
    return parts


HEAD = "(UID RFC822.SIZE BODY.PEEK[]<0.60000>)"


def summary(account: str, uid: str, raw: bytes, size: int = 0) -> dict[str, Any]:
    msg = email.message_from_bytes(raw)
    name, address = sender(msg)
    return {
        "account": account, "uid": uid, "name": name, "address": address,
        "subject": header(msg, "Subject"), "date": date_iso(msg), "message_id": message_id(msg),
        "preview": preview(msg), "size": size, "attachment": msg.get_content_type() == "multipart/mixed",
    }


def list_messages(account: str, cfg: dict, limit: int, search: str | None, cache: dict, folder: str = "INBOX",
                  since: str | None = None) -> list[dict]:
    """Newest `limit` messages of a folder (with `since`: only those that arrived on or after that day).
    Flags are always fresh; headers/previews are cached per UID."""
    m = connect(cfg, folder)
    d = imap_since(since)
    try:
        if search or d:
            s = (search or "").replace('"', "")
            if s and is_gmail(cfg):
                _, data = m.uid("SEARCH", "X-GM-RAW", q(s), *(["SINCE", d] if d else []))
            elif s:
                m.literal = s.encode("utf-8")
                _, data = m.uid("SEARCH", "CHARSET", "UTF-8", *(["SINCE", d] if d else []), "TEXT")
            else:
                _, data = m.uid("SEARCH", None, "SINCE", d)
            uids = (data[0].split() if data and data[0] else [])[-int(limit):]
            if not uids:
                return []
            _, res = m.uid("FETCH", b",".join(uids), "(UID FLAGS)")
            flags = _flags(res)
        else:
            # only the newest `limit` messages, by position: no list of every UID in the folder (Gmail: tens of thousands)
            n = m.exists if m.exists is not None else 0
            if not n:
                return []
            _, res = m.fetch(f"{max(1, n - int(limit) + 1)}:{n}", "(UID FLAGS)")
            flags = _flags(res)
            uids = sorted((u.encode() for u in flags), key=int)
        new = [u for u in uids if (account, folder, u.decode()) not in cache]
        rows = {}
        for i in range(0, len(new), 10):
            _, res = m.uid("FETCH", b",".join(new[i:i + 10]), HEAD)
            for info, raw, tail in _chunks(res):
                u = re.search(rb"UID (\d+)", info + b" " + tail)
                if not u:
                    continue
                g = re.search(rb"RFC822\.SIZE (\d+)", info + b" " + tail)
                uid = u.group(1).decode()
                rows[uid] = summary(account, uid, raw, int(g.group(1)) if g else 0)
                remember(cache, (account, folder, uid), rows[uid])
        out = []
        for u in uids:
            u = u.decode()
            r = dict(rows.get(u) or cache.get((account, folder, u)) or {"account": account, "uid": u, "name": "?", "subject": "", "date": "", "preview": ""})
            f = flags.get(u, "")
            r.update(folder=folder, seen="\\Seen" in f, flagged="\\Flagged" in f, answered="\\Answered" in f)
            out.append(r)
        return out
    finally:
        close(m)


DANGEROUS = [
    (r"(?is)<(script|iframe|object|embed|frame|frameset|applet)\b.*?(</\1\s*>|$)", ""),
    (r"(?is)<(script|iframe|object|embed|link|base)\b[^>]*>", ""),
    (r"(?is)<meta\b[^>]*http-equiv[^>]*>", ""),
    (r"(?i)\son\w+\s*=\s*(\"[^\"]*\"|'[^']*'|[^\s>]+)", ""),
    (r"(?i)(href|src)\s*=\s*([\"'])\s*javascript:[^\"']*\2", r'\1="#"'),
]


def is_tracking_pixel(tag: str) -> bool:
    t = tag.lower()

    def dim(k):
        return re.search(k + r"\s*=\s*[\"']?\s*([01])(px)?\s*[\"'\s/>]", t)

    style = re.search(r"style\s*=\s*[\"'][^\"']*(display\s*:\s*none|(width|height)\s*:\s*[01]px)", t)
    return bool((dim("width") and dim("height")) or style)


def read_message(cfg: dict, uid: str, mark: bool, folder: str = "INBOX") -> dict[str, Any]:
    """Full message as sanitised HTML (shown in a sandboxed iframe with a CSP); optionally marks it as seen."""
    m = connect(cfg, folder, readonly=not mark)
    try:
        _, res = m.uid("FETCH", uid, "(FLAGS BODY.PEEK[])")
        raw = next((r[1] for r in res or [] if isinstance(r, tuple)), None)
        if raw is None:
            raise MailError("not_found")
        if mark:
            m.uid("STORE", uid, "+FLAGS", "(\\Seen)")
    finally:
        close(m)
    msg = email.message_from_bytes(raw)
    name, address = sender(msg)
    html_part = text_part = None
    cid: dict[str, str] = {}
    attachments = []
    room = MAX_INLINE
    for p in msg.walk():
        if p.is_multipart():
            continue
        kind = p.get_content_type()
        filename = p.get_filename()
        cid_header = (p.get("Content-ID") or "").strip("<> ")
        if kind == "text/html" and not filename and html_part is None:
            html_part = part_text(p)
        elif kind == "text/plain" and not filename and text_part is None:
            text_part = part_text(p)
        elif kind.startswith("image/") and cid_header:
            data = p.get_payload(decode=True) or b""
            if len(data) <= room:
                room -= len(data)
                cid[cid_header] = f"data:{kind};base64,{base64.b64encode(data).decode()}"
        if filename:
            data = p.get_payload(decode=True) or b""
            attachments.append({"name": str(make_header(decode_header(filename))), "size": len(data), "type": kind})
    if html_part:
        h = html_part
        for pattern, repl in DANGEROUS:
            h = re.sub(pattern, repl, h)
        h = re.sub(r"(?is)<img\b[^>]*>", lambda t: "" if is_tracking_pixel(t.group(0)) else t.group(0), h)
        h = re.sub(r"(?i)cid:([^\"'\s>)]+)", lambda t: cid.get(t.group(1), "about:blank"), h)
        kind = "html"
    else:
        t = htmllib.escape(text_part or "")
        t = re.sub(r"(https?://[^\s<]+)", r'<a href="\1">\1</a>', t)
        h = f'<div style="white-space:pre-wrap;font:16px/1.45 -apple-system,system-ui,sans-serif">{t}</div>'
        kind = "text"

    def addresses(k):
        return [a.lower() for n, a in getaddresses([header(msg, k)]) if a]

    to = ", ".join([(n or a) for n, a in getaddresses([header(msg, "To"), header(msg, "Cc")]) if (n or a)])
    return {
        "uid": uid, "name": name, "address": address, "to": to, "subject": header(msg, "Subject"),
        "to_addresses": addresses("To"), "cc_addresses": addresses("Cc"),
        "reply_to": (addresses("Reply-To") or [address])[0],
        "date": date_iso(msg), "message_id": message_id(msg),
        "html": h, "kind": kind, "attachments": attachments,
    }


def get_attachment(cfg: dict, uid: str, folder: str, index: int) -> tuple[str, str, bytes]:
    """Attachment number `index` (same order as in read_message) of a message: (name, content type, bytes)."""
    m = connect(cfg, folder)
    try:
        _, res = m.uid("FETCH", str(uid), "(BODY.PEEK[])")
        raw = next((r[1] for r in res or [] if isinstance(r, tuple)), None)
    finally:
        close(m)
    if raw is None:
        raise MailError("not_found")
    n = 0
    for p in email.message_from_bytes(raw).walk():
        if p.is_multipart() or not p.get_filename():
            continue
        if n == index:
            return (str(make_header(decode_header(p.get_filename()))), p.get_content_type(), p.get_payload(decode=True) or b"")
        n += 1
    raise MailError("not_found")


def special_folder(m: imaplib.IMAP4, flag: str) -> str | None:
    """Folder with a SPECIAL-USE flag (\\Trash, \\Sent, \\All, \\Archive)."""
    _, data = m.list()
    for line in data or []:
        r = line.decode("utf-8", "replace") if isinstance(line, bytes) else str(line)
        if flag.lower() in r.lower():
            n = re.search(r'"([^"]+)"\s*$', r) or re.search(r"\s(\S+)\s*$", r)
            if n:
                return n.group(1)
    return None


ACTIONS = ("seen", "unseen", "flag", "unflag", "archive", "delete", "inbox")


def action(cfg: dict, uid: str, act: str, folder: str = "INBOX") -> dict[str, Any]:
    """seen/unseen/flag/unflag, archive, delete (in Trash: permanently) or move back to the inbox."""
    if act not in ACTIONS:
        raise MailError("unknown_action", act)
    m = connect(cfg, folder, readonly=False)
    try:
        if act in ("seen", "unseen", "flag", "unflag"):
            flag = "(\\Seen)" if act in ("seen", "unseen") else "(\\Flagged)"
            m.uid("STORE", uid, "+FLAGS" if act in ("seen", "flag") else "-FLAGS", flag)
            return {"ok": True}
        trash = special_folder(m, "\\Trash")
        if act == "delete" and folder == trash:
            m.uid("STORE", uid, "+FLAGS", "(\\Deleted)")
            try:
                m.uid("EXPUNGE", uid)
            except Exception:  # noqa: BLE001
                m.expunge()
            return {"ok": True, "permanent": True}
        if act == "inbox":
            target = "INBOX"
        elif act == "archive":
            target = special_folder(m, "\\All") if is_gmail(cfg) else (special_folder(m, "\\Archive") or "Archive")
            if not is_gmail(cfg) and target == "Archive":
                m.create(q(target))  # if it already exists the server just says so
        else:
            target = trash
            if not target:
                raise MailError("no_trash")
        typ, _ = m.uid("MOVE", uid, q(target))
        if typ != "OK":
            m.uid("COPY", uid, q(target))
            m.uid("STORE", uid, "+FLAGS", "(\\Deleted)")
            m.expunge()
        return {"ok": True, "folder": target}
    finally:
        close(m)


def decode_utf7(name: str) -> str:
    """IMAP folder names are 'modified UTF-7' (RFC 3501): &- = &, &AOk- = é."""

    def part(t):
        s = t.group(1)
        if not s:
            return "&"
        s = s.replace(",", "/")
        return base64.b64decode(s + "=" * (-len(s) % 4)).decode("utf-16-be", "replace")

    return re.sub(r"&([A-Za-z0-9+,]*)-", part, name)


KINDS = [("\\Drafts", "drafts"), ("\\Sent", "sent"), ("\\Junk", "junk"), ("\\Trash", "trash"), ("\\All", "all")]
NAMES = {
    "drafts": "drafts", "concepten": "drafts", "entwürfe": "drafts",
    "sent": "sent", "sent items": "sent", "sent messages": "sent", "verzonden": "sent", "verzonden items": "sent", "gesendet": "sent",
    "spam": "junk", "junk": "junk", "junk e-mail": "junk", "ongewenst": "junk",
    "trash": "trash", "deleted items": "trash", "deleted messages": "trash", "prullenbak": "trash", "papierkorb": "trash",
    "archive": "archive", "archief": "archive", "archiv": "archive",
}
ORDER = ["inbox", "drafts", "sent", "junk", "trash", "archive", "all"]


def mailboxes(cfg: dict, since: str | None = None) -> list[dict[str, Any]]:
    """All folders with counters, in iOS order: Inbox, Drafts, Sent, Junk, Trash, Archive, All, then custom folders.
    With `since` the inbox counts only unread mail of that period (like the web app shows it)."""
    m = connect(cfg, None)
    try:
        _, data = m.list()
        out = []
        for line in data or []:
            r = line.decode("utf-8", "replace") if isinstance(line, bytes) else str(line)
            p = re.match(r'\((?P<fl>[^)]*)\)\s+(?:"(?P<sep>[^"]*)"|NIL)\s+(?P<n>.+)$', r)
            if not p:
                continue
            fl, sep, raw = p.group("fl"), p.group("sep") or "", p.group("n").strip()
            raw = raw[1:-1].replace('\\"', '"').replace("\\\\", "\\") if raw.startswith('"') else raw
            if any(x in fl for x in ("\\Noselect", "\\NonExistent", "\\Important", "\\Flagged")):
                continue
            name = decode_utf7(raw)
            short = name.split(sep)[-1] if sep else name
            kind = "inbox" if raw.upper() == "INBOX" else next((k for f, k in KINDS if f in fl), None)
            if kind is None and name.lower() in NAMES and (not sep or sep not in name):
                kind = NAMES[name.lower()]
            total = unread = 0
            try:
                _, st = m.status(q(raw), "(MESSAGES UNSEEN)")
                t = (st[0] or b"").decode("utf-8", "replace")
                total = int((re.search(r"MESSAGES (\d+)", t) or [0, 0])[1])
                unread = int((re.search(r"UNSEEN (\d+)", t) or [0, 0])[1])
            except Exception:  # noqa: BLE001
                pass
            if kind == "inbox" and imap_since(since):
                try:
                    m.select(q(raw), readonly=True)
                    unread = _unseen(m, since)
                except Exception:  # noqa: BLE001
                    pass
            out.append({"folder": raw, "name": short, "path": name, "kind": kind or "custom", "total": total, "unread": unread})
        out.sort(key=lambda x: (ORDER.index(x["kind"]) if x["kind"] in ORDER else 99, x["path"].lower()))
        return out
    finally:
        close(m)


def inbox_status(cfg: dict) -> dict[str, int]:
    """Cheap poll: unread count, next UID and UIDVALIDITY of the inbox."""
    m = connect(cfg, None)
    try:
        _, st = m.status("INBOX", "(UNSEEN UIDNEXT UIDVALIDITY)")
        t = (st[0] or b"").decode("utf-8", "replace")

        def get(k):
            return int((re.search(k + r" (\d+)", t) or [0, 0])[1])

        return {"unread": get("UNSEEN"), "uidnext": get("UIDNEXT"), "uidvalidity": get("UIDVALIDITY")}
    finally:
        close(m)


def new_since(account: str, cfg: dict, first_uid: int, limit: int = 20) -> list[dict]:
    """Unseen messages in the inbox with UID >= first_uid (for new-mail events)."""
    m = connect(cfg, "INBOX")
    try:
        _, data = m.uid("SEARCH", None, f"UID {int(first_uid)}:* UNSEEN")
        uids = [u for u in (data[0].split() if data and data[0] else []) if int(u) >= first_uid][-limit:]
        out = []
        if uids:
            _, res = m.uid("FETCH", b",".join(uids), HEAD)
            for info, raw, tail in _chunks(res):
                u = re.search(rb"UID (\d+)", info + b" " + tail)
                if u:
                    out.append(summary(account, u.group(1).decode(), raw))
        return out
    finally:
        close(m)


def no_longer_unseen(cfg: dict, uids: list[str]) -> list[str]:
    """Of these inbox UIDs, the ones that are read or gone now (read or deleted in another app)."""
    if not uids:
        return []
    m = connect(cfg, "INBOX")
    try:
        _, data = m.uid("SEARCH", None, f"UID {','.join(str(int(u)) for u in uids)} UNSEEN")
        unseen = {u.decode() for u in (data[0].split() if data and data[0] else [])}
        return [u for u in uids if str(u) not in unseen]
    finally:
        close(m)


def contacts(cfg: dict, limit: int = 300) -> list[dict[str, str]]:
    """Known addresses: senders in the inbox plus recipients in the Sent folder (most recent first)."""
    seen: dict[str, str] = {}
    m = connect(cfg, None)
    try:
        sent = special_folder(m, "\\Sent")
        for folder, keys in (("INBOX", ("From",)), (sent, ("To", "Cc"))):
            if not folder:
                continue
            typ, _ = m.select(q(folder), readonly=True)
            if typ != "OK":
                continue
            _, data = m.uid("SEARCH", None, "ALL")
            uids = (data[0].split() if data and data[0] else [])[-limit:]
            if not uids:
                continue
            _, res = m.uid("FETCH", b",".join(uids), "(BODY.PEEK[HEADER.FIELDS (FROM TO CC)])")
            for _info, raw, _tail in reversed(_chunks(res)):
                msg = email.message_from_bytes(raw)
                for k in keys:
                    for n, a in getaddresses([header(msg, k)]):
                        a = a.lower()
                        if a and "@" in a and a not in seen and "noreply" not in a and "no-reply" not in a:
                            seen[a] = n.strip('" ')
    finally:
        close(m)
    own = cfg["email"].lower()
    return [{"address": a, "name": n} for a, n in seen.items() if a != own]


def test_account(cfg: dict) -> str | None:
    """Try IMAP and SMTP login. Returns an error code (see strings.json) or None."""
    try:
        m = imaplib.IMAP4_SSL(cfg["imap_server"], int(cfg["imap_port"]), timeout=20)
        try:
            m.login(cfg["email"], cfg["password"])
        finally:
            close(m)
    except imaplib.IMAP4.error as err:
        # Gmail/iCloud/Outlook answer the normal password with a hint that an app password is required.
        text = str(err).lower()
        if "application-specific" in text or "app password" in text or "app-specific" in text or "weblogin" in text:
            return "app_password_required"
        return "invalid_auth_imap"
    except Exception:  # noqa: BLE001
        return "cannot_connect_imap"
    try:
        s = _smtp(cfg, timeout=20)
        try:
            s.login(cfg["email"], cfg["password"])
        finally:
            try:
                s.quit()
            except Exception:  # noqa: BLE001
                pass
    except smtplib.SMTPAuthenticationError:
        return "invalid_auth_smtp"
    except Exception:  # noqa: BLE001
        return "cannot_connect_smtp"
    return None


def _smtp(cfg: dict, timeout: int = TIMEOUT) -> smtplib.SMTP:
    # Own EHLO name: the default '[172.x.x.x]' of a container is a spam signal for Gmail.
    ehlo = "mail." + cfg["email"].split("@")[-1].lower()
    port = int(cfg["smtp_port"])
    if port == 465:
        return smtplib.SMTP_SSL(cfg["smtp_server"], 465, timeout=timeout, local_hostname=ehlo)
    s = smtplib.SMTP(cfg["smtp_server"], port, timeout=timeout, local_hostname=ehlo)
    s.starttls()
    return s


QUOTE = {
    "en": {"wrote": "On {date}, {name} <{address}> wrote:", "fwd": "Begin forwarded message:", "from": "From",
           "subject": "Subject", "date": "Date", "to": "To", "fmt": "%b %d, %Y at %H:%M"},
    "nl": {"wrote": "Op {date} schreef {name} <{address}>:", "fwd": "Begin doorgestuurd bericht:", "from": "Van",
           "subject": "Onderwerp", "date": "Datum", "to": "Aan", "fmt": "%d-%m-%Y om %H:%M"},
}


def send(cfg: dict, sender_name: str, to: list[str], cc: list[str], subject: str, body: str,
         original_uid: str | None, mode: str, sent_folder: str | None, bcc: list[str] | None = None,
         folder: str = "INBOX", language: str = "en",
         attachments: list[tuple[str, str, bytes]] | None = None) -> dict[str, Any]:
    """Send via SMTP (same login as IMAP). reply/reply_all/forward quote the original (from `folder`).
    sent_folder: None = server keeps a copy itself (Gmail), "AUTO" = folder with \\Sent, else that folder."""
    words = QUOTE.get((language or "en")[:2], QUOTE["en"])
    orig = None
    if original_uid:
        m = connect(cfg, folder)
        try:
            _, res = m.uid("FETCH", str(original_uid), "(BODY.PEEK[])")
            raw = next((r[1] for r in res or [] if isinstance(r, tuple)), None)
        finally:
            close(m)
        if raw is None:
            raise MailError("original_not_found")
        orig = email.message_from_bytes(raw)

    own = cfg["email"].lower()
    msg = EmailMessage()
    msg["From"] = formataddr((sender_name, own)) if sender_name else own
    msg["To"] = ", ".join(to)
    if cc:
        msg["Cc"] = ", ".join(cc)
    msg["Subject"] = subject
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid(domain=own.split("@")[-1])

    html = "<div>" + htmllib.escape(body).replace("\n", "<br>") + "</div>"
    plain = body
    if orig is not None:
        o_html = o_text = None
        for p in orig.walk():
            if p.is_multipart() or p.get_filename():
                continue
            if p.get_content_type() == "text/html" and o_html is None:
                o_html = part_text(p)
            elif p.get_content_type() == "text/plain" and o_text is None:
                o_text = part_text(p)
        if o_text is None and o_html:
            o_text = html_to_text(o_html)
        o_name, o_address = sender(orig)
        o_date = orig.get("Date", "")
        try:
            o_date = parsedate_to_datetime(o_date).strftime(words["fmt"])
        except Exception:  # noqa: BLE001
            pass
        if mode == "forward":
            head = (f"{words['fwd']}\n\n{words['from']}: {o_name} <{o_address}>\n{words['subject']}: {header(orig, 'Subject')}\n"
                    f"{words['date']}: {o_date}\n{words['to']}: {header(orig, 'To')}\n\n")
            plain = body + "\n\n" + head + (o_text or "")
            html += "<br><div>" + htmllib.escape(head).replace("\n", "<br>") + "</div>" + (o_html or htmllib.escape(o_text or "").replace("\n", "<br>"))
        else:
            line = words["wrote"].format(date=o_date, name=o_name, address=o_address)
            plain = body + "\n\n" + line + "\n" + "\n".join(["> " + x for x in (o_text or "").splitlines()])
            html += ("<br><div>" + htmllib.escape(line) + "</div><blockquote type=\"cite\" style=\"margin:0 0 0 .8ex;"
                     "border-left:2px solid #0a84ff;padding-left:1ex\">" + (o_html or htmllib.escape(o_text or "").replace("\n", "<br>")) + "</blockquote>")
            mid = message_id(orig)
            if mid:
                msg["In-Reply-To"] = mid
                msg["References"] = (" ".join((orig.get("References") or "").split()) + " " + mid).strip()
    msg.set_content(plain)
    msg.add_alternative("<html><body style=\"font-family:-apple-system,Helvetica,Arial,sans-serif\">" + html + "</body></html>", subtype="html")
    if orig is not None and mode == "forward":
        for p in orig.walk():
            if p.get_filename() and not p.is_multipart():
                main, _, sub = p.get_content_type().partition("/")
                msg.add_attachment(p.get_payload(decode=True) or b"", maintype=main, subtype=sub or "octet-stream",
                                   filename=str(make_header(decode_header(p.get_filename()))))

    for name, ctype, data in attachments or []:
        main, _, sub = ctype.partition("/")
        msg.add_attachment(data, maintype=main or "application", subtype=sub or "octet-stream", filename=name)

    s = _smtp(cfg)
    try:
        s.login(cfg["email"], cfg["password"])
        s.send_message(msg, from_addr=own, to_addrs=list(to) + list(cc or []) + list(bcc or []))  # BCC not in headers
    finally:
        try:
            s.quit()
        except Exception:  # noqa: BLE001
            pass

    if sent_folder or (orig is not None and mode != "forward"):
        m = connect(cfg, folder if orig is not None else None, readonly=False)
        try:
            if sent_folder == "AUTO":
                sent_folder = special_folder(m, "\\Sent")
            if sent_folder:
                m.append(q(sent_folder), "(\\Seen)", imaplib.Time2Internaldate(time.time()), msg.as_bytes())
            if orig is not None and mode != "forward":
                m.uid("STORE", str(original_uid), "+FLAGS", "(\\Answered)")
        except Exception:  # noqa: BLE001
            pass  # sent is sent; the copy and the flag are secondary
        finally:
            close(m)
    return {"ok": True}
