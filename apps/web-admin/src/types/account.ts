export interface AccountUser { id: string; username: string; user_status: string; role_ids: string[]; role_names: string[]; reviewed_by: string | null; reviewed_at: string | null; review_note: string | null }
export interface AccountRole { id: string; role_code: string; role_name: string; permission_ids: string[] }
export interface Permission { id: string; permission_code: string; permission_name: string; permission_type: string }
export interface Page<T> { items: T[]; total: number; page: number; page_size: number }
