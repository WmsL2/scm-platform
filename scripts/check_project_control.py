"""Validate that non-project-control changes include project-control updates."""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

PROJECT_CONTROL_PREFIX = "project-control/"
CHANGE_RECORD_PREFIX = "project-control/changes/"
CURRENT_STATUS = "project-control/CURRENT_STATUS.md"
STATUS_PREFIXES = ("project-control/modules/", "project-control/sprints/")


@dataclass(frozen=True)
class GateResult:
    """The result of evaluating a PR's changed files."""

    passed: bool
    changed_files: tuple[str, ...]
    change_records: tuple[str, ...]
    status_files: tuple[str, ...]
    missing: tuple[str, ...]


def normalize_path(path: str) -> str:
    """Normalize Git paths for consistent checks on Windows and Linux."""
    return path.replace("\\", "/").removeprefix("./")


def is_change_record(path: str) -> bool:
    parts = path.split("/")
    return (
        path.startswith(CHANGE_RECORD_PREFIX)
        and path.endswith(".md")
        and len(parts) >= 4
    )


def is_status_file(path: str) -> bool:
    return path == CURRENT_STATUS or (
        path.endswith(".md") and any(path.startswith(prefix) for prefix in STATUS_PREFIXES)
    )


def evaluate_changed_files(changed_files: Sequence[str]) -> GateResult:
    """Evaluate changed paths without invoking Git, for reusable unit tests."""
    files = tuple(sorted({normalize_path(path) for path in changed_files if path.strip()}))
    change_records = tuple(path for path in files if is_change_record(path))
    status_files = tuple(path for path in files if is_status_file(path))
    has_non_project_control_change = any(
        not path.startswith(PROJECT_CONTROL_PREFIX) for path in files
    )

    if not has_non_project_control_change:
        return GateResult(True, files, change_records, status_files, ())

    missing: list[str] = []
    if not change_records:
        missing.append("Change Record")
    if not status_files:
        missing.append("Current Status / Module / Sprint 状态更新")
    return GateResult(
        passed=not missing,
        changed_files=files,
        change_records=change_records,
        status_files=status_files,
        missing=tuple(missing),
    )


def changed_files_from_git(base_sha: str, head_sha: str) -> tuple[str, ...]:
    """Read PR changed files through Git's three-dot comparison."""
    repository_root = Path(__file__).resolve().parent.parent
    completed = subprocess.run(
        ["git", "diff", "--name-only", f"{base_sha}...{head_sha}"],
        cwd=repository_root,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or "git diff 执行失败。"
        raise RuntimeError(detail)
    return tuple(completed.stdout.splitlines())


def print_result(result: GateResult) -> None:
    """Print a human-readable gate result for local and CI logs."""
    print(f"changed files: {len(result.changed_files)}")
    print("change record files:")
    print(*(result.change_records or ("- 无",)), sep="\n")
    print("status files:")
    print(*(result.status_files or ("- 无",)), sep="\n")

    if result.passed:
        print("PROJECT_CONTROL_GATE_PASS")
        return

    print("PROJECT_CONTROL_GATE_FAILED")
    print("检测到非 project-control 修改，但项目控制文档未完整同步。")
    print("缺少：")
    for item in result.missing:
        print(f"- {item}")
    print("请按照 Definition of Done 更新 project-control 后重新提交。")


def main(argv: Sequence[str] | None = None) -> int:
    arguments = tuple(sys.argv[1:] if argv is None else argv)
    if len(arguments) != 2:
        print("PROJECT_CONTROL_GATE_ERROR")
        print("用法：python scripts/check_project_control.py <base_sha> <head_sha>")
        return 2
    try:
        result = evaluate_changed_files(changed_files_from_git(*arguments))
    except RuntimeError as exc:
        print("PROJECT_CONTROL_GATE_ERROR")
        print(f"无法读取 Git 变更文件：{exc}")
        return 2
    print_result(result)
    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
