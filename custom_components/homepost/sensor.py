"""Unread counter per account."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, OPT_NAME
from .coordinator import HomepostCoordinator


async def async_setup_entry(hass, entry, async_add_entities: AddEntitiesCallback) -> None:
    async_add_entities([UnreadSensor(entry.runtime_data)])


class UnreadSensor(CoordinatorEntity[HomepostCoordinator], SensorEntity):
    _attr_has_entity_name = True
    _attr_translation_key = "unread"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "emails"
    _attr_icon = "mdi:email-outline"

    def __init__(self, coordinator: HomepostCoordinator) -> None:
        super().__init__(coordinator)
        entry = coordinator.entry
        self._attr_unique_id = f"{entry.entry_id}_unread"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.options.get(OPT_NAME) or entry.title,
            manufacturer="Homepost",
            model=entry.data["email"],
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def native_value(self) -> int | None:
        return (self.coordinator.data or {}).get("unread")

    @property
    def extra_state_attributes(self) -> dict:
        return {"account": self.coordinator.entry.entry_id, "email": self.coordinator.entry.data["email"]}
