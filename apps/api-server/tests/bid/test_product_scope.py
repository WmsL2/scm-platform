from app.modules.bid.domain.product_scope import ProductSelectionScope


def test_product_selection_scope_normalizes_and_freezes_values() -> None:
    scope = ProductSelectionScope.from_values(
        [" 上海公司 ", "北京公司", "上海公司", ""],
        [" 张三 ", "李四", "张三"],
    )

    assert scope.company_names == ("上海公司", "北京公司")
    assert scope.purchasing_agents == ("张三", "李四")
    assert scope.snapshot() == {
        "company_names": ["上海公司", "北京公司"],
        "purchasing_agents": ["张三", "李四"],
    }


def test_product_selection_scope_ignores_malformed_snapshot_values() -> None:
    scope = ProductSelectionScope.from_snapshot(
        {
            "company_names": ["上海公司", 1, None],
            "purchasing_agents": "not-a-list",
        }
    )

    assert scope.company_names == ("上海公司",)
    assert scope.purchasing_agents == ()
