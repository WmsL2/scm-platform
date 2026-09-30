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
    MAX_RANKING_CANDIDATES,
    AgentRecommendationResult,
    CandidateRanking,
    CategoryChoice,
    CategoryChoiceList,
    CategoryOption,
    ProductCandidate,
    ProductSearchRequest,
    RankedCandidate,
    RequirementAnalysis,
)

logger = logging.getLogger(__name__)


class PptRecommendationTools(RecommendationTools, Protocol):
    async def list_categories(
        self, keywords: Sequence[str], *, limit: int
    ) -> list[CategoryOption]: ...

    async def search_products(self, request: ProductSearchRequest) -> list[ProductCandidate]: ...


class PptSelectionAgentRunner(AgentRunner):
    """Type-5 semantic selection over controlled Product Master rows only."""

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
            return self._result(analysis, [], [])

        await self.ppt_tools.prepare(analysis)
        await self._check_cancelled(is_cancelled)
        await self._report(report_progress, "RETRIEVING", 30, "正在读取可用商品类目")
        self._consume_tool_call()
        categories = await self.ppt_tools.list_categories(
            analysis.category_keywords or analysis.keywords, limit=100
        )
        if not categories:
            return self._result(analysis, [], [])
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

        groups: list[list[ProductCandidate]] = []
        for index, choice in enumerate(choices.choices, start=1):
            await self._report(
                report_progress,
                "RETRIEVING",
                30 + int(index / len(choices.choices) * 35),
                f"正在检索第 {index}/{len(choices.choices)} 个选品方向",
            )
            self._consume_tool_call()
            groups.append(
                await self.ppt_tools.search_products(
                    ProductSearchRequest(
                        category_key=choice.category_key,
                        keywords=choice.search_keywords,
                        preferred_brands=list(
                            dict.fromkeys(
                                [*analysis.preferred_brands, *analysis.required_brands]
                            )
                        ),
                        agreement_price_min=analysis.agreement_price_min or analysis.budget_min,
                        agreement_price_max=analysis.agreement_price_max or analysis.budget_max,
                        limit=50,
                    )
                )
            )
            await self._check_cancelled(is_cancelled)
        candidates = self._round_robin(groups)
        if not candidates:
            return self._result(analysis, choices.choices, [])

        await self._report(report_progress, "RANKING", 75, "AI 正在生成推荐排序")
        ranking = await self._complete(
            CandidateRanking,
            system=(
                "只能从输入候选中选择并排序。每项只返回 product_id、score、reason，"
                "product_id 必须原样"
                "复制，不得重复或编造。结合甲方场景、预算档位、品类偏好、配送要求与真实商品字段评分。"
                "不得虚构活动价、库存、参数和履约承诺。最多返回 30 件，供人工选择及组成套装。"
            ),
            user=f"甲方需求={analysis.model_dump_json()}\n真实候选={compact_json(candidates)}",
        )
        allowed_ids = {item.product_id for item in candidates}
        ranked_ids = [item.product_id for item in ranking.candidates]
        if len(set(ranked_ids)) != len(ranked_ids) or any(
            product_id not in allowed_ids for product_id in ranked_ids
        ):
            raise RecommendationAgentContractError("AI 返回了无效或重复的候选商品 ID")
        ordered = sorted(ranking.candidates, key=lambda item: item.score, reverse=True)
        await self._report(report_progress, "CANDIDATES_READY", 100, "AI 推荐候选已生成")
        return self._result(analysis, choices.choices, ordered)

    def _result(
        self,
        analysis: RequirementAnalysis,
        choices: list[CategoryChoice],
        candidates: list[RankedCandidate],
    ) -> AgentRecommendationResult:
        return AgentRecommendationResult(
            analysis=analysis,
            category_choices=choices,
            candidates=candidates,
            provider=self.provider.provider,
            model=self.provider.model,
            prompt_version=self.provider.prompt_version,
            tool_call_count=self._tool_calls,
        )

    @staticmethod
    def _round_robin(groups: Sequence[Sequence[ProductCandidate]]) -> list[ProductCandidate]:
        selected: list[ProductCandidate] = []
        seen: set[object] = set()
        positions = [0] * len(groups)
        while len(selected) < MAX_RANKING_CANDIDATES:
            progressed = False
            for index, group in enumerate(groups):
                while positions[index] < len(group):
                    item = group[positions[index]]
                    positions[index] += 1
                    if item.product_id in seen:
                        continue
                    selected.append(item)
                    seen.add(item.product_id)
                    progressed = True
                    break
                if len(selected) >= MAX_RANKING_CANDIDATES:
                    break
            if not progressed:
                break
        return selected

    def _consume_tool_call(self) -> None:
        if self._tool_calls >= self.MAX_TOOL_CALLS:
            raise RecommendationAgentContractError("Agent 工具调用次数超过安全上限")
        self._tool_calls += 1
