from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.contracts import AppError, PageParams
from app.core.config import get_settings
from app.core.transaction import transaction_scope
from app.modules.bid.infrastructure.models import BidProject, BidProjectEvent
from app.modules.system.models import AsyncTask
from app.modules.system.task_domain import finish_domain, prepare_retry
from app.modules.system.task_schemas import (
    AsyncTaskCreate,
    AsyncTaskKind,
    AsyncTaskResponse,
    AsyncTaskStatus,
)

_HEAVY_KINDS = frozenset(
    kind for kind in AsyncTaskKind if kind != AsyncTaskKind.MAPPING_STRUCTURE_ANALYSIS
)
_ACTIVE_STATUSES = (AsyncTaskStatus.PENDING.value, AsyncTaskStatus.RUNNING.value)


class AsyncTaskService:
    """Own durable queue state; handlers retain their domain-specific writes."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def enqueue(self, request: AsyncTaskCreate) -> AsyncTaskResponse:
        async with transaction_scope(self.session):
            project = await self.ensure_available(request.project_id, request.task_kind)
            payload = self._safe_payload(request.payload_json)
            if request.task_kind in {AsyncTaskKind.TYPE1_MATCH, AsyncTaskKind.TYPE2_MATCH}:
                payload["restore_project_status"] = project.status
            task = AsyncTask(
                project_id=request.project_id,
                run_id=request.run_id
                or (
                    uuid4()
                    if request.task_kind in {AsyncTaskKind.TYPE1_MATCH, AsyncTaskKind.TYPE2_MATCH}
                    else None
                ),
                task_kind=request.task_kind.value,
                status=AsyncTaskStatus.PENDING.value,
                payload_json=payload,
                max_attempts=request.max_attempts,
                created_by=request.created_by,
            )
            self.session.add(task)
            await self.session.flush()
            self.session.add(
                BidProjectEvent(
                    project_id=project.id,
                    actor_id=request.created_by,
                    event_type="ASYNC_TASK_ENQUEUED",
                    from_status=project.status,
                    to_status=project.status,
                    note=f"{task.task_kind} 任务 {task.id} 已排队",
                )
            )
            await self.session.refresh(task)
        return self._response(task)

    async def ensure_available(
        self, project_id: UUID, kind: AsyncTaskKind, *, exclude_task_id: UUID | None = None
    ) -> BidProject:
        project = await self.session.scalar(
            select(BidProject).where(BidProject.id == project_id).with_for_update()
        )
        if project is None:
            raise AppError("BID_PROJECT_NOT_FOUND", "投标项目不存在", 404)
        if kind in _HEAVY_KINDS:
            conditions = [
                AsyncTask.project_id == project_id,
                AsyncTask.status.in_(_ACTIVE_STATUSES),
                AsyncTask.task_kind.in_([value.value for value in _HEAVY_KINDS]),
            ]
            if exclude_task_id:
                conditions.append(AsyncTask.id != exclude_task_id)
            active = await self.session.scalar(
                select(AsyncTask).where(*conditions).limit(1).with_for_update()
            )
            if active:
                raise AppError(
                    "ASYNC_TASK_ALREADY_ACTIVE",
                    f"项目已有进行中的任务（{active.id}，{active.status}），请等待完成后重试",
                    409,
                )
        return project

    async def get(self, task_id: UUID) -> AsyncTaskResponse:
        task = await self.session.get(AsyncTask, task_id)
        if task is None:
            raise AppError("ASYNC_TASK_NOT_FOUND", "异步任务不存在", 404)
        return self._response(task)

    async def list_for_project(
        self, project_id: UUID, page: PageParams
    ) -> tuple[list[AsyncTaskResponse], int]:
        statement = (
            select(AsyncTask)
            .where(AsyncTask.project_id == project_id)
            .order_by(
                case((AsyncTask.status.in_(_ACTIVE_STATUSES), 0), else_=1),
                AsyncTask.created_at.desc(),
                AsyncTask.id.desc(),
            )
        )
        total = int(
            await self.session.scalar(
                select(func.count())
                .select_from(AsyncTask)
                .where(AsyncTask.project_id == project_id)
            )
            or 0
        )
        rows = list(
            (
                await self.session.scalars(
                    statement.offset((page.page - 1) * page.page_size).limit(page.page_size)
                )
            ).all()
        )
        return [self._response(row) for row in rows], total

    async def latest_for_projects(self, project_ids: list[UUID]) -> dict[UUID, AsyncTaskResponse]:
        if not project_ids:
            return {}
        ranked = (
            select(
                AsyncTask.id,
                func.row_number()
                .over(
                    partition_by=AsyncTask.project_id,
                    order_by=(
                        case((AsyncTask.status.in_(_ACTIVE_STATUSES), 0), else_=1),
                        AsyncTask.created_at.desc(),
                        AsyncTask.id.desc(),
                    ),
                )
                .label("position"),
            )
            .where(AsyncTask.project_id.in_(project_ids))
            .subquery()
        )
        tasks = (
            await self.session.scalars(
                select(AsyncTask)
                .join(ranked, ranked.c.id == AsyncTask.id)
                .where(ranked.c.position == 1)
            )
        ).all()
        return {task.project_id: self._response(task) for task in tasks}

    async def cancel(self, task_id: UUID) -> AsyncTaskResponse:
        async with transaction_scope(self.session):
            await self._lock_project_for_task(task_id)
            task = await self._task_for_update(task_id)
            if task.status != AsyncTaskStatus.PENDING.value:
                raise AppError("ASYNC_TASK_CANCEL_NOT_ALLOWED", "只能取消尚未执行的任务", 409)
            task.status = AsyncTaskStatus.CANCELLED.value
            task.completed_at = self._now()
            task.progress_message = "任务已取消"
            await finish_domain(self.session, task, "任务已取消", cancelled=True)
        return self._response(task)

    async def retry(self, task_id: UUID) -> AsyncTaskResponse:
        async with transaction_scope(self.session):
            await self._lock_project_for_task(task_id)
            task = await self._task_for_update(task_id)
            if task.status != AsyncTaskStatus.FAILED.value:
                raise AppError("ASYNC_TASK_RETRY_NOT_ALLOWED", "只能重试失败任务", 409)
            if task.attempt_count >= task.max_attempts:
                raise AppError("ASYNC_TASK_RETRY_EXHAUSTED", "任务已达到最大重试次数", 409)
            project = await self.ensure_available(
                task.project_id, AsyncTaskKind(task.task_kind), exclude_task_id=task.id
            )
            if task.task_kind in {"TYPE1_MATCH", "TYPE2_MATCH"} and project.status not in {
                "IMPORTED",
                "SELECTING",
                "READY",
            }:
                raise AppError("ASYNC_TASK_RETRY_NOT_ALLOWED", "当前项目状态不能重试匹配", 409)
            if task.task_kind == "TYPE5_PPT_GENERATION" and project.status not in {
                "READY",
                "EXPORTED",
            }:
                raise AppError("ASYNC_TASK_RETRY_NOT_ALLOWED", "请先完成选品再重试 PPT", 409)
            if project.status in {"READY", "EXPORTED", "SUBMITTED", "WON", "LOST", "VOIDED"} and (
                task.task_kind
                not in {
                    "TYPE1_MATCH",
                    "TYPE2_MATCH",
                    "TYPE5_PPT_GENERATION",
                    "MAPPING_STRUCTURE_ANALYSIS",
                }
            ):
                raise AppError("ASYNC_TASK_RETRY_NOT_ALLOWED", "请先返回待选品状态再重试", 409)
            await prepare_retry(self.session, task)
            task.status = AsyncTaskStatus.PENDING.value
            task.error_code = None
            task.error_message = None
            task.progress_percent = 0
            task.progress_message = "等待重试"
            task.lease_expires_at = None
            task.heartbeat_at = None
            task.started_at = None
            task.completed_at = None
        return self._response(task)

    async def claim_next(
        self, kinds: set[AsyncTaskKind], task_id: UUID | None = None
    ) -> AsyncTask | None:
        """Claim one row in a short transaction using MySQL SKIP LOCKED."""
        async with transaction_scope(self.session):
            conditions = [
                AsyncTask.status == AsyncTaskStatus.PENDING.value,
                AsyncTask.task_kind.in_([kind.value for kind in kinds]),
            ]
            if task_id is not None:
                conditions.append(AsyncTask.id == task_id)
            task = await self.session.scalar(
                select(AsyncTask)
                .where(*conditions)
                .order_by(AsyncTask.created_at, AsyncTask.id)
                .limit(1)
                .with_for_update(skip_locked=True)
            )
            if task is None:
                return None
            now = self._now()
            task.status = AsyncTaskStatus.RUNNING.value
            task.attempt_count += 1
            task.started_at = now
            task.heartbeat_at = now
            task.lease_expires_at = now + timedelta(seconds=get_settings().task_lease_seconds)
            task.progress_percent = max(task.progress_percent, 1)
            task.progress_message = "任务已领取，正在执行"
            await self.session.flush()
            await self.session.refresh(task)
            return task

    async def heartbeat(
        self, task_id: UUID, *, percent: int, message: str, attempt: int | None = None
    ) -> None:
        async with transaction_scope(self.session):
            task = await self._task_for_update(task_id)
            if task.status != AsyncTaskStatus.RUNNING.value or (
                attempt is not None and task.attempt_count != attempt
            ):
                return
            now = self._now()
            task.heartbeat_at = now
            task.lease_expires_at = now + timedelta(seconds=get_settings().task_lease_seconds)
            task.progress_percent = min(99, max(task.progress_percent, percent))
            task.progress_message = message[:500]

    async def succeed(
        self, task_id: UUID, message: str = "任务完成", *, attempt: int | None = None
    ) -> None:
        async with transaction_scope(self.session):
            await self._lock_project_for_task(task_id)
            task = await self._task_for_update(task_id)
            if task.status != AsyncTaskStatus.RUNNING.value or (
                attempt is not None and task.attempt_count != attempt
            ):
                return
            task.status = AsyncTaskStatus.SUCCEEDED.value
            task.progress_percent = 100
            task.progress_message = message[:500]
            task.completed_at = self._now()
            task.lease_expires_at = None
            self.session.add(
                BidProjectEvent(
                    project_id=task.project_id,
                    actor_id=task.created_by,
                    event_type="ASYNC_TASK_SUCCEEDED",
                    note=f"任务 {task.id} 已完成",
                )
            )

    async def fail(
        self, task_id: UUID, *, code: str, message: str, attempt: int | None = None
    ) -> None:
        async with transaction_scope(self.session):
            await self._lock_project_for_task(task_id)
            task = await self._task_for_update(task_id)
            if task.status not in _ACTIVE_STATUSES or (
                attempt is not None and task.attempt_count != attempt
            ):
                return
            task.status = AsyncTaskStatus.FAILED.value
            task.error_code = code[:64]
            task.error_message = message[:2000]
            task.progress_message = "任务失败"
            task.completed_at = self._now()
            task.lease_expires_at = None
            await finish_domain(self.session, task, message[:2000])

    async def recover_stale(self) -> list[AsyncTask]:
        """Make expired work visible as a failed terminal task; never silently re-run AI."""
        async with transaction_scope(self.session):
            now = self._now()
            ids = list(
                (
                    await self.session.scalars(
                        select(AsyncTask.id)
                        .where(
                            AsyncTask.status == AsyncTaskStatus.RUNNING.value,
                            AsyncTask.lease_expires_at.is_not(None),
                            AsyncTask.lease_expires_at < now,
                        )
                        .limit(100)
                        .order_by(AsyncTask.project_id, AsyncTask.id)
                    )
                ).all()
            )
            rows: list[AsyncTask] = []
            for task_id in ids:
                await self._lock_project_for_task(task_id)
                task = await self._task_for_update(task_id)
                if (
                    task.status != "RUNNING"
                    or not task.lease_expires_at
                    or (task.lease_expires_at >= now)
                ):
                    continue
                await self.fail(
                    task.id, code="TASK_LEASE_EXPIRED", message="任务心跳已过期，请重试"
                )
                rows.append(task)
            return rows

    async def _lock_project_for_task(self, task_id: UUID) -> None:
        project_id = await self.session.scalar(
            select(AsyncTask.project_id).where(AsyncTask.id == task_id)
        )
        if project_id is None:
            raise AppError("ASYNC_TASK_NOT_FOUND", "异步任务不存在", 404)
        await self.session.scalar(
            select(BidProject).where(BidProject.id == project_id).with_for_update()
        )

    async def _task_for_update(self, task_id: UUID) -> AsyncTask:
        task = await self.session.scalar(
            select(AsyncTask)
            .where(AsyncTask.id == task_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if task is None:
            raise AppError("ASYNC_TASK_NOT_FOUND", "异步任务不存在", 404)
        return task

    @staticmethod
    def _safe_payload(payload: dict[str, object]) -> dict[str, object]:
        allowed = {
            "restore_project_status",
            "cache_key",
            "analysis_type",
            "file_id",
            "sheet_name",
            "header_row",
            "ppt_generation_task_id",
            "retry_plans",
        }
        return {
            key: value
            for key, value in payload.items()
            if key in allowed and isinstance(value, (str, int, bool, type(None)))
        }

    @staticmethod
    def _now() -> datetime:
        return datetime.now(UTC).replace(tzinfo=None)

    @staticmethod
    def _response(task: AsyncTask) -> AsyncTaskResponse:
        return AsyncTaskResponse(
            id=task.id,
            project_id=task.project_id,
            run_id=task.run_id,
            task_kind=AsyncTaskKind(task.task_kind),
            status=AsyncTaskStatus(task.status),
            progress_percent=task.progress_percent,
            progress_message=task.progress_message,
            attempt_count=task.attempt_count,
            max_attempts=task.max_attempts,
            error_code=task.error_code,
            error_message=task.error_message,
            lease_expires_at=task.lease_expires_at,
            heartbeat_at=task.heartbeat_at,
            started_at=task.started_at,
            completed_at=task.completed_at,
            created_by=task.created_by,
            created_at=task.created_at,
            updated_at=task.updated_at,
        )
