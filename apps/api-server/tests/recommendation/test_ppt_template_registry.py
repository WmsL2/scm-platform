from app.modules.recommendation.application.ppt_service import PptSolutionService
from app.modules.recommendation.application.ppt_template_registry import list_ppt_templates


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
