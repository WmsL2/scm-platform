# ruff: noqa: E501
from __future__ import annotations

import uuid
from io import BytesIO
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Depends, Query, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.contracts import ApiResponse, PageParams, success
from app.core.database import FunctionSessionDep, SessionLocal, get_db_session
from app.modules.auth.dependencies import require_permission, require_permission_before_response
from app.modules.auth.schemas import CurrentUser
from app.modules.bid.schemas import BidProjectFileResponse
from app.modules.system.mapping_analysis_service import MappingAnalysisService
from app.modules.system.task_schemas import AsyncTaskCreate, AsyncTaskKind, AsyncTaskResponse
from app.modules.system.task_service import AsyncTaskService
from app.modules.type3_recommendation.application.service import Type3RecommendationService
from app.modules.type3_recommendation.schemas import (
    Type3CandidateConfirmationRequest,
    Type3CandidatePage,
    Type3CandidateSheetSummary,
    Type3CandidateUnconfirmationRequest,
    Type3ExportField,
    Type3RunResponse,
    Type3SheetOutputStructure,
    Type3SheetPreview,
    Type3SheetSelectionRequest,
    Type3TemplatePreview,
)

router = APIRouter(prefix="/type3-recommendation-projects", tags=["type3-recommendation"])
SessionDep = Annotated[AsyncSession, Depends(get_db_session, scope="function")]


@router.get(
    "/{project_id}/template-preview",
    response_model=ApiResponse[Type3TemplatePreview | AsyncTaskResponse],
    status_code=status.HTTP_202_ACCEPTED,
)
async def template_preview(
    project_id: uuid.UUID,
    current: Annotated[CurrentUser, Depends(require_permission("recommendation:detail"))],
    session: SessionDep,
    response: Response,
) -> ApiResponse[Type3TemplatePreview | AsyncTaskResponse]:
    service = Type3RecommendationService(session)
    file_id = await service.template_file_id(project_id)
    result = await MappingAnalysisService(session).cached_or_enqueue(
        project_id=project_id,
        file_id=file_id,
        analysis_key="TYPE3_TEMPLATE_PREVIEW",
        payload_json={"analysis_type": "TYPE3_TEMPLATE_PREVIEW"},
        actor_id=current.user_id,
    )
    if isinstance(result, dict):
        response.status_code = status.HTTP_200_OK
        return success(Type3TemplatePreview.model_validate(result))
    return success(result)


@router.get(
    "/{project_id}/sheet-output-structure",
    response_model=ApiResponse[Type3SheetOutputStructure | AsyncTaskResponse],
    status_code=status.HTTP_202_ACCEPTED,
)
async def sheet_output_structure(
    project_id: uuid.UUID,
    sheet_name: str,
    header_row: Annotated[int, Query(ge=1)],
    current: Annotated[CurrentUser, Depends(require_permission("recommendation:detail"))],
    session: SessionDep,
    response: Response,
) -> ApiResponse[Type3SheetOutputStructure | AsyncTaskResponse]:
    service = Type3RecommendationService(session)
    file_id = await service.template_file_id(project_id)
    result = await MappingAnalysisService(session).cached_or_enqueue(
        project_id=project_id,
        file_id=file_id,
        analysis_key=f"TYPE3_SHEET_OUTPUT:{sheet_name}:{header_row}",
        payload_json={
            "analysis_type": "TYPE3_SHEET_OUTPUT",
            "sheet_name": sheet_name,
            "header_row": header_row,
        },
        actor_id=current.user_id,
    )
    if isinstance(result, dict):
        response.status_code = status.HTTP_200_OK
        return success(Type3SheetOutputStructure.model_validate(result))
    return success(result)


@router.get(
    "/{project_id}/export-fields", response_model=ApiResponse[list[Type3ExportField]]
)
async def export_fields(
    project_id: uuid.UUID,
    _: Annotated[CurrentUser, Depends(require_permission("recommendation:detail"))],
    session: SessionDep,
) -> ApiResponse[list[Type3ExportField]]:
    return success(await Type3RecommendationService(session).available_export_fields(project_id))


@router.get(
    "/{project_id}/sheet-selections", response_model=ApiResponse[list[Type3SheetPreview]]
)
async def saved_sheet_selections(
    project_id: uuid.UUID,
    _: Annotated[CurrentUser, Depends(require_permission("recommendation:detail"))],
    session: SessionDep,
) -> ApiResponse[list[Type3SheetPreview]]:
    return success(await Type3RecommendationService(session).saved_sheet_selections(project_id))


@router.put(
    "/{project_id}/sheet-selections", response_model=ApiResponse[list[Type3SheetPreview]]
)
async def save_sheet_selections(
    project_id: uuid.UUID,
    payload: Type3SheetSelectionRequest,
    current: Annotated[CurrentUser, Depends(require_permission("recommendation:create"))],
    session: FunctionSessionDep,
) -> ApiResponse[list[Type3SheetPreview]]:
    return success(
        await Type3RecommendationService(session).save_sheet_selection(
            project_id, payload, current.user_id
        )
    )


@router.post(
    "/{project_id}/runs",
    response_model=ApiResponse[AsyncTaskResponse],
    status_code=status.HTTP_202_ACCEPTED,
)
async def start(
    project_id: uuid.UUID,
    payload: Type3SheetSelectionRequest,
    current: Annotated[CurrentUser, Depends(require_permission("recommendation:run"))],
) -> ApiResponse[AsyncTaskResponse]:
    # Persist the posted selection and create its Run in the same committed transaction.
    # The inline executor therefore can never observe a previous Sheet configuration.
    async with SessionLocal.begin() as create_session:
        await AsyncTaskService(create_session).ensure_available(
            project_id, AsyncTaskKind.TYPE3_CANDIDATE_GENERATION
        )
        run = await Type3RecommendationService(create_session).save_and_start(
            project_id, payload, current.user_id
        )
        task = await AsyncTaskService(create_session).enqueue(
            AsyncTaskCreate(
                project_id=project_id,
                run_id=run.id,
                task_kind=AsyncTaskKind.TYPE3_CANDIDATE_GENERATION,
                created_by=current.user_id,
            )
        )
    return success(task)


@router.get("/{project_id}/runs", response_model=ApiResponse[list[Type3RunResponse]])
async def runs(
    project_id: uuid.UUID,
    _: Annotated[CurrentUser, Depends(require_permission("recommendation:detail"))],
    session: SessionDep,
) -> ApiResponse[list[Type3RunResponse]]:
    return success(await Type3RecommendationService(session).list_runs(project_id))


@router.get("/runs/{run_id}", response_model=ApiResponse[Type3RunResponse])
async def run(
    run_id: uuid.UUID,
    _: Annotated[CurrentUser, Depends(require_permission("recommendation:detail"))],
    session: SessionDep,
) -> ApiResponse[Type3RunResponse]:
    return success(await Type3RecommendationService(session).get_run(run_id))


@router.get("/runs/{run_id}/candidates", response_model=ApiResponse[Type3CandidatePage])
async def candidates(
    run_id: uuid.UUID,
    page: Annotated[PageParams, Depends()],
    _: Annotated[CurrentUser, Depends(require_permission("recommendation:detail"))],
    session: SessionDep,
    sheet_name: str | None = None,
) -> ApiResponse[Type3CandidatePage]:
    return success(await Type3RecommendationService(session).candidates(run_id, sheet_name, page))


@router.get(
    "/runs/{run_id}/candidate-sheets",
    response_model=ApiResponse[list[Type3CandidateSheetSummary]],
)
async def candidate_sheets(
    run_id: uuid.UUID,
    _: Annotated[CurrentUser, Depends(require_permission("recommendation:detail"))],
    session: SessionDep,
) -> ApiResponse[list[Type3CandidateSheetSummary]]:
    return success(await Type3RecommendationService(session).candidate_sheets(run_id))


@router.post("/candidates/confirm", response_model=ApiResponse[bool])
async def confirm(
    candidate_ids: list[uuid.UUID],
    current: Annotated[CurrentUser, Depends(require_permission("recommendation:review"))],
    session: SessionDep,
) -> ApiResponse[bool]:
    await Type3RecommendationService(session).confirm(candidate_ids, current.user_id)
    return success(True)


@router.post("/runs/{run_id}/candidate-confirmations", response_model=ApiResponse[int])
async def confirm_candidates(
    run_id: uuid.UUID,
    payload: Type3CandidateConfirmationRequest,
    current: Annotated[CurrentUser, Depends(require_permission("recommendation:review"))],
    session: SessionDep,
) -> ApiResponse[int]:
    return success(
        await Type3RecommendationService(session).confirm_candidates(
            run_id, payload, current.user_id
        )
    )


@router.post("/runs/{run_id}/candidate-unconfirmations", response_model=ApiResponse[int])
async def unconfirm_candidates(
    run_id: uuid.UUID,
    payload: Type3CandidateUnconfirmationRequest,
    current: Annotated[CurrentUser, Depends(require_permission("recommendation:review"))],
    session: SessionDep,
) -> ApiResponse[int]:
    return success(
        await Type3RecommendationService(session).unconfirm_candidates(
            run_id, payload, current.user_id
        )
    )


@router.post(
    "/{project_id}/runs/{run_id}/commands/complete-selection",
    response_model=ApiResponse[bool],
)
async def complete_selection(
    project_id: uuid.UUID,
    run_id: uuid.UUID,
    current: Annotated[CurrentUser, Depends(require_permission("recommendation:review"))],
    session: SessionDep,
) -> ApiResponse[bool]:
    await Type3RecommendationService(session).complete_selection(project_id, run_id, current.user_id)
    return success(True)


@router.post(
    "/{project_id}/runs/{run_id}/commands/reopen-selection",
    response_model=ApiResponse[bool],
)
async def reopen_selection(
    project_id: uuid.UUID,
    run_id: uuid.UUID,
    current: Annotated[CurrentUser, Depends(require_permission("recommendation:review"))],
    session: SessionDep,
) -> ApiResponse[bool]:
    await Type3RecommendationService(session).reopen_selection(project_id, run_id, current.user_id)
    return success(True)


@router.post(
    "/{project_id}/runs/{run_id}/exports", response_model=ApiResponse[BidProjectFileResponse]
)
async def export(
    project_id: uuid.UUID,
    run_id: uuid.UUID,
    current: Annotated[
        CurrentUser, Depends(require_permission_before_response("recommendation:export"))
    ],
    session: FunctionSessionDep,
) -> ApiResponse[BidProjectFileResponse]:
    return success(
        await Type3RecommendationService(session).export(project_id, run_id, current.user_id)
    )


@router.get("/runs/{run_id}/exports/{file_id}/download")
async def download(
    run_id: uuid.UUID,
    file_id: uuid.UUID,
    _: Annotated[CurrentUser, Depends(require_permission("recommendation:export"))],
    session: SessionDep,
) -> StreamingResponse:
    file, content = await Type3RecommendationService(session).download(run_id, file_id)
    return StreamingResponse(
        BytesIO(content),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename=\"type3-export.xlsx\"; filename*=UTF-8''{quote(file.original_filename, safe='')}"
        },
    )
