# STM32 Git Release Tool

A compact Windows desktop application for managing Git versions and release
packages in STM32, Keil MDK, and STM32CubeMX projects.

It provides guided workflows for commits, tags, release archives, branches,
history, code comparison, recovery, cleanup, and remote synchronization.
The interface can switch between Simplified Chinese and English at runtime.

## Features

- Initialize an STM32 project as a Git repository with suitable ignore rules.
- Commit meaningful project files while filtering build artifacts and caches.
- Create release tags and ZIP packages containing source and firmware files.
- Inspect commit history and source-oriented diffs.
- Search and compare tags, commits, or `HEAD` in a clear base-to-target direction.
- Compare any two local project folders without requiring a Git repository.
- Filter folder differences by change type, file type, name, and extension.
- Track long folder comparisons with progress and cooperative cancellation.
- Create, switch, merge, and delete branches.
- Delete a local tag or the latest unpublished commit with guarded confirmation.
- Create recovery branches before destructive reset operations.
- Clean Keil build artifacts such as `Debug/`, `Objects/`, `Listings/`,
  `*.map`, `*.axf`, `*.o`, and `*.d`.
- Pull, push, push tags, verify remotes, and clone repositories.
- Export diagnostics for troubleshooting.
- Switch between Simplified Chinese and English from the top-right language
  selector beside **Settings**.

## Download And Run

For normal Windows users, download `STM32GitReleaseTool.exe` from the GitHub
Releases page.

Requirements:

- Windows 10 or Windows 11 for the standard build
- Git installed and available in `PATH`

The application is portable. Place the EXE in any writable folder and run it.
Project settings, logs, diagnostics, release packages, and recovery metadata are
stored inside the selected project under `.stm32_git_tool/`.

> Windows 7 requires a separately built legacy package using an older Python,
> PyQt5, and PyInstaller toolchain. The standard build produced by the current
> Python 3.13 environment does not claim Windows 7 compatibility.

### Build On Windows 7

Use `STM32GitReleaseTool-Win7-BuildKit.zip` when a Windows 7 build is required:

1. Use Windows 7 SP1 64-bit with current SHA-2 and TLS updates.
2. Install 64-bit Python 3.8.10 and select **Add Python to PATH**.
3. Install Git for Windows and make sure `git --version` works.
4. Extract the complete build kit to a writable path without Chinese
   characters or an excessively long directory name.
5. Double-click `final_build_win7.bat`.

The script creates an isolated `.win7_build_env`, installs fixed legacy
dependencies, builds the application, and writes
`STM32GitReleaseTool-Win7.exe` beside the BAT file.

Fixed legacy build versions:

- Python 3.8.x 64-bit
- PyQt5 5.15.2
- PyQt5-Qt5 5.15.2
- PyQt5-sip 12.13.0
- Pillow 10.4.0
- PyInstaller 4.10

For offline building, place all required wheels in a `win7_wheels` directory
beside the BAT file. The script uses that directory instead of PyPI when it
exists.

## Run From Source

Requirements:

- Windows
- Python 3.10 or newer
- Git available in `PATH`

```powershell
python -m pip install -r requirements.txt
python .\main.py
```

## Build The Windows EXE

Install the runtime dependency and PyInstaller, then run the build script:

```powershell
python -m pip install -r requirements.txt
python -m pip install -r requirements-build.txt
powershell -ExecutionPolicy Bypass -File .\scripts\build_windows.ps1
```

The final executable is written to:

```text
dist/STM32GitReleaseTool.exe
```

The script removes previous `build/` and `dist/` output, builds from
`STM32GitReleaseTool.spec`, and performs a basic EXE existence and size check.

## Typical Workflow

1. Select the STM32 project root directory.
2. Click **Initialize Project** only when using the tool on a new repository.
3. Modify and compile the project.
4. Click **Commit Version** and confirm the meaningful file list.
5. Click **Publish Release** to create a Git tag and release ZIP.
6. Configure a remote URL in **Settings**.
7. Use **Push + Tags** to publish the branch and tags.

Branches and releases serve different purposes:

- Branches such as `master`, `dev`, `feature/*`, and `fix/*` hold lines of work.
- Tags such as `v1.0.0` identify immutable release points.
- A release does not require a separate branch for every version.

## Safety Notes

- **Browse History** enters detached HEAD mode for inspection only. Use
  **Return To Branch** before continuing normal development.
- Prefer **Revert** for undoing a published commit because it preserves history.
- **Force Reset** changes project files and history. The tool requires password
  and `RESET` confirmation and creates a `backup/*` branch first.
- Review the file list before every commit and release.
- Keep an external remote backup for important repositories.

## Diff Behavior

- The in-app code diff ignores whitespace-only changes for easier review.
- Repeated source lines are preserved; they are not deduplicated.
- Firmware and build artifacts are filtered from code-oriented previews.
- Full diff export preserves the original Git patch for strict review.

## Repository Hygiene

The tool filters common non-source artifacts, including:

- `*.hex`, `*.bin`, `*.crf`
- `*.elf`, `*.lib`, `*.a`, `*.obj`
- `*.map`, `*.axf`, `*.o`, `*.d`
- Keil user cache and generated report files
- `.stm32_git_tool/`

## Verification

Run the isolated critical-flow smoke test:

```powershell
python .\tests\smoke_test.py
```

The test creates temporary local repositories and verifies initialization,
commits, meaningful-change filtering, tags, diffs, branches, backup/reset,
release packaging, local remote push, and clone recovery.

## Current Release

The current release is `v1.2.0`. The application title displays
`V1.2`, while Windows file metadata uses the full semantic version `1.2.0`.
See [CHANGELOG.md](./CHANGELOG.md) for release details.

## Known Limitations

- Windows-first desktop application.
- Designed for STM32 and Keil-style project structures rather than arbitrary
  Git repositories.
- Git credentials are managed by the installed Git environment.
- The project currently has a smoke test but no full GUI automation suite.

## 中文说明

STM32 Git Release Tool 是面向 STM32、Keil MDK 和 STM32CubeMX 工程的 Windows
桌面工具，用按钮封装常用 Git 和版本发布操作。

主要功能包括：

- 初始化 Git 工程并生成 STM32 忽略规则
- 过滤编译产物后提交有效源码
- 创建版本 tag 和 Release ZIP
- 搜索 tag、commit、日期和修改说明，查看历史、代码 Diff 和版本对比
- 对比任意两个本地工程，支持筛选、改名识别、进度和取消
- 二次确认后删除本地 tag 或最新的未发布 commit
- 管理分支、备份分支和安全恢复
- 清理 Keil 编译缓存
- Pull、Push、Push Tags、验证远程和克隆
- 在主界面“设置”旁直接切换简体中文和 English

普通用户建议从 GitHub Releases 下载 `STM32GitReleaseTool.exe`。运行前需要
安装 Git，并确保命令行能够执行 `git --version`。

推荐流程：

1. 选择 STM32 工程根目录。
2. 新工程第一次使用时点击“初始化工程”。
3. 修改并编译代码。
4. 点击“提交版本”，核对文件列表后提交。
5. 点击“发布 Release”，创建 tag 和发布包。
6. 配置远程地址后使用“Push + Tags”推送代码和版本标签。

查看历史版本会进入 detached HEAD 状态，这只是查看旧版本。继续开发前应点击
“返回分支”。已经推送或发布的提交优先使用 Revert 撤销，谨慎使用强制回退。

## License

MIT License. See [LICENSE](./LICENSE).
