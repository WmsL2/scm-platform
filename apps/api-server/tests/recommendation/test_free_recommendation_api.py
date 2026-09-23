from __future__ import annotations

import hashlib
import uuid
from io import BytesIO

import pytest
from httpx import ASGITransport, AsyncClient
from openpyxl import Workbook
from sqlalchemy import delete, func, select

from app.core.database import SessionLocal
from app.infrastructure.adapters import get_object_storage
from app.main import app
from app.modules.auth.security import create_token, hash_password
from app.modules.bid.infrastructure.models import (
    BidProject,
    BidProjectEvent,
    BidProjectFile,
    BidProjectItem,
)
from app.modules.recommendation.template.models import RecommendationTemplateMapping
from app.modules.system.models import Permission, Role, RolePermission, User, UserRole


def _xlsx(headers: list[str] | None = None) -> bytes:
    workbook = Workbook()
    workbook.active.title = "推荐清单"
    workbook.active.append(headers or ["品牌", "名称", "毛利"])
    output = BytesIO()
    workbook.save(output)
    workbook.close()
    return output.getvalue()


async def _user(codes: tuple[str, ...]) -> tuple[uuid.UUID, uuid.UUID, dict[str, str]]:
    user_id, role_id = uuid.uuid4(), uuid.uuid4()
    async with SessionLocal() as session:
        permissions = list(
            (
                await session.scalars(
                    select(Permission).where(Permission.permission_code.in_(codes))
                )
            ).all()
        )
        assert len(permissions) == len(codes)
        session.add_all(
            [
                User(
                    id=user_id,
                    username=f"recommendation-api-{user_id}",
                    password_hash=hash_password("secret"),
                ),
                Role(
                    id=role_id,
                    role_code=f"recommendation-api-{role_id}",
                    role_name="recommendation api",
                ),
                UserRole(user_id=user_id, role_id=role_id),
                *[RolePermission(role_id=role_id, permission_id=item.id) for item in permissions],
            ]
        )
        await session.commit()
    return user_id, role_id, {"Authorization": f"Bearer {create_token(user_id, 1)}"}


async def _cleanup(user_id: uuid.UUID, role_id: uuid.UUID, projects: list[uuid.UUID]) -> None:
    async with SessionLocal() as session:
        files = list(
            (
                await session.scalars(
                    select(BidProjectFile).where(BidProjectFile.project_id.in_(projects))
                )
            ).all()
        )
        file_ids = [item.id for item in files]
        await session.execute(
            delete(RecommendationTemplateMapping).where(
                RecommendationTemplateMapping.project_id.in_(projects)
            )
        )
        await session.execute(
            delete(BidProjectEvent).where(BidProjectEvent.project_id.in_(projects))
        )
        await session.execute(delete(BidProjectItem).where(BidProjectItem.project_id.in_(projects)))
        await session.execute(delete(BidProjectFile).where(BidProjectFile.id.in_(file_ids)))
        await session.execute(delete(BidProject).where(BidProject.id.in_(projects)))
        await session.execute(delete(RolePermission).where(RolePermission.role_id == role_id))
        await session.execute(delete(UserRole).where(UserRole.user_id == user_id))
        await session.execute(delete(Role).where(Role.id == role_id))
        await session.execute(delete(User).where(User.id == user_id))
        await session.commit()
    storage = get_object_storage()
    for item in files:
        await storage.delete(item.storage_key)


async def _create_free(
    client: AsyncClient, headers: dict[str, str], name: str, content: bytes
) -> dict[str, object]:
    response = await client.post(
        "/api/v1/bid-projects",
        headers=headers,
        data={
            "project_type": "FREE_RECOMMENDATION",
            "project_name": name,
            "buyer_name": "集成测试客户",
            "remark": "这是至少二十个字符的自由推品真实接口集成测试需求说明",
        },
        files={
            "recommendation_template": (
                "recommendation.xlsx",
                content,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


@pytest.mark.asyncio
async def test_free_recommendation_router_mysql_contracts() -> None:
    user_id, role_id, headers = await _user(
        ("bid:create", "bid:list", "bid:detail", "recommendation:create")
    )
    projects: list[uuid.UUID] = []
    first, second = _xlsx(), _xlsx(["品牌", "名称", "京东价"])
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            created = await _create_free(client, headers, "自由推品A", first)
            project_id = uuid.UUID(str(created["id"]))
            projects.append(project_id)
            assert created["project_type"] == "FREE_RECOMMENDATION"
            assert created["import_status"] == "NOT_REQUIRED"
            listed = await client.get("/api/v1/bid-projects", headers=headers)
            assert any(
                row["id"] == str(project_id) and row["project_type"] == "FREE_RECOMMENDATION"
                for row in listed.json()["data"]["items"]
            )
            detail = await client.get(f"/api/v1/bid-projects/{project_id}", headers=headers)
            assert detail.json()["data"]["project_type"] == "FREE_RECOMMENDATION"
            async with SessionLocal() as session:
                project = await session.get(BidProject, project_id)
                assert (
                    project
                    and project.project_type == "FREE_RECOMMENDATION"
                    and project.import_status == "NOT_REQUIRED"
                )
                assert (
                    await session.scalar(
                        select(func.count())
                        .select_from(BidProjectItem)
                        .where(BidProjectItem.project_id == project_id)
                    )
                    == 0
                )
                v1 = await session.scalar(
                    select(BidProjectFile).where(
                        BidProjectFile.project_id == project_id, BidProjectFile.version_no == 1
                    )
                )
                assert (
                    v1
                    and v1.file_type == "RECOMMENDATION_TEMPLATE"
                    and v1.sha256 == hashlib.sha256(first).hexdigest()
                )
                v1_mapping = await session.scalar(
                    select(RecommendationTemplateMapping).where(
                        RecommendationTemplateMapping.template_file_id == v1.id
                    )
                )
                assert v1_mapping is not None
            v2_response = await client.post(
                f"/api/v1/bid-projects/{project_id}/recommendation-templates",
                headers=headers,
                files={
                    "recommendation_template": (
                        "v2.xlsx",
                        second,
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )
                },
            )
            assert v2_response.status_code == 200, v2_response.text
            assert v2_response.json()["data"]["version_no"] == 2
            templates = await client.get(
                f"/api/v1/bid-projects/{project_id}/recommendation-templates", headers=headers
            )
            assert [row["version_no"] for row in templates.json()["data"]] == [1, 2]
            file_id = uuid.UUID(templates.json()["data"][0]["id"])
            created_b = await _create_free(client, headers, "自由推品B", first)
            project_b_id = uuid.UUID(str(created_b["id"]))
            projects.append(project_b_id)
            async with SessionLocal() as session:
                original = await session.scalar(
                    select(RecommendationTemplateMapping).where(
                        RecommendationTemplateMapping.template_file_id == file_id
                    )
                )
                assert original is not None
                before = (
                    original.sheet_name,
                    original.header_row,
                    original.data_start_row,
                    original.mapping_json,
                    original.confirmed_by,
                    original.confirmed_at,
                )
            ownership_get = await client.get(
                f"/api/v1/bid-projects/{project_b_id}/recommendation-templates/{file_id}/mapping",
                headers=headers,
            )
            assert ownership_get.status_code == 404
            assert ownership_get.json()["code"] == "RECOMMENDATION_TEMPLATE_NOT_FOUND"
            ownership_patch = await client.patch(
                f"/api/v1/bid-projects/{project_b_id}/recommendation-templates/{file_id}/mapping",
                headers=headers,
                json={
                    "sheet_name": "推荐清单",
                    "header_row": 1,
                    "data_start_row": 2,
                    "mapping_json": {"brand": "品牌"},
                },
            )
            assert ownership_patch.status_code == 404
            invalid_payloads = [
                {
                    "sheet_name": "missing",
                    "header_row": 1,
                    "data_start_row": 2,
                    "mapping_json": {"brand": "品牌"},
                },
                {
                    "sheet_name": "推荐清单",
                    "header_row": 1,
                    "data_start_row": 1,
                    "mapping_json": {"brand": "品牌"},
                },
                {
                    "sheet_name": "推荐清单",
                    "header_row": 1,
                    "data_start_row": 2,
                    "mapping_json": {"brand": "不存在的测试列"},
                },
                {
                    "sheet_name": "推荐清单",
                    "header_row": 1,
                    "data_start_row": 2,
                    "mapping_json": {"password": "品牌"},
                },
                {
                    "sheet_name": "推荐清单",
                    "header_row": 1,
                    "data_start_row": 2,
                    "mapping_json": {"brand": "品牌"},
                    "confirmed_by": str(uuid.uuid4()),
                },
            ]
            for payload in invalid_payloads:
                invalid = await client.patch(
                    f"/api/v1/bid-projects/{project_id}/recommendation-templates/{file_id}/mapping",
                    headers=headers,
                    json=payload,
                )
                assert invalid.status_code == 422
            async with SessionLocal() as session:
                mapping = await session.scalar(
                    select(RecommendationTemplateMapping).where(
                        RecommendationTemplateMapping.template_file_id == file_id
                    )
                )
                assert mapping is not None
                assert (
                    mapping.sheet_name,
                    mapping.header_row,
                    mapping.data_start_row,
                    mapping.mapping_json,
                    mapping.confirmed_by,
                    mapping.confirmed_at,
                ) == before
            patched = await client.patch(
                f"/api/v1/bid-projects/{project_id}/recommendation-templates/{file_id}/mapping",
                headers=headers,
                json={
                    "sheet_name": "推荐清单",
                    "header_row": 1,
                    "data_start_row": 2,
                    "mapping_json": {"brand": "品牌", "product_name": "名称"},
                },
            )
            assert patched.status_code == 200, patched.text
            async with SessionLocal() as session:
                mapping = await session.scalar(
                    select(RecommendationTemplateMapping).where(
                        RecommendationTemplateMapping.template_file_id == file_id
                    )
                )
                assert mapping and mapping.mapping_json == {"brand": "品牌", "product_name": "名称"}
                assert mapping.confirmed_by == user_id and mapping.confirmed_at is not None
    finally:
        await _cleanup(user_id, role_id, projects)


@pytest.mark.asyncio
async def test_free_permission_and_filter_permission_regression() -> None:
    user_id, role_id, headers = await _user(("bid:create",))
    projects: list[uuid.UUID] = []
    content = _xlsx()
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            denied = await client.post(
                "/api/v1/bid-projects",
                headers=headers,
                data={
                    "project_type": "FREE_RECOMMENDATION",
                    "project_name": "拒绝",
                    "buyer_name": "客户",
                    "remark": "这是至少二十个字符的自由推品真实接口集成测试需求说明",
                },
                files={
                    "recommendation_template": (
                        "x.xlsx",
                        content,
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )
                },
            )
            assert denied.status_code == 403
            async with SessionLocal() as session:
                assert (
                    await session.scalar(
                        select(func.count())
                        .select_from(BidProject)
                        .where(BidProject.created_by == user_id)
                    )
                    == 0
                )
            filter_response = await client.post(
                "/api/v1/bid-projects",
                headers=headers,
                data={"project_name": "筛选回归", "buyer_name": "客户"},
                files={
                    "file": (
                        "buyer.xlsx",
                        content,
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )
                },
            )
            assert filter_response.status_code == 200, filter_response.text
            projects.append(uuid.UUID(filter_response.json()["data"]["id"]))
            async with SessionLocal() as session:
                permission = await session.scalar(
                    select(Permission).where(Permission.permission_code == "recommendation:create")
                )
                assert permission is not None
                session.add(RolePermission(role_id=role_id, permission_id=permission.id))
                await session.commit()
            created = await _create_free(client, headers, "补权成功", content)
            projects.append(uuid.UUID(str(created["id"])))
    finally:
        await _cleanup(user_id, role_id, projects)
