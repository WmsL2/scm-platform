from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import Protocol

from app.integrations.deepseek.client import compact_json
from app.modules.recommendation.application.agent_runner import (
    AgentRunner,
    CancellationChecker,
    ProgressReporter,
    RecommendationAgentContractError,
    RecommendationTools,
    StructuredProvider,
)
from app.modules.recommendation.application.agent_schemas import (
    AgentRecommendationResult,
    CategoryChoice,
    CategoryChoiceList,
    CategoryOption,
    RequirementAnalysis,
)

logger = logging.getLogger(__name__)


class PptRecommendationTools(RecommendationTools, Protocol):
    async def list_categories(
        self, keywords: Sequence[str], *, limit: int
    ) -> list[CategoryOption]: ...

class PptSelectionAgentRunner(AgentRunner):
    """Type-5 requirement analysis and controlled category selection only."""

    MAX_TOOL_CALLS = 8

    def __init__(self, provider: StructuredProvider, tools: PptRecommendationTools) -> None:
        super().__init__(provider, tools)
        self.ppt_tools = tools

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
        self._tool_calls = 0
        await self._check_cancelled(is_cancelled)
        await self._report(report_progress, "ANALYZING", 10, "AI 正在理解甲方需求")
        analysis = await self._complete(
            RequirementAnalysis,
            system=(
                "你是企业福利与礼品方案选品助手。理解甲方的场景、人群、节日、预算档位、禁选条件、"
                "价格、毛利、配送和履约要求。不得编造商品、库存或供应商事实。缺少数量不构成阻塞。"
                "明确数字条件要结构化保存；场景、品类、品牌与组合意图用于语义选品。"
                "只有需求完全不可执行、硬条件矛盾或必须由甲方作合规决定时才 needs_input=true。"
            ),
            user=requirement,
        )
        if analysis.needs_input:
            return self._result(analysis, [])

        await self.ppt_tools.prepare(analysis)
        await self._check_cancelled(is_cancelled)
        await self._report(report_progress, "RETRIEVING", 30, "正在读取可用商品类目")
        self._consume_tool_call()
        categories = await self.ppt_tools.list_categories(
            analysis.category_keywords or analysis.keywords, limit=100
        )
        if not categories:
            return self._result(analysis, [])
        choices = await self._complete(
            CategoryChoiceList,
            system=(
                "只能从给定的真实类目中选择最多 5 个与需求匹配的方向。category_key 必须原样返回，"
                "不得创造类目。价格档位可能通过单品或后续人工套装满足。"
            ),
            user=f"需求={analysis.model_dump_json()}\n可选类目={compact_json(categories)}",
        )
        allowed_keys = {item.key for item in categories}
        if any(choice.category_key not in allowed_keys for choice in choices.choices):
            raise RecommendationAgentContractError("AI 返回了商品主数据中不存在的类目")

        await self._report(
            report_progress, "CANDIDATES_READY", 100, "已确定推品类目，正在建立商品方案"
        )
        return self._result(analysis, choices.choices)

    def _result(
        self,
        analysis: RequirementAnalysis,
        choices: list[CategoryChoice],
    ) -> AgentRecommendationResult:
        return AgentRecommendationResult(
            analysis=analysis,
            category_choices=choices,
            candidates=[],
            provider=self.provider.provider,
            model=self.provider.model,
            prompt_version=self.provider.prompt_version,
            tool_call_count=self._tool_calls,
        )

    def _consume_tool_call(self) -> None:
        if self._tool_calls >= self.MAX_TOOL_CALLS:
            raise RecommendationAgentContractError("Agent 工具调用次数超过安全上限")
        self._tool_calls += 1
