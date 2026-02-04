from dataclasses import dataclass
from pathlib import Path

from dature import load
from dature.sources_loader.json_ import JsonLoader


class TestNameStyleMapping:
    def test_lower_snake_to_lower_camel(self, tmp_path: Path):
        @dataclass
        class Config:
            user_name: str
            user_age: int
            is_active: bool

        json_file = tmp_path / "config.json"
        json_file.write_text('{"userName": "John", "userAge": 25, "isActive": true}')

        loader = JsonLoader(name_style="lower_camel")
        result = loader.load(json_file, Config)

        assert result.user_name == "John"
        assert result.user_age == 25
        assert result.is_active is True

    def test_lower_camel_to_lower_snake(self, tmp_path: Path):
        @dataclass
        class Config:
            user_name: str
            user_age: int

        json_file = tmp_path / "config.json"
        json_file.write_text('{"user_name": "Alice", "user_age": 30}')

        loader = JsonLoader(name_style="lower_snake")
        result = loader.load(json_file, Config)

        assert result.user_name == "Alice"
        assert result.user_age == 30

    def test_upper_camel_pascal_case(self, tmp_path: Path):
        @dataclass
        class Config:
            user_name: str
            total_count: int

        json_file = tmp_path / "config.json"
        json_file.write_text('{"UserName": "Bob", "TotalCount": 100}')

        loader = JsonLoader(name_style="upper_camel")
        result = loader.load(json_file, Config)

        assert result.user_name == "Bob"
        assert result.total_count == 100

    def test_lower_kebab_case(self, tmp_path: Path):
        @dataclass
        class Config:
            user_name: str
            api_key: str

        json_file = tmp_path / "config.json"
        json_file.write_text('{"user-name": "Charlie", "api-key": "secret123"}')

        loader = JsonLoader(name_style="lower_kebab")
        result = loader.load(json_file, Config)

        assert result.user_name == "Charlie"
        assert result.api_key == "secret123"

    def test_upper_kebab_case(self, tmp_path: Path):
        @dataclass
        class Config:
            user_name: str
            api_key: str

        json_file = tmp_path / "config.json"
        json_file.write_text('{"USER-NAME": "Dave", "API-KEY": "secret456"}')

        loader = JsonLoader(name_style="upper_kebab")
        result = loader.load(json_file, Config)

        assert result.user_name == "Dave"
        assert result.api_key == "secret456"

    def test_upper_snake_case(self, tmp_path: Path):
        @dataclass
        class Config:
            user_name: str
            max_retries: int

        json_file = tmp_path / "config.json"
        json_file.write_text('{"USER_NAME": "Eve", "MAX_RETRIES": 3}')

        loader = JsonLoader(name_style="upper_snake")
        result = loader.load(json_file, Config)

        assert result.user_name == "Eve"
        assert result.max_retries == 3


class TestFieldMapping:
    def test_simple_field_mapping(self, tmp_path: Path):
        @dataclass
        class Config:
            name: str
            age: int
            active: bool

        json_file = tmp_path / "config.json"
        json_file.write_text('{"fullName": "John Doe", "userAge": 42, "isActive": true}')

        field_mapping = {
            "name": "fullName",
            "age": "userAge",
            "active": "isActive",
        }

        loader = JsonLoader(field_mapping=field_mapping)
        result = loader.load(json_file, Config)

        assert result.name == "John Doe"
        assert result.age == 42
        assert result.active is True

    def test_partial_field_mapping(self, tmp_path: Path):
        @dataclass
        class Config:
            name: str
            age: int
            city: str

        json_file = tmp_path / "config.json"
        json_file.write_text('{"userName": "Alice", "age": 28, "city": "NYC"}')

        field_mapping = {"name": "userName"}

        loader = JsonLoader(field_mapping=field_mapping)
        result = loader.load(json_file, Config)

        assert result.name == "Alice"
        assert result.age == 28
        assert result.city == "NYC"

    def test_combined_name_style_and_field_mapping(self, tmp_path: Path):
        @dataclass
        class Config:
            user_name: str
            user_age: int
            special_field: str

        json_file = tmp_path / "config.json"
        json_file.write_text('{"userName": "Bob", "userAge": 35, "customKey": "special"}')

        field_mapping = {"special_field": "customKey"}

        loader = JsonLoader(name_style="lower_camel", field_mapping=field_mapping)
        result = loader.load(json_file, Config)

        assert result.user_name == "Bob"
        assert result.user_age == 35
        assert result.special_field == "special"

    def test_nested_dataclass_with_field_mapping(self, tmp_path: Path):
        @dataclass
        class Address:
            city: str
            street: str

        @dataclass
        class User:
            name: str
            address: Address

        json_file = tmp_path / "config.json"
        json_file.write_text(
            '{"fullName": "Charlie", "location": {"cityName": "LA", "streetName": "Main St"}}',
        )

        field_mapping = {
            "name": "fullName",
            "address": "location",
            "city": "cityName",
            "street": "streetName",
        }

        loader = JsonLoader(field_mapping=field_mapping)
        result = loader.load(json_file, User)

        assert result.name == "Charlie"
        assert result.address.city == "LA"
        assert result.address.street == "Main St"


class TestLoadFunctionWithNameMapping:
    def test_load_function_with_name_style(self, tmp_path: Path):
        @dataclass
        class Config:
            user_name: str
            api_key: str

        json_file = tmp_path / "config.json"
        json_file.write_text('{"userName": "TestUser", "apiKey": "key123"}')

        result = load(str(json_file), name_style="lower_camel", dataclass_=Config)

        assert result.user_name == "TestUser"
        assert result.api_key == "key123"

    def test_load_function_with_field_mapping(self, tmp_path: Path):
        @dataclass
        class Config:
            name: str
            age: int

        json_file = tmp_path / "config.json"
        json_file.write_text('{"fullName": "Jane", "userAge": 40}')

        field_mapping = {"name": "fullName", "age": "userAge"}

        result = load(str(json_file), field_mapping=field_mapping, dataclass_=Config)

        assert result.name == "Jane"
        assert result.age == 40

    def test_load_decorator_with_name_style(self, tmp_path: Path):
        json_file = tmp_path / "config.json"
        json_file.write_text('{"userName": "DecoratorTest", "isActive": true}')

        @load(str(json_file), name_style="lower_camel")
        @dataclass
        class Config:
            user_name: str
            is_active: bool

        config = Config()

        assert config.user_name == "DecoratorTest"
        assert config.is_active is True

    def test_load_decorator_with_both_name_style_and_field_mapping(self, tmp_path: Path):
        json_file = tmp_path / "config.json"
        json_file.write_text('{"userName": "Combined", "customAge": 50, "extraField": "data"}')

        field_mapping = {"extra": "extraField"}

        @load(str(json_file), name_style="lower_camel", field_mapping=field_mapping)
        @dataclass
        class Config:
            user_name: str
            custom_age: int
            extra: str

        config = Config()

        assert config.user_name == "Combined"
        assert config.custom_age == 50
        assert config.extra == "data"
