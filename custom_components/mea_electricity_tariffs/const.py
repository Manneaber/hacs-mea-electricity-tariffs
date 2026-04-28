from homeassistant.const import Platform

DOMAIN = "mea_electricity_tariffs"
PLATFORMS = [Platform.SENSOR, Platform.BUTTON]
DATA_COORDINATOR = "coordinator"

# Storage
STORAGE_KEY = "mea_electricity_tariff_data"
STORAGE_VERSION = 1

# URLs
STATE_URL = "https://www.mea.or.th/electricity/electricity-tariffs/B0kv94Yol"
TARIFF_URL = "https://www.mea.or.th/our-services/tariff-calculation/other/D5xEaEwgU"
FT_URL = "https://www.mea.or.th/our-services/tariff-calculation/ft/bG2m6iSUN"

# Device / sensor meta
STATE_SENSOR_NAME = "MEA Time-of-Use State"
PRICE_UNIT = "THB/kWh"
DEVICE_NAME = "MEA Electricity Tariffs"
DEVICE_MANUFACTURER = "Manneaber"

# Thai months
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

# Price sensor definitions
PRICE_SENSOR_DEFINITIONS = [
    ("base_1_15", "MEA Tariff 1.1 1–15 Unit"),
    ("base_16_25", "MEA Tariff 1.1 16–25 Unit"),
    ("base_26_35", "MEA Tariff 1.1 26–35 Unit"),
    ("base_36_100", "MEA Tariff 1.1 36–100 Unit"),
    ("base_101_150", "MEA Tariff 1.1 101–150 Unit"),
    ("base_151_400", "MEA Tariff 1.1 151–400 Unit"),
    ("base_401_plus", "MEA Tariff 1.1 401+ Unit"),
    ("base2_1_150", "MEA Tariff 1.2 1–150 Unit"),
    ("base2_151_400", "MEA Tariff 1.2 151–400 Unit"),
    ("base2_401_plus", "MEA Tariff 1.2 401+ Unit"),
    ("tou_12_24_on_peak", "MEA TOU 12–24 kV On Peak"),
    ("tou_12_24_off_peak", "MEA TOU 12–24 kV Off Peak"),
    ("tou_lt_12_on_peak", "MEA TOU under 12 kV On Peak"),
    ("tou_lt_12_off_peak", "MEA TOU under 12 kV Off Peak"),
    ("ft_price", "MEA FT Rate"),
]

# Substrings identifying each section header in the raw tariff page HTML.
TARIFF_SECTION_MARKER_11 = "1.1 อัตราปกติปริมาณการใช้พลังงานไฟฟ้าไม่เกิน 150 หน่วยต่อเดือน"
TARIFF_SECTION_MARKER_12 = "1.2 อัตราปกติปริมาณการใช้พลังงานไฟฟ้าเกินกว่า 150 หน่วยต่อเดือน"
TARIFF_SECTION_MARKER_TOU = "1.3 อัตราตามช่วงเวลา"

# Row matchers for type 1.1 (usage ≤ 150 units/month)
TARIFF_ROW_MATCHERS_11: list[tuple[str, list[str]]] = [
    ("base_1_15", ["1 – 15", "15 หน่วย"]),
    ("base_16_25", ["16 – 25", "10 หน่วยต่อไป"]),
    ("base_26_35", ["26 – 35", "10 หน่วยต่อไป"]),
    ("base_36_100", ["36 – 100", "65 หน่วยต่อไป"]),
    ("base_101_150", ["101 – 150", "50 หน่วยต่อไป"]),
    ("base_151_400", ["151 – 400", "250 หน่วยต่อไป"]),
    ("base_401_plus", ["401"]),
    ("base_401_plus", ["เกินกว่า 400"]),
]

# Row matchers for type 1.2 (usage > 150 units/month)
TARIFF_ROW_MATCHERS_12: list[tuple[str, list[str]]] = [
    ("base2_1_150", ["1 – 150"]),
    ("base2_151_400", ["151 – 400"]),
    ("base2_401_plus", ["401"]),
    ("base2_401_plus", ["เกินกว่า 400"]),
]

# TOU multi-column row matchers: (label_prefix, on_peak_key, off_peak_key)
TARIFF_TOU_MATCHERS: list[tuple[str, str, str]] = [
    ("1.3.1", "tou_12_24_on_peak", "tou_12_24_off_peak"),
    ("1.3.2", "tou_lt_12_on_peak", "tou_lt_12_off_peak"),
]
