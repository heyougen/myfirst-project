# STM32 Git Release Tool

Windows desktop tool for STM32 / Keil / CubeMX projects.

It wraps common Git and release actions into a GUI so embedded developers can:

- initialize a repository for an STM32 project
- filter build artifacts before commit
- create version commits and tags
- generate release packages
- inspect history and code diffs
- compare versions
- manage branches and recovery branches

## Scope

This is not a general-purpose Git client.

It is designed for Windows-based STM32 workflows, especially projects built with:

- Keil MDK
- STM32CubeMX-generated code
- local release packaging based on `.bin` / `.hex` artifacts

## Features

- project selection and Git status overview
- repository initialization with STM32-oriented `.gitignore`
- `Commit Version` workflow with file confirmation
- `Release` workflow with tag creation and zip packaging
- branch management and backup branch recovery
- history view, code diff view, full patch export
- version comparison with clear base/target direction
- build artifact cleanup for `Debug/`, `Objects/`, `Listings/`, `*.map`, `*.axf`, `*.o`, `*.d`
- diagnostics export for logs, config, ignore rules, and repository checks

## Install

Requirements:

- Windows
- Python 3.10+
- Git available in `PATH`

Install dependencies and run:

```powershell
pip install -r requirements.txt
python .\main.py
```

## Typical Flow

1. Select the STM32 project directory.
2. Initialize the repository the first time.
3. Modify source files.
4. Use `Commit Version` to create a version commit.
5. Use `Release` to create a tag and release package.
6. Optionally configure a remote repository and push branch/tag refs.

## Branches And Release Tags

- Branches are for work lines such as `master`, `dev`, `feature/*`, `work/v1.3`.
- Releases are represented by Git tags such as `v1.0`, `v1.1`, `v1.3`.
- If the repository is in detached HEAD state, the tool can create a work branch from the current commit before continuing commit or release actions.

## Diff Behavior

- The in-app code diff preview ignores whitespace-only changes for easier review.
- Full diff export keeps the original patch content for strict inspection or archival use.
- Version comparison is directional: `base -> target`.

## Repository Hygiene

The tool treats the following as non-source artifacts and filters them from meaningful-change checks:

- `*.hex`
- `*.bin`
- `*.crf`
- `*.elf`
- `*.lib`
- `*.a`
- `*.obj`
- `*.map`
- `*.axf`
- `*.o`
- `*.d`

It also ignores Python cache files used during local development of this tool itself.

## Known Limitations

- Windows-first; not tested as a cross-platform GUI tool.
- Built around STM32/Keil-style project layouts, not arbitrary embedded repositories.
- Remote Git hosting integration is minimal unless a repository remote is configured locally.

## Open Source Status

Recommended first public release:

- `v0.1.0`

Reason:

- the tool is already usable
- behavior is still being refined from real project feedback
- workflow and UX may continue to change

## License

MIT License. See [LICENSE](./LICENSE).
