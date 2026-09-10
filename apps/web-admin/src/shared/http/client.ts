export interface ApiResponse<T> {
  code: string
  message: string
  data: T
  request_id?: string
}

export interface ErrorResponse {
  code: string
  message: string
  request_id?: string
}

export class HttpError extends Error {
  constructor(readonly status: number, readonly response: ErrorResponse) {
    super(response.message)
  }
}

export interface HttpClientOptions {
  baseUrl?: string
  timeoutMs?: number
  getAuthorization?: () => string | undefined
  onUnauthorized?: () => void
  onForbidden?: () => void
}

export interface RequestOptions {
  authenticated?: boolean
  headers?: HeadersInit
  requestId?: string
}

export class HttpClient {
  constructor(private readonly options: HttpClientOptions = {}) {}

  private async request<T>(
    method: "GET" | "POST" | "PUT" | "PATCH" | "DELETE",
    path: string,
    body?: unknown,
    requestOptions: RequestOptions = {},
  ): Promise<T> {
    const controller = new AbortController()
    const timeout = setTimeout(() => controller.abort(), this.options.timeoutMs ?? 10_000)
    try {
      const isFormData = body instanceof FormData
      const authorization = requestOptions.authenticated === false
        ? undefined
        : this.options.getAuthorization?.()
      const baseUrl = (this.options.baseUrl ?? import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000").replace(/\/$/, "")
      const response = await fetch(`${baseUrl}${path}`, {
        method,
        // API responses drive interactive lists and details. Never let a browser
        // reuse a stale GET response after a successful create/update/delete.
        cache: "no-store",
        headers: {
          Accept: "application/json",
          ...(body === undefined || isFormData ? {} : { "Content-Type": "application/json" }),
          ...(authorization ? { Authorization: authorization } : {}),
          "X-Request-ID": requestOptions.requestId ?? crypto.randomUUID(),
          ...requestOptions.headers,
        },
        body: body === undefined ? undefined : isFormData ? body : JSON.stringify(body),
        signal: controller.signal,
      })

      const rawBody = await response.text()
      let parsedBody: ApiResponse<T> | ErrorResponse
      try {
        parsedBody = rawBody
          ? JSON.parse(rawBody) as ApiResponse<T> | ErrorResponse
          : { code: response.ok ? "OK" : "HTTP_ERROR", message: response.statusText }
      } catch {
        parsedBody = {
          code: "INVALID_RESPONSE",
          message: "服务返回了无法识别的数据",
        }
      }

      if (response.status === 401) this.options.onUnauthorized?.()
      if (response.status === 403) this.options.onForbidden?.()
      if (!response.ok) throw new HttpError(response.status, parsedBody as ErrorResponse)

      const envelope = parsedBody as ApiResponse<T>
      if (envelope.code !== "OK") {
        throw new HttpError(response.status, envelope)
      }
      return envelope.data
    } finally {
      clearTimeout(timeout)
    }
  }

  get<T>(path: string, options?: RequestOptions): Promise<T> {
    return this.request<T>("GET", path, undefined, options)
  }

  async getBlob(path: string, requestOptions: RequestOptions = {}): Promise<Blob> {
    const controller = new AbortController()
    const timeout = setTimeout(() => controller.abort(), this.options.timeoutMs ?? 10_000)
    try {
      const authorization = requestOptions.authenticated === false
        ? undefined
        : this.options.getAuthorization?.()
      const baseUrl = (this.options.baseUrl ?? import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000").replace(/\/$/, "")
      const response = await fetch(`${baseUrl}${path}`, {
        headers: {
          Accept: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
          ...(authorization ? { Authorization: authorization } : {}),
          "X-Request-ID": requestOptions.requestId ?? crypto.randomUUID(),
          ...requestOptions.headers,
        },
        signal: controller.signal,
      })
      if (response.status === 401) this.options.onUnauthorized?.()
      if (response.status === 403) this.options.onForbidden?.()
      if (!response.ok) {
        const rawBody = await response.text()
        let error: ErrorResponse = { code: "HTTP_ERROR", message: response.statusText }
        try {
          error = JSON.parse(rawBody) as ErrorResponse
        } catch {
          // Keep the fallback error when a binary endpoint returns a non-JSON response.
        }
        throw new HttpError(response.status, error)
      }
      return response.blob()
    } finally {
      clearTimeout(timeout)
    }
  }

  post<T, TBody = unknown>(path: string, body?: TBody, options?: RequestOptions): Promise<T> {
    return this.request<T>("POST", path, body, options)
  }

  put<T, TBody = unknown>(path: string, body?: TBody, options?: RequestOptions): Promise<T> {
    return this.request<T>("PUT", path, body, options)
  }

  patch<T, TBody = unknown>(path: string, body?: TBody, options?: RequestOptions): Promise<T> {
    return this.request<T>("PATCH", path, body, options)
  }

  delete<T>(path: string, options?: RequestOptions): Promise<T> {
    return this.request<T>("DELETE", path, undefined, options)
  }
}
