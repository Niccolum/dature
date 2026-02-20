import types
from typing import Annotated, Literal, Self
from urllib.parse import ParseResult

type JSONValue = dict[str, JSONValue] | list[JSONValue] | str | int | float | bool | None


class NotLoaded:
    _instance: "NotLoaded | None" = None

    def __new__(cls) -> Self:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance  # type: ignore[return-value]

    def __repr__(self) -> str:
        return "NOT_LOADED"

    def __bool__(self) -> bool:
        return False

    def __hash__(self) -> int:
        return hash("NOT_LOADED")


NOT_LOADED = NotLoaded()

type ProbeValue = dict[str, ProbeValue] | list[ProbeValue] | str | int | float | bool | NotLoaded | None

type ProbeDict = dict[str, ProbeValue]

# Result of get_type_hints() / get_args(): concrete class or parameterized generic
type TypeAnnotation = type[object] | types.GenericAlias

# Examples: "app", "app.database", "app.database.host"
type DotSeparatedPath = Annotated[str, "Dot-separated path for nested dictionary navigation"]

type NameStyle = Literal[
    "lower_snake",
    "upper_snake",
    "lower_camel",
    "upper_camel",
    "lower_kebab",
    "upper_kebab",
]

type FieldMapping = dict[str, str]

type URL = ParseResult

type Base64UrlBytes = bytes
type Base64UrlStr = str

type ExpandEnvVarsMode = Literal["disabled", "default", "empty", "strict"]
