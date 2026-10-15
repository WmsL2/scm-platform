"""MySQL-backed worker for bid/recommendation tasks.

Run one process per queue:
  python -m app.jobs.task_worker --queue heavy
  python -m app.jobs.task_worker --queue mapping
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import logging
from contextlib import suppress
from functools import partial
from uuid import UUID

from app.core.config import get_settings
from app.core.database import SessionLocal, close_database
from app.infrastructure.adapters import get_object_storage
from app.integrations.deepseek.client import DeepSeekClient
from app.jobs.recommendation_agent import (
    execute_ppt_recommendation_agent_inline,
    execute_recommendation_agent_inline,
)
from app.modules.bid.application.service import BidProjectService
from app.modules.bid.infrastructure.models import BidProject, BidProjectFile, BidTemplate, MatchTask
from app.modules.matching.application.service import MatchingService
from app.modules.matching.application.type1_agent import Type1Agent
from app.modules.matching.application.type2_agent import Type2Agent
from app.modules.recommendation.application.ppt_service import PptSolutionService
from app.modules.recommendation.infrastructure.models import PptGenerationTask, RecommendationRun
from app.modules.system.mapping_analysis_service import MappingAnalysisService
from app.modules.system.models import AsyncTask
from app.modules.system.task_schemas import AsyncTaskKind
from app.modules.system.task_service import AsyncTaskService
from app.modules.type3_recommendation.application.agent import execute_type3_agent_inline
from app.modules.type3_recommendation.application.service import Type3RecommendationService
from app.modules.type3_recommendation.infrastructure.models import Type3Run
from app.modules.type3_recommendation.schemas import Type3TemplatePreview

logger = logging.getLogger(__name__)

_HEAVY_KINDS = {
    AsyncTaskKind.TYPE1_MATCH,
    AsyncTaskKind.TYPE2_MATCH,
    AsyncTaskKind.TYPE3_CANDIDATE_GENERATION,
    AsyncTaskKind.TYPE4_RECOMMENDATION_AGENT,
    AsyncTaskKind.TYPE5_RECOMMENDATION_GENERATION,
    AsyncTaskKind.TYPE5_PPT_GENERATION,
}


async def _heartbeat(task_id: UUID, attempt: int, stop: asyncio.Event) -> None:
    seconds = get_settings().task_heartbeat_seconds
    while not await _wait_or_stop(stop, seconds):
        try:
            async with SessionLocal() as session:
                await AsyncTaskService(session).heartbeat(
                    task_id, percent=5, message="任务执行中", attempt=attempt
                )
        except Exception as exc:
            logger.warning(
                "task heartbeat failed: task_id=%s error=%s", task_id, type(exc).__name__
            )


async def _wait_or_stop(stop: asyncio.Event, seconds: int) -> bool:
    try:
        await asyncio.wait_for(stop.wait(), timeout=seconds)
    except TimeoutError:
        return False
    return True


class DomainTaskFailed(RuntimeError):
    """A handler handled its own exception but recorded a failed domain state."""


async def execute(task: AsyncTask) -> None:
    kind = AsyncTaskKind(task.task_kind)
    if kind in {AsyncTaskKind.TYPE1_MATCH, AsyncTaskKind.TYPE2_MATCH}:
        async with SessionLocal() as session:
            service = MatchingService(
                session,
                type1_agent=Type1Agent(DeepSeekClient()),
                type2_agent=Type2Agent(DeepSeekClient()),
            )
            handler = (
                service._run_type1_ai_matching
                if kind is AsyncTaskKind.TYPE1_MATCH
                else (service._run_type2_ai_matching)
            )
            await handler(task.project_id, task.created_by, task.run_id)
        return
    if kind is AsyncTaskKind.TYPE3_CANDIDATE_GENERATION:
        if task.run_id is None:
            raise RuntimeError("TYPE3 task is missing run_id")
        async with SessionLocal() as session:
            await execute_type3_agent_inline(task.run_id, Type3RecommendationService(session))
        return
    if kind is AsyncTaskKind.TYPE4_RECOMMENDATION_AGENT:
        if task.run_id is None:
            raise RuntimeError("TYPE4 task is missing run_id")
        async with SessionLocal() as session:
            await execute_recommendation_agent_inline(task.run_id, session)
        return
    if kind is AsyncTaskKind.TYPE5_RECOMMENDATION_GENERATION:
        if task.run_id is None:
            raise RuntimeError("TYPE5 task is missing run_id")
        if task.payload_json.get("retry_plans"):
            async with SessionLocal() as session:
                await PptSolutionService(session).create_ai_generated_plans(
                    task.run_id, DeepSeekClient()
                )
            async with SessionLocal.begin() as session:
                run = await session.get(RecommendationRun, task.run_id)
                if run:
                    run.error = None
        else:
            await execute_ppt_recommendation_agent_inline(task.run_id)
        return
    if kind is AsyncTaskKind.TYPE5_PPT_GENERATION:
        generation_task_id = task.payload_json.get("ppt_generation_task_id")
        if not isinstance(generation_task_id, str):
            raise RuntimeError("TYPE5 PPT task is missing ppt_generation_task_id")
        async with SessionLocal() as session:
            await PptSolutionService(session).execute_generation(UUID(generation_task_id))
        return
    if kind is AsyncTaskKind.MAPPING_STRUCTURE_ANALYSIS:
        await _execute_mapping(task)
        return
    raise RuntimeError(f"unsupported task kind {kind}")


async def _execute_mapping(task: AsyncTask) -> None:
    """Run blocking openpyxl reads only in the dedicated mapping process."""
    payload = task.payload_json
    analysis_type = payload.get("analysis_type")
    file_id = payload.get("file_id")
    if not isinstance(analysis_type, str) or not isinstance(file_id, str):
        raise RuntimeError("mapping task payload is incomplete")
    async with SessionLocal.begin() as session:
        await MappingAnalysisService(session).mark_running(task.id)
    async with SessionLocal() as session:
        file = await session.get(BidProjectFile, UUID(file_id))
        if file is None or file.project_id != task.project_id:
            raise RuntimeError("mapping file no longer belongs to project")
        storage_key, expected_sha = file.storage_key, file.sha256
        sheet_name = payload.get("sheet_name")
        header_row = payload.get("header_row", 1)
        if analysis_type == "BID_OUTPUT_HEADERS" and not (
            isinstance(sheet_name, str) and isinstance(payload.get("header_row"), int)
        ):
            # Older queued tasks predate explicit Sheet/header cache keys.
            project = await session.get(BidProject, task.project_id)
            template = (
                await session.get(BidTemplate, project.template_id)
                if (project and project.template_id)
                else None
            )
            if template is None:
                raise RuntimeError("project template missing")
            sheet_name, header_row = template.sheet_name, template.header_row
    # DB session/locks are closed before storage and workbook I/O. Running the
    # parser in this process's thread also keeps its heartbeat loop responsive.
    content = await get_object_storage().read(storage_key)
    if await asyncio.to_thread(lambda: hashlib.sha256(content).hexdigest()) != expected_sha:
        raise RuntimeError("mapping file digest mismatch")
    result_json: dict[str, object]
    if analysis_type == "TYPE3_TEMPLATE_PREVIEW":
        sheets = await asyncio.to_thread(Type3RecommendationService._inspect, content)
        result_json = Type3TemplatePreview(
            template_file_id=UUID(file_id), sheets=sheets
        ).model_dump(mode="json")
    elif analysis_type == "TYPE3_SHEET_OUTPUT":
        if not isinstance(sheet_name, str) or not isinstance(header_row, int):
            raise RuntimeError("type3 sheet analysis payload is incomplete")
        result = await asyncio.to_thread(
            Type3RecommendationService.inspect_sheet_output, content, sheet_name, header_row
        )
        result_json = result.model_dump(mode="json")
    elif analysis_type == "BID_OUTPUT_HEADERS":
        assert isinstance(sheet_name, str) and isinstance(header_row, int)
        headers = await asyncio.to_thread(
            BidProjectService._workbook_headers, content, sheet_name, header_row
        )
        result_json = {"headers": headers}
    elif analysis_type == "RECOMMENDATION_TEMPLATE_STRUCTURE":
        from app.modules.recommendation.template.analyzer import inspect_template_structure
        from app.modules.recommendation.template.schemas import (
            RecommendationTemplateStructureResponse,
        )

        structure = await asyncio.to_thread(
            partial(
                inspect_template_structure,
                content,
                sheet_name=str(sheet_name) if sheet_name else None,
                header_row=int(str(header_row)),
            )
        )
        result_json = RecommendationTemplateStructureResponse.model_validate(
            structure, from_attributes=True
        ).model_dump(mode="json")
    else:
        raise RuntimeError(f"unsupported mapping analysis {analysis_type}")
    async with SessionLocal.begin() as session:
        current = await session.get(AsyncTask, task.id, with_for_update=True)
        if current and current.status == "RUNNING" and current.attempt_count == task.attempt_count:
            await MappingAnalysisService(session).succeed(task.id, result_json)


async def _assert_domain_succeeded(task: AsyncTask) -> None:
    """Do not report queue success when a legacy runner persisted a failure itself."""
    kind = AsyncTaskKind(task.task_kind)
    async with SessionLocal() as session:
        if kind in {AsyncTaskKind.TYPE1_MATCH, AsyncTaskKind.TYPE2_MATCH}:
            match = await session.get(MatchTask, task.run_id) if task.run_id else None
            if match is None or match.status != "COMPLETED":
                raise DomainTaskFailed("匹配任务未完成或已失败")
        elif kind is AsyncTaskKind.TYPE3_CANDIDATE_GENERATION:
            assert task.run_id is not None
            type3_run = await session.get(Type3Run, task.run_id)
            if type3_run is None or type3_run.status not in {
                "WAITING_CONFIRMATION",
                "CONFIRMED",
                "EXPORTED",
                "NO_CANDIDATES",
            }:
                raise DomainTaskFailed("类型 3 候选生成失败")
        elif kind in {
            AsyncTaskKind.TYPE4_RECOMMENDATION_AGENT,
            AsyncTaskKind.TYPE5_RECOMMENDATION_GENERATION,
        }:
            assert task.run_id is not None
            recommendation_run = await session.get(RecommendationRun, task.run_id)
            if (
                recommendation_run is None
                or recommendation_run.error
                or (
                    recommendation_run.status
                    not in {
                        "WAITING_CONFIRMATION",
                        "CANDIDATES_READY",
                        "CONFIRMED",
                        "EXPORTED",
                        "NO_CANDIDATES",
                    }
                )
            ):
                raise DomainTaskFailed("推荐任务未生成可继续处理的结果")
        elif kind is AsyncTaskKind.TYPE5_PPT_GENERATION:
            value = task.payload_json.get("ppt_generation_task_id")
            assert isinstance(value, str)
            generation = await session.get(PptGenerationTask, UUID(value))
            if generation is None or generation.status != "SUCCEEDED":
                raise DomainTaskFailed("PPT 生成任务未成功")


async def run_once(kinds: set[AsyncTaskKind], task_id: UUID | None = None) -> bool:
    async with SessionLocal() as session:
        task = await AsyncTaskService(session).claim_next(kinds, task_id)
    if task is None:
        return False
    stop = asyncio.Event()
    heartbeat = asyncio.create_task(_heartbeat(task.id, task.attempt_count, stop))
    try:
        async with SessionLocal() as session:
            await AsyncTaskService(session).heartbeat(
                task.id, percent=5, message="正在执行任务", attempt=task.attempt_count
            )
        await execute(task)
        await _assert_domain_succeeded(task)
    except Exception as exc:
        logger.exception("async task failed: task_id=%s kind=%s", task.id, task.task_kind)
        async with SessionLocal() as session:
            await AsyncTaskService(session).fail(
                task.id,
                code="TASK_EXECUTION_FAILED",
                message=f"任务执行失败（{type(exc).__name__}），请重试或查看服务端日志。",
                attempt=task.attempt_count,
            )
    else:
        async with SessionLocal() as session:
            await AsyncTaskService(session).succeed(task.id, attempt=task.attempt_count)
    finally:
        stop.set()
        heartbeat.cancel()
        with suppress(asyncio.CancelledError):
            await heartbeat
    return True


async def worker(queue: str) -> None:
    kinds = _HEAVY_KINDS if queue == "heavy" else {AsyncTaskKind.MAPPING_STRUCTURE_ANALYSIS}
    concurrency = (
        get_settings().task_worker_concurrency
        if queue == "heavy"
        else get_settings().mapping_parse_concurrency
    )
    logger.info("task worker started: queue=%s concurrency=%s", queue, concurrency)
    try:
        while True:
            try:
                async with SessionLocal() as session:
                    recovered = await AsyncTaskService(session).recover_stale()
                if recovered:
                    logger.warning("recovered %s stale task(s)", len(recovered))
                results = await asyncio.gather(
                    *(run_once(kinds) for _ in range(concurrency)), return_exceptions=True
                )
                for result in results:
                    if isinstance(result, BaseException):
                        logger.warning(
                            "worker slot failed: queue=%s error=%s", queue, type(result).__name__
                        )
                if not any(result is True for result in results):
                    await asyncio.sleep(0.5)
            except Exception as exc:
                logger.warning(
                    "worker polling failed: queue=%s error=%s", queue, type(exc).__name__
                )
                await asyncio.sleep(1)
    finally:
        await close_database()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queue", choices=("heavy", "mapping"), default="heavy")
    parser.add_argument("--once", action="store_true", help="Process at most one task then exit")
    parser.add_argument("--task-id", type=UUID, help="With --once, only claim this task")
    args = parser.parse_args()
    if args.task_id and not args.once:
        parser.error("--task-id requires --once")
    logging.basicConfig(level=logging.INFO)
    if args.once:

        async def once() -> None:
            try:
                kinds = (
                    _HEAVY_KINDS
                    if args.queue == "heavy"
                    else {AsyncTaskKind.MAPPING_STRUCTURE_ANALYSIS}
                )
                await run_once(kinds, args.task_id)
            finally:
                await close_database()

        asyncio.run(once())
    else:
        asyncio.run(worker(args.queue))


if __name__ == "__main__":
    main()
