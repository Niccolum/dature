"""Generate changelog.md from GitHub Releases.

Fetches all releases from the GitHub API and writes a Markdown changelog
with embedded release notes and links to each release page.
"""

import json
import os
import urllib.request
from pathlib import Path

REPO = "Niccolum/dature"
OUTPUT = Path(__file__).parent / "changelog.md"


def fetch_releases() -> list[dict[str, str]]:
    url = f"https://api.github.com/repos/{REPO}/releases?per_page=100"
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github+json")

    token = os.environ.get("GITHUB_TOKEN", "")
    if token:
        req.add_header("Authorization", f"Bearer {token}")

    with urllib.request.urlopen(req) as response:
        result: list[dict[str, str]] = json.loads(response.read().decode())
        return result


def build_changelog(releases: list[dict[str, str]]) -> str:
    lines = ["# Changelog", ""]

    if not releases:
        lines.append(
            f"See [GitHub Releases](https://github.com/{REPO}/releases) for the full changelog.",
        )
        return "\n".join(lines) + "\n"

    for release in releases:
        tag = release.get("tag_name", "")
        name = release.get("name") or tag
        url = release.get("html_url", "")
        body = (release.get("body") or "").strip()
        prerelease = release.get("prerelease", False)

        heading = f"## [{name}]({url})"
        if prerelease:
            heading += " (pre-release)"
        lines.append(heading)
        lines.append("")

        if body:
            lines.append(body)
        else:
            lines.append("*No release notes.*")
        lines.append("")

    return "\n".join(lines) + "\n"


def main() -> None:
    try:
        releases = fetch_releases()
    except Exception as exc:
        print(f"Warning: failed to fetch releases from GitHub API: {exc}")
        print("Keeping existing changelog.md")
        return

    content = build_changelog(releases)
    OUTPUT.write_text(content)
    print(f"Generated changelog.md with {len(releases)} release(s)")


if __name__ == "__main__":
    main()
