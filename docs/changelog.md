# Changelog

## [v0.14.0](https://github.com/Niccolum/dature/releases/tag/v0.14.0)

### Improvements
- Refactored error handling in the exceptions module to provide clearer messages.
- Enhanced the sources loader to improve performance and reliability.
- Updated validation examples to demonstrate new features and best practices.
- Improved error handling in the loading module to prevent crashes on invalid inputs.

### Fixes
- Resolved issues with error reporting in the validation module.
- Fixed bugs in the masking examples to ensure accurate functionality.
- Corrected various test cases to improve coverage and reliability.
- Addressed errors in the source loading process to enhance stability.
- Fixed errors related to loading configurations from different sources.

## [v0.13.0](https://github.com/Niccolum/dature/releases/tag/v0.13.0)

### Features
- Introduced a new strategy for configuration loading.

### Improvements
- Enhanced the `int_from_string` function to correctly cast boolean values to integers.
- Improved documentation for advanced configuration options.

### Fixes
- Updated the README to reflect recent changes and improvements.
- Addressed comments from Devin regarding code clarity and documentation.

## [v0.12.4](https://github.com/Niccolum/dature/releases/tag/v0.12.4)

### Fixes
- Ensured JSON5 support is now correctly required in the configuration loader.
- Resolved issues related to loading configurations from JSON5 files.

## [v0.12.3](https://github.com/Niccolum/dature/releases/tag/v0.12.3)

### Improvements
- Refactored the strict retort functionality for enhanced performance.
- Added a fallback mechanism for Read the Docs (RTD) to improve documentation accessibility.

### Fixes
- Resolved issues in various source loader files to ensure better compatibility and functionality.

## [v0.12.2](https://github.com/Niccolum/dature/releases/tag/v0.12.2)

### Improvements
- Removed duplicate error messages for better clarity.
- Eliminated unnecessary traceback information to streamline error reporting.

### Fixes
- Fixed the Read the Docs configuration in the CI workflow to ensure proper documentation generation.

## [v0.12.1](https://github.com/Niccolum/dature/releases/tag/v0.12.1)

### Improvements
- Enhanced the changelog generation process to ensure accurate updates.
- Updated documentation to include support for `timedelta` as a valid type.
- Resolved security issues to improve overall safety.

### Docs
- Corrected documentation tags for clarity and consistency.

### Features
- Added logging functionality to `dature`.
- Added Docker Secrets loader.
- Added `SecretStr`, `PaymentCardNumber`, and `ByteSize` special field types.
- Added secret masking in error messages (by field name and heuristic detection).
- Added ENV variable expansion in config values.
- Added field alias provider for flexible field name mapping.
- Added `configure()` for global masking, error display, and loading settings.
- Added `F` field path objects with field mapping support.
- Added field group support for merge rules.
- Added custom merge functions and merge strategies (`append`, `prepend`, `first_wins`, etc.).
- Added `skip_invalid` and `skip_broken` merge options (global and per-source).
- Added mypy plugin.

### Improvements
- Restructured source code into subpackages: `errors/`, `expansion/`, `fields/`, `loading/`, `masking/`, `merging/`.
- Restructured tests to mirror `src/` layout.
- Improved path finders for YAML, TOML, JSON, JSON5, and INI formats.
- Improved error formatting with source location context.
- Improved source loader base with better type safety.
- Improved ENV loader with strip and type handling.
- Skipped lint/test jobs on tag push in CI (already verified on main push).
- Improved CI configurations for better stability and reliability.

### Fixes
- Fixed various issues in the CI configuration.
- Resolved multiple bugs affecting functionality and stability.

### Docs
- Added documentation site (MkDocs + Material) with full coverage: getting started, features, advanced topics, API reference.
- Added `CHANGELOG.md` with AI-generated entries on PR creation.
- Added social cards, minify, 8-bit themed headings, and custom color scheme to docs.
- Added changelog workflow: AI generates changelog entries per PR, release job extracts them for GitHub Releases.
- Added CI support for tag push: `pypi-publish`, `github-release`, and `trigger-rtd` now run on tag events.
- Added `trigger-rtd` job supporting both `latest` (main) and `stable` (tag) RTD builds.
- Added version-bump, dependency-review, scorecard, and docs CI workflows.
- Added dependabot configuration.
- Added CODEOWNERS and SECURITY.md.
- Added comprehensive examples for all features.
- Slimmed down `README.md` in favor of documentation site.

## [v0.11.0](https://github.com/Niccolum/dature/releases/tag/v0.11.0)

## What's Changed
* ci/fix_test_required by @Niccolum in https://github.com/Niccolum/dature/pull/27
* Refactor/delete big ball of mud by @Niccolum in https://github.com/Niccolum/dature/pull/28
* chore: bump version to 0.11.0 by @Niccolum in https://github.com/Niccolum/dature/pull/29


**Full Changelog**: https://github.com/Niccolum/dature/compare/v0.10.1...v0.11.0

## [v0.10.1](https://github.com/Niccolum/dature/releases/tag/v0.10.1)

## What's Changed
* ci: bump astral-sh/setup-uv from 7.3.0 to 7.3.1 by @dependabot[bot] in https://github.com/Niccolum/dature/pull/20
* ci: bump actions/checkout from 4.3.1 to 6.0.2 by @dependabot[bot] in https://github.com/Niccolum/dature/pull/24
* ci: bump actions/setup-python from 5.6.0 to 6.2.0 by @dependabot[bot] in https://github.com/Niccolum/dature/pull/21
* ci: bump actions/upload-artifact from 6.0.0 to 7.0.0 by @dependabot[bot] in https://github.com/Niccolum/dature/pull/22
* ci: bump actions/attest-build-provenance from 2.4.0 to 4.1.0 by @dependabot[bot] in https://github.com/Niccolum/dature/pull/23
* feature/add_global_config by @Niccolum in https://github.com/Niccolum/dature/pull/25
* chore: bump version to 0.10.1 by @Niccolum in https://github.com/Niccolum/dature/pull/26


**Full Changelog**: https://github.com/Niccolum/dature/compare/v0.10.0...v0.10.1

## [v0.10.0](https://github.com/Niccolum/dature/releases/tag/v0.10.0)

## What's Changed
* add branch name rule by @Niccolum in https://github.com/Niccolum/dature/pull/5
* ci: bump astral-sh/setup-uv from 5.4.2 to 7.3.0 by @dependabot[bot] in https://github.com/Niccolum/dature/pull/4
* Ci/add dependabot prefix by @Niccolum in https://github.com/Niccolum/dature/pull/6
* ci: bump github/codeql-action from 3.32.4 to 4.32.4 by @dependabot[bot] in https://github.com/Niccolum/dature/pull/3
* ci: bump actions/upload-artifact from 4.6.2 to 6.0.0 by @dependabot[bot] in https://github.com/Niccolum/dature/pull/1
* ci: bump actions/labeler from 5.0.0 to 6.0.1 by @dependabot[bot] in https://github.com/Niccolum/dature/pull/2
* Feat/pretty metadata parsers - remove custom by @Niccolum in https://github.com/Niccolum/dature/pull/7
* Feat/secret configs by @Niccolum in https://github.com/Niccolum/dature/pull/8
* Feat/custom merge function by @Niccolum in https://github.com/Niccolum/dature/pull/9
* Refactor/path finders by @Niccolum in https://github.com/Niccolum/dature/pull/10
* fix bump version in ci by @Niccolum in https://github.com/Niccolum/dature/pull/11
* Ci/fix bump v2 by @Niccolum in https://github.com/Niccolum/dature/pull/13
* Ci/fix bump v3 by @Niccolum in https://github.com/Niccolum/dature/pull/15
* fix existing branch by @Niccolum in https://github.com/Niccolum/dature/pull/16
* chore: bump version to 0.10.0 by @Niccolum in https://github.com/Niccolum/dature/pull/17
* ci/fix_bump_v6 by @Niccolum in https://github.com/Niccolum/dature/pull/18

## New Contributors
* @Niccolum made their first contribution in https://github.com/Niccolum/dature/pull/5
* @dependabot[bot] made their first contribution in https://github.com/Niccolum/dature/pull/4

**Full Changelog**: https://github.com/Niccolum/dature/compare/v0.9.1...v0.10.0

## [v0.9.1](https://github.com/Niccolum/dature/releases/tag/v0.9.1)

**Full Changelog**: https://github.com/Niccolum/dature/compare/v0.9.0...v0.9.1

