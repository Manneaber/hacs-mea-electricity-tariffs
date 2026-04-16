# MEA Electricity Tariffs

Home Assistant custom integration for MEA electricity tariffs.

This integration provides:
- A `sensor` for current MEA Time-of-Use state (`off-peak` / `on-peak`).
- Price sensors for MEA base tariff blocks.
- Time-of-Use (TOU) tariff sensors for 12–24 kV and under 12 kV.
- FT price sensor based on the current FT rate.
- Monthly refresh of tariff prices.
- Force-refresh support via a dedicated service button.
- Device grouping so all MEA tariff entities belong to the same device.

## Features

- Parses MEA tariff pages from:
  - `https://www.mea.or.th/electricity/electricity-tariffs/B0kv94Yol` for holiday schedule.
  - `https://www.mea.or.th/our-services/tariff-calculation/other/D5xEaEwgU` for price.
  - `https://www.pea.co.th/en/our-services/tariff/ft` for FT price (use PEA site since price will be equals between MEA and PEA).
- Supports config entry setup through the Home Assistant UI.
- Stores tariff prices and holiday in Home Assistant storage.

## Entities

The integration exposes the following entities:

- `sensor.mea_time_of_use_state`
- `sensor.mea_tariff_15_units_first_1_15`
- `sensor.mea_tariff_10_units_next_16_25`
- `sensor.mea_tariff_10_units_next_26_35`
- `sensor.mea_tariff_65_units_next_36_100`
- `sensor.mea_tariff_50_units_next_101_150`
- `sensor.mea_tariff_250_units_next_151_400`
- `sensor.mea_tariff_above_400_units`
- `sensor.mea_tou_12_24_kv_on_peak`
- `sensor.mea_tou_12_24_kv_off_peak`
- `sensor.mea_tou_under_12_kv_on_peak`
- `sensor.mea_tou_under_12_kv_off_peak`
- `sensor.mea_ft_price`

> All entities are grouped under a single device for simpler management.

## Installation

### HACS (Custom Repository)

1. Add this repository as a custom integration in HACS.
2. Install the integration from HACS.
3. Restart Home Assistant.
4. Go to Settings > Devices & Services > Add Integration.
5. Search for `MEA Electricity Tariffs` and follow the setup flow.

### Manual installation

1. Copy the `custom_components/mea_electricity_tariffs` folder into your Home Assistant `custom_components` directory.
2. Restart Home Assistant.
3. Add the integration from Settings > Devices & Services > Add Integration.

## Dependencies

- Home Assistant core integration APIs
- Uses the built-in `aiohttp` session from Home Assistant

## Notes

- The integration refreshes tariff prices once per month.
- The state sensor remains current with hourly updates.
- A forced refresh action is available to immediately re-fetch all tariff data.
- All codes are AI-generated.

## License

MIT
