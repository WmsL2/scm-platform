import uuid

from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select

from app.core.database import SessionLocal
from app.main import app
from app.modules.auth.security import create_token, hash_password
from app.modules.bid.infrastructure.models import BidProject
from app.modules.catalog.infrastructure.models import Product
from app.modules.supplier.infrastructure.models import Supplier
from app.modules.system.models import Permission, Role, RolePermission, User, UserRole


async def create_dashboard_user() -> tuple[uuid.UUID, dict[str, str]]:
    user_id = uuid.uuid4()
    async with SessionLocal() as session:
        session.add(
            User(
                id=user_id,
                username=f"dashboard-test-{user_id}",
                password_hash=hash_password("secret"),
            )
        )
        await session.commit()
    return user_id, {"Authorization": f"Bearer {create_token(user_id, 1)}"}


async def test_dashboard_summary_counts_formal_products_and_normal_suppliers() -> None:
    user_id, headers = await create_dashboard_user()
    normal_supplier_id = uuid.uuid4()
    stopped_supplier_id = uuid.uuid4()
    deleted_supplier_id = uuid.uuid4()
    disabled_product_id = uuid.uuid4()
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            unauthorized = await client.get("/api/v1/dashboard/summary")
            assert unauthorized.status_code == 401

            before = await client.get("/api/v1/dashboard/summary", headers=headers)
            assert before.status_code == 200
            before_data = before.json()["data"]

        async with SessionLocal() as session:
            session.add_all(
                [
                    Supplier(
                        id=normal_supplier_id,
                        supplier_code=f"DST{str(normal_supplier_id)[:8]}",
                        supplier_name=f"统计正常归档供应商-{normal_supplier_id}",
                        main_brands="测试",
                        advantage="测试",
                        archive_status="ARCHIVED",
                        cooperation_status="NORMAL",
                    ),
                    Supplier(
                        id=stopped_supplier_id,
                        supplier_code=f"DST{str(stopped_supplier_id)[:8]}",
                        supplier_name=f"统计停止归档供应商-{stopped_supplier_id}",
                        main_brands="测试",
                        advantage="测试",
                        archive_status="ARCHIVED",
                        cooperation_status="STOPPED",
                    ),
                    Supplier(
                        id=deleted_supplier_id,
                        supplier_code=f"DST{str(deleted_supplier_id)[:8]}",
                        supplier_name=f"统计已删除归档供应商-{deleted_supplier_id}",
                        main_brands="测试",
                        advantage="测试",
                        archive_status="ARCHIVED",
                        cooperation_status="NORMAL",
                        is_deleted=True,
                    ),
                ]
            )
            await session.flush()
            session.add_all(
                [
                    Product(
                        id=uuid.uuid4(),
                        product_name="统计正式商品",
                        sku=f"DASH-{normal_supplier_id}",
                        source_supplier_id=normal_supplier_id,
                        cost_price="1.0000",
                    ),
                    Product(
                        id=uuid.uuid4(),
                        product_name="统计停止供应商商品",
                        sku=f"DASH-{stopped_supplier_id}",
                        source_supplier_id=stopped_supplier_id,
                        cost_price="1.0000",
                    ),
                    Product(
                        id=disabled_product_id,
                        product_name="统计停用商品",
                        sku=f"DASH-{disabled_product_id}",
                        source_supplier_id=normal_supplier_id,
                        cost_price="1.0000",
                        status="DISABLED",
                    ),
                ]
            )
            await session.commit()

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            after = await client.get("/api/v1/dashboard/summary", headers=headers)
            assert after.status_code == 200
            after_data = after.json()["data"]
            assert after_data["formal_product_count"] == before_data["formal_product_count"] + 1
            assert after_data["normal_supplier_count"] == before_data["normal_supplier_count"] + 1
            assert after_data["active_project_count"] == before_data["active_project_count"]
            assert after_data["pending_supplier_count"] == before_data["pending_supplier_count"]
            assert after_data["recent_projects"] == []
    finally:
        async with SessionLocal() as session:
            await session.execute(
                delete(Product).where(
                    Product.source_supplier_id.in_(
                        (normal_supplier_id, stopped_supplier_id, deleted_supplier_id)
                    )
                )
            )
            await session.execute(
                delete(Supplier).where(
                    Supplier.id.in_((normal_supplier_id, stopped_supplier_id, deleted_supplier_id))
                )
            )
            await session.execute(delete(User).where(User.id == user_id))
            await session.commit()


async def test_dashboard_summary_includes_active_and_recent_projects() -> None:
    user_id, headers = await create_dashboard_user()
    role_id = uuid.uuid4()
    active_project_id = uuid.uuid4()
    failed_project_id = uuid.uuid4()
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            before = await client.get("/api/v1/dashboard/summary", headers=headers)
            assert before.status_code == 200
            before_data = before.json()["data"]

        async with SessionLocal() as session:
            permission_id = await session.scalar(
                select(Permission.id).where(Permission.permission_code == "bid:list")
            )
            assert permission_id is not None
            session.add(
                Role(
                    id=role_id,
                    role_code=f"dashboard-bid-{str(role_id)[:8]}",
                    role_name="工作台项目测试角色",
                )
            )
            await session.flush()
            session.add_all(
                [
                    UserRole(user_id=user_id, role_id=role_id),
                    RolePermission(role_id=role_id, permission_id=permission_id),
                ]
            )
            session.add_all(
                [
                    BidProject(
                        id=active_project_id,
                        project_code=f"DASH-A-{str(active_project_id)[:8]}",
                        project_name="工作台进行中项目",
                        buyer_name="测试需求方",
                        status="SELECTING",
                        project_type="FREE_RECOMMENDATION",
                        import_status="NOT_REQUIRED",
                        created_by=user_id,
                    ),
                    BidProject(
                        id=failed_project_id,
                        project_code=f"DASH-F-{str(failed_project_id)[:8]}",
                        project_name="工作台导入失败项目",
                        buyer_name="测试需求方",
                        status="WON",
                        project_type="FILTER_RECOMMENDATION",
                        import_status="FAILED",
                        created_by=user_id,
                    ),
                ]
            )
            await session.commit()

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            after = await client.get("/api/v1/dashboard/summary", headers=headers)
            assert after.status_code == 200
            after_data = after.json()["data"]
            assert after_data["active_project_count"] == before_data["active_project_count"] + 1
            recent_ids = {item["id"] for item in after_data["recent_projects"]}
            assert str(active_project_id) in recent_ids
            assert str(failed_project_id) in recent_ids
    finally:
        async with SessionLocal() as session:
            await session.execute(
                delete(BidProject).where(BidProject.id.in_((active_project_id, failed_project_id)))
            )
            await session.execute(delete(RolePermission).where(RolePermission.role_id == role_id))
            await session.execute(delete(UserRole).where(UserRole.role_id == role_id))
            await session.execute(delete(Role).where(Role.id == role_id))
            await session.execute(delete(User).where(User.id == user_id))
            await session.commit()
