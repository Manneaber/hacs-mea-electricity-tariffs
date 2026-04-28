# MEA Electricity Tariffs

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
![version](https://img.shields.io/badge/version-0.3.4-blue)

Home Assistant custom integration for MEA (Metropolitan Electricity Authority) electricity tariffs.

This integration provides:

- A `sensor` for the current MEA Time-of-Use state (`off-peak` / `on-peak`).
- Price sensors for MEA base tariff blocks (units 1–15 through 401+).
- Time-of-Use (TOU) tariff sensors for 12–24 kV and under 12 kV.
- FT (Fuel Tariff) price sensor.
- A `button` to force-refresh all tariff data on demand.
- Monthly refresh of tariff prices and annual refresh of the holiday schedule.
- Device grouping so all MEA tariff entities belong to the same device.

## Features

- Parses MEA tariff pages from:
  - `https://www.mea.or.th/electricity/electricity-tariffs/B0kv94Yol` — holiday schedule.
  - `https://www.mea.or.th/our-services/tariff-calculation/other/D5xEaEwgU` — base and TOU tariff prices.
  - `https://www.mea.or.th/our-services/tariff-calculation/ft/bG2m6iSUN` — FT rate history.
- Supports config entry setup through the Home Assistant UI.
- Persists tariff prices and holidays in Home Assistant storage so they survive restarts.

## Time-of-Use Schedule

| Period   | Days                                  | Hours         |
| -------- | ------------------------------------- | ------------- |
| On-peak  | Mon – Fri (excluding public holidays) | 09:00 – 22:00 |
| Off-peak | Mon – Fri (excluding public holidays) | 22:00 – 09:00 |
| Off-peak | Sat – Sun and public holidays         | All day       |

## Entities

The integration exposes the following entities (all grouped under one device):

### Sensors

| Entity ID                             | Display Name                 | Unit                   |
| ------------------------------------- | ---------------------------- | ---------------------- |
| `sensor.mea_time_of_use_state`        | MEA Time-of-Use State        | `on-peak` / `off-peak` |
| `sensor.mea_tariff_1_1_1_15_unit`     | MEA Tariff 1.1 1–15 Unit     | THB/kWh                |
| `sensor.mea_tariff_1_1_16_25_unit`    | MEA Tariff 1.1 16–25 Unit    | THB/kWh                |
| `sensor.mea_tariff_1_1_26_35_unit`    | MEA Tariff 1.1 26–35 Unit    | THB/kWh                |
| `sensor.mea_tariff_1_1_36_100_unit`   | MEA Tariff 1.1 36–100 Unit   | THB/kWh                |
| `sensor.mea_tariff_1_1_101_150_unit`  | MEA Tariff 1.1 101–150 Unit  | THB/kWh                |
| `sensor.mea_tariff_1_1_151_400_unit`  | MEA Tariff 1.1 151–400 Unit  | THB/kWh                |
| `sensor.mea_tariff_1_1_401_unit`      | MEA Tariff 1.1 401+ Unit     | THB/kWh                |
| `sensor.mea_tariff_1_2_1_150_unit`    | MEA Tariff 1.2 1–150 Unit    | THB/kWh                |
| `sensor.mea_tariff_1_2_151_400_unit`  | MEA Tariff 1.2 151–400 Unit  | THB/kWh                |
| `sensor.mea_tariff_1_2_401_unit`      | MEA Tariff 1.2 401+ Unit     | THB/kWh                |
| `sensor.mea_tou_12_24_kv_on_peak`     | MEA TOU 12–24 kV On Peak     | THB/kWh                |
| `sensor.mea_tou_12_24_kv_off_peak`    | MEA TOU 12–24 kV Off Peak    | THB/kWh                |
| `sensor.mea_tou_under_12_kv_on_peak`  | MEA TOU under 12 kV On Peak  | THB/kWh                |
| `sensor.mea_tou_under_12_kv_off_peak` | MEA TOU under 12 kV Off Peak | THB/kWh                |
| `sensor.mea_ft_price`                 | MEA FT Rate                  | THB/kWh                |

### Button

| Entity ID                        | Display Name            |
| -------------------------------- | ----------------------- |
| `button.refresh_mea_tariff_data` | Refresh MEA Tariff Data |

## Installation

### HACS (Custom Repository)

1. Add this repository as a custom integration in HACS.
2. Install the integration from HACS.
3. Restart Home Assistant.
4. Go to **Settings → Devices & Services → Add Integration**.
5. Search for `MEA Electricity Tariffs` and follow the setup flow.

### Manual Installation

1. Copy the `custom_components/mea_electricity_tariffs` folder into your Home Assistant `custom_components` directory.
2. Restart Home Assistant.
3. Add the integration from **Settings → Devices & Services → Add Integration**.

## Dependencies

- Home Assistant core integration APIs
- Uses the built-in `aiohttp` session from Home Assistant

## Notes

- Tariff prices are refreshed once per month; the holiday schedule is refreshed once per Thai calendar year.
- The Time-of-Use state sensor is recalculated every hour.
- Press the **Refresh MEA Tariff Data** button to immediately re-fetch all tariff data from the source websites.
- All code is AI-generated.

## License

MIT
