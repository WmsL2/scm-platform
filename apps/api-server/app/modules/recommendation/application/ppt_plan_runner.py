"""Token-bounded Type-5 plan composition over an immutable candidate snapshot."""

from __future__ import annotations

import asyncio
import json
import logging
from collections import defaultdict, deque
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from time import perf_counter

from app.core.config import Settings, get_settings
from app.integrations.deepseek.client import (
    DeepSeekConfigurationError,
    DeepSeekRequestTelemetry,
    DeepSeekStructuredOutputError,
    capture_deepseek_request_telemetry,
)
from app.modules.recommendation.application.agent_runner import (
    RecommendationAgentContractError,
    StructuredProvider,
)
from app.modules.recommendation.infrastructure.models import RecommendationCandidate
from app.modules.recommendation.ppt_schemas import (
    PptCandidateAssessment,
    PptCandidateAssessmentList,
    PptDirectSelectionProposal,
    PptFrozenRecommendationConfig,
    PptPlanProposalList,
    PptPriceBandInput,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PptDirectSelectedCandidate:
    candidate: RecommendationCandidate
    overall_score: int


class PptPlanAgentRunner:
    """Run Type-5 selection through bounded short-ID model requests.

    Character/token conversion deliberately overestimates (four characters per
    token) because no provider tokenizer is available in the local-first runtime.
    The complete pool remains frozen in MySQL; direct selection never fills a
    result with a candidate the AI did not assess.
    """

    MAX_PROVIDER_ATTEMPTS = 2

    def __init__(self, provider: StructuredProvider, settings: Settings | None = None) -> None:
        self.provider = provider
        self.settings = settings or get_settings()

    async def run(
        self, config: PptFrozenRecommendationConfig, candidates: list[RecommendationCandidate]
    ) -> PptPlanProposalList:
        plans = []
        for index, band in enumerate(config.price_bands, 1):
            if len(self.band_candidates(band, candidates)) >= config.candidate_count_per_band:
                plans.extend((await self.run_band(index, band, config, candidates)).plans)
        return PptPlanProposalList(plans=plans)

    async def run_band(
        self,
        index: int,
        band: PptPriceBandInput,
        config: PptFrozenRecommendationConfig,
        candidates: list[RecommendationCandidate],
        *,
        item_count: int | None = None,
        plan_count: int | None = None,
    ) -> PptPlanProposalList:
        eligible = self.band_candidates(band, candidates)
        quantity = item_count or band.item_count
        requested_plans = plan_count or config.plan_count_per_band
        if len(eligible) < quantity:
            return PptPlanProposalList()
        window, key_map = self._window(eligible)
        seed_count = min(quantity, self.settings.ppt_ai_seed_count_per_plan)
        payload = json.dumps(
            {
                "price_band_index": index,
                "recommendation_mode": config.recommendation_mode,
                "items_per_plan": quantity,
                "plans_per_band": requested_plans,
                "seed_count_limit": seed_count,
                "candidate_window_count": len(window),
                "candidates": window,
            },
            ensure_ascii=False,
            separators=(",", ":"),
        )
        retry_note = ""
        for attempt in range(self.MAX_PROVIDER_ATTEMPTS):
            try:
                result = await self.provider.structured_completion(
                    system_prompt=(
                        "你是类型 5 PPT 商品方案编排助手。只能从 candidates 中返回 server-issued "
                        "short candidate_keys（例如 c1），绝不能生成 UUID、商品或清单外 key。"
                        f"每张方案仅选择 1 到 {seed_count} 个不重复核心商品；"
                        "服务器会从完整合格池补齐剩余数量。返回严格 JSON。"
                    ),
                    user_prompt=f"{payload}{retry_note}",
                    response_model=PptPlanProposalList,
                    max_tokens=min(
                        self.settings.ppt_ai_output_token_budget, self.settings.deepseek_max_tokens
                    ),
                )
                self._validate_provider_result(result, index, requested_plans, key_map)
                return result
            except DeepSeekConfigurationError:
                raise
            except (DeepSeekStructuredOutputError, RecommendationAgentContractError) as exc:
                if attempt + 1 == self.MAX_PROVIDER_ATTEMPTS:
                    raise
                detail = (
                    exc.safe_validation_summary
                    if isinstance(exc, DeepSeekStructuredOutputError)
                    else str(exc)
                )
                logger.warning(
                    "ppt token-safe plan retry band=%s validation=%s",
                    index,
                    detail,
                )
                retry_note = (
                    "\n上一次输出未通过方案合同校验。请仅重新输出完整且合法 JSON；"
                    f"脱敏错误：{detail}"
                )
                continue
        raise RecommendationAgentContractError("类型 5 AI 未返回可用方案")

    async def select_direct_candidates(
        self,
        index: int,
        band: PptPriceBandInput,
        candidates: list[RecommendationCandidate],
        *,
        item_count: int,
        scene_context: str,
    ) -> list[PptDirectSelectedCandidate]:
        """Score every frozen candidate before selecting one exact direct-result list.

        A complete frozen price-band pool can be much larger than one provider request.
        Every candidate is therefore sent once in a bounded assessment batch.  A final
        selection call refines the highest-scoring subset when that subset fits the
        configured input budget; otherwise the complete AI assessment ranking is the
        final selection.  The server never fills direct results with unassessed items.
        """
        permitted = self.band_candidates(band, candidates)
        if len(permitted) < item_count:
            raise RecommendationAgentContractError("价格档冻结候选不足，无法生成指定数量商品")
        key_map = self._direct_key_map(permitted)
        # First-pass rows intentionally keep lengthy specification and selling-point
        # text compact. Every frozen candidate still receives a model assessment.
        rows = [self._assessment_row(key, candidate) for key, candidate in key_map.items()]
        batches = self._assessment_batches(rows)
        semaphore = asyncio.Semaphore(self.settings.ppt_ai_assessment_concurrency)

        async def assess(
            batch_no: int, batch: list[dict[str, object]]
        ) -> PptCandidateAssessmentList:
            async with semaphore:
                return await self._assess_batch(
                    index=index,
                    batch_no=batch_no,
                    scene_context=scene_context,
                    rows=batch,
                )

        results = await asyncio.gather(
            *(assess(batch_no, batch) for batch_no, batch in enumerate(batches, start=1))
        )
        assessments = {
            item.candidate_key: item for result in results for item in result.assessments
        }

        if set(assessments) != set(key_map):
            raise RecommendationAgentContractError("类型 5 AI 未完成全部冻结候选的评分")
        ranked_keys = sorted(
            assessments,
            key=lambda key: (
                -assessments[key].overall_score,
                -assessments[key].scene_score,
                -assessments[key].value_score,
                key_map[key].rank,
            ),
        )
        diversified_keys = self._category_diversified_keys(ranked_keys, key_map)
        finalists = self._finalist_rows(diversified_keys, key_map, assessments, item_count)
        if len(finalists) >= item_count:
            proposal = await self._select_finalists(
                index=index,
                item_count=item_count,
                scene_context=scene_context,
                finalists=finalists,
            )
            selected_keys = proposal.candidate_keys
        else:
            # The final comparison itself cannot fit the safe input budget.  Every
            # candidate was still AI-assessed. Keep the strongest representative
            # from each third-level category ahead of same-category repetitions,
            # rather than silently producing a one-category deterministic filler.
            logger.warning(
                "type5 final selection fallback band=%s requested=%s finalists=%s "
                "reason=input_budget",
                index,
                item_count,
                len(finalists),
            )
            selected_keys = diversified_keys[:item_count]

        if len(selected_keys) != item_count or len(selected_keys) != len(set(selected_keys)):
            raise RecommendationAgentContractError("类型 5 AI 未按要求返回精确且不重复的商品数量")
        if any(key not in key_map for key in selected_keys):
            raise RecommendationAgentContractError("类型 5 AI 返回了清单外商品")
        return [
            PptDirectSelectedCandidate(
                candidate=key_map[key], overall_score=assessments[key].overall_score
            )
            for key in selected_keys
        ]

    async def _assess_batch(
        self,
        *,
        index: int,
        batch_no: int,
        scene_context: str,
        rows: list[dict[str, object]],
    ) -> PptCandidateAssessmentList:
        payload = json.dumps(
            {
                "stage": "scene_value_assessment",
                "price_band_index": index,
                "batch_no": batch_no,
                "scene_context": scene_context,
                "candidates": rows,
            },
            ensure_ascii=False,
            separators=(",", ":"),
        )
        retry_note = ""
        expected_keys = {str(row["id"]) for row in rows}
        input_characters = len(payload)
        for attempt in range(self.MAX_PROVIDER_ATTEMPTS):
            telemetry = DeepSeekRequestTelemetry(
                label=f"type5_scene_value:band={index}:batch={batch_no}:attempt={attempt + 1}"
            )
            started = perf_counter()
            try:
                with capture_deepseek_request_telemetry(telemetry):
                    result = await self.provider.structured_completion(
                        system_prompt=(
                            "你是类型 5 商品场景与性价比评估助手。"
                            "只评估 candidates 中服务端给出的短编号。"
                            "必须为每一件候选商品返回一次评估，不能遗漏、重复或生成清单外编号。"
                            "scene_score 衡量其与客户场景、用途、明确类目和品牌要求的匹配程度；"
                            "value_score 衡量同类商品的规格、卖点、品牌、协议价、京东价、"
                            "折扣率、销量和好评率"
                            "所体现的综合性价比。不能把最低价格或最高折扣机械等同于高性价比。"
                            "overall_score 由你综合前两项自主判断。"
                            "只能依据输入商品信息，不得编造质量、库存或外部评价。"
                            "严格返回 JSON。"
                        ),
                        user_prompt=f"{payload}{retry_note}",
                        response_model=PptCandidateAssessmentList,
                        max_tokens=min(
                            self.settings.ppt_ai_output_token_budget,
                            self.settings.deepseek_max_tokens,
                        ),
                    )
                self._validate_assessments(result, expected_keys)
                self._log_batch_telemetry(
                    index=index,
                    batch_no=batch_no,
                    candidate_count=len(rows),
                    input_characters=input_characters,
                    retry_count=attempt,
                    elapsed_ms=round((perf_counter() - started) * 1000),
                    telemetry=telemetry,
                    outcome="succeeded",
                )
                return result
            except DeepSeekConfigurationError:
                raise
            except (DeepSeekStructuredOutputError, RecommendationAgentContractError) as exc:
                self._log_batch_telemetry(
                    index=index,
                    batch_no=batch_no,
                    candidate_count=len(rows),
                    input_characters=input_characters,
                    retry_count=attempt,
                    elapsed_ms=round((perf_counter() - started) * 1000),
                    telemetry=telemetry,
                    outcome=f"failed:{type(exc).__name__}",
                )
                if attempt + 1 == self.MAX_PROVIDER_ATTEMPTS:
                    raise
                detail = (
                    exc.safe_validation_summary
                    if isinstance(exc, DeepSeekStructuredOutputError)
                    else str(exc)
                )
                logger.warning(
                    "ppt scene-value assessment retry band=%s batch=%s validation=%s",
                    index,
                    batch_no,
                    detail,
                )
                retry_note = f"\n上一次输出无效。请仅返回完整合法 JSON；脱敏错误：{detail}"
        raise RecommendationAgentContractError("类型 5 AI 未返回完整商品评分")

    async def _select_finalists(
        self,
        *,
        index: int,
        item_count: int,
        scene_context: str,
        finalists: list[dict[str, object]],
    ) -> PptDirectSelectionProposal:
        payload = json.dumps(
            {
                "stage": "final_direct_selection",
                "price_band_index": index,
                "required_item_count": item_count,
                "scene_context": scene_context,
                "candidates": finalists,
            },
            ensure_ascii=False,
            separators=(",", ":"),
        )
        retry_note = ""
        allowed_keys = {str(row["id"]) for row in finalists}
        for attempt in range(self.MAX_PROVIDER_ATTEMPTS):
            telemetry = DeepSeekRequestTelemetry(
                label=f"type5_final_selection:band={index}:attempt={attempt + 1}"
            )
            started = perf_counter()
            try:
                with capture_deepseek_request_telemetry(telemetry):
                    result = await self.provider.structured_completion(
                        system_prompt=(
                            "你是类型 5 最终商品选择助手。根据客户场景和候选中的初评得分，"
                            "从 candidates 返回恰好 required_item_count 件最相关、"
                            "综合性价比最高的商品。"
                            "优先场景适配，再综合规格卖点、品牌和价格价值；"
                            "若客户需求未明确限定单一类目，应在场景相关的候选中尽量覆盖多个"
                            "三级类目；当不同三级类目的商品相关性和性价比接近时，优先选择"
                            "尚未覆盖的三级类目。不得为了凑类目数量选择明显不相关的商品；"
                            "当需求明确限定单一类目或相关类目候选不足时，允许选择同一三级类目的多件商品。"
                            "不能把最低价格或最高折扣机械等同于性价比。"
                            "只能返回服务端给出的短编号，不能重复、遗漏数量或生成清单外商品。"
                            "严格返回 JSON。"
                        ),
                        user_prompt=f"{payload}{retry_note}",
                        response_model=PptDirectSelectionProposal,
                        max_tokens=min(
                            self.settings.ppt_ai_output_token_budget,
                            self.settings.deepseek_max_tokens,
                        ),
                    )
                if len(result.candidate_keys) != item_count:
                    raise RecommendationAgentContractError("类型 5 AI 未返回指定数量的最终商品")
                if any(key not in allowed_keys for key in result.candidate_keys):
                    raise RecommendationAgentContractError("类型 5 AI 返回了清单外商品")
                logger.info(
                    "type5 final selection band=%s finalists=%s input_chars=%s retry_count=%s "
                    "elapsed_ms=%s provider_elapsed_ms=%s prompt_tokens=%s completion_tokens=%s "
                    "total_tokens=%s outcome=succeeded",
                    index,
                    len(finalists),
                    len(payload),
                    attempt,
                    round((perf_counter() - started) * 1000),
                    telemetry.provider_duration_ms,
                    telemetry.prompt_tokens,
                    telemetry.completion_tokens,
                    telemetry.total_tokens,
                )
                return result
            except DeepSeekConfigurationError:
                raise
            except (DeepSeekStructuredOutputError, RecommendationAgentContractError) as exc:
                logger.warning(
                    "type5 final selection band=%s finalists=%s input_chars=%s retry_count=%s "
                    "elapsed_ms=%s provider_elapsed_ms=%s prompt_tokens=%s completion_tokens=%s "
                    "total_tokens=%s outcome=failed:%s",
                    index,
                    len(finalists),
                    len(payload),
                    attempt,
                    round((perf_counter() - started) * 1000),
                    telemetry.provider_duration_ms,
                    telemetry.prompt_tokens,
                    telemetry.completion_tokens,
                    telemetry.total_tokens,
                    type(exc).__name__,
                )
                if attempt + 1 == self.MAX_PROVIDER_ATTEMPTS:
                    raise
                detail = (
                    exc.safe_validation_summary
                    if isinstance(exc, DeepSeekStructuredOutputError)
                    else str(exc)
                )
                logger.warning(
                    "ppt final direct selection retry band=%s validation=%s", index, detail
                )
                retry_note = f"\n上一次输出无效。请仅返回完整合法 JSON；脱敏错误：{detail}"
        raise RecommendationAgentContractError("类型 5 AI 未返回最终商品选择")

    @staticmethod
    def _validate_assessments(
        result: PptCandidateAssessmentList, expected_keys: set[str]
    ) -> None:
        keys = [item.candidate_key for item in result.assessments]
        if len(keys) != len(set(keys)) or set(keys) != expected_keys:
            raise RecommendationAgentContractError("类型 5 AI 商品评分未覆盖完整候选批次")

    @staticmethod
    def _direct_key_map(
        candidates: Sequence[RecommendationCandidate],
    ) -> dict[str, RecommendationCandidate]:
        buckets: dict[tuple[str, str], deque[RecommendationCandidate]] = defaultdict(deque)
        for candidate in candidates:
            product = candidate.product_snapshot
            buckets[
                (str(product.get("category_level3_name") or ""), str(product.get("brand") or ""))
            ].append(candidate)
        ordered = deque(sorted(buckets))
        selected: list[RecommendationCandidate] = []
        while ordered:
            bucket = ordered.popleft()
            selected.append(buckets[bucket].popleft())
            if buckets[bucket]:
                ordered.append(bucket)
        return {f"c{index}": candidate for index, candidate in enumerate(selected, 1)}

    def _assessment_batches(self, rows: list[dict[str, object]]) -> list[list[dict[str, object]]]:
        max_chars = max(4000, int(self.settings.ppt_ai_input_token_budget * 4 * 0.40))
        batches: list[list[dict[str, object]]] = []
        current: list[dict[str, object]] = []
        current_size = 2
        for row in rows:
            row_size = len(json.dumps(row, ensure_ascii=False, separators=(",", ":"))) + 1
            if current and (len(current) >= 80 or current_size + row_size > max_chars):
                batches.append(current)
                current, current_size = [], 2
            current.append(row)
            current_size += row_size
        if current:
            batches.append(current)
        return batches

    def _finalist_rows(
        self,
        ranked_keys: list[str],
        key_map: dict[str, RecommendationCandidate],
        assessments: dict[str, PptCandidateAssessment],
        item_count: int,
    ) -> list[dict[str, object]]:
        desired_count = min(len(ranked_keys), max(item_count * 3, 80))
        max_chars = max(4000, int(self.settings.ppt_ai_input_token_budget * 4 * 0.45))
        finalists: list[dict[str, object]] = []
        current_size = 2
        for key in ranked_keys[:desired_count]:
            row = self._finalist_row(key, key_map[key], assessments[key])
            row_size = len(json.dumps(row, ensure_ascii=False, separators=(",", ":"))) + 1
            if finalists and current_size + row_size > max_chars:
                break
            finalists.append(row)
            current_size += row_size
        return finalists

    @staticmethod
    def _category_diversified_keys(
        ranked_keys: list[str], key_map: dict[str, RecommendationCandidate]
    ) -> list[str]:
        """Interleave score-ranked third-level categories for the final AI shortlist.

        The first item in each bucket remains that category's highest-scoring item.
        This preserves the first-pass AI ranking while giving the final Type-5-only
        selection call a chance to cover different customer-relevant categories.
        """
        buckets: dict[str, deque[str]] = {}
        for key in ranked_keys:
            category = str(
                key_map[key].product_snapshot.get("category_level3_name") or "未分类"
            ).strip() or "未分类"
            buckets.setdefault(category, deque()).append(key)
        ordered_categories = deque(buckets)
        diversified: list[str] = []
        while ordered_categories:
            category = ordered_categories.popleft()
            diversified.append(buckets[category].popleft())
            if buckets[category]:
                ordered_categories.append(category)
        return diversified

    @staticmethod
    def _assessment_row(key: str, candidate: RecommendationCandidate) -> dict[str, object]:
        """Compact first-pass evidence so full-pool scoring can be parallelized safely."""
        product = candidate.product_snapshot
        price = candidate.price_snapshot
        return {
            "id": key,
            "name": PptPlanAgentRunner._short_text(product.get("product_name"), 100),
            "brand": PptPlanAgentRunner._short_text(product.get("brand"), 48),
            "model": PptPlanAgentRunner._short_text(product.get("model"), 64),
            "category": PptPlanAgentRunner._short_text(product.get("category_level3_name"), 64),
            "specification": PptPlanAgentRunner._short_text(
                product.get("product_specification"), 60
            ),
            "selling_points": PptPlanAgentRunner._short_text(product.get("selling_points"), 72),
            "agreement_price": price.get("agreement_price"),
            "jd_price": price.get("jd_price"),
            "discount_rate": price.get("discount_rate"),
            "sales_volume": product.get("sales_volume"),
            "positive_rating": price.get("positive_rating"),
        }

    @staticmethod
    def _finalist_row(
        key: str, candidate: RecommendationCandidate, assessment: PptCandidateAssessment
    ) -> dict[str, object]:
        # Finalists are few, so retain their complete relevant product evidence.
        product = candidate.product_snapshot
        price = candidate.price_snapshot
        row: dict[str, object] = {
            "id": key,
            "name": product.get("product_name"),
            "brand": product.get("brand"),
            "model": product.get("model"),
            "category": product.get("category_level3_name"),
            "specification": product.get("product_specification"),
            "selling_points": product.get("selling_points"),
            "agreement_price": price.get("agreement_price"),
            "jd_price": price.get("jd_price"),
            "discount_rate": price.get("discount_rate"),
            "sales_volume": product.get("sales_volume"),
            "positive_rating": price.get("positive_rating"),
        }
        row["assessment"] = {
            "scene_score": assessment.scene_score,
            "value_score": assessment.value_score,
            "overall_score": assessment.overall_score,
        }
        return row

    @staticmethod
    def _log_batch_telemetry(
        *,
        index: int,
        batch_no: int,
        candidate_count: int,
        input_characters: int,
        retry_count: int,
        elapsed_ms: int,
        telemetry: DeepSeekRequestTelemetry,
        outcome: str,
    ) -> None:
        logger.info(
            "type5 scene-value batch band=%s batch=%s candidates=%s input_chars=%s "
            "retry_count=%s elapsed_ms=%s provider_elapsed_ms=%s prompt_tokens=%s "
            "completion_tokens=%s total_tokens=%s outcome=%s",
            index,
            batch_no,
            candidate_count,
            input_characters,
            retry_count,
            elapsed_ms,
            telemetry.provider_duration_ms,
            telemetry.prompt_tokens,
            telemetry.completion_tokens,
            telemetry.total_tokens,
            outcome,
        )

    @staticmethod
    def _short_text(value: object, max_length: int) -> str | None:
        text = str(value).strip() if value is not None else ""
        return text[:max_length] if text else None

    @staticmethod
    def _validate_provider_result(
        result: PptPlanProposalList,
        band_index: int,
        plan_count: int,
        key_map: dict[str, RecommendationCandidate],
    ) -> None:
        expected_slots = {(band_index, number) for number in range(1, plan_count + 1)}
        actual_slots = {(item.price_band_index, item.plan_no) for item in result.plans}
        if actual_slots != expected_slots or len(actual_slots) != len(result.plans):
            raise RecommendationAgentContractError(
                "类型 5 方案 AI 未按价格档返回完整且唯一的方案"
            )
        if any(
            key not in key_map
            for proposal in result.plans
            for key in proposal.candidate_keys
        ):
            raise RecommendationAgentContractError("类型 5 方案 AI 返回了清单外商品")

    def window_key_map(
        self, candidates: list[RecommendationCandidate]
    ) -> dict[str, RecommendationCandidate]:
        """Rebuild the deterministic short-key mapping used for one AI window."""
        return self._window(candidates)[1]

    def _window(
        self, candidates: list[RecommendationCandidate]
    ) -> tuple[list[dict[str, object]], dict[str, RecommendationCandidate]]:
        buckets: dict[tuple[str, str], deque[RecommendationCandidate]] = defaultdict(deque)
        for candidate in candidates:
            product = candidate.product_snapshot
            buckets[
                (str(product.get("category_level3_name") or ""), str(product.get("brand") or ""))
            ].append(candidate)
        ordered = deque(sorted(buckets))
        selected: list[RecommendationCandidate] = []
        limit_chars = max(800, int(self.settings.ppt_ai_input_token_budget * 4 * 0.65))
        total_chars = 2
        while ordered:
            bucket = ordered.popleft()
            candidate = buckets[bucket].popleft()
            row_size = (
                len(
                    json.dumps(
                        self._row(f"c{len(selected) + 1}", candidate),
                        ensure_ascii=False,
                        separators=(",", ":"),
                    )
                )
                + 1
            )
            if selected and total_chars + row_size > limit_chars:
                break
            selected.append(candidate)
            total_chars += row_size
            if buckets[bucket]:
                ordered.append(bucket)
        if not selected:
            raise RecommendationAgentContractError("类型 5 AI 请求预算不足，无法构造候选窗口")
        key_map = {f"c{index}": candidate for index, candidate in enumerate(selected, 1)}
        return [self._row(key, candidate) for key, candidate in key_map.items()], key_map

    @staticmethod
    def _row(key: str, candidate: RecommendationCandidate) -> dict[str, object]:
        product = candidate.product_snapshot
        return {
            "id": key,
            "name": product.get("product_name"),
            "brand": product.get("brand"),
            "price": str(candidate.price_snapshot.get("agreement_price")),
            "category": product.get("category_level3_name"),
        }

    @classmethod
    def band_candidates(
        cls, band: PptPriceBandInput, candidates: list[RecommendationCandidate]
    ) -> list[RecommendationCandidate]:
        minimum, maximum = band.min_price, band.max_price
        return [
            candidate
            for candidate in candidates
            if (price := cls._decimal(candidate.price_snapshot.get("agreement_price"))) is not None
            and price <= maximum
            and (minimum is None or price >= minimum)
        ]

    @staticmethod
    def _decimal(value: object) -> Decimal | None:
        try:
            return Decimal(str(value)) if value is not None else None
        except (InvalidOperation, TypeError):
            return None
