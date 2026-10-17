import { getRefreshToken, getToken, removeToken, setTokens } from "./auth";
import {
  AuditLogItem,
  Document,
  DocumentChunk,
  GraphVisualizationResponse,
  QueryHistoryItem,
  QueryResponse,
  ResearchHistoryDetail,
  ResearchHistoryItem,
  ResearchHistoryListResponse,
  ResearchReport,
  User,
} from "../types";

const DEFAULT_API_BASE =
  process.env.NODE_ENV === "production"
    ? "https://graphintel-api-mrbj.onrender.com/api/v1"
    : "http://localhost:8000/api/v1";

const configuredApiBase = process.env.NEXT_PUBLIC_API_URL || DEFAULT_API_BASE;

// Auto-correct outdated Render subdomain without the random suffix
export const API_BASE = configuredApiBase.replace(
  "https://graphintel-api.onrender.com",
  "https://graphintel-api-mrbj.onrender.com"
);
export const API_DOCS_URL = `${API_BASE}/docs`;

let isRefreshing = false;
let refreshSubscribers: ((token: string) => void)[] = [];

function onRefreshed(token: string) {
  refreshSubscribers.forEach((cb) => cb(token));
  refreshSubscribers = [];
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  if (!(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }

  let response: Response;
  try {
    response = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers,
      credentials: "include",
    });
  } catch (err: any) {
    if (err?.name === "TypeError" || err?.message?.toLowerCase().includes("fetch")) {
      throw new Error(
        `Unable to reach backend API at ${API_BASE}. Please ensure the backend server is running.`
      );
    }
    throw err;
  }

  // Attempt automatic refresh on 401
  if (
    response.status === 401 &&
    !endpoint.includes("/auth/login") &&
    !endpoint.includes("/auth/refresh") &&
    !endpoint.includes("/auth/me")
  ) {
    const isPublicPage =
      typeof window !== "undefined" &&
      (window.location.pathname === "/" ||
        window.location.pathname.startsWith("/login") ||
        window.location.pathname.startsWith("/register") ||
        window.location.pathname.startsWith("/forgot-password") ||
        window.location.pathname.startsWith("/reset-password"));

    const refreshToken = getRefreshToken();
    if (refreshToken && !isRefreshing) {
      isRefreshing = true;
      try {
        const refreshResp = await fetch(`${API_BASE}/auth/refresh`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
          body: JSON.stringify({ refresh_token: refreshToken }),
        });
        if (refreshResp.ok) {
          const data = await refreshResp.json();
          setTokens(data.access_token, data.refresh_token);
          onRefreshed(data.access_token);
          headers["Authorization"] = `Bearer ${data.access_token}`;
          response = await fetch(`${API_BASE}${endpoint}`, { ...options, headers, credentials: "include" });
        } else {
          removeToken();
          if (typeof window !== "undefined" && !isPublicPage) {
            window.location.href = `/login?next=${encodeURIComponent(window.location.pathname)}`;
          }
        }
      } catch (_) {
        removeToken();
      } finally {
        isRefreshing = false;
      }
    } else if (!refreshToken) {
      removeToken();
      if (typeof window !== "undefined" && !isPublicPage) {
        window.location.href = `/login?next=${encodeURIComponent(window.location.pathname)}`;
      }
    }
  }

  if (!response.ok) {
    let errorMsg = `Request failed: ${response.statusText}`;
    try {
      const errorData = await response.json();
      if (errorData.error?.message) {
        errorMsg = errorData.error.message;
      } else if (errorData.detail) {
        errorMsg = typeof errorData.detail === "string" ? errorData.detail : JSON.stringify(errorData.detail);
      }
    } catch (_) {}
    throw new Error(errorMsg);
  }

  if (response.status === 204) {
    return {} as T;
  }

  return response.json();
}

export const api = {
  auth: {
    register: (data: { email: string; password: string; full_name?: string; role?: string }) =>
      request<User>("/auth/register", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    login: (data: { email: string; password: string }) =>
      request<{ access_token: string; refresh_token: string; token_type: string; expires_in: number }>("/auth/login/json", {
        method: "POST",
        body: JSON.stringify(data),
      }),

    refresh: (refreshToken: string) =>
      request<{ access_token: string; refresh_token: string; token_type: string; expires_in: number }>("/auth/refresh", {
        method: "POST",
        body: JSON.stringify({ refresh_token: refreshToken }),
      }),
    logout: () => {
      const refreshToken = getRefreshToken();
      return request<{ message: string }>("/auth/logout", {
        method: "POST",
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
    },
    me: () => {
      if (!getToken()) {
        return Promise.reject(new Error("No token"));
      }
      return request<User>("/auth/me");
    },
    forgotPassword: (email: string) =>
      request<{ message: string }>("/auth/forgot-password", {
        method: "POST",
        body: JSON.stringify({ email }),
      }),
    resetPassword: (token: string, new_password: string) =>
      request<{ message: string }>("/auth/reset-password", {
        method: "POST",
        body: JSON.stringify({ token, new_password }),
      }),
  },
  documents: {
    list: (skip = 0, limit = 50) =>
      request<{ items: Document[]; total: number }>(`/documents?skip=${skip}&limit=${limit}`),
    get: (id: string) => request<Document>(`/documents/${id}`),
    status: (id: string) =>
      request<{ id: string; status: Document["status"]; error_message?: string; total_chunks: number }>(
        `/documents/${id}/status`
      ),
    chunks: (id: string, skip = 0, limit = 100) =>
      request<DocumentChunk[]>(`/documents/${id}/chunks?skip=${skip}&limit=${limit}`),
    upload: (file: File, title?: string, syncProcess = false) => {
      const formData = new FormData();
      formData.append("file", file);
      if (title) formData.append("title", title);
      return request<Document>(`/documents?sync_process=${syncProcess}`, {
        method: "POST",
        body: formData,
      });
    },
    delete: (id: string) =>
      request<void>(`/documents/${id}`, {
        method: "DELETE",
      }),
  },
  graph: {
    visualization: (limit = 150) =>
      request<GraphVisualizationResponse>(`/graph/visualization?limit=${limit}`),
    search: (q = "", entityType?: string, limit = 50) =>
      request<any[]>(
        `/graph/search?q=${encodeURIComponent(q)}${entityType ? `&entity_type=${entityType}` : ""}&limit=${limit}`
      ),
    neighbors: (id: string, maxHops = 1, year?: number) =>
      request<GraphVisualizationResponse>(
        `/graph/neighbors/${id}?max_hops=${maxHops}${year ? `&year=${year}` : ""}`
      ),
    paths: (fromName: string, toName?: string, maxDepth = 3) =>
      request<any[]>(
        `/graph/paths?from_name=${encodeURIComponent(fromName)}${toName ? `&to_name=${encodeURIComponent(toName)}` : ""}&max_depth=${maxDepth}`
      ),
    entity: (id: string) => request<any>(`/graph/entity/${id}`),
    relationships: (id: string, direction = "both", year?: number) =>
      request<any[]>(`/entities/${id}/relationships?direction=${direction}${year ? `&year=${year}` : ""}`),
  },
  query: {
    execute: (data: {
      question: string;
      top_k?: number;
      retrieval_mode?: string;
      max_graph_hops?: number;
      document_ids?: string[];
      temporal_year?: number;
    }) =>
      request<QueryResponse>("/query", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    agent: (data: { question: string }) =>
      request<QueryResponse>("/query/agent", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    history: (skip = 0, limit = 20) =>
      request<QueryHistoryItem[]>(`/query/history?skip=${skip}&limit=${limit}`),
  },
  research: {
    history: (params: {
      q?: string;
      retrieval_mode?: string;
      start_date?: string;
      end_date?: string;
      skip?: number;
      limit?: number;
    } = {}) => {
      const queryParams = new URLSearchParams();
      if (params.q) queryParams.set("q", params.q);
      if (params.retrieval_mode && params.retrieval_mode !== "all") {
        queryParams.set("retrieval_mode", params.retrieval_mode);
      }
      if (params.start_date) queryParams.set("start_date", params.start_date);
      if (params.end_date) queryParams.set("end_date", params.end_date);
      queryParams.set("skip", String(params.skip ?? 0));
      queryParams.set("limit", String(params.limit ?? 20));
      return request<ResearchHistoryListResponse>(`/research/history?${queryParams.toString()}`);
    },
    detail: (id: string) => request<ResearchHistoryDetail>(`/research/history/${id}`),
    delete: (id: string) =>
      request<{ message: string; id: string }>(`/research/history/${id}`, {
        method: "DELETE",
      }),
    clear: () =>
      request<{ message: string; cleared_count: number }>("/research/history", {
        method: "DELETE",
      }),
    migrate: (guestSessionId?: string) =>
      request<{ migrated_count: number; message: string }>("/research/history/migrate", {
        method: "POST",
        body: JSON.stringify({ guest_session_id: guestSessionId }),
      }),
  },
  admin: {
    auditLogs: (limit = 50, offset = 0, action?: string) =>
      request<AuditLogItem[]>(`/admin/audit-logs?limit=${limit}&offset=${offset}${action ? `&action=${action}` : ""}`),
    users: (skip = 0, limit = 50) =>
      request<User[]>(`/admin/users?skip=${skip}&limit=${limit}`),
    updateRole: (userId: string, role: string) =>
      request<User>(`/admin/users/${userId}/role`, {
        method: "PATCH",
        body: JSON.stringify({ role }),
      }),
  },
  health: {
    check: () => request<{ status: string; services: Record<string, string> }>("/health"),
  },
  reports: {
    // Placeholder for future server-side report storage
    list: () => Promise.resolve([] as any[]),
  },
};
