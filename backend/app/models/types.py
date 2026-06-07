from typing import Any

from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB

JsonDict = dict[str, Any]
JsonList = list[Any]
JsonValue = JsonDict | JsonList | str | int | float | bool | None

JSONBType = JSONB().with_variant(JSON(), "sqlite")
