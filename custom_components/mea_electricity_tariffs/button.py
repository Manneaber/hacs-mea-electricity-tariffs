from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DATA_COORDINATOR, DEVICE_MANUFACTURER, DEVICE_NAME, DOMAIN
from .sensor import MeaTariffCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the MEA Electricity Tariff refresh button."""
    coordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]
    async_add_entities([MeaTariffRefreshButton(coordinator)])


class MeaTariffRefreshButton(ButtonEntity):
    """Button to force refresh MEA tariff data."""

    _attr_icon = "mdi:reload"
    _attr_name = "Refresh MEA Tariff Data"
    _attr_should_poll = False

    def __init__(self, coordinator: MeaTariffCoordinator) -> None:
        self.coordinator = coordinator
        self._attr_unique_id = f"{DOMAIN}_refresh"
        self._remove_listener = None

    @property
    def available(self) -> bool:
        return self.coordinator.available

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, DOMAIN)},
            name=DEVICE_NAME,
            manufacturer=DEVICE_MANUFACTURER,
        )

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._remove_listener = self.coordinator.async_add_listener(self._handle_coordinator_update)

    async def async_will_remove_from_hass(self) -> None:
        if self._remove_listener is not None:
            self._remove_listener()
            self._remove_listener = None

    async def async_press(self) -> None:
        """Force refresh the tariff data."""
        await self.coordinator.async_force_refresh()

    @callback
    def _handle_coordinator_update(self) -> None:
        self.async_write_ha_state()
