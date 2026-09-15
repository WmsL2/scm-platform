# ruff: noqa: E501, E701, E702
import uuid
from decimal import Decimal
from io import BytesIO

from httpx import ASGITransport, AsyncClient
from openpyxl import Workbook, load_workbook
from sqlalchemy import delete, event, select

from app.common.contracts import AppError
from app.core.database import SessionLocal
from app.main import app
from app.modules.auth.security import create_token, hash_password
from app.modules.catalog.application.category_service import CategoryService
from app.modules.catalog.infrastructure.models import Category
from app.modules.system.models import Permission, Role, RolePermission, User, UserRole

HEADERS = ("一级类目ID", "一级类目名称", "二级类目ID", "二级类目名称", "三级类目ID", "三级类目名称", "有效标记", "上下柜标记", "主营事业部")

async def auth() -> tuple[uuid.UUID, dict[str, str]]:
    uid, rid = uuid.uuid4(), uuid.uuid4()
    async with SessionLocal() as s:
        ps = list((await s.scalars(select(Permission).where(Permission.permission_code.in_(("product:list", "product:update", "product:import"))))).all())
        s.add_all([User(id=uid, username=f"cat-{uid}", password_hash=hash_password("test")), Role(id=rid, role_code=f"cat-{rid}", role_name="cat"), UserRole(user_id=uid, role_id=rid), *[RolePermission(role_id=rid, permission_id=p.id) for p in ps]])
        await s.commit()
    return uid, {"Authorization": f"Bearer {create_token(uid, 1)}"}

def row(ident: object, active: object = 1) -> dict[str, object]: return dict(zip(HEADERS, ("1", "一级", "2", "二级", ident, f"三级{ident}", active, "", ""), strict=True))
def book(rows: list[dict[str, object]], headers: tuple[str, ...] = HEADERS) -> bytes:
    wb = Workbook(); ws = wb.active; assert ws; ws.append(headers)
    for item in rows: ws.append([item.get(h) for h in headers])
    out = BytesIO(); wb.save(out); return out.getvalue()
async def post(c: AsyncClient, h: dict[str, str], content: bytes, rate: str = "8"):
    return await c.post("/api/v1/categories/imports", headers=h, data={"deduction_rate_percent": rate}, files={"file": ("categories.xlsx", content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
async def clean(uid: uuid.UUID) -> None:
    async with SessionLocal() as s:
        await s.execute(delete(Category).where(Category.level3_external_id.like("cat-test-%")))
        rids = list((await s.scalars(select(UserRole.role_id).where(UserRole.user_id == uid))).all()); await s.execute(delete(RolePermission).where(RolePermission.role_id.in_(rids))); await s.execute(delete(UserRole).where(UserRole.user_id == uid)); await s.execute(delete(Role).where(Role.id.in_(rids))); await s.execute(delete(User).where(User.id == uid)); await s.commit()

async def test_category_import_chinese_template_and_rates() -> None:
    uid, h = await auth()
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            template = await c.get("/api/v1/categories/imports/template", headers=h); ws = load_workbook(BytesIO(template.content)).active; assert ws and tuple(x.value for x in ws[1]) == HEADERS and ws.freeze_panes == "A2"
            for suffix, rate, expected in (("1", "5", "0.0500"), ("2", "8", "0.0800"), ("3", "7.5", "0.0750"), ("4", "6.25", "0.0625")):
                assert (await post(c, h, book([row("cat-test-" + suffix)]), rate)).status_code == 200
                async with SessionLocal() as s: assert (await s.scalar(select(Category.deduction_rate).where(Category.level3_external_id == "cat-test-" + suffix))) == Decimal(expected)
            assert (await post(c, h, book([row("cat-test-5", "是"), row("cat-test-6", "否")]))).status_code == 200
            for rate in ("6.255", "-1", "100.01", "101", "abc", "NaN", "Infinity"):
                assert (await post(c, h, book([row("cat-test-bad" + rate.replace(".", ""))]), rate)).status_code == 422
    finally: await clean(uid)

async def test_category_import_headers_identity_skip_and_ids() -> None:
    uid, h = await auth()
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            assert (await post(c, h, book([row("cat-test-00123")], tuple(reversed(HEADERS))))).status_code == 200
            duplicate = await post(c, h, book([row("cat-test-dup"), row("cat-test-dup")]))
            assert duplicate.json()["data"]["errors"][0]["field"] == "level3_external_id"
            assert (await post(c, h, book([row(123.45)]))).json()["data"]["failed"] == 1
            assert (await post(c, h, book([row("cat-test-skip")]))).status_code == 200
            assert (await post(c, h, book([row("cat-test-skip")]))).json()["data"]["skipped"] == 1
            assert (await post(c, h, book([row("cat-test-skip")]), "5")).json()["data"]["failed"] == 1
            for bad in (HEADERS[:-1], HEADERS + ("测试",), HEADERS[:-1] + ("三级类目ID",)):
                assert (await post(c, h, book([row("cat-test-header")], bad))).status_code == 422
    finally: await clean(uid)

async def test_category_import_write_failure_rolls_back_all_rows() -> None:
    uid, _ = await auth()
    try:
        async with SessionLocal() as session:
            injected = False
            def inject(sync: object, *_: object) -> None:
                nonlocal injected
                if not injected:
                    injected = True
                    sync.add(Category(source_type="MALL_LEVEL3", level1_name="一级", level2_name="二级", level3_name="冲突", level3_external_id="cat-test-r2", deduction_rate=Decimal("0.0800")))  # type: ignore[attr-defined]
            event.listen(session.sync_session, "before_flush", inject)
            try:
                try: await CategoryService(session).import_xlsx("rollback.xlsx", book([row("cat-test-r1"), row("cat-test-r2")]), "8", uid)
                except AppError as exc: assert exc.code == "CATEGORY_IMPORT_CONFLICT"
            finally: event.remove(session.sync_session, "before_flush", inject)
        async with SessionLocal() as session:
            remaining = list((await session.scalars(select(Category.id).where(Category.level3_external_id.in_(("cat-test-r1", "cat-test-r2"))))).all())
            assert remaining == []
    finally: await clean(uid)
