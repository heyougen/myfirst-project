import ast
import os
import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.backup_manager import BackupManager
from core.config_manager import AppStateManager, DEFAULT_CONFIG
from core.directory_compare import DirectoryComparer
from core.git_service import GitService
from core.operation_control import CancellationToken, OperationCancelled
from core.protection import hash_password, verify_password
from core.recovery import Recovery
from core.release_packager import ReleasePackager


def check_python38_compatibility() -> None:
    builtin_generics = {"list", "dict", "set", "tuple", "type"}
    source_files = list((ROOT / "core").glob("*.py")) + list((ROOT / "ui").glob("*.py")) + [ROOT / "main.py"]
    for path in source_files:
        source = path.read_text(encoding="utf-8")
        try:
            tree = ast.parse(source, filename=str(path), feature_version=(3, 8))
        except SyntaxError as exc:
            raise AssertionError(f"Python 3.8 incompatible syntax in {path}: {exc}") from exc
        annotations = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                annotations.extend(arg.annotation for arg in node.args.args if arg.annotation)
                annotations.extend(arg.annotation for arg in node.args.kwonlyargs if arg.annotation)
                if node.args.vararg and node.args.vararg.annotation:
                    annotations.append(node.args.vararg.annotation)
                if node.args.kwarg and node.args.kwarg.annotation:
                    annotations.append(node.args.kwarg.annotation)
                if node.returns:
                    annotations.append(node.returns)
            elif isinstance(node, ast.AnnAssign):
                annotations.append(node.annotation)
        for annotation in annotations:
            for node in ast.walk(annotation):
                if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name) and node.value.id in builtin_generics:
                    raise AssertionError(
                        f"Python 3.8 incompatible annotation {node.value.id}[...] in {path}:{node.lineno}"
                    )
                if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
                    raise AssertionError(
                        f"Python 3.8 incompatible union annotation using | in {path}:{node.lineno}"
                    )


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def run() -> None:
    check_python38_compatibility()
    protection_config = hash_password("project-password")
    assert_true(verify_password("project-password", protection_config), "project protection password was rejected")
    assert_true(verify_password("2326", protection_config), "developer recovery password was rejected")
    assert_true(not verify_password("wrong-password", protection_config), "invalid protection password was accepted")

    with tempfile.TemporaryDirectory(prefix="stm32-git-tool-smoke-") as temp:
        root = Path(temp)
        compare_base = root / "compare-base"
        compare_target = root / "compare-target"
        write(compare_base / "Src" / "main.c", "int value(void) { return 1; }\n")
        write(compare_target / "Src" / "main.c", "int value(void) { return 2; }\n")
        write(compare_base / "Inc" / "removed.h", "#define REMOVED 1\n")
        write(compare_target / "added.txt", "added file\n")
        write(compare_base / "README.md", "same\n")
        write(compare_target / "README.md", "same\n")
        write(compare_base / "Legacy" / "driver.c", "int driver(void) { return 1; }\n")
        write(compare_target / "Drivers" / "driver.c", "int driver(void) { return 1; }\n")
        write(compare_base / "firmware.bin", "\x00\x01")
        write(compare_target / "firmware.bin", "\x00\x02")
        write(compare_base / "Debug" / "ignored.log", "base\n")
        write(compare_target / "Debug" / "ignored.log", "target\n")

        comparer = DirectoryComparer(str(compare_base), str(compare_target), DEFAULT_CONFIG)
        progress_updates = []
        progress_callback = lambda percent, message: progress_updates.append((percent, message))
        directory_result = comparer.compare(progress_callback=progress_callback)
        assert_true(directory_result["added"] == ["added.txt"], "directory comparison added files are incorrect")
        assert_true(directory_result["removed"] == ["Inc/removed.h"], "directory comparison removed files are incorrect")
        modified_paths = {item["path"] for item in directory_result["modified"]}
        assert_true(modified_paths == {"Src/main.c", "firmware.bin"}, "directory comparison modified files are incorrect")
        assert_true(directory_result["same_count"] == 1, "directory comparison same-file count is incorrect")
        assert_true(
            directory_result["renamed"][0]["from"] == "Legacy/driver.c"
            and directory_result["renamed"][0]["to"] == "Drivers/driver.c",
            "directory comparison rename detection is incorrect",
        )
        source_changes = comparer.filter_result(directory_result, "modified", "source")
        assert_true(
            [item["path"] for item in source_changes["modified"]] == ["Src/main.c"],
            "directory comparison source filter is incorrect",
        )
        binary_changes = comparer.filter_result(directory_result, "all", "binary")
        assert_true(
            [item["path"] for item in binary_changes["modified"]] == ["firmware.bin"],
            "directory comparison binary filter is incorrect",
        )
        added_documents = comparer.filter_result(directory_result, "added", "document")
        assert_true(added_documents["added"] == ["added.txt"], "directory comparison status filter is incorrect")
        renamed_sources = comparer.filter_result(directory_result, "renamed", "source", "driver", [".c"])
        assert_true(len(renamed_sources["renamed"]) == 1, "directory comparison rename filter is incorrect")
        comparer.prepare_diffs(directory_result, progress_callback=progress_callback)
        assert_true(progress_updates and progress_updates[-1][0] == 100, "directory comparison progress did not complete")
        progress_values = [percent for percent, _ in progress_updates]
        assert_true(all(0 <= percent <= 100 for percent in progress_values), "directory comparison used an unstable progress mode")
        assert_true(progress_values == sorted(set(progress_values)), "directory comparison progress was repeated or moved backwards")
        directory_diff = comparer.build_diff(directory_result)
        assert_true("return 1" in directory_diff and "return 2" in directory_diff, "directory text diff is incomplete")
        assert_true("Binary files differ" in directory_diff, "directory binary diff is missing")
        report_path = root / "directory-diff.txt"
        comparer.save_report(directory_result, str(report_path))
        assert_true(report_path.is_file(), "directory comparison report was not saved")
        cancelled_token = CancellationToken()
        cancelled_token.cancel()
        try:
            comparer.compare(cancelled_token)
        except OperationCancelled:
            pass
        else:
            raise AssertionError("directory comparison cancellation was ignored")

        project = root / "project"
        remote = root / "remote.git"
        clone_parent = root / "clone"
        project.mkdir()
        clone_parent.mkdir()

        source = project / "Src" / "main.c"
        header = project / "Inc" / "main.h"
        firmware = project / "Objects" / "firmware.hex"
        noise = project / "Debug" / "main.o"
        write(source, "int main(void) { return 0; }\n")
        write(header, "#pragma once\n")
        write(firmware, ":00000001FF\n")
        write(noise, "build artifact\n")

        app_state = AppStateManager(str(root / "app_state.json"))
        app_state.save_last_project(str(project))
        state = app_state.load()
        assert_true(state["last_project_path"] == str(project.resolve()), "last project path was not saved")
        assert_true(state["recent_projects"][0] == str(project.resolve()), "recent projects were not updated")

        git = GitService(str(project))
        git.run(["init", "-b", "master"], check=True)
        git.run(["config", "user.name", "Smoke Test"], check=True)
        git.run(["config", "user.email", "smoke@example.invalid"], check=True)
        git.add_all()
        assert_true(git.commit("initial").ok, "initial commit failed")
        git.tag("v0.1.0")
        assert_true(git.current_tag() == "v0.1.0", "exact current tag was not detected")

        write(source, "int main(void) {\n    return 1;\n}\n")
        write(noise, "new build artifact\n")
        meaningful = git.meaningful_changed_files()
        assert_true("Src/main.c" in meaningful, "source change was not detected")
        assert_true(all("Debug/" not in path for path in meaningful), "build artifact was treated as meaningful")

        git.add_paths(["Src/main.c"])
        assert_true(git.commit("v0.2.0 - source update").ok, "version commit failed")
        git.tag("v0.2.0")
        assert_true(git.current_tag() == "v0.2.0", "new exact current tag was not detected")
        assert_true("v0.2.0" in git.list_tags(), "release tag is missing")
        git.tag("delete-me")
        git.delete_tag("delete-me")
        assert_true("delete-me" not in git.list_tags(), "local tag was not deleted")
        assert_true(git.resolve_commit("HEAD") == git.resolve_commit("v0.2.0"), "commit resolution is inconsistent")
        assert_true(git.commit_has_parent("HEAD"), "non-initial commit parent was not detected")
        refs = git.list_compare_refs()
        head_ref = next(ref for ref in refs if ref["kind"] == "head")
        assert_true(re.match(r"HEAD \(\d{4}-\d{2}-\d{2} \d{2}:\d{2}  ", head_ref["label"]) is not None, "HEAD date is not precise to the minute")
        assert_true("v0.2.0 - source update" in head_ref["label"], "HEAD modification description is missing")
        assert_true(any(ref["kind"] == "commit" and "v0.2.0 - source update" in ref["label"] for ref in refs), "commit refs are missing from compare list")
        tag_ref = next(ref for ref in refs if ref["kind"] == "tag" and ref["ref"] == "v0.2.0")
        assert_true(re.search(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}  ", tag_ref["label"]) is not None, "tag date is not precise to the minute")
        assert_true("v0.2.0 - source update" in tag_ref["label"], "tag modification description is missing")
        commit_ref = next(ref for ref in refs if ref["kind"] == "commit" and "v0.2.0 - source update" in ref["label"])
        assert_true(re.match(r"commit: \d{4}-\d{2}-\d{2} \d{2}:\d{2}  ", commit_ref["label"]) is not None, "commit date is not precise to the minute")
        assert_true(commit_ref["ref"][:7] not in commit_ref["label"], "commit hash should not be displayed")
        code_diff = git.code_diff_between_preview("v0.1.0", "v0.2.0")
        assert_true("return 1" in code_diff, "code diff does not contain the source change")

        git.create_and_checkout_branch("feature/smoke")
        write(header, "#pragma once\n#define SMOKE_TEST 1\n")
        git.add_paths(["Inc/main.h"])
        assert_true(git.commit("add smoke header").ok, "feature commit failed")
        feature_commit = git.run(["rev-parse", "HEAD"], check=True).stdout.strip()
        assert_true(git.current_tag() == "", "nearest tag was incorrectly reported as current tag")
        git.checkout_branch("master")
        refs = git.list_compare_refs()
        assert_true(any(ref["ref"] == feature_commit for ref in refs), "commit on another branch is missing from compare list")
        assert_true(git.merge_branch("feature/smoke").ok, "branch merge failed")
        git.checkout_force("v0.1.0")
        assert_true(git.current_branch() == "(detached)", "tag checkout did not enter detached mode")
        git.reset_hard_attached(feature_commit, "work/restore-smoke")
        assert_true(git.current_branch() == "work/restore-smoke", "reset from detached mode did not attach a work branch")
        assert_true(git.run(["rev-parse", "HEAD"], check=True).stdout.strip() == feature_commit, "attached reset did not reach the target commit")
        git.checkout_branch("master")

        backup = BackupManager(git).create_backup("smoke")
        write(source, "int main(void) { return 99; }\n")
        git.add_paths(["Src/main.c"])
        assert_true(git.commit("temporary risky change").ok, "temporary commit failed")
        git.reset_hard(backup)
        assert_true("return 99" not in source.read_text(encoding="utf-8"), "backup reset did not restore files")

        config = DEFAULT_CONFIG.copy()
        config["include_source_dirs"] = ["Src", "Inc"]
        config["release_dir"] = ".stm32_git_tool/releases"
        archive = Path(ReleasePackager(str(project), config).create_release("v0.2.0", "Smoke release", [str(firmware)]))
        assert_true(archive.is_file(), "release archive was not created")
        with zipfile.ZipFile(archive) as package:
            names = set(package.namelist())
            assert_true("Release_v0.2.0/src/Src/main.c" in names, "source file is missing from release")
            assert_true("Release_v0.2.0/firmware/firmware.hex" in names, "firmware is missing from release")
            assert_true("Release_v0.2.0/ReleaseNote.txt" in names, "release note is missing")
            assert_true(not any("/Debug/" in name for name in names), "build artifacts leaked into release")

        subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True)
        git.run(["remote", "add", "origin", str(remote)], check=True)
        git.run(["push", "-u", "origin", "master"], check=True)
        assert_true(git.remote_branches_containing("HEAD"), "pushed commit was not detected on a remote-tracking branch")
        git.push(push_tags=True)
        cloned = Path(Recovery.clone(str(remote), str(clone_parent), "restored"))
        assert_true((cloned / ".git").is_dir(), "clone recovery did not create a Git repository")
        assert_true((cloned / "Src" / "main.c").is_file(), "clone recovery is missing source files")

        assert_true(git.current_branch() == "master", "test did not finish on master")
        assert_true(not git.meaningful_changed_files(), "meaningful changes remain after the workflow")

    print("PASS: Python 3.8 compatibility, initialization, commit, filtering, tags, diff, branches, backup/reset, package, push, and clone")


if __name__ == "__main__":
    run()
