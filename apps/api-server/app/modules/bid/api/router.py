import uuid
from datetime import datetime
from io import BytesIO
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, Query, Response, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.contracts import ApiResponse, AppError, PageParams, PageResult, success
from app.core.database import FunctionSessionDep, get_db_session
from app.integrations.deepseek.client import DeepSeekClient
from app.modules.auth.dependencies import require_permission, require_permission_before_response
from app.modules.auth.schemas import CurrentUser
from app.modules.bid.application.service import BidProjectService
from app.modules.bid.domain.lifecycle import (
    BidItemStatus,
    BidProjectStatus,
    BidProjectType,
    BidRecommendationType,
)
from app.modules.bid.schemas import (
    BidInputMappingResponse,
    BidInputMappingUpdateRequest,
    BidOutputMappingResponse,
    BidOutputMappingUpdateRequest,
    BidProjectCreateResponse,
    BidProjectDetailResponse,
    BidProjectFileResponse,
    BidProjectItemResponse,
    BidProjectListItem,
    BidProjectStatusResponse,
    BidProjectUpdateRequest,
    BidResultRequest,
    BidSubmitRequest,
    BidVoidRequest,
)
from app.modules.matching.application.type1_agent import Type1Agent
from app.modules.matching.application.type2_agent import Type2Agent
from app.modules.recommendation.template.schemas import (
    RecommendationTemplateFileResponse,
    RecommendationTemplateMappingResponse,
    RecommendationTemplateMappingUpdateRequest,
    RecommendationTemplateStructureResponse,
)
from app.modules.system.mapping_analysis_service import MappingAnalysisService
from app.modules.system.task_schemas import AsyncTaskResponse

router = APIRouter(prefix="/bid-projects", tags=["bid-projects"])
SessionDep = Annotated[AsyncSession, Depends(get_db_session)]


@router.post("", response_model=ApiResponse[BidProjectCreateResponse])
async def create_bid_project(
    project_name: Annotated[str, Form(min_length=1, max_length=255)],
    buyer_name: Annotated[str, Form(min_length=1, max_length=255)],
    current: Annotated[CurrentUser, Depends(require_permission("bid:create"))],
    session: SessionDep,
    file: Annotated[UploadFile | None, File()] = None,
    start_at: Annotated[datetime | None, Form()] = None,
    deadline_at: Annotated[datetime | None, Form()] = None,
    remark: Annotated[str | None, Form(max_length=5000)] = None,
    project_type: Annotated[BidProjectType, Form()] = BidProjectType.FILTER_RECOMMENDATION,
    recommendation_type: Annotated[BidRecommendationType | None, Form()] = None,
    recommendation_template: Annotated[UploadFile | None, File()] = None,
) -> ApiResponse[BidProjectCreateResponse]:
    if (
        project_type in {BidProjectType.FREE_RECOMMENDATION, BidProjectType.PPT_SOLUTION}
        and "recommendation:create" not in current.permissions
    ):
        raise AppError("AUTH_FORBIDDEN", "Permission denied", 403)
    return success(
        await BidProjectService(
            session,
            type1_agent=Type1Agent(DeepSeekClient()),
            type2_agent=Type2Agent(DeepSeekClient()),
        ).create(
            project_name=project_name,
            buyer_name=buyer_name,
            start_at=start_at,
            deadline_at=deadline_at,
            remark=remark,
            filename=(file.filename if file else None),
            file_bytes=(await file.read() if file else None),
            recommendation_template_filename=(
                recommendation_template.filename if recommendation_template else None
            ),
            recommendation_template_bytes=(
                await recommendation_template.read() if recommendation_template else None
            ),
            project_type=project_type,
            recommendation_type=recommendation_type,
            actor_id=current.user_id,
        )
    )


@router.get("", response_model=ApiResponse[PageResult[BidProjectListItem]])
async def list_bid_projects(
    _: Annotated[CurrentUser, Depends(require_permission("bid:list"))],
    session: SessionDep,
    page_params: Annotated[PageParams, Depends()],
    keyword: Annotated[str | None, Query(max_length=255)] = None,
    status: BidProjectStatus | None = None,
) -> ApiResponse[PageResult[BidProjectListItem]]:
    return success(
        await BidProjectService(session).list_projects(
            page_params,
            keyword=keyword,
            status=status,
        )
    )


@router.post(
    "/{project_id}/recommendation-templates",
    response_model=ApiResponse[RecommendationTemplateFileResponse],
)
async def upload_recommendation_template(
    project_id: uuid.UUID,
    recommendation_template: Annotated[UploadFile, File(...)],
    current: Annotated[CurrentUser, Depends(require_permission("recommendation:create"))],
    session: SessionDep,
) -> ApiResponse[RecommendationTemplateFileResponse]:
    return success(
        await BidProjectService(session).add_recommendation_template(
            project_id,
            recommendation_template.filename or "recommendation-template.xlsx",
            await recommendation_template.read(),
            current.user_id,
        )
    )


@router.get(
    "/{project_id}/recommendation-templates",
    response_model=ApiResponse[list[RecommendationTemplateFileResponse]],
)
async def list_recommendation_templates(
    project_id: uuid.UUID,
    _: Annotated[CurrentUser, Depends(require_permission("recommendation:create"))],
    session: SessionDep,
) -> ApiResponse[list[RecommendationTemplateFileResponse]]:
    return success(await BidProjectService(session).recommendation_templates(project_id))


@router.get(
    "/{project_id}/recommendation-templates/{file_id}/mapping",
    response_model=ApiResponse[RecommendationTemplateMappingResponse],
)
async def get_recommendation_template_mapping(
    project_id: uuid.UUID,
    file_id: uuid.UUID,
    _: Annotated[CurrentUser, Depends(require_permission("recommendation:create"))],
    session: SessionDep,
) -> ApiResponse[RecommendationTemplateMappingResponse]:
    return success(
        await BidProjectService(session).recommendation_template_mapping(project_id, file_id)
    )


@router.get(
    "/{project_id}/recommendation-templates/{file_id}/structure",
    response_model=ApiResponse[RecommendationTemplateStructureResponse | AsyncTaskResponse],
)
async def get_recommendation_template_structure(
    project_id: uuid.UUID,
    file_id: uuid.UUID,
    current: Annotated[CurrentUser, Depends(require_permission("recommendation:create"))],
    session: SessionDep,
    response: Response,
    sheet_name: Annotated[str | None, Query()] = None,
    header_row: Annotated[int, Query(ge=1)] = 1,
) -> ApiResponse[RecommendationTemplateStructureResponse | AsyncTaskResponse]:
    await BidProjectService(session).recommendation_template_mapping(project_id, file_id)
    result = await MappingAnalysisService(session).cached_or_enqueue(
        project_id=project_id,
        file_id=file_id,
        analysis_key=f"RECOMMENDATION_TEMPLATE_STRUCTURE:{sheet_name or ''}:{header_row}",
        payload_json={
            "analysis_type": "RECOMMENDATION_TEMPLATE_STRUCTURE",
            "sheet_name": sheet_name,
            "header_row": header_row,
        },
        actor_id=current.user_id,
    )
    if isinstance(result, dict):
        return success(RecommendationTemplateStructureResponse.model_validate(result))
    response.status_code = status.HTTP_202_ACCEPTED
    return success(result)


@router.patch(
    "/{project_id}/recommendation-templates/{file_id}/mapping",
    response_model=ApiResponse[RecommendationTemplateMappingResponse],
)
async def patch_recommendation_template_mapping(
    project_id: uuid.UUID,
    file_id: uuid.UUID,
    payload: RecommendationTemplateMappingUpdateRequest,
    current: Annotated[CurrentUser, Depends(require_permission("recommendation:create"))],
    session: SessionDep,
) -> ApiResponse[RecommendationTemplateMappingResponse]:
    return success(
        await BidProjectService(session).update_recommendation_template_mapping(
            project_id, file_id, payload, current.user_id
        )
    )


@router.get("/{project_id}", response_model=ApiResponse[BidProjectDetailResponse])
async def get_bid_project(
    project_id: uuid.UUID,
    _: Annotated[CurrentUser, Depends(require_permission("bid:detail"))],
    session: SessionDep,
) -> ApiResponse[BidProjectDetailResponse]:
    return success(await BidProjectService(session).get(project_id))


@router.get(
    "/{project_id}/input-mapping",
    response_model=ApiResponse[BidInputMappingResponse],
)
async def get_bid_input_mapping(
    project_id: uuid.UUID,
    _: Annotated[CurrentUser, Depends(require_permission("bid:detail"))],
    session: SessionDep,
    sheet_name: Annotated[str | None, Query()] = None,
    header_row: Annotated[int | None, Query(ge=1)] = None,
) -> ApiResponse[BidInputMappingResponse]:
    return success(
        await BidProjectService(session).input_mapping(
            project_id, sheet_name=sheet_name, header_row=header_row
        )
    )


@router.put(
    "/{project_id}/input-mapping",
    response_model=ApiResponse[BidInputMappingResponse],
)
async def put_bid_input_mapping(
    project_id: uuid.UUID,
    payload: BidInputMappingUpdateRequest,
    current: Annotated[CurrentUser, Depends(require_permission("bid:update"))],
    session: SessionDep,
) -> ApiResponse[BidInputMappingResponse]:
    return success(
        await BidProjectService(session).confirm_input_mapping(
            project_id, payload, current.user_id
        )
    )


@router.get(
    "/{project_id}/output-mapping",
    response_model=ApiResponse[BidOutputMappingResponse | AsyncTaskResponse],
    status_code=status.HTTP_202_ACCEPTED,
)
async def get_bid_output_mapping(
    project_id: uuid.UUID,
    current: Annotated[CurrentUser, Depends(require_permission("bid:detail"))],
    session: SessionDep,
    response: Response,
) -> ApiResponse[BidOutputMappingResponse | AsyncTaskResponse]:
    service = BidProjectService(session)
    file_id, sheet_name, header_row = await service.output_mapping_analysis_context(project_id)
    analysis = await MappingAnalysisService(session).cached_or_enqueue(
        project_id=project_id,
        file_id=file_id,
        analysis_key=f"BID_OUTPUT_HEADERS:{sheet_name}:{header_row}",
        payload_json={
            "analysis_type": "BID_OUTPUT_HEADERS",
            "sheet_name": sheet_name,
            "header_row": header_row,
        },
        actor_id=current.user_id,
    )
    if not isinstance(analysis, dict):
        return success(analysis)
    raw_headers = analysis.get("headers")
    if not isinstance(raw_headers, list) or not all(
        isinstance(value, str) or value is None for value in raw_headers
    ):
        raise AppError("MAPPING_ANALYSIS_INVALID", "回填表头缓存格式无效，请重试", 409)
    response.status_code = status.HTTP_200_OK
    return success(await service.output_mapping(project_id, headers=raw_headers))


@router.put(
    "/{project_id}/output-mapping",
    response_model=ApiResponse[BidOutputMappingResponse],
)
async def put_bid_output_mapping(
    project_id: uuid.UUID,
    payload: BidOutputMappingUpdateRequest,
    current: Annotated[CurrentUser, Depends(require_permission("bid:update"))],
    session: SessionDep,
) -> ApiResponse[BidOutputMappingResponse]:
    service = BidProjectService(session)
    file_id, sheet_name, header_row = await service.output_mapping_analysis_context(project_id)
    analysis = await MappingAnalysisService(session).cached_or_enqueue(
        project_id=project_id,
        file_id=file_id,
        analysis_key=f"BID_OUTPUT_HEADERS:{sheet_name}:{header_row}",
        payload_json={
            "analysis_type": "BID_OUTPUT_HEADERS",
            "sheet_name": sheet_name,
            "header_row": header_row,
        },
        actor_id=current.user_id,
    )
    if not isinstance(analysis, dict):
        raise AppError("MAPPING_ANALYSIS_PENDING", "客户原表结构正在解析，请稍后重新保存", 409)
    raw_headers = analysis.get("headers")
    if not isinstance(raw_headers, list) or not all(
        isinstance(value, str) or value is None for value in raw_headers
    ):
        raise AppError("MAPPING_ANALYSIS_INVALID", "回填表头缓存格式无效，请重试", 409)
    return success(
        await service.update_output_mapping(
            project_id, payload, current.user_id, headers=raw_headers
        )
    )


@router.patch("/{project_id}", response_model=ApiResponse[BidProjectDetailResponse])
async def update_bid_project(
    project_id: uuid.UUID,
    payload: BidProjectUpdateRequest,
    current: Annotated[CurrentUser, Depends(require_permission("bid:update"))],
    session: SessionDep,
) -> ApiResponse[BidProjectDetailResponse]:
    return success(await BidProjectService(session).update(project_id, payload, current.user_id))


@router.get("/{project_id}/items", response_model=ApiResponse[PageResult[BidProjectItemResponse]])
async def list_bid_project_items(
    project_id: uuid.UUID,
    _: Annotated[CurrentUser, Depends(require_permission("bid:detail"))],
    session: SessionDep,
    page_params: Annotated[PageParams, Depends()],
    status: BidItemStatus | None = None,
    keyword: Annotated[str | None, Query(max_length=255)] = None,
) -> ApiResponse[PageResult[BidProjectItemResponse]]:
    return success(
        await BidProjectService(session).items(
            project_id, page_params, status=status, keyword=keyword
        )
    )


@router.get("/{project_id}/files", response_model=ApiResponse[list[BidProjectFileResponse]])
async def list_bid_project_files(
    project_id: uuid.UUID,
    _: Annotated[CurrentUser, Depends(require_permission("bid:detail"))],
    session: SessionDep,
) -> ApiResponse[list[BidProjectFileResponse]]:
    return success(await BidProjectService(session).files(project_id))


@router.get("/{project_id}/files/{file_id}/download")
async def download_bid_project_file(
    project_id: uuid.UUID,
    file_id: uuid.UUID,
    _: Annotated[CurrentUser, Depends(require_permission("bid:file:download"))],
    session: SessionDep,
) -> StreamingResponse:
    file, content = await BidProjectService(session).download(project_id, file_id)
    return StreamingResponse(
        BytesIO(content),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": (
                f"attachment; filename*=UTF-8''{quote(file.original_filename, safe='')}"
            )
        },
    )


@router.post("/{project_id}/exports", response_model=ApiResponse[BidProjectFileResponse])
async def export_bid_project(
    project_id: uuid.UUID,
    current: Annotated[CurrentUser, Depends(require_permission_before_response("bid:export"))],
    session: FunctionSessionDep,
) -> ApiResponse[BidProjectFileResponse]:
    return success(await BidProjectService(session).export(project_id, current.user_id))


@router.post("/{project_id}/commands/submit", response_model=ApiResponse[BidProjectStatusResponse])
async def submit_bid_project(
    project_id: uuid.UUID,
    payload: BidSubmitRequest,
    current: Annotated[CurrentUser, Depends(require_permission("bid:submit"))],
    session: SessionDep,
) -> ApiResponse[BidProjectStatusResponse]:
    return success(
        await BidProjectService(session).submit(
            project_id, payload.submitted_file_id, payload.note, current.user_id
        )
    )


@router.post("/{project_id}/commands/win", response_model=ApiResponse[BidProjectStatusResponse])
async def win_bid_project(
    project_id: uuid.UUID,
    payload: BidResultRequest,
    current: Annotated[CurrentUser, Depends(require_permission("bid:result"))],
    session: SessionDep,
) -> ApiResponse[BidProjectStatusResponse]:
    return success(
        await BidProjectService(session).result(
            project_id, BidProjectStatus.WON, payload.note, current.user_id
        )
    )


@router.post("/{project_id}/commands/lose", response_model=ApiResponse[BidProjectStatusResponse])
async def lose_bid_project(
    project_id: uuid.UUID,
    payload: BidResultRequest,
    current: Annotated[CurrentUser, Depends(require_permission("bid:result"))],
    session: SessionDep,
) -> ApiResponse[BidProjectStatusResponse]:
    return success(
        await BidProjectService(session).result(
            project_id, BidProjectStatus.LOST, payload.note, current.user_id
        )
    )


@router.post("/{project_id}/commands/void", response_model=ApiResponse[BidProjectStatusResponse])
async def void_bid_project(
    project_id: uuid.UUID,
    payload: BidVoidRequest,
    current: Annotated[CurrentUser, Depends(require_permission("bid:void"))],
    session: SessionDep,
) -> ApiResponse[BidProjectStatusResponse]:
    return success(
        await BidProjectService(session).void(project_id, payload.reason, current.user_id)
    )
