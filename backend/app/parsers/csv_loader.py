import csv
from io import StringIO
from typing import Any


def load_csv_payload(content: bytes) -> list[dict[str, Any]]:
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(StringIO(text))
    return [dict(row) for row in reader]
