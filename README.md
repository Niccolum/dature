# dature

Type-safe configuration loader for Python dataclasses. Load config from YAML, JSON, TOML, INI, ENV files and environment variables with automatic type conversion, validation, and human-readable error messages.

## Installation

```bash
pip install dature
```

Optional format support:

```bash
pip install dature[yaml]   # YAML support (ruamel.yaml)
pip install dature[json5]  # JSON5 support
```

## Quick Start

```python
from dataclasses import dataclass
from dature import LoadMetadata, load

@dataclass
class Config:
    host: str
    port: int
    debug: bool = False

# From a file
config = load(LoadMetadata(file_="config.yaml"), Config)

# From environment variables
config = load(LoadMetadata(prefix="APP_"), Config)

# As a decorator (auto-loads on instantiation)
@load(LoadMetadata(file_="config.yaml"))
@dataclass
class Config:
    host: str
    port: int
    debug: bool = False

config = Config()           # loads from config.yaml
config = Config(port=9090)  # override specific fields
```

## Supported Formats

| Format | Extension | Loader | Extra dependency |
|--------|-----------|--------|------------------|
| YAML 1.1 | `.yaml`, `.yml` | `yaml` | `ruamel.yaml` |
| YAML 1.2 | `.yaml`, `.yml` | `yaml1.2` | `ruamel.yaml` |
| JSON | `.json` | `json` | - |
| JSON5 | `.json5` | `json5` | `json5` |
| TOML | `.toml` | `toml` | - |
| INI | `.ini`, `.cfg` | `ini` | - |
| ENV file | `.env` | `envfile` | - |
| Environment variables | - | `env` | - |

The format is auto-detected from the file extension. When `file_` is not specified, environment variables are used. You can also set the loader explicitly:

```python
LoadMetadata(file_="config.txt", loader="json")
```

## LoadMetadata

```python
@dataclass(frozen=True, slots=True, kw_only=True)
class LoadMetadata:
    file_: str | None = None
    loader: LoaderType | None = None
    prefix: str | None = None
    split_symbols: str = "__"
    name_style: NameStyle | None = None
    field_mapping: dict[str, str] | None = None
    root_validators: tuple[ValidatorProtocol, ...] | None = None
    enable_expand_env_vars: bool = True
```

### prefix

Filters keys for ENV, or extracts a nested object from files:

```python
# ENV: APP_HOST=localhost, APP_PORT=8080
config = load(LoadMetadata(prefix="APP_"), Config)
```

```python
# config.yaml: { app: { database: { host: localhost, port: 5432 } } }
db = load(LoadMetadata(file_="config.yaml", prefix="app.database"), Database)
```

### split_symbols

Delimiter for building nested structures from flat ENV variables. Default: `"__"`.

```bash
APP_DB__HOST=localhost
APP_DB__PORT=5432
```

```python
@dataclass
class Database:
    host: str
    port: int

@dataclass
class Config:
    db: Database

config = load(LoadMetadata(prefix="APP_", split_symbols="__"), Config)
```

### name_style

Maps dataclass field names to config keys using a naming convention:

| Value | Example |
|-------|---------|
| `lower_snake` | `my_field` |
| `upper_snake` | `MY_FIELD` |
| `lower_camel` | `myField` |
| `upper_camel` | `MyField` |
| `lower_kebab` | `my-field` |
| `upper_kebab` | `MY-FIELD` |

```python
# config.json: { "databaseHost": "localhost", "databasePort": 5432 }
config = load(
    LoadMetadata(file_="config.json", name_style="lower_camel"),
    Config,
)
```

### field_mapping

Explicit field renaming. Takes priority over `name_style`:

```python
config = load(
    LoadMetadata(
        file_="config.json",
        field_mapping={"database_url": "db_url", "api_key": "apiKey"},
    ),
    Config,
)
```

## Decorator Mode vs Function Mode

**Function mode** -- load once and get a result:

```python
config = load(LoadMetadata(file_="config.yaml"), Config)
```

**Decorator mode** -- auto-loads on every instantiation with caching:

```python
@load(LoadMetadata(file_="config.yaml"))
@dataclass
class Config:
    host: str
    port: int

config = Config()           # loaded from config.yaml
config = Config(port=9090)  # host from config, port overridden
```

Explicit arguments to `__init__` take priority over loaded values.

Caching is enabled by default. Disable it with `cache=False`:

```python
@load(LoadMetadata(file_="config.yaml"), cache=False)
@dataclass
class Config:
    host: str
    port: int
```

## Merging Multiple Sources

Load configuration from several sources and merge them into one dataclass:

```python
from dature import LoadMetadata, MergeMetadata, MergeStrategy, load

config = load(
    MergeMetadata(
        sources=(
            LoadMetadata(file_="defaults.yaml"),
            LoadMetadata(file_=".env", prefix="APP_"),
            LoadMetadata(prefix="APP_"),  # env vars, highest priority
        ),
        strategy=MergeStrategy.LAST_WINS,
    ),
    Config,
)
```

Shorthand with a tuple (uses `LAST_WINS` by default):

```python
config = load(
    (
        LoadMetadata(file_="defaults.yaml"),
        LoadMetadata(prefix="APP_"),
    ),
    Config,
)
```

Works as a decorator too:

```python
@load(MergeMetadata(
    sources=(
        LoadMetadata(file_="defaults.yaml"),
        LoadMetadata(prefix="APP_"),
    ),
    strategy=MergeStrategy.FIRST_WINS,
))
@dataclass
class Config:
    host: str
    port: int
```

### Merge Strategies

| Strategy | Behavior |
|----------|----------|
| `LAST_WINS` | Last source overrides (default) |
| `FIRST_WINS` | First source wins |
| `RAISE_ON_CONFLICT` | Raises `MergeConflictError` if the same key appears in multiple sources with different values |

Nested dicts are merged recursively. Lists and scalars are replaced entirely according to the strategy.

### Per-Field Merge Strategies

Override the global strategy for individual fields using `field_merges`:

```python
from dature import F, FieldMergeStrategy, LoadMetadata, MergeMetadata, MergeRule, MergeStrategy, load

@dataclass
class Config:
    host: str
    port: int
    tags: list[str]

config = load(
    MergeMetadata(
        sources=(
            LoadMetadata(file_="defaults.yaml"),
            LoadMetadata(file_="overrides.yaml"),
        ),
        strategy=MergeStrategy.LAST_WINS,
        field_merges=(
            MergeRule(F[Config].host, FieldMergeStrategy.FIRST_WINS),
            MergeRule(F[Config].tags, FieldMergeStrategy.APPEND),
        ),
    ),
    Config,
)
```

`F[Config].host` builds a field path with eager validation -- the dataclass and field name are checked immediately. For decorator mode where the class is not yet defined, use a string: `F["Config"].host` (validation is skipped).

| Strategy | Behavior |
|----------|----------|
| `FIRST_WINS` | Keep the value from the first source |
| `LAST_WINS` | Keep the value from the last source |
| `APPEND` | Concatenate lists: `base + override` |
| `APPEND_UNIQUE` | Concatenate lists, removing duplicates |
| `PREPEND` | Concatenate lists: `override + base` |
| `PREPEND_UNIQUE` | Concatenate lists in reverse order, removing duplicates |
| `MAX` | Keep the larger value (int, float, str) |
| `MIN` | Keep the smaller value (int, float, str) |

Nested fields are supported: `F[Config].database.host`.

Per-field strategies also work with `RAISE_ON_CONFLICT` -- fields with an explicit strategy are excluded from conflict detection:

```python
config = load(
    MergeMetadata(
        sources=(
            LoadMetadata(file_="a.yaml"),
            LoadMetadata(file_="b.yaml"),
        ),
        strategy=MergeStrategy.RAISE_ON_CONFLICT,
        field_merges=(
            MergeRule(F[Config].host, FieldMergeStrategy.LAST_WINS),
        ),
    ),
    Config,
)
# "host" can differ between sources without raising an error,
# all other fields still raise MergeConflictError on conflict.
```

## Load Report

Pass `debug=True` to `load()` to collect a `LoadReport` with detailed information about which source provided each field value. This works for both single-source and multi-source (merge) loads.

### Programmatic access

```python
from dature import load, get_load_report, LoadMetadata, MergeMetadata

config = load(
    MergeMetadata(
        sources=(
            LoadMetadata(file_="defaults.yaml"),
            LoadMetadata(file_="overrides.json"),
        ),
    ),
    Config,
    debug=True,
)

report = get_load_report(config)

# Which sources were loaded
for source in report.sources:
    print(f"Source {source.index}: {source.loader_type} from {source.file_path}")
    print(f"  Raw data: {source.raw_data}")

# Which source won for each field
for origin in report.field_origins:
    print(f"{origin.key} = {origin.value!r}  <-- source {origin.source_index} ({origin.source_file})")

# The final merged dict before dataclass conversion
print(report.merged_data)
```

Without `debug=True`, `get_load_report` returns `None` and emits a warning.

### Debug logging

All loading steps are logged at `DEBUG` level under the `"dature"` logger regardless of the `debug` flag:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

config = load(LoadMetadata(file_="config.json"), Config)
```

Example output for a two-source merge:

```
[Config] Source 0 loaded: loader=json, file=defaults.json, keys=['host', 'port']
[Config] Source 0 raw data: {'host': 'localhost', 'port': 3000}
[Config] Source 1 loaded: loader=json, file=overrides.json, keys=['port']
[Config] Source 1 raw data: {'port': 8080}
[Config] Merge step 0 (strategy=last_wins): added=['host', 'port'], overwritten=[]
[Config] State after step 0: {'host': 'localhost', 'port': 3000}
[Config] Merge step 1 (strategy=last_wins): added=[], overwritten=['port']
[Config] State after step 1: {'host': 'localhost', 'port': 8080}
[Config] Merged result (strategy=last_wins, 2 sources): {'host': 'localhost', 'port': 8080}
[Config] Field 'host' = 'localhost'  <-- source 0 (defaults.json)
[Config] Field 'port' = 8080  <-- source 1 (overrides.json)
```

### Report on error

If loading fails with `DatureConfigError` and `debug=True` was passed, the report is attached to the dataclass type so you can inspect what was loaded before the failure:

```python
from dature.errors import DatureConfigError

try:
    config = load(MergeMetadata(sources=(...,)), Config, debug=True)
except DatureConfigError:
    report = get_load_report(Config)
    # report.sources contains raw data from each source
    # report.merged_data contains the merged dict that failed to convert
```

## Validators

Validators are declared using `typing.Annotated`:

```python
from dataclasses import dataclass
from typing import Annotated

from dature.validators.number import Ge, Le
from dature.validators.string import MinLength, MaxLength, RegexPattern
from dature.validators.sequence import MinItems, MaxItems, UniqueItems

@dataclass
class Config:
    port: Annotated[int, Ge(value=1), Le(value=65535)]
    password: Annotated[str, MinLength(value=8), MaxLength(value=128)]
    email: Annotated[str, RegexPattern(pattern=r"^[\w\.-]+@[\w\.-]+\.\w+$")]
    tags: Annotated[list[str], MinItems(value=1), MaxItems(value=10), UniqueItems()]
```

### Available Validators

**Numbers:** `Gt`, `Ge`, `Lt`, `Le`

**Strings:** `MinLength`, `MaxLength`, `RegexPattern`

**Sequences:** `MinItems`, `MaxItems`, `UniqueItems`

### Root Validators

Validate the entire object after loading:

```python
from dature.validators.root import RootValidator

def check_privileged_port(obj: Config) -> bool:
    if obj.port < 1024:
        return obj.user == "root"
    return True

config = load(
    LoadMetadata(
        file_="config.yaml",
        root_validators=(
            RootValidator(
                func=check_privileged_port,
                error_message="Ports below 1024 require root user",
            ),
        ),
    ),
    Config,
)
```

## Special Types

```python
from dature.fields import SecretStr, PaymentCardNumber, ByteSize
from dature.types import URL, Base64UrlBytes, Base64UrlStr
```

### SecretStr

Masks the value in `str()` and `repr()`:

```python
@dataclass
class Config:
    api_key: SecretStr

config = load(meta, Config)
print(config.api_key)                       # **********
print(config.api_key.get_secret_value())    # actual_secret
```

### ByteSize

Parses human-readable sizes:

```python
@dataclass
class Config:
    max_upload: ByteSize

# config.yaml: { max_upload: "1.5 GB" }
config = load(meta, Config)
print(int(config.max_upload))                          # 1500000000
print(config.max_upload.human_readable(decimal=True))  # 1.5GB
```

Supported units: B, KB, MB, GB, TB, PB, KiB, MiB, GiB, TiB, PiB.

### PaymentCardNumber

Validates using the Luhn algorithm and detects the brand:

```python
@dataclass
class Config:
    card: PaymentCardNumber

config = load(meta, Config)
print(config.card.brand)   # Visa
print(config.card.masked)  # ************1111
```

### URL

Parsed into `urllib.parse.ParseResult`:

```python
@dataclass
class Config:
    api_url: URL

config = load(meta, Config)
print(config.api_url.scheme)  # https
print(config.api_url.netloc)  # api.example.com
```

### Base64UrlBytes / Base64UrlStr

Decoded from Base64 string in the config:

```python
@dataclass
class Config:
    token: Base64UrlStr      # decoded to str
    data: Base64UrlBytes     # decoded to bytes
```

## ENV Variable Substitution

All file formats support `$VAR` and `${VAR}` substitution. Environment variables in string values are automatically expanded using `os.path.expandvars`:

```yaml
# config.yaml
api_url: $BASE_URL/api/v1
secret: ${SECRET_KEY}
```

If your config contains literal `$` characters that should not be treated as variable references, disable substitution with `enable_expand_env_vars=False`:

```python
config = load(LoadMetadata(file_="config.yaml", enable_expand_env_vars=False), Config)
```

## Error Messages

dature provides human-readable error messages with source location:

```
Config loading errors (2)

  [database.host]  Missing required field
   └── FILE 'config.json', line 3
       "database": {

  [port]  Expected int, got str
   └── ENV 'APP_PORT'
```

Merge conflicts:

```
Config merge conflicts (1)

  [host]  Conflicting values in multiple sources
   └── FILE 'defaults.yaml', line 2
       host: localhost
   └── FILE 'overrides.yaml', line 2
       host: production
```

## Type Coercion

String values from ENV and file formats are automatically converted:

| Source | Target | Example |
|--------|--------|---------|
| `"42"` | `int` | `42` |
| `"3.14"` | `float` | `3.14` |
| `"true"` | `bool` | `True` |
| `"2024-01-15"` | `date` | `date(2024, 1, 15)` |
| `"2024-01-15T10:30:00"` | `datetime` | `datetime(...)` |
| `"10:30:00"` | `time` | `time(10, 30)` |
| `"1 day, 2:30:00"` | `timedelta` | `timedelta(...)` |
| `"1+2j"` | `complex` | `(1+2j)` |
| `"192.168.1.1"` | `IPv4Address` | `IPv4Address(...)` |
| `"[1, 2, 3]"` | `list[int]` | `[1, 2, 3]` |

Nested dataclasses, `Optional`, and `Union` types are also supported.

## Requirements

- Python >= 3.12
- [adaptix](https://github.com/reagento/adaptix) >= 3.0.0b11

## License

Apache License 2.0
