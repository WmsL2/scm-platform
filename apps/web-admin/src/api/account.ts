import { http } from "../shared/http/runtime"
import type { AccountRole, AccountUser, Page, Permission, RoleCreateRequest } from "../types/account"

export const accountApi = {
  register: (username: string, password: string) => http.post<AccountUser>("/api/v1/auth/register", { username, password }, { authenticated: false }),
  changePassword: (current_password: string, new_password: string) => http.post<{ status: string }>("/api/v1/auth/change-password", { current_password, new_password }),
  users: () => http.get<Page<AccountUser>>("/api/v1/admin/users"),
  setUserRoles: (id: string, role_ids: string[]) => http.put<AccountUser>(`/api/v1/admin/users/${id}/roles`, { role_ids }),
  deleteUser: (id: string) => http.delete<{ status: string }>(`/api/v1/admin/users/${id}`),
  roles: () => http.get<AccountRole[]>("/api/v1/admin/roles"),
  createRole: (payload: RoleCreateRequest) => http.post<AccountRole>("/api/v1/admin/roles", payload),
  setRolePermissions: (id: string, permission_ids: string[]) => http.put<AccountRole>(`/api/v1/admin/roles/${id}/permissions`, { permission_ids }),
  permissions: () => http.get<Permission[]>("/api/v1/admin/permissions"),
  registrations: () => http.get<Page<AccountUser>>("/api/v1/admin/registration-requests"),
  registrationHistory: (page = 1, pageSize = 20) => http.get<Page<AccountUser>>(
    `/api/v1/admin/registration-history?page=${page}&page_size=${pageSize}`,
  ),
  review: (id: string, approve: boolean, review_note?: string) => http.post<AccountUser>(`/api/v1/admin/registration-requests/${id}/commands/${approve ? "approve" : "reject"}`, { review_note }),
}
