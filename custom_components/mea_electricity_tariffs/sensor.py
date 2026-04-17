from __future__ import annotations

import datetime
from typing import Callable

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import (
    DATA_COORDINATOR,
    DEVICE_MANUFACTURER,
    DEVICE_NAME,
    DOMAIN,
    FT_URL,
    PRICE_SENSOR_DEFINITIONS,
    PRICE_UNIT,
    STATE_SENSOR_NAME,
    STATE_URL,
    STORAGE_KEY,
    STORAGE_VERSION,
    TARIFF_URL,
)
from .parser import parse_ft_page, parse_holiday_table, parse_tariff_page


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the MEA Electricity Tariff sensor platform from a config entry."""
    coordinator: MeaTariffCoordinator = hass.data[DOMAIN][entry.entry_id][
        DATA_COORDINATOR
    ]
    sensors: list[SensorEntity] = [
        MeaTariffPriceSensor(coordinator, key, name)
        for key, name in PRICE_SENSOR_DEFINITIONS
    ]
    sensors.append(MeaElectricityTariffSensor(coordinator))
    async_add_entities(sensors)


_DEVICE_INFO = DeviceInfo(
    identifiers={(DOMAIN, DOMAIN)},
    name=DEVICE_NAME,
    manufacturer=DEVICE_MANUFACTURER,
)


class MeaTariffCoordinator:
    """Shared data manager for MEA tariff prices and holidays."""

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        self._store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self._prices: dict[str, float] = {}
        self._ft_price: float | None = None
        self._stored_price_year: int | None = None
        self._stored_price_month: int | None = None
        self._holidays: set[datetime.date] = set()
        self._stored_holiday_year: int | None = None
        self._last_price_update: str | None = None
        self._last_holiday_update: str | None = None
        self._available = True
        self._listeners: list[Callable[[], None]] = []
        self._unsub_daily = None
        self._unsub_hourly = None

    @property
    def available(self) -> bool:
        return self._available

    def get_price(self, key: str) -> float | None:
        if key == "ft_price":
            return self._ft_price
        return self._prices.get(key)

    def get_holidays(self) -> set[datetime.date]:
        return self._holidays

    async def async_initialize(self) -> None:
        await self._load()
        await self._refresh_prices_if_needed()
        await self._refresh_holidays_if_needed()
        self._unsub_daily = async_track_time_change(
            self.hass,
            self._async_daily_refresh,
            hour=0,
            minute=0,
            second=0,
        )
        self._unsub_hourly = async_track_time_change(
            self.hass,
            self._async_hourly_refresh,
            minute=0,
            second=0,
        )

    async def async_force_refresh(self) -> None:
        """Force a fetch from the remote sources, bypassing cache."""
        try:
            await self._fetch_prices()
            now = dt_util.now()
            self._stored_price_year = now.year
            self._stored_price_month = now.month
            self._last_price_update = dt_util.utcnow().isoformat()
        except Exception:
            pass

        try:
            now_local = dt_util.as_local(dt_util.utcnow())
            current_thai_year = now_local.year + 543
            holidays = await self._fetch_holidays(current_thai_year)
            if holidays:
                self._holidays = holidays
                self._stored_holiday_year = current_thai_year
                self._last_holiday_update = dt_util.utcnow().isoformat()
        except Exception:
            pass

        await self._save()
        self._available = True
        self._async_notify_listeners()

    async def async_cleanup(self) -> None:
        """Cancel scheduled timers."""
        if self._unsub_daily is not None:
            self._unsub_daily()
            self._unsub_daily = None
        if self._unsub_hourly is not None:
            self._unsub_hourly()
            self._unsub_hourly = None

    def async_add_listener(self, listener: Callable[[], None]) -> Callable[[], None]:
        self._listeners.append(listener)

        def remove_listener() -> None:
            if listener in self._listeners:
                self._listeners.remove(listener)

        return remove_listener

    @callback
    def _async_notify_listeners(self) -> None:
        for listener in list(self._listeners):
            listener()

    @callback
    def _async_daily_refresh(self, now: datetime.datetime) -> None:
        self.hass.async_create_task(self._daily_refresh())

    @callback
    def _async_hourly_refresh(self, now: datetime.datetime) -> None:
        self.hass.async_create_task(self._hourly_refresh())

    async def _daily_refresh(self) -> None:
        updated = await self._refresh_prices_if_needed()
        updated = (await self._refresh_holidays_if_needed()) or updated
        if updated:
            self._async_notify_listeners()

    async def _hourly_refresh(self) -> None:
        # Notify listeners so the state sensor recalculates on the hour
        self._async_notify_listeners()

    async def _load(self) -> None:
        stored = await self._store.async_load()
        if not stored:
            return

        year = stored.get("price_year")
        month = stored.get("price_month")
        prices = stored.get("prices", {})
        ft_price = stored.get("ft_price")

        if isinstance(year, int) and isinstance(month, int):
            self._stored_price_year = year
            self._stored_price_month = month

        if isinstance(prices, dict):
            self._prices = {
                key: float(value) for key, value in prices.items() if value is not None
            }

        if isinstance(ft_price, (int, float, str)):
            try:
                self._ft_price = float(ft_price)
            except ValueError:
                self._ft_price = None

        self._last_price_update = stored.get("last_price_update")

        holiday_year = stored.get("holiday_year")
        dates = stored.get("holiday_dates", [])
        if isinstance(holiday_year, int) and isinstance(dates, list):
            self._stored_holiday_year = holiday_year
            self._holidays = {
                datetime.date.fromisoformat(d) for d in dates if isinstance(d, str)
            }
            self._last_holiday_update = stored.get("last_holiday_update")

    async def _save(self) -> None:
        await self._store.async_save(
            {
                "price_year": self._stored_price_year,
                "price_month": self._stored_price_month,
                "prices": self._prices,
                "ft_price": self._ft_price,
                "last_price_update": self._last_price_update,
                "holiday_year": self._stored_holiday_year,
                "holiday_dates": [d.isoformat() for d in sorted(self._holidays)],
                "last_holiday_update": self._last_holiday_update,
            }
        )

    async def _refresh_prices_if_needed(self) -> bool:
        now = dt_util.now()
        if (
            self._stored_price_year == now.year
            and self._stored_price_month == now.month
            and self._prices
            and self._ft_price is not None
        ):
            return False

        try:
            await self._fetch_prices()
            self._stored_price_year = now.year
            self._stored_price_month = now.month
            self._last_price_update = dt_util.utcnow().isoformat()
            await self._save()
            self._available = True
            return True
        except Exception:
            if not self._prices or self._ft_price is None:
                self._available = False
            return False

    async def _refresh_holidays_if_needed(self) -> bool:
        now_local = dt_util.as_local(dt_util.utcnow())
        current_thai_year = now_local.year + 543
        if self._stored_holiday_year == current_thai_year and self._holidays:
            return False

        try:
            holidays = await self._fetch_holidays(current_thai_year)
            if holidays:
                self._holidays = holidays
                self._stored_holiday_year = current_thai_year
                self._last_holiday_update = dt_util.utcnow().isoformat()
                await self._save()
                return True
        except Exception:
            if not self._holidays:
                self._available = False
        return False

    async def _fetch_prices(self) -> None:
        session = async_get_clientsession(self.hass)

        response = await session.get(TARIFF_URL, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()
        self._prices = parse_tariff_page(await response.text())

        response = await session.get(FT_URL, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()
        today = dt_util.as_local(dt_util.utcnow()).date()
        self._ft_price = parse_ft_page(await response.text(), today)

    async def _fetch_holidays(self, current_thai_year: int) -> set[datetime.date]:
        session = async_get_clientsession(self.hass)
        response = await session.get(STATE_URL, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()
        return parse_holiday_table(await response.text(), current_thai_year)


def _compute_tou_state(
    current_date: datetime.date,
    current_time: datetime.time,
    holidays: set[datetime.date],
) -> str:
    """Return 'off-peak' or 'on-peak' for the given date/time."""
    if current_date in holidays:
        return "off-peak"
    if current_date.weekday() >= 5:
        return "off-peak"
    if current_time >= datetime.time(22, 0) or current_time < datetime.time(9, 0):
        return "off-peak"
    return "on-peak"


class _CoordinatorEntity(SensorEntity):
    """Base class: wires up coordinator listener lifecycle and shared properties."""

    _attr_should_poll = False

    def __init__(self, coordinator: MeaTariffCoordinator) -> None:
        self.coordinator = coordinator
        self._remove_listener: Callable[[], None] | None = None

    @property
    def available(self) -> bool:
        return self.coordinator.available

    @property
    def device_info(self) -> DeviceInfo:
        return _DEVICE_INFO

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._remove_listener = self.coordinator.async_add_listener(
            self._handle_coordinator_update
        )

    async def async_will_remove_from_hass(self) -> None:
        if self._remove_listener is not None:
            self._remove_listener()
            self._remove_listener = None

    @callback
    def _handle_coordinator_update(self) -> None:
        self.async_write_ha_state()


class MeaTariffPriceSensor(_CoordinatorEntity):
    """Sensor for a single MEA tariff price."""

    _attr_icon = "mdi:currency-thb"
    _attr_native_unit_of_measurement = PRICE_UNIT

    def __init__(self, coordinator: MeaTariffCoordinator, key: str, name: str) -> None:
        super().__init__(coordinator)
        self._key = key
        self._attr_name = name
        self._attr_unique_id = f"{DOMAIN}_{key}"

    @property
    def native_value(self) -> float | None:
        return self.coordinator.get_price(self._key)


class MeaElectricityTariffSensor(_CoordinatorEntity):
    """Sensor for current MEA off-peak / on-peak state."""

    _attr_name = STATE_SENSOR_NAME
    _attr_icon = "mdi:clock-outline"
    _attr_unique_id = f"{DOMAIN}_tou_state"
    _attr_native_unit_of_measurement = None

    def __init__(self, coordinator: MeaTariffCoordinator) -> None:
        super().__init__(coordinator)

    @property
    def native_value(self) -> str:
        now = dt_util.as_local(dt_util.utcnow())
        return _compute_tou_state(
            now.date(), now.time(), self.coordinator.get_holidays()
        )
