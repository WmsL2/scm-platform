import { http } from "../shared/http/runtime"
import type { ProductDetail, ProductListParams, ProductPage } from "../types/catalog"

function path(suffix = ""): string {
  return `/api/v1/products${suffix}`
}

function listQuery(params: ProductListParams): string {
  const query = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== "") query.set(key, String(value))
  }
  const serialized = query.toString()
  return serialized ? `?${serialized}` : ""
}

export const productApi = {
  list(params: ProductListParams = {}): Promise<ProductPage> {
    return http.get<ProductPage>(path(listQuery(params)))
  },

  get(id: string): Promise<ProductDetail> {
    return http.get<ProductDetail>(path(`/${id}`))
  },

  updateCost(id: string, costPrice: string): Promise<ProductDetail> {
    return http.patch<ProductDetail, { cost_price: string }>(path(`/${id}/cost-price`), {
      cost_price: costPrice,
    })
  },
}
