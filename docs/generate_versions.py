"""Generate versions.json for Material for MkDocs version selector.

Fetches active/built versions from RTD API and produces a mike-compatible
versions.json so the Material theme renders a version dropdown in the header.
"""

import json
import os
import urllib.request
from pathlib import Path


def main() -> None:
    project = os.environ.get("READTHEDOCS_PROJECT", "")
    current_version = os.environ.get("READTHEDOCS_VERSION", "")
    output_dir = os.environ.get("READTHEDOCS_OUTPUT", "")

    if not project or not output_dir:
        print("Not running on RTD, skipping versions.json generation")
        return

    url = (
        f"https://readthedocs.org/api/v3/projects/{project}/versions/"
        f"?active=true&built=true&privacy_level=public&limit=50"
    )

    req = urllib.request.Request(url)
    req.add_header("Accept", "application/json")

    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
    except Exception as exc:
        print(f"Warning: failed to fetch versions from RTD API: {exc}")
        print("Generating versions.json with current version only")
        data = {"results": []}

    versions: list[dict[str, str | list[str]]] = []

    for v in data.get("results", []):
        slug = v.get("slug", "")
        verbose_name = v.get("verbose_name", slug)
        if not slug:
            continue

        aliases: list[str] = []
        if slug == "stable":
            aliases.append("stable")

        title = verbose_name
        if slug == "stable":
            title = f"{verbose_name} (stable)"
        elif slug == "latest":
            title = f"{verbose_name} (dev)"

        versions.append(
            {
                "version": slug,
                "title": title,
                "aliases": aliases,
            },
        )

    if not versions and current_version:
        versions.append(
            {
                "version": current_version,
                "title": current_version,
                "aliases": [],
            },
        )

    content = json.dumps(versions, indent=2)

    # Material looks for ../versions.json relative to base URL.
    # On RTD, base is /en/<version>/, so it resolves to /en/versions.json.
    # Place the file both inside the build output and one level above.
    html_dir = Path(output_dir) / "html"
    for path in [html_dir / "versions.json", html_dir.parent / "versions.json"]:
        path.write_text(content)
        print(f"Generated versions.json at {path}")


if __name__ == "__main__":
    main()
