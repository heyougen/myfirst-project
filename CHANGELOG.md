# Changelog

All notable changes to STM32 Git Release Tool are documented here.

## [1.2.0] - 2026-08-01

### Added

- Searchable version points across the main window, history, and version
  comparison views, including tags, commits, dates, and descriptions.
- Comparison between any two local project folders without requiring Git.
- Project comparison filters for status, file type, filename, extension, and
  temporary exclusions.
- Progress reporting, cooperative cancellation, and same-content rename
  detection for project comparison.
- Guarded deletion of local tags and the latest unpublished commit.
- Developer recovery password support for protected reset operations.

### Changed

- Updated the application title and Windows metadata to v1.2.0.
- Added `icn.png` as the Windows executable and application window icon.
- Version and history lists now show minute-level dates and descriptions.
- History actions use the same structured version display as version
  comparison.
- Detached-HEAD commits and resets now create normal recovery/work branches.
- The current project path and selected version point are restored more
  consistently.

### Fixed

- Prevented stale search text from leaving version drop-down arrows empty.
- Prevented main-window checkout/reset actions from using a previously selected
  ref when the visible search text has not been selected.
- Unified version-comparison terminology as old version/new version and old
  line/new line.
- Unified project-comparison terminology as old project/new project and old
  line/new line.
- Stabilized project-comparison progress updates by keeping a determinate,
  monotonic percentage.

## [1.0.0] - 2026-06-27

### Added

- Simplified Chinese and English interface switching from the main tab bar.
- Windows 10/11 single-file executable build.
- Windows 7 legacy build kit based on Python 3.8 and PyInstaller 4.10.
- Isolated critical-flow smoke test covering Git initialization, commits,
  filtering, tags, diffs, branches, backup/reset, release packaging, local
  push, and clone recovery.
- Windows file version metadata and reproducible build scripts.

### Changed

- Improved compact main-window layout and increased execution log space.
- Improved source-focused diff display while preserving repeated code lines.
- Improved detached HEAD recovery and release branch handling.
- Expanded English translations for dialogs, help, diagnostics, and logs.

### Fixed

- Prevented repeated commits when no meaningful project changes exist.
- Corrected version comparison direction and whitespace-only diff handling.
- Added Python 3.8-compatible type annotations for the Windows 7 build.
- Prevented Git and `attrib` child processes from flashing CMD windows.
- Improved repository protection, backup branches, and reset safeguards.

### Compatibility

- Standard executable: Windows 10/11 x64.
- Legacy executable: Windows 7 SP1 x64, built and tested separately with
  Python 3.8.x, PyQt5 5.15.2, and PyInstaller 4.10.

## [0.1.0] - 2026-06-27

- Initial open-source source release.
