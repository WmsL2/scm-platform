import logging
import uuid
from io import BytesIO
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, BackgroundTasks, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.contracts import ApiResponse, success
from app.core.config import get_settings
from app.core.database import SessionLocal, get_db_session
from app.infrastructure.adapters import get_task_queue
from app.integrations.deepseek.client import DeepSeekClient
from app.modules.auth.dependencies import require_permission, require_permission_before_response
from app.modules.auth.schemas import CurrentUser
from app.modules.recommendation.application.ppt_service import PptSolutionService
from app.modules.recommendation.ppt_schemas import (
    PptGenerationCreateRequest,
    PptGenerationTaskResponse,
    PptPackageCreateRequest,
    PptPackageResponse,
    PptPriceBandAvailabilityResponse,
    PptRecommendationConfigResponse,
    PptRecommendationConfigUpdateRequest,
    PptSolutionPlanResponse,
    PptTemplateResponse,
)

router = APIRouter(prefix="/ppt-solution-projects", tags=["ppt-solution"])
SessionDep = Annotated[AsyncSession, Depends(get_db_session)]
logger = logging.getLogger(__name__)


@router.get(
    "/{project_id}/recommendation-config",
    response_model=ApiResponse[PptRecommendationConfigResponse | None],
)
async def get_recommendation_config(
    project_id: uuid.UUID,
    _: Annotated[CurrentUser, Depends(require_permission("recommendation:detail"))],
    session: SessionDep,
) -> ApiResponse[PptRecommendationConfigResponse | None]:
    return success(await PptSolutionService(session).config(project_id))


@router.put(
    "/{project_id}/recommendation-config",
    response_model=ApiResponse[PptRecommendationConfigResponse],
)
async def put_recommendation_config(
    project_id: uuid.UUID,
    payload: PptRecommendationConfigUpdateRequest,
    current: Annotated[CurrentUser, Depends(require_permission("recommendation:run"))],
    session: SessionDep,
) -> ApiResponse[PptRecommendationConfigResponse]:
    result = await PptSolutionService(session).save_config(project_id, payload, current.user_id)
    return success(result)


@router.get("/runs/{run_id}/plans", response_model=ApiResponse[list[PptSolutionPlanResponse]])
async def list_plans(
    run_id: uuid.UUID,
    _: Annotated[CurrentUser, Depends(require_permission("recommendation:detail"))],
    session: SessionDep,
) -> ApiResponse[list[PptSolutionPlanResponse]]:
    return success(await PptSolutionService(session).list_plans(run_id))


@router.post("/plans/{plan_id}/select", response_model=ApiResponse[PptSolutionPlanResponse])
async def select_plan(
    plan_id: uuid.UUID,
    current: Annotated[CurrentUser, Depends(require_permission("recommendation:review"))],
    session: SessionDep,
) -> ApiResponse[PptSolutionPlanResponse]:
    return success(await PptSolutionService(session).select_plan(plan_id, current.user_id))


@router.get(
    "/runs/{run_id}/plan-availability",
    response_model=ApiResponse[list[PptPriceBandAvailabilityResponse]],
)
async def get_plan_availability(
    run_id: uuid.UUID,
    _: Annotated[CurrentUser, Depends(require_permission("recommendation:detail"))],
    session: SessionDep,
) -> ApiResponse[list[PptPriceBandAvailabilityResponse]]:
    return success(await PptSolutionService(session).plan_availability(run_id))


@router.post(
    "/runs/{run_id}/commands/retry-plans", response_model=ApiResponse[list[PptSolutionPlanResponse]]
)
async def retry_incomplete_plans(
    run_id: uuid.UUID,
    _: Annotated[CurrentUser, Depends(require_permission("recommendation:run"))],
    session: SessionDep,
) -> ApiResponse[list[PptSolutionPlanResponse]]:
    """Retry only missing slots from this Run's immutable candidate snapshot."""
    return success(
        await PptSolutionService(session).create_ai_generated_plans(run_id, DeepSeekClient())
    )


@router.get("/runs/{run_id}/packages", response_model=ApiResponse[list[PptPackageResponse]])
async def list_packages(
    run_id: uuid.UUID,
    _: Annotated[CurrentUser, Depends(require_permission("recommendation:detail"))],
    session: SessionDep,
) -> ApiResponse[list[PptPackageResponse]]:
    return success(await PptSolutionService(session).list_packages(run_id))


@router.post("/runs/{run_id}/packages", response_model=ApiResponse[PptPackageResponse])
async def create_package(
    run_id: uuid.UUID,
    payload: PptPackageCreateRequest,
    current: Annotated[CurrentUser, Depends(require_permission("recommendation:review"))],
    session: SessionDep,
) -> ApiResponse[PptPackageResponse]:
    return success(
        await PptSolutionService(session).create_package(run_id, payload, current.user_id)
    )


@router.delete("/packages/{package_id}", response_model=ApiResponse[bool])
async def delete_package(
    package_id: uuid.UUID,
    current: Annotated[CurrentUser, Depends(require_permission("recommendation:review"))],
    session: SessionDep,
) -> ApiResponse[bool]:
    return success(await PptSolutionService(session).delete_package(package_id, current.user_id))


@router.post(
    "/{project_id}/runs/{run_id}/generations",
    response_model=ApiResponse[PptGenerationTaskResponse],
)
async def create_generation(
    project_id: uuid.UUID,
    run_id: uuid.UUID,
    payload: PptGenerationCreateRequest,
    current: Annotated[
        CurrentUser, Depends(require_permission_before_response("recommendation:export"))
    ],
    background_tasks: BackgroundTasks,
) -> ApiResponse[PptGenerationTaskResponse]:
    # Create with an independent transaction.  In local inline mode, a FastAPI
    # BackgroundTask can be cancelled after setting the task to RUNNING; that
    # leaves a permanently stuck task and no PPT download.  Local rendering is
    # deliberately synchronous here, while a real queue remains asynchronous.
    async with SessionLocal() as task_session:
        task = await PptSolutionService(task_session).create_generation(
            project_id,
            run_id,
            current.user_id,
            use_default_template=payload.use_default_template,
            template_code=payload.template_code,
        )
    if get_settings().task_mode == "inline":
        await _dispatch_generation(task.id)
    else:
        background_tasks.add_task(_dispatch_generation, task.id)
    return success(task)


@router.get("/templates", response_model=ApiResponse[list[PptTemplateResponse]])
async def list_templates(
    _: Annotated[CurrentUser, Depends(require_permission("recommendation:detail"))],
) -> ApiResponse[list[PptTemplateResponse]]:
    return success(PptSolutionService.list_templates())


async def _dispatch_generation(task_id: uuid.UUID) -> None:
    async with SessionLocal() as task_session:
        service = PptSolutionService(task_session)
        try:
            await get_task_queue().enqueue(service.execute_generation, task_id)
        except Exception as exc:
            # Do not leave a user-facing task queued forever when a background
            # dispatcher has been configured incorrectly.
            logger.exception("PPT generation dispatch failed: task_id=%s", task_id)
            await service.mark_generation_failed(
                task_id,
                f"PPT 后台任务派发失败（{type(exc).__name__}），请检查服务端任务配置。",
            )


@router.get(
    "/{project_id}/generations", response_model=ApiResponse[list[PptGenerationTaskResponse]]
)
async def list_generations(
    project_id: uuid.UUID,
    _: Annotated[CurrentUser, Depends(require_permission("recommendation:detail"))],
    session: SessionDep,
) -> ApiResponse[list[PptGenerationTaskResponse]]:
    return success(await PptSolutionService(session).list_generations(project_id))


@router.get("/generations/{task_id}/files/{file_id}/download")
async def download_generation(
    task_id: uuid.UUID,
    file_id: uuid.UUID,
    _: Annotated[CurrentUser, Depends(require_permission("recommendation:export"))],
    session: SessionDep,
) -> StreamingResponse:
    file, content = await PptSolutionService(session).download(task_id, file_id)
    disposition = (
        'attachment; filename="ppt-solution.pptx"; '
        f"filename*=UTF-8''{quote(file.original_filename, safe='')}"
    )
    return StreamingResponse(
        BytesIO(content),
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        headers={"Content-Disposition": disposition},
    )
