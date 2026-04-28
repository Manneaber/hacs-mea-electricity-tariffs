"""Pure HTML/text parsing helpers for MEA tariff and holiday data."""

from __future__ import annotations

import datetime
import html
import re

from .const import (
    MONTHS_TH,
    PRICE_SENSOR_DEFINITIONS,
    TARIFF_ROW_MATCHERS_11,
    TARIFF_ROW_MATCHERS_12,
    TARIFF_SECTION_MARKER_11,
    TARIFF_SECTION_MARKER_12,
    TARIFF_SECTION_MARKER_TOU,
    TARIFF_TOU_MATCHERS,
)


def clean_html_cell(text: str) -> str:
    """Strip tags, unescape entities, and normalise whitespace."""
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    return html.unescape(text).strip()


def parse_price(price_text: str) -> float:
    """Extract a numeric price from a raw cell string."""
    price_text = price_text.replace("บาท", "").replace(",", "").strip()
    match = re.search(r"([0-9]+\.?[0-9]*)", price_text)
    if not match:
        raise ValueError(f"Cannot parse price from: {price_text!r}")
    return float(match.group(1))


def parse_tariff_page(html_text: str) -> dict[str, float]:
    """Parse the MEA tariff HTML page and return a {key: price} mapping."""
    prices: dict[str, float] = {}

    # Locate section boundaries by their header text.
    pos11 = html_text.find(TARIFF_SECTION_MARKER_11)
    pos12 = html_text.find(TARIFF_SECTION_MARKER_12)
    pos_tou = html_text.find(TARIFF_SECTION_MARKER_TOU)

    if pos11 == -1 or pos12 == -1:
        raise ValueError("Cannot locate type 1.1 / 1.2 tariff sections in page")

    sec11_html = html_text[pos11:pos12]
    sec12_end = pos_tou if pos_tou != -1 else len(html_text)
    sec12_html = html_text[pos12:sec12_end]
    tou_html = html_text[pos_tou:] if pos_tou != -1 else ""

    # Parse each base-rate section with its own matchers.
    for section_html, matchers in (
        (sec11_html, TARIFF_ROW_MATCHERS_11),
        (sec12_html, TARIFF_ROW_MATCHERS_12),
    ):
        for row_html in re.findall(r"<tr[^>]*>(.*?)</tr>", section_html, re.S | re.I):
            cells = [
                clean_html_cell(cell)
                for cell in re.findall(r"<td[^>]*>(.*?)</td>", row_html, re.S | re.I)
            ]
            if len(cells) < 2:
                continue
            label = cells[0]
            for key, required in matchers:
                if key not in prices and all(s in label for s in required):
                    try:
                        prices[key] = parse_price(cells[-1])
                    except ValueError:
                        pass
                    break

    # Multi-column TOU rows — scan the TOU section only.
    for row_html in re.findall(r"<tr[^>]*>(.*?)</tr>", tou_html, re.S | re.I):
        cells = [
            clean_html_cell(cell)
            for cell in re.findall(r"<td[^>]*>(.*?)</td>", row_html, re.S | re.I)
        ]
        if len(cells) < 3:
            continue
        label = cells[0]
        for prefix, on_key, off_key in TARIFF_TOU_MATCHERS:
            if label.startswith(prefix):
                try:
                    prices[on_key] = parse_price(cells[1])
                    prices[off_key] = parse_price(cells[2])
                except ValueError:
                    pass
                break

    missing = [
        key
        for key, _ in PRICE_SENSOR_DEFINITIONS
        if key != "ft_price" and key not in prices
    ]
    if missing:
        raise ValueError(f"Missing tariff prices: {missing}")
    return prices


def parse_ft_page(html_text: str, today: datetime.date | None = None) -> float:
    """Extract the current FT price from the MEA FT history page.

    The table lists values in satang/unit by Thai year and month.
    Returns the value converted to THB/kWh (satang ÷ 100).
    The *today* parameter allows injecting the reference date for testing.
    """
    if today is None:
        today = datetime.date.today()

    current_thai_year = today.year + 543
    current_month = today.month  # 1-based; cells[1]=Jan … cells[12]=Dec

    # Collect all data rows keyed by Thai year.
    rows: dict[int, list[str]] = {}
    for row_match in re.finditer(r"<tr[^>]*>(.*?)</tr>", html_text, re.S | re.I):
        cells = [
            clean_html_cell(cell)
            for cell in re.findall(
                r"<td[^>]*>(.*?)</td>", row_match.group(1), re.S | re.I
            )
        ]
        if len(cells) < 2:
            continue
        year_match = re.search(r"(\d{4})", cells[0])
        if not year_match:
            continue
        thai_year = int(year_match.group(1))
        if 2500 <= thai_year <= 2700:  # sanity-check Thai BE year range
            rows[thai_year] = cells

    if not rows:
        raise ValueError("Unable to find FT history table")

    # Walk back from the current Thai year to find the most recent published value.
    # For the current year only look at months up to and including the current month;
    # for prior years scan all 12 months in reverse.
    for thai_year in range(current_thai_year, current_thai_year - 2, -1):
        cells = rows.get(thai_year)
        if cells is None:
            continue
        max_month = current_month if thai_year == current_thai_year else 12
        for month in range(max_month, 0, -1):
            if month >= len(cells):
                continue
            value_str = cells[month].strip()
            if not value_str:
                continue
            num_match = re.search(r"(-?[0-9]+\.?[0-9]*)", value_str)
            if num_match:
                return float(num_match.group(1)) / 100.0

    raise ValueError(f"Unable to determine FT price for {today.isoformat()}")


def parse_holiday_table(html_text: str, current_thai_year: int) -> set[datetime.date]:
    """Parse the MEA holiday HTML table and return the set of holiday dates."""
    table_match = re.search(
        r'<table[^>]*class="table"[^>]*>(.*?)</table>', html_text, re.S | re.I
    )
    if not table_match:
        raise ValueError("Unable to find holiday table")

    table_html = table_match.group(1)
    header_cells = re.findall(r"<th[^>]*>(.*?)</th>", table_html, re.S | re.I)

    year_to_index: dict[int, int] = {}
    for index, cell in enumerate(header_cells[2:], start=2):
        m = re.search(r"(\d{4})", clean_html_cell(cell))
        if m:
            year_to_index[int(m.group(1))] = index

    if current_thai_year not in year_to_index:
        if not year_to_index:
            raise ValueError("No year columns found in holiday table")
        current_thai_year = max(year_to_index)

    col_index = year_to_index[current_thai_year]
    tbody_match = re.search(r"<tbody>(.*?)</tbody>", table_html, re.S | re.I)
    rows_html = tbody_match.group(1) if tbody_match else table_html

    holidays: set[datetime.date] = set()
    for row_match in re.finditer(r"<tr[^>]*>(.*?)</tr>", rows_html, re.S | re.I):
        cells = re.findall(r"<td[^>]*>(.*?)</td>", row_match.group(1), re.S | re.I)
        if len(cells) <= col_index - 1:
            continue
        cell_text = clean_html_cell(cells[col_index - 1])
        if not cell_text:
            continue
        first_line = cell_text.splitlines()[0].strip()
        try:
            holidays.add(_parse_thai_date(first_line, current_thai_year - 543))
        except ValueError:
            continue

    return holidays


def _parse_thai_date(date_text: str, year: int) -> datetime.date:
    date_text = date_text.replace("\u00a0", " ").strip()
    match = re.search(r"(\d{1,2})\s+([\u0e00-\u0e7f]+)", date_text)
    if not match:
        raise ValueError(f"Cannot parse Thai date: {date_text!r}")
    day = int(match.group(1))
    month_name = match.group(2).strip()
    if month_name not in MONTHS_TH:
        raise ValueError(f"Unknown Thai month: {month_name!r}")
    return datetime.date(year, MONTHS_TH[month_name], day)
