import types
from typing import Annotated, Literal
from urllib.parse import ParseResult

type JSONValue = dict[str, JSONValue] | list[JSONValue] | str | int | float | bool | None

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
