import importlib.util
import sys
from pathlib import Path

SCRIPT_DIRECTORY = Path(__file__).resolve().parents[3] / "scripts"
SCRIPT_PATH = SCRIPT_DIRECTORY / "check_project_control.py"
SPEC = importlib.util.spec_from_file_location("check_project_control", SCRIPT_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Unable to load check_project_control.py")
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)

evaluate_changed_files = MODULE.evaluate_changed_files


def test_project_control_only_changes_pass() -> None:
    result = evaluate_changed_files(
        [
            "project-control/changes/2026-09/2026-09-03-008-governance.md",
            "project-control/modules/system.md",
        ]
    )
    assert result.passed


def test_application_change_with_change_record_and_current_status_passes() -> None:
    result = evaluate_changed_files(
        [
            "apps/api-server/app/main.py",
            "project-control/changes/2026-09/2026-09-03-008-governance.md",
            "project-control/CURRENT_STATUS.md",
        ]
    )
    assert result.passed


def test_application_change_with_change_record_and_module_status_passes() -> None:
    result = evaluate_changed_files(
        [
            "apps/web-admin/src/main.ts",
            "project-control/changes/2026-09/2026-09-03-008-governance.md",
            "project-control/modules/system.md",
        ]
    )
    assert result.passed


def test_windows_style_paths_are_normalized() -> None:
    result = evaluate_changed_files(
        [
            r"apps\api-server\app\main.py",
            r"project-control\changes\2026-09\2026-09-03-008-governance.md",
            r"project-control\CURRENT_STATUS.md",
        ]
    )
    assert result.passed


def test_application_change_without_project_control_fails() -> None:
    result = evaluate_changed_files(["apps/api-server/app/main.py"])
    assert not result.passed
    assert result.missing == ("Change Record", "Current Status / Module / Sprint 状态更新")


def test_application_change_with_only_change_record_fails() -> None:
    result = evaluate_changed_files(
        [
            "apps/api-server/app/main.py",
            "project-control/changes/2026-09/2026-09-03-008-governance.md",
        ]
    )
    assert not result.passed
    assert result.missing == ("Current Status / Module / Sprint 状态更新",)


def test_application_change_with_only_status_file_fails() -> None:
    result = evaluate_changed_files(
        ["apps/api-server/app/main.py", "project-control/sprints/sprint-01-auth-supplier.md"]
    )
    assert not result.passed
    assert result.missing == ("Change Record",)
