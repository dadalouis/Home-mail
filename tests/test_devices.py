import types

from conftest import DEVICES, notify


def fake_hass(services, entries):
    return types.SimpleNamespace(
        services=types.SimpleNamespace(has_service=lambda domain, name: domain == "notify" and name in services),
        config_entries=types.SimpleNamespace(async_entries=lambda domain: entries if domain == "mobile_app" else []),
    )


def entry(entry_id, user, title, device_name, os_name="iOS"):
    return types.SimpleNamespace(entry_id=entry_id, title=title,
                                 data={"user_id": user, "device_name": device_name, "os_name": os_name})


def test_renamed_iphone_is_found():
    # The real case: registered as "Laurence Koelewijn's iPhone pro", renamed to "iPhone Laurence" in HA,
    # so the service is notify.mobile_app_iphone_laurence.
    DEVICES["E1"] = [types.SimpleNamespace(name_by_user="iPhone Laurence", name="Laurence Koelewijn’s iPhone pro")]
    hass = fake_hass({"mobile_app_iphone_laurence"}, [entry("E1", "u1", "Laurence Koelewijn’s iPhone pro", "Laurence Koelewijn’s iPhone pro")])
    assert notify.app_devices(hass, "u1") == [{"name": "iPhone Laurence", "service": "mobile_app_iphone_laurence", "os": "iOS"}]


def test_not_renamed_device_and_other_users():
    DEVICES["E2"] = [types.SimpleNamespace(name_by_user=None, name="wall tab")]
    hass = fake_hass({"mobile_app_wall_tab"}, [entry("E2", "u1", "wall tab", "wall tab", "Android"),
                                               entry("E3", "u2", "Lennie", "Lennie")])
    assert notify.app_devices(hass, "u1") == [{"name": "wall tab", "service": "mobile_app_wall_tab", "os": "Android"}]
    assert notify.app_devices(hass, "u2") == []  # no notify service for it: skipped, not an error
