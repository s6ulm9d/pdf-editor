"""Data Cleaning and Normalization Utilities.

Formats cell values from Excel (.xlsx) and CSV files, removing unwanted
timestamps like '00:00:00' from dates and ensuring pristine output strings for PDFs.
"""

import re
import datetime
from typing import Any, Dict


def clean_cell_value(val: Any) -> str:
    """Formats cell values cleanly, converting datetimes to clean date-only strings without timestamps.
    
    Examples:
        datetime.datetime(2026, 7, 17, 0, 0, 0) -> "2026-07-17"
        "2026-07-17 00:00:00" -> "2026-07-17"
        "17-07-2026 00:00:00" -> "17-07-2026"
        "17/07/2026 00:00:00" -> "17/07/2026"
        "2026-07-17T00:00:00.000Z" -> "2026-07-17"
        12345.0 -> "12345"
    """
    if val is None:
        return ""

    # Handle Python datetime/date objects (from openpyxl or pandas)
    if isinstance(val, (datetime.datetime, datetime.date)):
        return val.strftime("%Y-%m-%d")

    s = str(val).strip()

    # Match standard dates followed by time (e.g., 2026-07-17 00:00:00 or 17-07-2026 00:00:00)
    date_pattern = r'^(\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{4})(?:[T\s]\d{1,2}:\d{2}(?::\d{2})?(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?)?$'
    m = re.match(date_pattern, s)
    if m:
        return m.group(1)

    # Clean embedded date+timestamp substrings
    s = re.sub(r'(\d{4}-\d{2}-\d{2})\s+\d{1,2}:\d{2}(?::\d{2})?', r'\1', s)
    s = re.sub(r'(\d{2}[-/]\d{2}[-/]\d{4})\s+\d{1,2}:\d{2}(?::\d{2})?', r'\1', s)
    s = re.sub(r'[\sT]00:00(:00)?(\.0+)?$', '', s)

    # Strip float decimals for integer-like values (e.g., 100.0 -> 100)
    if re.match(r'^-?\d+\.0$', s):
        s = s[:-2]

    return s


def clean_row_dict(row: Dict[str, Any]) -> Dict[str, str]:
    """Cleans all keys and values in a row dictionary."""
    return {clean_cell_value(k): clean_cell_value(v) for k, v in row.items() if k is not None}
