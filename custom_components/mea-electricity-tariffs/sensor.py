from __future__ import annotations

import datetime
import html
import re

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

STORAGE_KEY = "mea_electricity_tariff_off_peak"
STORAGE_VERSION = 1
DATA_URL = "https://www.mea.or.th/electricity/electricity-tariffs/B0kv94Yol"
DEFAULT_NAME = "MEA Electricity Tariff"
MONTHS_TH = {
    "มกราคม": 1,
    "กุมภาพันธ์": 2,
    "มีนาคม": 3,
    "เมษายน": 4,
    "พฤษภาคม": 5,
    "มิถุนายน": 6,
    "กรกฎาคม": 7,
    "สิงหาคม": 8,
    "กันยายน": 9,
    "ตุลาคม": 10,
    "พฤศจิกายน": 11,
    "ธันวาคม": 12,
}


async def async_setup_platform(
    hass: HomeAssistant,
    config,
    async_add_entities: AddEntitiesCallback,
    discovery_info=None,
) -> None:
    """Set up the MEA Electricity Tariff sensor platform."""
    async_add_entities([MeaElectricityTariffSensor(hass)])


class MeaElectricityTariffSensor(SensorEntity):
    """Sensor for current MEA off-peak / on-peak state."""

    _attr_name = DEFAULT_NAME
    _attr_icon = "mdi:clock-outline"
    _attr_native_unit_of_measurement = None
    _attr_should_poll = False

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        self._store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self._holidays: set[datetime.date] = set()
        self._stored_year: int | None = None
        self._state: str | None = None
        self._last_update: str | None = None
        self._available = True
        self._unsub_refresh = None

    async def async_added_to_hass(self) -> None:
        await self._load_holidays()
        await self._refresh_if_needed()
        self.async_write_ha_state()
        self._unsub_refresh = async_track_time_change(
            self.hass,
            self._async_hourly_update,
            minute=0,
            second=0,
        )

    async def async_will_remove_from_hass(self) -> None:
        if self._unsub_refresh is not None:
            self._unsub_refresh()
            self._unsub_refresh = None

    @callback
    def _async_hourly_update(self, now: datetime.datetime) -> None:
        self.hass.async_create_task(self._refresh_and_write())

    async def _refresh_and_write(self) -> None:
        await self._refresh_if_needed()
        self.async_write_ha_state()

    @property
    def native_value(self) -> str | None:
        if self._state is None:
            return "unknown"
        return self._state

    @property
    def available(self) -> bool:
        return self._available

    async def async_update(self) -> None:
        await self._refresh_if_needed()

    async def _load_holidays(self) -> None:
        stored = await self._store.async_load()
        if not stored:
            return
        year = stored.get("year")
        dates = stored.get("holiday_dates", [])
        if isinstance(year, int) and isinstance(dates, list):
            self._stored_year = year
            self._holidays = {
                datetime.date.fromisoformat(date)
                for date in dates
                if isinstance(date, str)
            }
            self._last_update = stored.get("last_update")

    async def _refresh_if_needed(self) -> None:
        now = dt_util.as_local(dt_util.utcnow())
        current_thai_year = now.year + 543
        if self._stored_year == current_thai_year and self._holidays:
            self._state = self._compute_state(now.date(), now.time())
            return

        try:
            holidays = await self._fetch_holidays(current_thai_year)
            if holidays:
                self._holidays = holidays
                self._stored_year = current_thai_year
                self._last_update = dt_util.utcnow().isoformat()
                await self._store.async_save(
                    {
                        "year": self._stored_year,
                        "holiday_dates": [
                            date.isoformat() for date in sorted(self._holidays)
                        ],
                        "last_update": self._last_update,
                    }
                )
        except Exception:
            self._available = False

        self._state = self._compute_state(now.date(), now.time())

    def _compute_state(
        self, current_date: datetime.date, current_time: datetime.time
    ) -> str:
        if current_date in self._holidays:
            return "off-peak"

        weekday = current_date.weekday()
        if weekday >= 5:
            return "off-peak"

        if current_time >= datetime.time(22, 0) or current_time < datetime.time(9, 0):
            return "off-peak"

        return "on-peak"

    async def _fetch_holidays(self, current_thai_year: int) -> set[datetime.date]:
        session = async_get_clientsession(self.hass)
        response = await session.get(DATA_URL, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()
        text = await response.text()
        return self._parse_holiday_table(text, current_thai_year)

    def _parse_holiday_table(
        self, html_text: str, current_thai_year: int
    ) -> set[datetime.date]:
        table_match = re.search(
            r"<table[^>]*class=\"table\"[^>]*>(.*?)</table>", html_text, re.S | re.I
        )
        if not table_match:
            raise ValueError("Unable to find tariff table")

        table_html = table_match.group(1)
        header_cells = re.findall(r"<th[^>]*>(.*?)</th>", table_html, re.S | re.I)
        year_columns = [self._clean_text(cell) for cell in header_cells[2:]]
        year_to_index = {}
        for index, year_text in enumerate(year_columns, start=2):
            year_digits = re.search(r"(\d{4})", year_text)
            if year_digits:
                year_to_index[int(year_digits.group(1))] = index

        if current_thai_year not in year_to_index:
            if year_to_index:
                current_thai_year = max(year_to_index)
            else:
                raise ValueError("No year columns found in tariff table")

        tbody_match = re.search(r"<tbody>(.*?)</tbody>", table_html, re.S | re.I)
        rows_html = tbody_match.group(1) if tbody_match else table_html
        holidays: set[datetime.date] = set()

        for row_match in re.finditer(r"<tr[^>]*>(.*?)</tr>", rows_html, re.S | re.I):
            row_html = row_match.group(1)
            cells = re.findall(r"<td[^>]*>(.*?)</td>", row_html, re.S | re.I)
            if len(cells) <= year_to_index[current_thai_year] - 1:
                continue
            cell_text = self._clean_text(cells[year_to_index[current_thai_year] - 1])
            if not cell_text:
                continue
            first_line = cell_text.splitlines()[0].strip()
            try:
                holidays.add(self._parse_thai_date(first_line, current_thai_year - 543))
            except ValueError:
                continue

        return holidays

    def _clean_text(self, text: str) -> str:
        text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
        text = re.sub(r"<[^>]+>", "", text)
        text = html.unescape(text)
        return text.strip()

    def _parse_thai_date(self, date_text: str, year: int) -> datetime.date:
        date_text = date_text.replace("\u00a0", " ").strip()
        match = re.search(r"(\d{1,2})\s+([ก-๙]+)", date_text)
        if not match:
            raise ValueError("Invalid Thai date text")

        day = int(match.group(1))
        month_name = match.group(2).strip()
        if month_name not in MONTHS_TH:
            raise ValueError("Unknown Thai month: %s" % month_name)

        return datetime.date(year, MONTHS_TH[month_name], day)
