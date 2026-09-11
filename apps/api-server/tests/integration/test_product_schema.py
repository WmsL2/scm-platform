from sqlalchemy import text

from app.core.database import SessionLocal


async def test_product_schema_and_permission_directory() -> None:
    expected_product_columns = {
            "id", "listed_at", "brand", "image_reference", "model", "sku", "product_name",
            "category_id", "category_level1_name", "category_level2_name", "category_level3_name",
            "item_number", "jd_same_product_url", "cost_price", "market_price",
        "jd_price", "agreement_price", "agreement_purchase_price", "profit", "jd_margin",
        "purchasing_agent", "source_supplier_id", "barcode_text", "deduction_review",
        "product_specification", "selling_points", "gross_margin", "remark", "discount_rate",
        "restricted_regions", "jd_self_operated_price", "reference_url", "storefront_type",
        "price_inflation_rate", "deduction_rate", "created_by", "updated_by", "created_at",
        "updated_at", "is_deleted", "deleted_by", "deleted_at",
    }
    async with SessionLocal() as session:
        table_rows = await session.execute(
            text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = DATABASE() AND table_name IN ('scm_category', 'scm_product')"
            )
        )
        assert {row[0] for row in table_rows} == {"scm_category", "scm_product"}
        product_columns = {
            row[0]
            for row in (
                await session.execute(
                    text(
                        "SELECT column_name FROM information_schema.columns "
                        "WHERE table_schema = DATABASE() AND table_name = 'scm_product'"
                    )
                )
            )
        }
        assert product_columns == expected_product_columns
        category_columns = await session.execute(
            text(
                "SELECT column_name, is_nullable FROM information_schema.columns "
                "WHERE table_schema = DATABASE() AND table_name = 'scm_product' "
                "AND column_name IN ('category_id', 'category_level1_name', "
                "'category_level2_name', 'category_level3_name')"
            )
        )
        assert {row[0]: row[1] for row in category_columns} == {
            "category_id": "YES",
            "category_level1_name": "YES",
            "category_level2_name": "YES",
            "category_level3_name": "YES",
        }
        decimal_columns = await session.execute(
            text(
                "SELECT table_name, column_name, numeric_precision, numeric_scale "
                "FROM information_schema.columns "
                "WHERE table_schema = DATABASE() "
                "AND ((table_name = 'scm_category' AND column_name = 'deduction_rate') "
                "OR (table_name = 'scm_product' AND column_name = 'cost_price'))"
            )
        )
        assert {
            (row[0], row[1], row[2], row[3]) for row in decimal_columns
        } == {
            ("scm_category", "deduction_rate", 9, 4),
            ("scm_product", "cost_price", 18, 4),
        }
        permissions = await session.execute(
            text(
                "SELECT permission_code FROM sys_permission "
                "WHERE permission_code LIKE 'product:%'"
            )
        )
        assert {row[0] for row in permissions} == {
            "product:list",
            "product:detail",
                "product:cost:update",
                "product:update",
                "product:delete",
                "product:import",
            "product:import:resolve",
        }
        quote_tables = await session.execute(
            text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = DATABASE() AND table_name = 'scm_supplier_product_quote'"
            )
        )
        assert list(quote_tables) == []
