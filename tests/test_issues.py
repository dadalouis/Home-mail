import types

from conftest import ISSUES, issues


def entry(users):
    return types.SimpleNamespace(entry_id="E1", title="Gmail", options={"users": users, "name": "Anna gmail"})


def test_warning_when_every_admin_may_read():
    issues.check_access(None, entry([]))
    assert ISSUES["shared_with_admins_E1"]["translation_placeholders"] == {"account": "Anna gmail"}
    issues.check_access(None, entry(["user-1"]))
    assert "shared_with_admins_E1" not in ISSUES


def test_idle_notice_comes_and_goes():
    issues.idle_failing(None, entry([]), True, "timeout")
    assert ISSUES["idle_failing_E1"]["translation_placeholders"]["error"] == "timeout"
    issues.idle_failing(None, entry([]), False)
    assert "idle_failing_E1" not in ISSUES
