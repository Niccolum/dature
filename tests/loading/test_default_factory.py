"""Unit tests for dature.loading.default_factory — the unsafe-default_factory schema tree."""

from dataclasses import dataclass, field

import pytest

from dature.loading.default_factory import (
    UnsafeFactoryField,
    iter_unsafe_fields,
    required_params_of,
    unsafe_factory_tree,
)


@dataclass
class _TgProxyConfig:
    url: str
    port: int


@dataclass
class _TgConfig:
    admins: list[int]
    use_proxy: bool
    proxy: _TgProxyConfig = field(default_factory=_TgProxyConfig)


@dataclass
class _DbConfig:
    host: str = "localhost"
    port: int = 5432


@dataclass
class _Config:
    debug: bool = False
    db: _DbConfig = field(default_factory=_DbConfig)
    tg: _TgConfig = field(default_factory=_TgConfig)


@dataclass
class _AllDefaults:
    value: int = 0


@dataclass
class _NoFactory:
    value: int


@dataclass
class _SelfRef:
    name: str = ""
    child: "_SelfRef | None" = None


def _zero_arg_lambda() -> int:
    return 0


class TestRequiredParamsOf:
    @pytest.mark.parametrize(
        ("factory", "expected"),
        [
            pytest.param(list, None, id="list-safe"),
            pytest.param(dict, None, id="dict-builtin-safe"),
            pytest.param(_zero_arg_lambda, None, id="zero-arg-callable-safe"),
            pytest.param(_AllDefaults, None, id="all-defaults-dataclass-safe"),
            pytest.param(_TgConfig, ("admins", "use_proxy"), id="tgconfig-unsafe"),
        ],
    )
    def test_required_params(self, factory, expected):
        result = required_params_of(factory)

        assert result == expected


class TestUnsafeFactoryTree:
    def test_schema_with_no_unsafe_factory_returns_none(self):
        node = unsafe_factory_tree(_AllDefaults)

        assert node is None

    def test_schema_with_no_factory_at_all_returns_none(self):
        node = unsafe_factory_tree(_NoFactory)

        assert node is None

    def test_top_level_unsafe_field_reported(self):
        node = unsafe_factory_tree(_Config)

        assert node is not None
        assert [f.name for f in node.unsafe] == ["tg"]
        assert node.unsafe[0].factory_name == "_TgConfig"
        assert node.unsafe[0].required_params == ("admins", "use_proxy")

    def test_nested_unsafe_field_reachable_via_children(self):
        node = unsafe_factory_tree(_Config)

        assert node is not None
        tg_child = node.children["tg"]
        assert [f.name for f in tg_child.unsafe] == ["proxy"]
        assert tg_child.unsafe[0].required_params == ("url", "port")

    def test_self_referential_schema_terminates(self):
        node = unsafe_factory_tree(_SelfRef)

        assert node is None


class TestIterUnsafeFields:
    def test_none_node_returns_empty_list(self):
        result = iter_unsafe_fields(None)

        assert result == []

    def test_flattens_all_levels_with_full_paths(self):
        node = unsafe_factory_tree(_Config)

        result = iter_unsafe_fields(node)

        assert result == [
            (("tg",), UnsafeFactoryField(name="tg", factory_name="_TgConfig", required_params=("admins", "use_proxy"))),
            (
                ("tg", "proxy"),
                UnsafeFactoryField(name="proxy", factory_name="_TgProxyConfig", required_params=("url", "port")),
            ),
        ]
