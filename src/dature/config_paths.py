import os
import sys
from collections.abc import Iterator
from pathlib import Path


def _get_appdata_path() -> Path | None:
    """Get Windows %APPDATA% path."""
    if sys.platform != "win32":
        return None
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata)
    return None


def _get_xdg_config_home() -> Path:
    """Get XDG config home (~/.config or $XDG_CONFIG_HOME)."""
    xdg_config = os.environ.get("XDG_CONFIG_HOME")
    if xdg_config:
        return Path(xdg_config)
    return Path.home() / ".config"


def _get_xdg_config_dirs() -> list[Path]:
    """Get XDG config dirs ($XDG_CONFIG_DIRS or /etc/xdg)."""
    xdg_dirs = os.environ.get("XDG_CONFIG_DIRS")
    if xdg_dirs:
        return [Path(d) for d in xdg_dirs.split(os.pathsep)]
    return [Path("/etc/xdg")]


def _get_macos_app_support() -> Path:
    """Get macOS ~/Library/Application Support path."""
    return Path.home() / "Library" / "Application Support"


def get_system_config_dirs() -> list[Path]:
    """Get list of system config directories for current platform.

    Returns:
        List of directories in priority order (user-specific first, then system-wide).
    """
    result: list[Path] = []

    # User-specific directories
    if sys.platform == "win32":
        appdata = _get_appdata_path()
        if appdata:
            result.append(appdata)
    elif sys.platform == "darwin":
        result.append(_get_macos_app_support())
        result.append(_get_xdg_config_home())
    else:
        # Linux and others
        result.append(_get_xdg_config_home())

    # System-wide directories (non-Windows)
    if sys.platform != "win32":
        result.append(Path("/etc"))
        result.extend(_get_xdg_config_dirs())

    return result


def iter_config_paths(
    filename: str,
    system_config_dirs: tuple[Path, ...] | None = None,
) -> Iterator[Path]:
    dirs = system_config_dirs if system_config_dirs is not None else get_system_config_dirs()
    for d in dirs:
        yield d / filename


def find_config(
    filename: str,
    system_config_dirs: tuple[Path, ...] | None = None,
) -> Path | None:
    """Find first existing config file in standard locations.

    Args:
        filename: Config filename to search for.
        system_config_dirs: Optional custom directories. If None, auto-detects based on platform.

    Returns:
        Path to first existing config file, or None if not found.

    Example:
        >>> from dature.config_paths import find_config
        >>> config_path = find_config("myapp.yaml")
        >>> if config_path:
        ...     print(f"Found: {config_path}")
    """
    for path in iter_config_paths(filename, system_config_dirs):
        if path.exists():
            return path
    return None
