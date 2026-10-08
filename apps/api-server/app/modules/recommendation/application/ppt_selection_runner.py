"""Type-5-only controlled catalogue selection runner.

It intentionally does not inherit the Type-4 runner: prompt evolution and tool
contracts remain isolated even though both implement the same V8 policy.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Awaitable, Callable
from typing import Protocol, TypeVar

from pydantic import BaseModel

from app.core.config import get_settings
from app.integrations.deepseek.client import (
    DeepSeekConfigurationError,
    DeepSeekStructuredOutputError,
)
from app.modules.recommendation.application.agent_runner import (
    RecommendationAgentCancelled,
    RecommendationAgentContractError,
    StructuredProvider,
)
from app.modules.recommendation.application.agent_schemas import (
    AgentRecommendationResult,
    CategoryCatalogMatch,
    RequirementAnalysis,
)
from app.modules.recommendation.schemas import CategoryCatalogItem, CategoryCatalogSnapshot

logger = logging.getLogger(__name__)
ProgressReporter = Callable[[str, int, str], Awaitable[None]]
CancellationChecker = Callable[[], Awaitable[bool]]
StructuredModel = TypeVar("StructuredModel", bound=BaseModel)


class PptCatalogTools(Protocol):
    async def prepare(self, analysis: RequirementAnalysis) -> CategoryCatalogSnapshot: ...
    async def record_catalog_category_matches(self, category_keys: list[str]) -> None: ...


class PptSelectionAgentRunner:
    """Run Type-5's own copy of the V8 parse -> frozen-catalogue flow."""

    MAX_PROVIDER_ATTEMPTS = 2

    def __init__(self, provider: StructuredProvider, tools: PptCatalogTools) -> None:
        self.provider = provider
        self.tools = tools

    async def run(
        self,
        requirement: str,
        *,
        report_progress: ProgressReporter | None = None,
        is_cancelled: CancellationChecker | None = None,
    ) -> AgentRecommendationResult:
        requirement = requirement.strip()
        if len(requirement) < 20:
            raise RecommendationAgentContractError("PPT 方案需求说明不能少于 20 个字符")
        await self._check_cancelled(is_cancelled)
        await self._report(report_progress, "ANALYZING", 10, "AI 正在理解 PPT 方案需求")
        analysis = await self._complete(
            RequirementAnalysis,
            system=(
                "你是企业福利与礼品 PPT 方案需求分析助手。只分析客户原文，"
                "不编造商品、供应商、库存或数据库事实。"
                "只提取可由正式商品主数据确定性校验的协议价、京东价、折扣率和点位（毛利率）条件。"
                "客户用“必须、仅限、指定、只要”，或直接用“需要、要、采购、推品、需求”提出具体商品类型时，"
                "必须写入 explicit_category_keywords。场景、人群、节日、用途不是商品类目。"
                "category_intents 必须固定返回空数组；不得生成近义词、同义词或自造类目。"
                "普通品牌提及不做硬筛，只有明确强制品牌要求才写入 required_brands。"
                "库存、配送、履约、数量、评分和卖点不参与商品筛选，不能因此要求补充信息。"
                "只有需求不可执行、硬条件矛盾或必须由客户作合规决定时才 needs_input=true。"
                "严格返回 JSON Schema 对应对象。"
            ),
            user=requirement,
        )
        if analysis.needs_input:
            return self._result(analysis)

        catalog = await self.tools.prepare(analysis)
        if analysis.explicit_category_keywords:
            await self._report(report_progress, "MATCHING_CATEGORIES", 45, "正在匹配真实商品类目")
            matched_keys: list[str] = []
            for batch in self._catalog_batches(catalog):
                match = await self._complete(
                    CategoryCatalogMatch,
                    system=(
                        "你是类型 5 受控商品类目匹配器。只能返回 "
                        "category_catalog.items 中已有的 category_key，"
                        "绝不能输出类目文字或清单外 key。一级、二级、三级节点均可选择；"
                        "选父节点时服务端会展开下级。"
                        "只匹配客户明确提出的商品类目及其明确上下级或同义对应，场景关联不算类目。"
                        "客户明确类目没有匹配时返回空 category_keys。"
                        "严格返回 JSON Schema 对应对象。"
                    ),
                    user=f"客户需求：{requirement}\n\ncategory_catalog：\n{batch.model_dump_json()}",
                )
                matched_keys.extend(match.category_keys)
            await self.tools.record_catalog_category_matches(list(dict.fromkeys(matched_keys)))
        await self._check_cancelled(is_cancelled)
        await self._report(report_progress, "RETRIEVING", 60, "正在冻结类型 5 完整合格商品池")
        await self._report(
            report_progress, "CANDIDATES_READY", 100, "类型 5 候选商品硬条件筛选完成"
        )
        return self._result(analysis)

    def _result(self, analysis: RequirementAnalysis) -> AgentRecommendationResult:
        return AgentRecommendationResult(
            analysis=analysis,
            category_choices=[],
            candidates=[],
            provider=self.provider.provider,
            model=self.provider.model,
            prompt_version=self.provider.prompt_version,
            tool_call_count=0,
        )

    @staticmethod
    def _catalog_batches(catalog: CategoryCatalogSnapshot) -> list[CategoryCatalogSnapshot]:
        """Cover every real category in bounded requests; never permanently truncate it."""
        max_chars = max(1000, int(get_settings().ppt_ai_input_token_budget * 4 * 0.65))
        batches: list[CategoryCatalogSnapshot] = []
        current: list[CategoryCatalogItem] = []
        size = 64
        for item in catalog.items:
            item_size = len(json.dumps(item.model_dump(mode="json"), ensure_ascii=False)) + 1
            if current and size + item_size > max_chars:
                batches.append(
                    CategoryCatalogSnapshot(generated_at=catalog.generated_at, items=current)
                )
                current, size = [], 64
            current.append(item)
            size += item_size
        if current or not batches:
            batches.append(
                CategoryCatalogSnapshot(generated_at=catalog.generated_at, items=current)
            )
        return batches

    async def _complete(
        self, response_model: type[StructuredModel], *, system: str, user: str
    ) -> StructuredModel:
        retry_user = user
        for attempt in range(self.MAX_PROVIDER_ATTEMPTS):
            try:
                return await self.provider.structured_completion(
                    system_prompt=system, user_prompt=retry_user, response_model=response_model
                )
            except DeepSeekConfigurationError:
                raise
            except DeepSeekStructuredOutputError as exc:
                if attempt + 1 == self.MAX_PROVIDER_ATTEMPTS:
                    raise
                logger.warning("ppt selection schema retry stage=%s", response_model.__name__)
                retry_user = (
                    f"{user}\n\n上一次输出未通过 JSON Schema 校验，请仅重新输出合法 JSON。"
                    f"脱敏错误：{exc.safe_validation_summary}"
                )
        raise RecommendationAgentContractError("类型 5 AI 未返回可用结构化结果")

    @staticmethod
    async def _report(
        reporter: ProgressReporter | None, status: str, percent: int, message: str
    ) -> None:
        if reporter is not None:
            await reporter(status, percent, message)

    @staticmethod
    async def _check_cancelled(checker: CancellationChecker | None) -> None:
        if checker is not None and await checker():
            raise RecommendationAgentCancelled("类型 5 推品任务已取消")
