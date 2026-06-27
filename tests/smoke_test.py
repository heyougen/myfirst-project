import ast
import os
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.backup_manager import BackupManager
from core.config_manager import DEFAULT_CONFIG
from core.git_service import GitService
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
    with tempfile.TemporaryDirectory(prefix="stm32-git-tool-smoke-") as temp:
        root = Path(temp)
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

        git = GitService(str(project))
        git.run(["init", "-b", "master"], check=True)
        git.run(["config", "user.name", "Smoke Test"], check=True)
        git.run(["config", "user.email", "smoke@example.invalid"], check=True)
        git.add_all()
        assert_true(git.commit("initial").ok, "initial commit failed")
        git.tag("v0.1.0")

        write(source, "int main(void) {\n    return 1;\n}\n")
        write(noise, "new build artifact\n")
        meaningful = git.meaningful_changed_files()
        assert_true("Src/main.c" in meaningful, "source change was not detected")
        assert_true(all("Debug/" not in path for path in meaningful), "build artifact was treated as meaningful")

        git.add_paths(["Src/main.c"])
        assert_true(git.commit("v0.2.0 - source update").ok, "version commit failed")
        git.tag("v0.2.0")
        assert_true("v0.2.0" in git.list_tags(), "release tag is missing")
        code_diff = git.code_diff_between_preview("v0.1.0", "v0.2.0")
        assert_true("return 1" in code_diff, "code diff does not contain the source change")

        git.create_and_checkout_branch("feature/smoke")
        write(header, "#pragma once\n#define SMOKE_TEST 1\n")
        git.add_paths(["Inc/main.h"])
        assert_true(git.commit("add smoke header").ok, "feature commit failed")
        git.checkout_branch("master")
        assert_true(git.merge_branch("feature/smoke").ok, "branch merge failed")

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
        git.push(push_tags=True)
        cloned = Path(Recovery.clone(str(remote), str(clone_parent), "restored"))
        assert_true((cloned / ".git").is_dir(), "clone recovery did not create a Git repository")
        assert_true((cloned / "Src" / "main.c").is_file(), "clone recovery is missing source files")

        assert_true(git.current_branch() == "master", "test did not finish on master")
        assert_true(not git.meaningful_changed_files(), "meaningful changes remain after the workflow")

    print("PASS: Python 3.8 compatibility, initialization, commit, filtering, tags, diff, branches, backup/reset, package, push, and clone")


if __name__ == "__main__":
    run()
