from collections.abc import Awaitable, Callable, Sequence
from typing import Protocol, TypeVar

from pydantic import BaseModel

from app.integrations.deepseek.client import DeepSeekConfigurationError, compact_json
from app.modules.recommendation.application.agent_schemas import (
    AgentRecommendationResult,
    CandidateRanking,
    CategoryChoiceList,
    CategoryOption,
    ProductCandidate,
    ProductSearchRequest,
    RequirementAnalysis,
)

ProgressReporter = Callable[[str, int, str], Awaitable[None]]
CancellationChecker = Callable[[], Awaitable[bool]]
StructuredModel = TypeVar("StructuredModel", bound=BaseModel)


class StructuredProvider(Protocol):
    @property
    def provider(self) -> str: ...

    @property
    def model(self) -> str: ...

    @property
    def prompt_version(self) -> str: ...

    async def structured_completion(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_model: type[StructuredModel],
    ) -> StructuredModel: ...


class RecommendationTools(Protocol):
    async def prepare(self, analysis: RequirementAnalysis) -> None: ...

    async def list_categories(
        self, keywords: Sequence[str], *, limit: int
    ) -> list[CategoryOption]: ...

    async def search_products(self, request: ProductSearchRequest) -> list[ProductCandidate]: ...


class RecommendationAgentCancelled(RuntimeError):
    pass


class RecommendationAgentContractError(RuntimeError):
    pass


class AgentRunner:
    MAX_TOOL_CALLS = 8
    MAX_PROVIDER_ATTEMPTS = 2

    def __init__(self, provider: StructuredProvider, tools: RecommendationTools) -> None:
        self.provider = provider
        self.tools = tools
        self._tool_calls = 0

    async def run(
        self,
        requirement: str,
        *,
        report_progress: ProgressReporter | None = None,
        is_cancelled: CancellationChecker | None = None,
    ) -> AgentRecommendationResult:
        requirement = requirement.strip()
        if len(requirement) < 20:
            raise RecommendationAgentContractError("自由推品需求说明不能少于 20 个字符")
        self._tool_calls = 0
        await self._check_cancelled(is_cancelled)
        await self._report(report_progress, "ANALYZING", 10, "正在理解业务需求")
        analysis = await self._complete(
            RequirementAnalysis,
            system=(
                "你是企业职工福利自由推品需求分析助手。只分析用户文字，不编造商品、供应商或数据库信息。"
                "自由推品允许需求方不指定类目、品牌、单价、预算和数量；这些字段缺失或写明暂无时，"
                "保留为空并继续推荐，绝不能仅因此设置 needs_input=true。category_keywords 只填写"
                "需求方"
                "明确限定的商品类目词，节日、活动、特价、人群等放入 keywords 或 scenarios。只有需求"
                "无法形成任何可执行场景、硬性条件互相矛盾或存在必须由需求方决策的合规问题时，才设置"
                " needs_input=true，并分别使用 UNUSABLE_REQUIREMENT、CONTRADICTORY_CONSTRAINTS 或"
                " COMPLIANCE_DECISION_REQUIRED 作为 blocking_reasons；不得创建其他原因。毛利率 6%"
                " 必须表示为 0.06。一件代发写入"
                " fulfillment_mode。严格返回符合 JSON Schema 的对象。"
            ),
            user=requirement,
        )
        if analysis.needs_input:
            return AgentRecommendationResult(
                analysis=analysis,
                category_choices=[],
                candidates=[],
                provider=self.provider.provider,
                model=self.provider.model,
                prompt_version=self.provider.prompt_version,
                tool_call_count=self._tool_calls,
            )

        await self.tools.prepare(analysis)
        await self._check_cancelled(is_cancelled)
        await self._report(report_progress, "RETRIEVING", 30, "正在读取可用商品类目")
        categories = await self._call_list_categories(
            analysis.category_keywords or analysis.keywords
        )
        if not categories:
            return AgentRecommendationResult(
                analysis=analysis,
                category_choices=[],
                candidates=[],
                provider=self.provider.provider,
                model=self.provider.model,
                prompt_version=self.provider.prompt_version,
                tool_call_count=self._tool_calls,
            )
        choices = await self._complete(
            CategoryChoiceList,
            system=(
                "你只能从给定的真实类目中选择最多 5 个方向。category_key 必须原样返回，"
                "不得创造新类目。为每个方向提供检索关键词和简洁理由。"
            ),
            user=f"需求={analysis.model_dump_json()}\n可选类目={compact_json(categories)}",
        )
        allowed_keys = {item.key for item in categories}
        if any(choice.category_key not in allowed_keys for choice in choices.choices):
            raise RecommendationAgentContractError("模型返回了商品主数据中不存在的类目")

        await self._check_cancelled(is_cancelled)
        all_candidates: dict[str, ProductCandidate] = {}
        for index, choice in enumerate(choices.choices, start=1):
            await self._report(
                report_progress,
                "RETRIEVING",
                30 + int(index / len(choices.choices) * 35),
                f"正在检索第 {index}/{len(choices.choices)} 个类目方向",
            )
            request = ProductSearchRequest(
                category_key=choice.category_key,
                keywords=choice.search_keywords,
                preferred_brands=analysis.preferred_brands,
                agreement_price_min=analysis.budget_min,
                agreement_price_max=analysis.budget_max,
            )
            for candidate in await self._call_search_products(request):
                all_candidates[str(candidate.product_id)] = candidate
            await self._check_cancelled(is_cancelled)

        if not all_candidates:
            return AgentRecommendationResult(
                analysis=analysis,
                category_choices=choices.choices,
                candidates=[],
                provider=self.provider.provider,
                model=self.provider.model,
                prompt_version=self.provider.prompt_version,
                tool_call_count=self._tool_calls,
            )

        await self._report(report_progress, "RANKING", 75, "正在生成候选排序和推荐理由")
        candidates = list(all_candidates.values())
        ranking = await self._complete(
            CandidateRanking,
            system=(
                "你只能对给定候选商品排序。只能返回候选中存在的 product_id，不得修改价格、"
                "计算新价格或补充不存在的商品。score 范围为 0 到 100，理由必须基于已给字段。"
            ),
            user=f"需求={analysis.model_dump_json()}\n候选={compact_json(candidates)}",
        )
        candidate_ids = {item.product_id for item in candidates}
        ranked_ids = [item.product_id for item in ranking.candidates]
        if len(set(ranked_ids)) != len(ranked_ids) or any(
            product_id not in candidate_ids for product_id in ranked_ids
        ):
            raise RecommendationAgentContractError("模型返回了无效或重复的候选商品 ID")
        ordered = sorted(ranking.candidates, key=lambda item: item.score, reverse=True)
        await self._report(report_progress, "CANDIDATES_READY", 100, "推荐候选已生成")
        return AgentRecommendationResult(
            analysis=analysis,
            category_choices=choices.choices,
            candidates=ordered,
            provider=self.provider.provider,
            model=self.provider.model,
            prompt_version=self.provider.prompt_version,
            tool_call_count=self._tool_calls,
        )

    async def _complete(
        self,
        response_model: type[StructuredModel],
        *,
        system: str,
        user: str,
    ) -> StructuredModel:
        last_error: Exception | None = None
        for attempt in range(self.MAX_PROVIDER_ATTEMPTS):
            try:
                return await self.provider.structured_completion(
                    system_prompt=system,
                    user_prompt=user,
                    response_model=response_model,
                )
            except DeepSeekConfigurationError:
                raise
            except Exception as exc:
                last_error = exc
                if attempt + 1 == self.MAX_PROVIDER_ATTEMPTS:
                    raise
        assert last_error is not None
        raise last_error

    async def _call_list_categories(self, keywords: Sequence[str]) -> list[CategoryOption]:
        self._consume_tool_call()
        return await self.tools.list_categories(keywords, limit=100)

    async def _call_search_products(self, request: ProductSearchRequest) -> list[ProductCandidate]:
        self._consume_tool_call()
        return await self.tools.search_products(request)

    def _consume_tool_call(self) -> None:
        if self._tool_calls >= self.MAX_TOOL_CALLS:
            raise RecommendationAgentContractError("Agent 工具调用次数超过安全上限")
        self._tool_calls += 1

    @staticmethod
    async def _report(
        reporter: ProgressReporter | None, status: str, percent: int, message: str
    ) -> None:
        if reporter is not None:
            await reporter(status, percent, message)

    @staticmethod
    async def _check_cancelled(checker: CancellationChecker | None) -> None:
        if checker is not None and await checker():
            raise RecommendationAgentCancelled("推荐任务已取消")
