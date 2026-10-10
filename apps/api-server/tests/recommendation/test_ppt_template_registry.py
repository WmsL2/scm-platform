from pathlib import Path
from types import SimpleNamespace

from app.modules.recommendation.application import ppt_template_registry
from app.modules.recommendation.application.ppt_service import PptSolutionService
from app.modules.recommendation.application.ppt_template_registry import (
    get_ppt_template,
    is_ppt_template_available,
    list_ppt_templates,
)


def test_builtin_template_catalog_is_fixed_and_complete() -> None:
    templates = list_ppt_templates()

    assert [item.code for item in templates] == [
        "SYSTEM_DEFAULT",
        "JD_DETAIL_RED",
        "JD_FESTIVE_RED",
        "CATALOG_MINIMAL",
        "UNION_QUOTE_WHITE",
    ]
    versions = {item.code: item.version for item in templates}
    assert versions["SYSTEM_DEFAULT"] == "1"
    assert all(versions[code] == "3" for code in versions if code != "SYSTEM_DEFAULT")
    assert [item.template_code for item in PptSolutionService.list_templates()] == [
        item.code for item in templates
    ]


def test_private_template_is_unavailable_without_its_configured_asset(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(
        ppt_template_registry,
        "get_settings",
        lambda: SimpleNamespace(ppt_template_asset_dir=tmp_path, app_env="production"),
    )

    assert is_ppt_template_available(get_ppt_template("SYSTEM_DEFAULT")) is True
    assert is_ppt_template_available(get_ppt_template("JD_FESTIVE_RED")) is False
    available = {
        item.template_code: item.is_available for item in PptSolutionService.list_templates()
    }
    assert available["SYSTEM_DEFAULT"] is True
    assert available["JD_FESTIVE_RED"] is False
