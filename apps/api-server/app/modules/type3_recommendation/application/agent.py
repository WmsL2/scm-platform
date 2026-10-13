# ruff: noqa: E501
from __future__ import annotations

import logging
from typing import cast
from uuid import UUID

from app.integrations.deepseek.client import (
    DeepSeekClient,
    DeepSeekConfigurationError,
    DeepSeekProviderError,
    DeepSeekStructuredOutputError,
)
from app.modules.type3_recommendation.application.service import Type3RecommendationService
from app.modules.type3_recommendation.schemas import Type3CategoryMatchResponse, Type3RemarkAnalysis

logger = logging.getLogger(__name__)


async def execute_type3_agent_inline(run_id: UUID, service: Type3RecommendationService) -> None:
    """Type-3-only AI adapter: it never imports the Type-4 AgentRunner or service."""
    try:
        run = await service.get_run(run_id)
        # A plain SELECT opens an implicit SQLAlchemy transaction.  This adapter performs
        # external model work between several independently durable state transitions, so
        # close that read transaction before prepare/execute/fail each own their commit.
        await service.session.rollback()
        provider = DeepSeekClient()
        remark = run.raw_remark_snapshot or "无额外备注。"
        analysis = await provider.structured_completion(
            system_prompt=(
                "你是类型3指定类目推品的备注分析器。只从备注提取可确定性筛选的协议价、京东价、"
                "折扣率、毛利率，以及客户明确使用必须/仅限/指定语气的品牌。"
                "不得提取类目；类目以人工在Excel中勾选为准。未提及则留空，严格输出 JSON。"
            ),
            user_prompt=remark,
            response_model=Type3RemarkAnalysis,
        )
        frozen = await service.prepare_for_category_mapping(
            run_id,
            analysis,
            provider=provider.provider,
            model=provider.model,
            prompt_version=provider.prompt_version,
        )
        sheets = cast(list[dict[str, object]], frozen["sheets"])
        nodes = [
            node
            for sheet in sheets
            for node in cast(list[dict[str, object]], sheet["selected_nodes"])
        ]
        matches = await provider.structured_completion(
            system_prompt=(
                "你是受控类目翻译器。客户已人工从Excel选择类目节点；你只能把每个 node_id 映射到"
                "category_catalog 中已有的 category_key。不得增加类目、不得遗漏 node_id。"
                "名称相近时可选择同义/上下级真实类目；没有可靠匹配时返回空数组。严格输出 JSON。"
            ),
            user_prompt=f"selected_nodes={nodes}\ncategory_catalog={frozen['catalog']}",
            response_model=Type3CategoryMatchResponse,
        )
        await service.execute(
            run_id,
            analysis,
            provider=provider.provider,
            model=provider.model,
            prompt_version=provider.prompt_version,
            category_matches={item.node_id: item.category_keys for item in matches.matches},
        )
    except DeepSeekConfigurationError as exc:
        await service.fail(run_id, str(exc))
    except (DeepSeekProviderError, DeepSeekStructuredOutputError) as exc:
        logger.warning(
            "type3 agent provider failure run_id=%s class=%s", run_id, type(exc).__name__
        )
        await service.fail(run_id, "类型 3 AI 备注/类目解析失败，请检查模型配置后重新生成")
    except Exception:
        logger.exception("type3 agent failure run_id=%s", run_id)
        await service.fail(run_id, "类型 3 推品任务执行失败，请稍后重试")
