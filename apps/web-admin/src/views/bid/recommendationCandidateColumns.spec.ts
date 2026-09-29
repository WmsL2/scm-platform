import { describe, expect, it } from "vitest"
import {
  RECOMMENDATION_CANDIDATE_OPTIONAL_COLUMNS,
  restoreRecommendationCandidateOptionalColumns,
  updateRecommendationCandidateOptionalColumns,
} from "./recommendationCandidateColumns"

describe("recommendation candidate display columns", () => {
  it("shares the product master column definitions while fixing image, SKU and name", () => {
    expect(RECOMMENDATION_CANDIDATE_OPTIONAL_COLUMNS.map(({ key }) => key)).toContain("category_level3_name")
    expect(RECOMMENDATION_CANDIDATE_OPTIONAL_COLUMNS.map(({ key }) => key)).toContain("jd_price")
    expect(RECOMMENDATION_CANDIDATE_OPTIONAL_COLUMNS.map(({ key }) => key)).toContain("agreement_price")
    expect(RECOMMENDATION_CANDIDATE_OPTIONAL_COLUMNS.map(({ key }) => key)).not.toContain("image_reference")
    expect(RECOMMENDATION_CANDIDATE_OPTIONAL_COLUMNS.map(({ key }) => key)).not.toContain("sku")
    expect(RECOMMENDATION_CANDIDATE_OPTIONAL_COLUMNS.map(({ key }) => key)).not.toContain("product_name")
  })

  it("restores supported saved choices in order and falls back to practical defaults", () => {
    expect(restoreRecommendationCandidateOptionalColumns('["jd_price","category_level3_name","jd_price","unknown"]')).toEqual([
      "jd_price",
      "category_level3_name",
    ])
    expect(restoreRecommendationCandidateOptionalColumns("not json")).toContain("agreement_price")
  })

  it("adds and removes one field without duplicating it", () => {
    expect(updateRecommendationCandidateOptionalColumns(["jd_price"], "jd_price", true)).toEqual(["jd_price"])
    expect(updateRecommendationCandidateOptionalColumns(["jd_price"], "agreement_price", true)).toEqual([
      "jd_price",
      "agreement_price",
    ])
    expect(updateRecommendationCandidateOptionalColumns(["jd_price"], "jd_price", false)).toEqual([])
  })
})
