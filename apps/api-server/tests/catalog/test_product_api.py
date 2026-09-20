import uuid
from decimal import Decimal

from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select

from app.core.database import SessionLocal
from app.main import app
from app.modules.auth.security import create_token, hash_password
from app.modules.catalog.infrastructure.models import Category, Product, ProductPurgeAudit
from app.modules.catalog.schemas import _serialize_product_price
from app.modules.supplier.infrastructure.models import Supplier
from app.modules.system.models import Permission, Role, RolePermission, User, UserRole

PRODUCT_PERMISSIONS = (
    "product:list",
    "product:detail",
    "product:cost:update",
    "product:update",
    "product:disable",
    "product:purge",
)


def test_product_price_json_keeps_significant_digits_and_legacy_minimum() -> None:
    assert _serialize_product_price(Decimal("160.000000000000000000000000000000")) == "160.0000"
    assert _serialize_product_price(Decimal("100.123450000000000000000000000000")) == "100.12345"
    assert (
        _serialize_product_price(Decimal("100.123456789012345678901234567891"))
        == "100.123456789012345678901234567891"
    )
    assert _serialize_product_price(None) is None


class RecordingStorage:
    def __init__(self) -> None:
        self.saved: list[str] = []
        self.deleted: list[str] = []

    async def save(self, name: str, content: bytes) -> str:
        assert content
        key = f"{name}.stored"
        self.saved.append(key)
        return key

    async def read(self, key: str) -> bytes:
        del key
        return b""

    async def delete(self, key: str) -> None:
        self.deleted.append(key)


async def create_product_user(
    permission_codes: tuple[str, ...],
) -> tuple[uuid.UUID, dict[str, str]]:
    user_id, role_id = uuid.uuid4(), uuid.uuid4()
    async with SessionLocal() as session:
        permissions = list(
            (
                await session.scalars(
                    select(Permission).where(Permission.permission_code.in_(permission_codes))
                )
            ).all()
        )
        assert len(permissions) == len(permission_codes)
        session.add_all(
            [
                User(
                    id=user_id,
                    username=f"product-test-{user_id}",
                    password_hash=hash_password("secret"),
                ),
                Role(id=role_id, role_code=f"product-test-{role_id}", role_name="product test"),
                UserRole(user_id=user_id, role_id=role_id),
                *[
                    RolePermission(role_id=role_id, permission_id=permission.id)
                    for permission in permissions
                ],
            ]
        )
        await session.commit()
    return user_id, {"Authorization": f"Bearer {create_token(user_id, 1)}"}


async def cleanup_user(user_id: uuid.UUID) -> None:
    async with SessionLocal() as session:
        role_ids = list(
            (
                await session.scalars(select(UserRole.role_id).where(UserRole.user_id == user_id))
            ).all()
        )
        await session.execute(delete(RolePermission).where(RolePermission.role_id.in_(role_ids)))
        await session.execute(delete(UserRole).where(UserRole.user_id == user_id))
        await session.execute(delete(Role).where(Role.id.in_(role_ids)))
        await session.execute(delete(User).where(User.id == user_id))
        await session.commit()


async def create_product_fixture(
    *, created_by: uuid.UUID | None = None, updated_by: uuid.UUID | None = None
) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
    supplier_id, category_id, product_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    async with SessionLocal() as session:
        session.add_all(
            [
                Supplier(
                    id=supplier_id,
                    supplier_code=f"TST{str(supplier_id)[:8]}",
                    supplier_name=f"商品测试来源供应商-{supplier_id}",
                    main_brands="测试品牌",
                    advantage="测试优势",
                    archive_status="ARCHIVED",
                    cooperation_status="NORMAL",
                ),
                Category(
                    id=category_id,
                    source_type="MALL_LEVEL3",
                    level1_name="一级",
                    level2_name="二级",
                    level3_name="三级",
                    level3_external_id=f"test-{category_id}",
                    deduction_rate=Decimal("0.0500"),
                ),
            ]
        )
        await session.flush()
        session.add(
            Product(
                id=product_id,
                product_name="商品成本价测试",
                company_name="众诚测试公司",
                brand="测试品牌",
                image_reference="local-media/product-images/test-product.png",
                model="MODEL-1",
                sku="SKU-1",
                category_level1_name="一级",
                category_level2_name="二级",
                category_level3_name="三级",
                source_supplier_id=supplier_id,
                cost_price=Decimal("100.0000"),
                agreement_price=Decimal("160.0000"),
                discount_rate=Decimal("0.8000"),
                sales_volume=88,
                positive_rating=Decimal("0.9500"),
                purchasing_agent="张三",
                jd_price=Decimal("200.0000"),
                jd_self_operated_price=Decimal("180.0000"),
                created_by=created_by,
                updated_by=updated_by,
            )
        )
        await session.commit()
    return supplier_id, category_id, product_id


async def cleanup_fixture(
    supplier_id: uuid.UUID, category_id: uuid.UUID, product_id: uuid.UUID
) -> None:
    async with SessionLocal() as session:
        await session.execute(delete(Product).where(Product.id == product_id))
        await session.execute(
            delete(ProductPurgeAudit).where(ProductPurgeAudit.product_id == product_id)
        )
        await session.execute(delete(Category).where(Category.id == category_id))
        await session.execute(delete(Supplier).where(Supplier.id == supplier_id))
        await session.commit()


async def test_product_api_lists_details_and_updates_cost_independently() -> None:
    importer_id, headers = await create_product_user(PRODUCT_PERMISSIONS)
    updater_id, updater_headers = await create_product_user(("product:cost:update",))
    supplier_id, category_id, product_id = await create_product_fixture(
        created_by=importer_id, updated_by=importer_id
    )
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            listing = await client.get("/api/v1/products?keyword=成本价", headers=headers)
            assert listing.status_code == 200
            assert any(item["id"] == str(product_id) for item in listing.json()["data"]["items"])
            listed_product = next(
                item for item in listing.json()["data"]["items"] if item["id"] == str(product_id)
            )
            assert listed_product["image_reference"] == (
                "local-media/product-images/test-product.png"
            )
            assert listed_product["created_by"] == str(importer_id)
            assert listed_product["created_by_username"] == f"product-test-{importer_id}"
            assert listed_product["created_at"]
            assert listed_product["updated_by"] == str(importer_id)
            assert listed_product["updated_by_username"] == f"product-test-{importer_id}"
            assert listed_product["updated_at"]
            assert listed_product["company_name"] == "众诚测试公司"
            assert listed_product["sales_volume"] == 88

            filtered = await client.get(
                "/api/v1/products?company_name=众诚&supplier_name=商品测试"
                "&cost_price_min=99&cost_price_max=101&agreement_price_min=160"
                "&discount_rate_min=0.8&discount_rate_max=0.8"
                "&sales_volume_min=88&sales_volume_max=88",
                headers=headers,
            )
            assert filtered.status_code == 200
            assert str(product_id) in {item["id"] for item in filtered.json()["data"]["items"]}

            invalid_range = await client.get(
                "/api/v1/products?cost_price_min=200&cost_price_max=100", headers=headers
            )
            assert invalid_range.status_code == 422
            assert invalid_range.json()["code"] == "PRODUCT_FILTER_RANGE_INVALID"

            assert (
                await client.get(
                    "/api/v1/products?discount_rate_min=1&discount_rate_max=2",
                    headers=headers,
                )
            ).status_code == 200
            assert (
                await client.get(
                    "/api/v1/products?discount_rate_min=-1&discount_rate_max=0",
                    headers=headers,
                )
            ).status_code == 200
            invalid_discount_range = await client.get(
                "/api/v1/products?discount_rate_min=2&discount_rate_max=1", headers=headers
            )
            assert invalid_discount_range.status_code == 422
            assert invalid_discount_range.json()["code"] == "PRODUCT_FILTER_RANGE_INVALID"

            supplier_products = await client.get(
                f"/api/v1/products?source_supplier_id={supplier_id}", headers=headers
            )
            assert supplier_products.status_code == 200
            supplier_product_items = supplier_products.json()["data"]["items"]
            assert any(item["id"] == str(product_id) for item in supplier_product_items)
            assert {item["source_supplier_id"] for item in supplier_product_items} == {
                str(supplier_id)
            }

            detail = await client.get(f"/api/v1/products/{product_id}", headers=headers)
            assert detail.status_code == 200
            assert detail.json()["data"]["category_level1_name"] == "一级"
            assert detail.json()["data"]["category_level2_name"] == "二级"
            assert detail.json()["data"]["category_level3_name"] == "三级"

            updated = await client.patch(
                f"/api/v1/products/{product_id}/cost-price",
                headers=updater_headers,
                json={"cost_price": "120.0000"},
            )
            assert updated.status_code == 200
            data = updated.json()["data"]
            assert data["cost_price"] == "120.0000"
            assert data["market_price"] is None
            assert data["agreement_price"] == "160.0000"
            assert data["agreement_purchase_price"] is None
            assert data["profit"] is None
            assert data["discount_rate"] == "0.8000"
            assert data["deduction_rate"] is None

            refreshed_listing = await client.get("/api/v1/products?keyword=成本价", headers=headers)
            refreshed_product = next(
                item
                for item in refreshed_listing.json()["data"]["items"]
                if item["id"] == str(product_id)
            )
            assert refreshed_product["updated_by"] == str(updater_id)
            assert refreshed_product["updated_by_username"] == f"product-test-{updater_id}"

        async with SessionLocal() as session:
            stored = await session.get(Product, product_id)
            assert stored is not None
            assert stored.cost_price == Decimal("120.0000")
            assert stored.source_supplier_id == supplier_id
    finally:
        await cleanup_fixture(supplier_id, category_id, product_id)
        await cleanup_user(importer_id)
        await cleanup_user(updater_id)


async def test_product_api_filters_multiple_category_ids_as_a_union() -> None:
    user_id, headers = await create_product_user(PRODUCT_PERMISSIONS)
    supplier_id, first_category_id, first_product_id = await create_product_fixture()
    second_category_id, second_product_id = uuid.uuid4(), uuid.uuid4()
    try:
        async with SessionLocal() as session:
            session.add_all(
                [
                    Category(
                        id=second_category_id,
                        source_type="MALL_LEVEL3",
                        level1_name="另一一级",
                        level2_name="另一二级",
                        level3_name="另一三级",
                        level3_external_id=f"test-{second_category_id}",
                        deduction_rate=Decimal("0.0800"),
                    ),
                    Product(
                        id=second_product_id,
                        product_name="第二个类目商品",
                        sku="SKU-CATEGORY-SECOND",
                        source_supplier_id=supplier_id,
                        category_level1_name="另一一级",
                        category_level2_name="另一二级",
                        category_level3_name="另一三级",
                        cost_price=Decimal("200.0000"),
                    ),
                ]
            )
            await session.commit()

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            level1_options = await client.get(
                "/api/v1/products/category-filter-options",
                headers=headers,
                params={"level": "LEVEL1", "keyword": "一级"},
            )
            level3_options = await client.get(
                "/api/v1/products/category-filter-options",
                headers=headers,
                params={"level": "LEVEL3", "keyword": "另一三级"},
            )
            assert level1_options.status_code == 200
            assert level3_options.status_code == 200
            first_level1_key = next(
                item["selection_key"]
                for item in level1_options.json()["data"]["items"]
                if item["label"] == "一级"
            )
            second_level3_key = level3_options.json()["data"]["items"][0]["selection_key"]
            direct_selection = await client.get(
                "/api/v1/products",
                headers=headers,
                params=[
                    ("category_selections", first_level1_key),
                    ("category_selections", second_level3_key),
                ],
            )
            assert direct_selection.status_code == 200
            assert {str(first_product_id), str(second_product_id)}.issubset(
                {item["id"] for item in direct_selection.json()["data"]["items"]}
            )

            invalid_selection = await client.get(
                "/api/v1/products",
                headers=headers,
                params={"category_selections": "LEVEL3:not-a-selection-key"},
            )
            assert invalid_selection.status_code == 422
            assert invalid_selection.json()["code"] == "PRODUCT_CATEGORY_SELECTION_INVALID"
    finally:
        async with SessionLocal() as session:
            await session.execute(delete(Product).where(Product.id == second_product_id))
            await session.execute(delete(Category).where(Category.id == second_category_id))
            await session.commit()
        await cleanup_fixture(supplier_id, first_category_id, first_product_id)
        await cleanup_user(user_id)


async def test_product_category_options_are_derived_from_product_master_data() -> None:
    user_id, headers = await create_product_user(PRODUCT_PERMISSIONS)
    supplier_id, category_id, product_id = await create_product_fixture()
    master_only_product_id = uuid.uuid4()
    try:
        async with SessionLocal() as session:
            session.add(
                Product(
                    id=master_only_product_id,
                    product_name="只存在于商品主数据的类目商品",
                    sku="SKU-MASTER-CATEGORY",
                    source_supplier_id=supplier_id,
                    category_level1_name="主数据一级",
                    category_level2_name="主数据二级",
                    category_level3_name="主数据三级",
                    cost_price=Decimal("300.0000"),
                )
            )
            await session.commit()

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            options = await client.get(
                "/api/v1/products/category-filter-options",
                headers=headers,
                params={"level": "LEVEL3", "keyword": "主数据三级"},
            )
            assert options.status_code == 200
            option = options.json()["data"]["items"][0]
            assert option["label"] == "主数据一级 / 主数据二级 / 主数据三级"

            selected = await client.get(
                "/api/v1/products",
                headers=headers,
                params=[("category_selections", option["selection_key"])],
            )
            assert selected.status_code == 200
            assert str(master_only_product_id) in {
                item["id"] for item in selected.json()["data"]["items"]
            }
    finally:
        async with SessionLocal() as session:
            await session.execute(delete(Product).where(Product.id == master_only_product_id))
            await session.commit()
        await cleanup_fixture(supplier_id, category_id, product_id)
        await cleanup_user(user_id)


async def test_product_api_enforces_permissions_and_validates_paths() -> None:
    user_id, headers = await create_product_user(("product:cost:update",))
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            assert (await client.get("/api/v1/products")).status_code == 401
            forbidden = await client.get("/api/v1/products", headers=headers)
            assert forbidden.status_code == 403
            invalid_path = await client.patch(
                "/api/v1/products/not-a-uuid/cost-price",
                headers=headers,
                json={"cost_price": "1.0000"},
            )
            assert invalid_path.status_code == 422
    finally:
        await cleanup_user(user_id)


async def test_product_image_upload_and_clear_use_controlled_storage(monkeypatch) -> None:
    storage = RecordingStorage()
    monkeypatch.setattr(
        "app.modules.catalog.application.service.get_object_storage", lambda: storage
    )
    user_id, headers = await create_product_user(("product:update", "product:detail"))
    supplier_id, category_id, product_id = await create_product_fixture()
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            uploaded = await client.post(
                f"/api/v1/products/{product_id}/image",
                headers=headers,
                files={"file": ("product.png", b"png-content", "image/png")},
            )
            assert uploaded.status_code == 200
            reference = uploaded.json()["data"]["image_reference"]
            assert reference.startswith("local-media/product-images/manual/")
            assert "product-images/test-product.png" in storage.deleted

            cleared = await client.delete(f"/api/v1/products/{product_id}/image", headers=headers)
            assert cleared.status_code == 200
            assert cleared.json()["data"]["image_reference"] is None
            assert reference.removeprefix("local-media/") in storage.deleted
    finally:
        await cleanup_fixture(supplier_id, category_id, product_id)
        await cleanup_user(user_id)


async def test_product_disable_enable_and_purge_follow_lifecycle_rules() -> None:
    user_id, headers = await create_product_user(
        ("product:list", "product:detail", "product:disable", "product:purge")
    )
    supplier_id, category_id, product_id = await create_product_fixture()
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            forbidden = await client.delete(f"/api/v1/products/{product_id}")
            assert forbidden.status_code == 401

            active_purge = await client.request(
                "DELETE", f"/api/v1/products/{product_id}", headers=headers, json={"confirm": True}
            )
            assert active_purge.status_code == 409
            assert active_purge.json()["code"] == "PRODUCT_PURGE_REQUIRES_DISABLED"

            disabled = await client.post(
                f"/api/v1/products/{product_id}/commands/disable", headers=headers
            )
            assert disabled.status_code == 200
            assert disabled.json()["data"] == {"id": str(product_id), "status": "DISABLED"}

            listing = await client.get("/api/v1/products", headers=headers)
            assert listing.status_code == 200
            assert str(product_id) not in {item["id"] for item in listing.json()["data"]["items"]}
            hidden_detail = await client.get(f"/api/v1/products/{product_id}", headers=headers)
            assert hidden_detail.status_code == 404

            disabled_list = await client.get("/api/v1/products?status=DISABLED", headers=headers)
            assert disabled_list.status_code == 200
            assert str(product_id) in {item["id"] for item in disabled_list.json()["data"]["items"]}

            enabled = await client.post(
                f"/api/v1/products/{product_id}/commands/enable", headers=headers
            )
            assert enabled.status_code == 200
            assert enabled.json()["data"] == {"id": str(product_id), "status": "ACTIVE"}

            await client.post(f"/api/v1/products/{product_id}/commands/disable", headers=headers)
            purged = await client.request(
                "DELETE", f"/api/v1/products/{product_id}", headers=headers, json={"confirm": True}
            )
            assert purged.status_code == 200
            assert purged.json()["data"] == {"id": str(product_id), "status": "PURGED"}

        async with SessionLocal() as session:
            product = await session.get(Product, product_id)
            assert product is None
            audit = await session.scalar(
                select(ProductPurgeAudit).where(ProductPurgeAudit.product_id == product_id)
            )
            assert audit is not None
            assert audit.purged_by == user_id
    finally:
        await cleanup_fixture(supplier_id, category_id, product_id)
        await cleanup_user(user_id)


async def test_product_editing_and_supplier_lifecycle_visibility() -> None:
    user_id, headers = await create_product_user(PRODUCT_PERMISSIONS)
    supplier_id, category_id, product_id = await create_product_fixture()
    duplicate_id = uuid.uuid4()
    try:
        async with SessionLocal() as session:
            session.add(
                Product(
                    id=duplicate_id,
                    product_name="重复 SKU 参照商品",
                    sku="SKU-DUPLICATE",
                    source_supplier_id=supplier_id,
                    cost_price=Decimal("1.0000"),
                )
            )
            await session.commit()

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            candidates = await client.get(
                "/api/v1/products/source-supplier-candidates", headers=headers
            )
            assert candidates.status_code == 200
            assert str(supplier_id) in {item["id"] for item in candidates.json()["data"]}

            edited = await client.patch(
                f"/api/v1/products/{product_id}",
                headers=headers,
                json={
                    "product_name": "已编辑商品",
                    "selling_points": "编辑后的卖点",
                    "category_level1_name": "手工一级",
                    "category_level2_name": "手工二级",
                    "category_level3_name": "手工三级",
                },
            )
            assert edited.status_code == 200
            assert edited.json()["data"]["product_name"] == "已编辑商品"
            assert edited.json()["data"]["sku"] == "SKU-1"
            assert edited.json()["data"]["cost_price"] == "100.0000"

            above_one = await client.patch(
                f"/api/v1/products/{product_id}",
                headers=headers,
                json={
                    "discount_rate": "1.2000",
                    "category_level1_name": "手工一级",
                    "category_level2_name": "手工二级",
                    "category_level3_name": "手工三级",
                },
            )
            assert above_one.status_code == 200
            assert above_one.json()["data"]["discount_rate"] == "1.2000"
            below_zero = await client.patch(
                f"/api/v1/products/{product_id}",
                headers=headers,
                json={
                    "discount_rate": "-0.2000",
                    "category_level1_name": "手工一级",
                    "category_level2_name": "手工二级",
                    "category_level3_name": "手工三级",
                },
            )
            assert below_zero.status_code == 200
            assert below_zero.json()["data"]["discount_rate"] == "-0.2000"

            immutable_key_edit = await client.patch(
                f"/api/v1/products/{product_id}",
                headers=headers,
                json={"sku": "SKU-DUPLICATE", "source_supplier_id": str(supplier_id)},
            )
            assert immutable_key_edit.status_code == 422

        async with SessionLocal() as session:
            supplier = await session.get(Supplier, supplier_id)
            assert supplier is not None
            supplier.cooperation_status = "STOPPED"
            await session.commit()

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            hidden_list = await client.get(
                f"/api/v1/products?source_supplier_id={supplier_id}", headers=headers
            )
            assert hidden_list.status_code == 200
            assert str(product_id) not in {
                item["id"] for item in hidden_list.json()["data"]["items"]
            }
            assert (
                await client.get(f"/api/v1/products/{product_id}", headers=headers)
            ).status_code == 404
            assert (
                await client.patch(
                    f"/api/v1/products/{product_id}/cost-price",
                    headers=headers,
                    json={"cost_price": "120.0000"},
                )
            ).status_code == 404

        async with SessionLocal() as session:
            supplier = await session.get(Supplier, supplier_id)
            assert supplier is not None
            supplier.cooperation_status = "NORMAL"
            await session.commit()

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            restored = await client.get(f"/api/v1/products/{product_id}", headers=headers)
            assert restored.status_code == 200
    finally:
        async with SessionLocal() as session:
            await session.execute(delete(Product).where(Product.id == duplicate_id))
            await session.commit()
        await cleanup_fixture(supplier_id, category_id, product_id)
        await cleanup_user(user_id)
