import json
from datetime import date, datetime, time
from typing import Any, cast

# Expected number of time parts in HH:MM:SS format
TIME_PARTS_WITH_SECONDS = 3

# Expected number of time parts in HH:MM format
TIME_PARTS_WITHOUT_SECONDS = 2


def date_from_string(value: str) -> date:
    return date.fromisoformat(value)


def datetime_from_string(value: str) -> datetime:
    return datetime.fromisoformat(value)


def time_from_string(value: str) -> time:
    parts = value.split(":")
    if len(parts) == TIME_PARTS_WITH_SECONDS:
        return time(int(parts[0]), int(parts[1]), int(parts[2]))
    if len(parts) == TIME_PARTS_WITHOUT_SECONDS:
        return time(int(parts[0]), int(parts[1]))
    msg = f"Invalid time format: {value}"
    raise ValueError(msg)


def date_passthrough(value: date) -> date:
    return value


def datetime_passthrough(value: datetime) -> datetime:
    return value


def bytearray_from_string(value: str) -> bytearray:
    return bytearray(value, "utf-8")


def none_from_empty_string(value: str) -> None:
    if value == "":
        return
    msg = f"Cannot convert {value!r} to None"
    raise TypeError(msg)


def optional_from_empty_string(value: str) -> str | None:
    if value == "":
        return None
    return value


def bool_from_string(value: str) -> bool:
    lower = value.lower().strip()
    if lower in ("true", "1", "yes", "on"):
        return True
    if lower in ("false", "0", "no", "off", ""):
        return False
    msg = f"Cannot convert {value!r} to bool"
    raise TypeError(msg)


def bytearray_from_json_string(value: str) -> bytearray:
    if value == "":
        return bytearray()

    if value.startswith("["):
        items = json.loads(value)
        if not isinstance(items, list):
            msg = f"Expected list in JSON, got {type(items)}"
            raise TypeError(msg)
        return bytearray(items)

    return bytearray(value.encode("utf-8"))


def list_from_json_string(value: str) -> list[Any]:
    if value == "":
        return []

    return cast("list[Any]", json.loads(value))


def tuple_from_json_string(value: str) -> tuple[Any, ...]:
    if value == "":
        return ()

    parsed = json.loads(value)
    if not isinstance(parsed, list):
        msg = f"Expected list in JSON, got {type(parsed)}"
        raise TypeError(msg)
    result = [tuple(item) if isinstance(item, list) else item for item in parsed]
    return tuple(result)


def set_from_json_string(value: str) -> set[Any]:
    if value == "":
        return set()

    parsed = json.loads(value)
    if not isinstance(parsed, list):
        msg = f"Expected list in JSON, got {type(parsed)}"
        raise TypeError(msg)
    return set(parsed)


def frozenset_from_json_string(value: str) -> frozenset[Any]:
    if value == "":
        return frozenset()

    parsed = json.loads(value)
    if not isinstance(parsed, list):
        msg = f"Expected list in JSON, got {type(parsed)}"
        raise TypeError(msg)
    return frozenset(parsed)
