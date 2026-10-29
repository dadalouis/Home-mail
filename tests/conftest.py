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
_stub("homeassistant.core", HomeAssistant=_Any)
_stub("homeassistant.helpers")
_stub("homeassistant.helpers.entity_registry", async_get=lambda hass: None)
_stub("homeassistant.util", slugify=lambda s: re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_"),
      dt=types.SimpleNamespace(now=datetime.now))
sys.modules["homeassistant.util.dt"] = sys.modules["homeassistant.util"].dt

pkg = types.ModuleType("homemail")
pkg.__path__ = [str(PKG)]
sys.modules["homemail"] = pkg

mail = importlib.import_module("homemail.mail")
notify = importlib.import_module("homemail.notify")
idle = importlib.import_module("homemail.idle")
