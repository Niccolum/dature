# Supported Types

## Type Coercion

String values from ENV and file formats are automatically converted.

All supported types in one dataclass:

```python
--8<-- "examples/all_types_dataclass.py"
```

### Coercion by Source

Different formats store values differently. YAML, JSON and TOML parse some types natively, while ENV and INI treat everything as strings:

=== "YAML"

    ```yaml
    --8<-- "examples/sources/all_types_yaml12.yaml"
    ```

=== "JSON"

    ```json
    --8<-- "examples/sources/all_types.json"
    ```

=== "TOML"

    ```toml
    --8<-- "examples/sources/all_types_toml11.toml"
    ```

=== "INI"

    ```ini
    --8<-- "examples/sources/all_types.ini"
    ```

=== "ENV"

    ```bash
    --8<-- "examples/sources/all_types.env"
    ```

### `timedelta` Formats

`timedelta` values are parsed from strings. Supported formats:

| Format | Example |
|---|---|
| `hh:mm` | `2:30` |
| `hh:mm:ss` | `2:30:00` |
| `hh:mm:ss.microseconds` | `2:03:04.500000` |
| `N day[s][,] hh:mm[:ss[.microseconds]]` | `1 day, 2:30:00` |
| `N week[s][,] [N day[s][,]] [hh:mm[:ss[.microseconds]]]` | `2 weeks, 3 days 1:02:03` |
| `N day[s]` | `3 days` |
| `N week[s]` | `2 weeks` |

All time components and days/weeks support negative values: `-2:30`, `-1 day, 23:59:59`, `-2 weeks`.

For custom types and file format loaders, see [Custom Types & Loaders](advanced/custom_types.md).
