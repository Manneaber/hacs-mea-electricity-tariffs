"""Pure HTML/text parsing helpers for MEA tariff and holiday data."""

from __future__ import annotations

import datetime
import html
import re

from .const import (
    MONTHS_TH,
    PRICE_SENSOR_DEFINITIONS,
    TARIFF_ROW_MATCHERS,
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

    for row_html in re.findall(r"<tr[^>]*>(.*?)</tr>", html_text, re.S | re.I):
        cells = [
            clean_html_cell(cell)
            for cell in re.findall(r"<td[^>]*>(.*?)</td>", row_html, re.S | re.I)
        ]
        if len(cells) < 2:
            continue

        label = cells[0]

        # Single-value base tariff rows — first matching entry wins.
        for key, required in TARIFF_ROW_MATCHERS:
            if key not in prices and all(s in label for s in required):
                try:
                    prices[key] = parse_price(cells[-1])
                except ValueError:
                    pass
                break

        # Multi-column TOU rows.
        for prefix, on_key, off_key in TARIFF_TOU_MATCHERS:
            if label.startswith(prefix) and len(cells) >= 3:
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


def parse_ft_page(html_text: str) -> float:
    """Extract the current FT price from the PEA FT HTML page."""
    for pattern in (
        r"Ft\s*\([^)]*\).*?<span[^>]*>\s*([0-9]+\.[0-9]+)\s*</span>\s*THB/Unit",
        r"Ft\s*\([^)]*\).*?([0-9]+\.[0-9]+)\s*THB/Unit",
        r"([0-9]+\.[0-9]+)\s*THB/Unit",
    ):
        match = re.search(pattern, html_text, re.S | re.I)
        if match:
            return float(match.group(1))
    raise ValueError("Unable to parse FT price")


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
