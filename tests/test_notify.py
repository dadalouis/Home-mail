from datetime import datetime

from conftest import notify

MON_10 = datetime(2026, 10, 26, 10, 0)  # a Monday
MON_23 = datetime(2026, 10, 26, 23, 30)


def cfg(**kw):
    return notify.clean(kw, {})


def msg(address="anna@example.com"):
    return {"address": address, "name": "Anna", "subject": "Hi", "uid": "1"}


def test_defaults_notify_everything():
    assert notify.wanted(cfg(), "acc", msg(), MON_10)


def test_switched_off_and_account_off():
    assert not notify.wanted(cfg(on=False), "acc", msg(), MON_10)
    assert not notify.wanted(cfg(accounts_off=["acc"]), "acc", msg(), MON_10)
    assert notify.wanted(cfg(accounts_off=["other"]), "acc", msg(), MON_10)


def test_days():
    assert not notify.wanted(cfg(days=[1, 2, 3, 4, 5, 6]), "acc", msg(), MON_10)  # Monday off
    assert notify.wanted(cfg(days=[0]), "acc", msg(), MON_10)


def test_quiet_hours_over_midnight():
    c = cfg(quiet_on=True, quiet_from="22:00", quiet_to="07:00")
    assert notify.in_quiet_hours(c, MON_23)
    assert notify.in_quiet_hours(c, datetime(2026, 10, 27, 6, 59))
    assert not notify.in_quiet_hours(c, datetime(2026, 10, 27, 7, 0))
    assert not notify.wanted(c, "acc", msg(), MON_23)
    assert notify.wanted(c, "acc", msg(), MON_10)


def test_quiet_hours_same_day_and_off():
    c = cfg(quiet_on=True, quiet_from="12:00", quiet_to="13:00")
    assert notify.in_quiet_hours(c, datetime(2026, 10, 26, 12, 30))
    assert not notify.in_quiet_hours(c, MON_10)
    assert not notify.in_quiet_hours(cfg(quiet_from="00:00", quiet_to="23:59"), MON_10)  # quiet_on off


def test_sender_lists():
    assert notify.sender_in("anna@example.com", "Anna@Example.com")
    assert notify.sender_in("example.com", "bob@mail.example.com")  # subdomain
    assert notify.sender_in("@example.com", "bob@example.com")
    assert not notify.sender_in("example.com", "bob@notexample.com")
    assert not notify.sender_in("", "bob@example.com")


def test_vip_and_mute():
    assert not notify.wanted(cfg(mute="example.com"), "acc", msg(), MON_10)
    assert not notify.wanted(cfg(only="vip", vip="boss@work.nl"), "acc", msg(), MON_10)
    assert notify.wanted(cfg(only="vip", vip="boss@work.nl\nexample.com"), "acc", msg(), MON_10)
    assert not notify.wanted(cfg(only="vip", vip="example.com", mute="anna@example.com"), "acc", msg(), MON_10)


def test_clean_ignores_bad_input():
    c = notify.clean({"quiet_from": "25:00", "only": "nobody", "days": [0, 9, "x"], "on": 0}, {})
    assert c["quiet_from"] == "22:00" and c["only"] == "all" and c["days"] == [0] and c["on"] is False


def test_clean_preview_drops_links():
    text = "Politie is op de hoogte\nLogo van Nextdoor Je profielfoto (https://nextdoor.nl/news_feed/?ct=abc&ec=x=)"
    assert notify.clean_preview(text) == "Politie is op de hoogte Logo van Nextdoor Je profielfoto"
    assert notify.clean_preview("a " * 200).endswith("…")
    assert len(notify.clean_preview("a " * 200)) <= 141


def test_clean_device_accounts():
    out = notify.clean({"device_accounts_off": {"web:Home-mail iPhone ab12": ["E1"], "app:Pad": [], "bad": "x"}}, {})
    assert out["device_accounts_off"] == {"web:Home-mail iPhone ab12": ["E1"]}


def test_targets_per_device_account(monkeypatch):
    monkeypatch.setattr(notify, "app_devices", lambda hass, user: [{"name": "iPhone", "service": "s1", "os": "iOS"},
                                                                    {"name": "Pad", "service": "s2", "os": "iPadOS"}])
    monkeypatch.setattr(notify, "web_devices", lambda hass, names: [{"name": n, "entity_id": f"notify.{n}"} for n in names])
    c = cfg(device_accounts_off={"app:Pad": ["WORK"], "web:w1": ["WORK"]})
    to = notify.targets(None, "u1", c, ["w1", "w2"], "WORK")
    assert [d["name"] for d in to["app"]] == ["iPhone"] and to["web"] == ["notify.w2"] and to["web_names"] == {"notify.w2": "w2"}
    to = notify.targets(None, "u1", c, ["w1", "w2"], "GMAIL")
    assert len(to["app"]) == 2 and to["web"] == ["notify.w1", "notify.w2"]


def test_since_date():
    from datetime import date
    today = date(2026, 3, 31)
    assert notify.since_date({"n": 2, "unit": "w"}, today) == "2026-03-17"
    assert notify.since_date({"n": 10, "unit": "d"}, today) == "2026-03-21"
    assert notify.since_date({"n": 1, "unit": "m"}, today) == "2026-02-28"  # no 31 February
    assert notify.since_date({"n": 1, "unit": "y"}, date(2028, 2, 29)) == "2027-02-28"
    assert notify.since_date({"all": True}, today) is None and notify.since_date(None, today) is None
