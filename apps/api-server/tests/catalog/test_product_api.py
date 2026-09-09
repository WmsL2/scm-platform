import uuid
from decimal import Decimal

from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select

from app.core.database import SessionLocal
from app.main import app
from app.modules.auth.security import create_token, hash_password
from app.modules.catalog.infrastructure.models import Category, Product
from app.modules.supplier.infrastructure.models import Supplier
from app.modules.system.models import Permission, Role, RolePermission, User, UserRole

PRODUCT_PERMISSIONS = ("product:list", "product:detail", "product:cost:update")


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


async def create_product_fixture() -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
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
                brand="测试品牌",
                model="MODEL-1",
                sku="SKU-1",
                category_id=category_id,
                source_supplier_id=supplier_id,
                cost_price=Decimal("100.0000"),
                jd_price=Decimal("200.0000"),
                jd_self_operated_price=Decimal("180.0000"),
            )
        )
        await session.commit()
    return supplier_id, category_id, product_id


async def cleanup_fixture(
    supplier_id: uuid.UUID, category_id: uuid.UUID, product_id: uuid.UUID
) -> None:
    async with SessionLocal() as session:
        await session.execute(delete(Product).where(Product.id == product_id))
        await session.execute(delete(Category).where(Category.id == category_id))
        await session.execute(delete(Supplier).where(Supplier.id == supplier_id))
        await session.commit()


async def test_product_api_lists_details_and_recalculates_cost_atomically() -> None:
    user_id, headers = await create_product_user(PRODUCT_PERMISSIONS)
    supplier_id, category_id, product_id = await create_product_fixture()
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            listing = await client.get("/api/v1/products?keyword=成本价", headers=headers)
            assert listing.status_code == 200
            assert any(item["id"] == str(product_id) for item in listing.json()["data"]["items"])

            detail = await client.get(f"/api/v1/products/{product_id}", headers=headers)
            assert detail.status_code == 200
            assert detail.json()["data"]["category"]["deduction_rate"] == "0.0500"

            updated = await client.patch(
                f"/api/v1/products/{product_id}/cost-price",
                headers=headers,
                json={"cost_price": "120.0000"},
            )
            assert updated.status_code == 200
            data = updated.json()["data"]
            assert data["cost_price"] == "120.0000"
            assert data["market_price"] == "210.0000"
            assert data["agreement_price"] == "144.0000"
            assert data["agreement_purchase_price"] == "136.8000"
            assert data["profit"] == "16.8000"
            assert data["deduction_rate"] == "0.0500"

        async with SessionLocal() as session:
            stored = await session.get(Product, product_id)
            assert stored is not None
            assert stored.cost_price == Decimal("120.0000")
            assert stored.source_supplier_id == supplier_id
    finally:
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
