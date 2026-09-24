import logging
from collections.abc import Awaitable, Callable, Sequence
from typing import Protocol, TypeVar

from pydantic import BaseModel

from app.integrations.deepseek.client import (
    DeepSeekConfigurationError,
    DeepSeekStructuredOutputError,
    compact_json,
)
from app.modules.recommendation.application.agent_schemas import (
    MAX_RANKING_CANDIDATES,
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
logger = logging.getLogger(__name__)


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
                "保留为空并继续推荐，绝不能仅因此设置 needs_input=true。"
                "explicit_category_keywords 只填写明确限定的商品类目；"
                "category_intents、scenarios、promotion_preference 与 search_keywords"
                " 是软排序/召回信号，"
                "不可当硬过滤。required_brands 是必须品牌，preferred_brands 只是偏好，"
                "excluded_brands 和 excluded_category_keywords 才是排除条件。"
                "没有明确毛利要求时 gross_margin_min 必须为 null，"
                "绝不使用隐藏的 6% 默认值。特价使用 SPECIAL_PRICE，且只是排序偏好。"
                "一件代发必须生成 DROP_SHIPPING、PENDING 的 required manual_checks；"
                "shipping_courier 不能证明一件代发。"
                "现货、48小时发货等无法由商品主数据证明的条件同样生成 PENDING 人工核验，"
                "不能声称已满足。"
                "只有需求"
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
        category_candidates: list[list[ProductCandidate]] = []
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
            category_candidates.append(await self._call_search_products(request))
            await self._check_cancelled(is_cancelled)

        candidates = self._select_ranking_candidates(category_candidates)
        if not candidates:
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
        logger.debug(
            "recommendation provider call stage=CandidateRanking candidate_count=%s attempt=1",
            len(candidates),
        )
        ranking = await self._complete(
            CandidateRanking,
            system=(
                '只能返回 JSON object，顶层只能是 {"candidates":[...]}，不得输出 Markdown、'
                "代码块或额外字段。每个 candidate 只能含 product_id、score、reason；product_id 必须"
                "原样复制输入候选的 UUID，示例 UUID 仅表示结构，实际值只能来自输入。"
                "score 必须为 0 到 100 的数字，reason 必须为非空字符串。"
                "不得返回不存在或重复的 product_id，不得超过输入"
                f"数量，也不得超过 {MAX_RANKING_CANDIDATES} 条。"
                "硬约束已经由后端执行；仅将软偏好用于排序。"
                "SPECIAL_PRICE 时只可引用输入中真实的折扣、协议价和京东价，"
                "不能杜撰活动价、库存、时效、"
                "一件代发或物流能力。未完成的人工核验必须表述为仍需人工确认。"
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
        retry_user = user
        for attempt in range(self.MAX_PROVIDER_ATTEMPTS):
            try:
                return await self.provider.structured_completion(
                    system_prompt=system,
                    user_prompt=retry_user,
                    response_model=response_model,
                )
            except DeepSeekConfigurationError:
                raise
            except DeepSeekStructuredOutputError as exc:
                last_error = exc
                if attempt + 1 == self.MAX_PROVIDER_ATTEMPTS:
                    raise
                logger.warning(
                    "recommendation structured output retry "
                    "stage=%s attempt=%s error_kind=%s validation=%s",
                    response_model.__name__,
                    attempt + 1,
                    exc.error_kind,
                    exc.safe_validation_summary,
                )
                retry_user = (
                    f"{user}\n\n上一次输出未通过 JSON Schema 校验。请重新生成完整 JSON。"
                    f"以下是脱敏校验错误：{exc.safe_validation_summary}。"
                    "不要解释，不要输出 Markdown，只输出合法 JSON。"
                )
            except Exception as exc:
                last_error = exc
                if attempt + 1 == self.MAX_PROVIDER_ATTEMPTS:
                    raise
        assert last_error is not None
        raise last_error

    @staticmethod
    def _select_ranking_candidates(
        category_candidates: Sequence[Sequence[ProductCandidate]],
    ) -> list[ProductCandidate]:
        """Round-robin deterministic repository-ordered candidates across AI choices."""
        selected: list[ProductCandidate] = []
        selected_ids: set[str] = set()
        positions = [0] * len(category_candidates)
        while len(selected) < MAX_RANKING_CANDIDATES:
            progressed = False
            for index, group in enumerate(category_candidates):
                while positions[index] < len(group):
                    candidate = group[positions[index]]
                    positions[index] += 1
                    if str(candidate.product_id) in selected_ids:
                        continue
                    selected.append(candidate)
                    selected_ids.add(str(candidate.product_id))
                    progressed = True
                    break
                if len(selected) == MAX_RANKING_CANDIDATES:
                    break
            if not progressed:
                break
        return selected

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
