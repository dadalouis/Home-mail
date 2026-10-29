"""Load Home-mail's modules without a full Home Assistant install.

Only the parts that are plain Python are tested here (filters, quiet hours, attachments, IMAP IDLE). The
Home Assistant imports they make are replaced by small stand-ins, and the package __init__ is not run.
"""
import importlib
import re
import sys
import types
from datetime import datetime
from pathlib import Path

PKG = Path(__file__).resolve().parent.parent / "custom_components" / "homemail"


def _stub(name: str, **attrs) -> types.ModuleType:
    mod = sys.modules.get(name) or types.ModuleType(name)
    for k, v in attrs.items():
        setattr(mod, k, v)
    sys.modules[name] = mod
    return mod


class _Any:  # stands in for Home Assistant classes that are only used in type hints
    pass


_stub("homeassistant")
_stub("homeassistant.config_entries", ConfigEntry=_Any)
_stub("homeassistant.core", HomeAssistant=_Any, Event=_Any, callback=lambda f: f)
_stub("homeassistant.helpers")
_stub("homeassistant.helpers.entity_registry", async_get=lambda hass: None)
DEVICES = {}  # config entry id -> [device]
_stub("homeassistant.helpers.device_registry", async_get=lambda hass: None,
      async_entries_for_config_entry=lambda reg, entry_id: DEVICES.get(entry_id, []))
ISSUES = {}
_stub("homeassistant.helpers.issue_registry",
      IssueSeverity=types.SimpleNamespace(WARNING="warning"),
      async_create_issue=lambda hass, domain, issue_id, **kw: ISSUES.__setitem__(issue_id, kw),
      async_delete_issue=lambda hass, domain, issue_id: ISSUES.pop(issue_id, None))
_stub("homeassistant.util", slugify=lambda s: re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_"),
      dt=types.SimpleNamespace(now=datetime.now))
sys.modules["homeassistant.util.dt"] = sys.modules["homeassistant.util"].dt

pkg = types.ModuleType("homemail")
pkg.__path__ = [str(PKG)]
sys.modules["homemail"] = pkg

mail = importlib.import_module("homemail.mail")
notify = importlib.import_module("homemail.notify")
idle = importlib.import_module("homemail.idle")
actions = importlib.import_module("homemail.actions")
issues = importlib.import_module("homemail.issues")


class _Coordinator:  # minimal DataUpdateCoordinator: enough to build the Home-mail coordinator in tests
    def __class_getitem__(cls, item):
        return cls

    def __init__(self, hass, logger, name=None, config_entry=None, update_interval=None):
        self.hass, self.update_interval, self.data = hass, update_interval, None


_stub("homeassistant.exceptions", ConfigEntryAuthFailed=type("ConfigEntryAuthFailed", (Exception,), {}))
_stub("homeassistant.helpers.dispatcher", async_dispatcher_send=lambda *a: None)
_stub("homeassistant.helpers.update_coordinator", DataUpdateCoordinator=_Coordinator,
      UpdateFailed=type("UpdateFailed", (Exception,), {}))
coordinator = importlib.import_module("homemail.coordinator")
