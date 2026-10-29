import types

from conftest import actions


def hass(lang="nl"):
    return types.SimpleNamespace(config=types.SimpleNamespace(language=lang))


def test_action_ids_round_trip():
    a = actions.action_id("archive", "01ENTRY", "41449")
    assert actions.parse(a) == ("archive", "01ENTRY", "41449")
    assert actions.parse("ALARM") is None
    assert actions.parse("HOMEMAIL|explode|x|1") is None


def test_buttons_ios_and_android():
    ios = actions.buttons(hass(), "E", "7", "iOS")
    assert [b["title"] for b in ios] == ["Gelezen", "Archiveer", "Verwijder", "Beantwoord"]
    assert ios[2]["destructive"] is True and ios[3]["behavior"] == "textInput"
    android = actions.buttons(hass("en"), "E", "7", "Android")
    assert len(android) == 3  # Android shows at most three buttons
    assert [b["title"] for b in android] == ["Mark as read", "Archive", "Reply"]
    assert "textInputPlaceholder" not in android[2]


def test_reply_subject():
    assert actions.reply_subject("Hallo") == "Re: Hallo"
    assert actions.reply_subject("RE: Hallo") == "RE: Hallo"
