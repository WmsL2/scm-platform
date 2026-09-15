export interface Category { id: string; source_type: "MALL_LEVEL3" | "INDUSTRIAL_LINE"; level1_external_id?: string | null; level1_name: string; level2_external_id?: string | null; level2_name: string; level3_external_id?: string | null; level3_name: string; deduction_rate: string; is_active: boolean; shelf_flag?: string | null; business_unit?: string | null }
export type CategoryPayload = Omit<Category, "id"> 
export interface CategoryPage { items: Category[]; total: number; page: number; page_size: number }
export interface CategoryImportResult { total: number; success: number; skipped: number; failed: number; errors: { row_number: number; field: string | null; value: string | null; reason: string }[] }
