from typing import Annotated, Literal

type JSONValue = dict[str, JSONValue] | list[JSONValue] | str | int | float | bool | None

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
