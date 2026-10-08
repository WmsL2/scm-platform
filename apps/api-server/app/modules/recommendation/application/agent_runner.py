import logging
from collections.abc import Awaitable, Callable
from typing import Protocol, TypeVar, cast

from pydantic import BaseModel

from app.integrations.deepseek.client import (
    DeepSeekConfigurationError,
    DeepSeekStructuredOutputError,
)
from app.modules.recommendation.application.agent_schemas import (
    AgentRecommendationResult,
    CategoryCatalogMatch,
    RequirementAnalysis,
)
from app.modules.recommendation.schemas import CategoryCatalogSnapshot

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
        max_tokens: int | None = None,
    ) -> StructuredModel: ...


class RecommendationTools(Protocol):
    async def prepare(self, analysis: RequirementAnalysis) -> object: ...


class CategoryCatalogTools(RecommendationTools, Protocol):
    async def prepare(self, analysis: RequirementAnalysis) -> CategoryCatalogSnapshot: ...

    async def record_catalog_category_matches(self, category_keys: list[str]) -> None: ...


class RecommendationAgentCancelled(RuntimeError):
    pass


class RecommendationAgentContractError(RuntimeError):
    pass


class AgentRunner:
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
                "本版本提取可由商品主数据确定性校验的数值硬条件：协议价、京东价、折扣率和点位（毛利率）。"
                "仅当客户明确使用“必须、仅限、指定、只要”等强制语气要求品牌时，"
                "才填 required_brands；普通品牌提及、偏好或推荐不得填入。"
                "以下三种情况都属于明确商品类目，必须填写 explicit_category_keywords："
                "客户使用“必须、仅限、指定、只要”等强制语气；客户直接以“需要、要、采购、推品、需求”等"
                "表达提出具体商品类型；客户在“类目 + 数量”分配中明确列出类目。"
                "例如“需要水杯、保温杯、随行杯”必须提取这些类目，而“适合出游、送礼、员工福利”不是类目。"
                "category_intents 必须返回空数组；不得猜测或生成同义、近义类目词。"
                "类目与真实商品库类目的语义匹配会在后续受控类目清单中单独完成。"
                "若需求以“家电250个、厨具135个、日用115个”这类方式明确给出“类目 + 数量”分配，"
                "即使没有“必须、仅限”，其中每个类目也属于明确类目要求：必须写入"
                " explicit_category_keywords，category_intents 仍必须为空数组。"
                "数字只是业务背景，不是库存、采购下单数量或候选数量上限；不得生成总名额、配额、开放池或"
                "任何数量筛选。"
                "场景、用途、主题、节日、物流、库存、资质、数量、价格有效期、厂直、销量、评分和卖点"
                "一律不参与筛选：这些字段必须返回空值或空数组，不能作为 needs_input 原因。"
                "自由推品允许不指定任何价格条件；字段缺失或写明暂无时保持为空并继续推荐。"
                "“200元以内”等未说明口径的价格写入 agreement_price_min/max；"
                "只有明确说京东价时才写入 jd_price_min/max。"
                "折扣条件仅按上限/下限解析：例如“可以满足9折优惠”表示 discount_rate_max=0.9，"
                "discount_rate_min 必须为空，不得把它解析成精确等于 0.9。"
                "“点位”映射为商品 gross_margin，6% 写为 gross_margin_min=0.06。"
                "不要输出人工核验字段。"
                "只有需求"
                "无法形成任何可执行场景、硬性条件互相矛盾或存在必须由需求方决策的合规问题时，才设置"
                " needs_input=true，并分别使用 UNUSABLE_REQUIREMENT、CONTRADICTORY_CONSTRAINTS 或"
                " COMPLIANCE_DECISION_REQUIRED 作为 blocking_reasons；不得创建其他原因。"
                "严格返回符合 JSON Schema 的对象。"
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

        catalog_tools = cast(CategoryCatalogTools, self.tools)
        category_catalog = await catalog_tools.prepare(analysis)
        if analysis.explicit_category_keywords:
            await self._report(report_progress, "MATCHING_CATEGORIES", 45, "正在匹配商品库真实类目")
            category_match = await self._complete(
                CategoryCatalogMatch,
                system=(
                    "你是受控商品类目匹配器。你只能从用户消息中的 category_catalog.items 返回"
                    " category_key，绝不能输出任何清单之外的 key 或自行发明类目名称。"
                    "清单同时包含 LEVEL1、LEVEL2、LEVEL3 节点。客户提出宽泛一级类目时，"
                    "优先选择对应 LEVEL1；提出二级类目时优先选择对应 LEVEL2；"
                    "只有客户明确到具体三级类目时才选择 LEVEL3。选中父级后服务端会自动展开"
                    "其下全部真实三级路径，因此不得只挑其中少数叶子路径。"
                    "只选择与客户明确类目原词完全一致、同义或明确上下级对应的真实节点；"
                    "场景、送礼、用途、人群、节日等宽泛关联不算类目匹配。"
                    "客户明确提出类目但清单中没有语义相关项时，返回空 category_keys。"
                    "必须尽可能选全有直接关系的路径，不能因 candidate_count 大小擅自省略。"
                    "严格返回符合 JSON Schema 的对象。"
                ),
                user=(
                    f"客户需求：{requirement}\n\n"
                    "category_catalog（服务器从当前可推荐商品生成的唯一可选清单）：\n"
                    f"{category_catalog.model_dump_json()}"
                ),
            )
            await catalog_tools.record_catalog_category_matches(category_match.category_keys)
        await self._check_cancelled(is_cancelled)
        await self._report(report_progress, "RETRIEVING", 60, "正在按硬条件检索全部可用商品")
        await self._report(report_progress, "CANDIDATES_READY", 100, "候选商品硬条件筛选完成")
        return AgentRecommendationResult(
            analysis=analysis,
            category_choices=[],
            candidates=[],
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
    async def _report(
        reporter: ProgressReporter | None, status: str, percent: int, message: str
    ) -> None:
        if reporter is not None:
            await reporter(status, percent, message)

    @staticmethod
    async def _check_cancelled(checker: CancellationChecker | None) -> None:
        if checker is not None and await checker():
            raise RecommendationAgentCancelled("推荐任务已取消")
