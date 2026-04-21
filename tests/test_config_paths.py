"""Tests for config_paths utilities."""

import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from dature.config_paths import (
    _get_appdata_path,
    _get_macos_app_support,
    _get_xdg_config_dirs,
    _get_xdg_config_home,
    find_config,
    get_system_config_dirs,
    iter_config_paths,
)


class TestGetAppdataPath:
    """Tests for Windows %APPDATA% path detection."""

    def test_returns_none_on_non_windows(self) -> None:
        """Should return None on non-Windows platforms."""
        with patch.object(sys, "platform", "linux"):
            assert _get_appdata_path() is None

    def test_returns_appdata_on_windows(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Should return APPDATA path on Windows."""
        with patch.object(sys, "platform", "win32"):
            monkeypatch.setenv("APPDATA", "C:\\Users\\Test\\AppData\\Roaming")
            assert _get_appdata_path() == Path("C:\\Users\\Test\\AppData\\Roaming")

    def test_returns_none_when_appdata_not_set(self) -> None:
        """Should return None when APPDATA is not set."""
        with patch.object(sys, "platform", "win32"):
            with patch.dict(os.environ, {}, clear=False):
                os.environ.pop("APPDATA", None)
                assert _get_appdata_path() is None


class TestGetXdgConfigHome:
    """Tests for XDG config home detection."""

    def test_uses_xdg_config_home_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Should use XDG_CONFIG_HOME when set."""
        monkeypatch.setenv("XDG_CONFIG_HOME", "/custom/config")
        assert _get_xdg_config_home() == Path("/custom/config")

    def test_uses_default_xdg_when_not_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Should use ~/.config when XDG_CONFIG_HOME is not set."""
        monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
        monkeypatch.setattr(Path, "home", lambda: Path("/home/user"))
        assert _get_xdg_config_home() == Path("/home/user/.config")


class TestGetXdgConfigDirs:
    """Tests for XDG config directories detection."""

    def test_uses_xdg_config_dirs_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Should use XDG_CONFIG_DIRS when set."""
        monkeypatch.setenv("XDG_CONFIG_DIRS", "/etc/xdg:/usr/local/etc/xdg")
        assert _get_xdg_config_dirs() == [Path("/etc/xdg"), Path("/usr/local/etc/xdg")]

    def test_uses_default_when_not_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Should use /etc/xdg when XDG_CONFIG_DIRS is not set."""
        monkeypatch.delenv("XDG_CONFIG_DIRS", raising=False)
        assert _get_xdg_config_dirs() == [Path("/etc/xdg")]


class TestGetMacosAppSupport:
    """Tests for macOS Application Support path detection."""

    def test_returns_correct_path(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Should return ~/Library/Application Support."""
        monkeypatch.setattr(Path, "home", lambda: Path("/Users/test"))
        assert _get_macos_app_support() == Path("/Users/test/Library/Application Support")


class TestGetSystemConfigDirs:
    """Tests for get_system_config_dirs function."""

    @pytest.mark.parametrize(
        ("platform", "home", "expected_first", "expected_last"),
        [
            ("linux", "/home/user", "/home/user/.config", "/etc/xdg"),
            ("darwin", "/Users/user", "/Users/user/Library/Application Support", "/etc/xdg"),
        ],
    )
    def test_unix_dirs(
        self,
        platform: str,
        home: str,
        expected_first: str,
        expected_last: str,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Should return correct dirs for Linux/macOS."""
        monkeypatch.setattr(sys, "platform", platform)
        monkeypatch.setattr(Path, "home", lambda: Path(home))
        monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
        monkeypatch.delenv("XDG_CONFIG_DIRS", raising=False)

        dirs = get_system_config_dirs()

        assert dirs[0] == Path(expected_first)
        assert dirs[-1] == Path(expected_last)

    def test_windows_dirs(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Should return correct dirs for Windows."""
        monkeypatch.setattr(sys, "platform", "win32")
        monkeypatch.setenv("APPDATA", "C:\\Users\\Test\\AppData\\Roaming")

        dirs = get_system_config_dirs()

        assert dirs == [Path("C:\\Users\\Test\\AppData\\Roaming")]


class TestIterConfigPaths:
    """Tests for iter_config_paths function."""

    @pytest.mark.parametrize(
        ("platform", "home", "filename", "expected"),
        [
            (
                "linux",
                "/home/user",
                "config.yaml",
                [
                    "/home/user/.config/config.yaml",
                    "/etc/config.yaml",
                    "/etc/xdg/config.yaml",
                ],
            ),
            (
                "darwin",
                "/Users/user",
                "config.yaml",
                [
                    "/Users/user/Library/Application Support/config.yaml",
                    "/Users/user/.config/config.yaml",
                    "/etc/config.yaml",
                    "/etc/xdg/config.yaml",
                ],
            ),
            (
                "linux",
                "/home/user",
                "settings.json",
                [
                    "/home/user/.config/settings.json",
                    "/etc/settings.json",
                    "/etc/xdg/settings.json",
                ],
            ),
        ],
    )
    def test_paths_by_platform(
        self,
        platform: str,
        home: str,
        filename: str,
        expected: list[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Should return correct paths for each platform."""
        monkeypatch.setattr(sys, "platform", platform)
        monkeypatch.setattr(Path, "home", lambda: Path(home))
        monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
        monkeypatch.delenv("XDG_CONFIG_DIRS", raising=False)

        paths = list(iter_config_paths(filename))

        assert paths == [Path(p) for p in expected]

    def test_custom_dirs(self, tmp_path: Path) -> None:
        """Should use custom directories when provided."""
        first_dir = tmp_path / "first"
        first_dir.mkdir()
        second_dir = tmp_path / "second"
        second_dir.mkdir()

        paths = list(iter_config_paths("config.yaml", (first_dir, second_dir)))

        assert paths == [first_dir / "config.yaml", second_dir / "config.yaml"]


class TestFindConfig:
    """Tests for find_config function."""

    def test_returns_first_existing(self, tmp_path: Path) -> None:
        """Should return first existing config file."""
        # Create two directories with config files
        first_dir = tmp_path / "first"
        first_dir.mkdir()
        first_config = first_dir / "config.yaml"
        first_config.write_text("test: first")

        second_dir = tmp_path / "second"
        second_dir.mkdir()
        second_config = second_dir / "config.yaml"
        second_config.write_text("test: second")

        # Pass custom directories directly to find_config
        assert find_config("config.yaml", (first_dir, second_dir)) == first_config

    def test_returns_none_when_not_found(self, tmp_path: Path) -> None:
        """Should return None when no config file exists."""
        assert find_config("nonexistent.yaml", (tmp_path / "nonexistent",)) is None
