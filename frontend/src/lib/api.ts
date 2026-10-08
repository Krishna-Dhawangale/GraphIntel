import { getRefreshToken, getToken, removeToken, setTokens } from "./auth";
import {
  AuditLogItem,
  Document,
  DocumentChunk,
  GraphVisualizationResponse,
  QueryHistoryItem,
  QueryResponse,
  ResearchReport,
  User,
} from "../types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

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

  let response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });

  // Attempt automatic refresh on 401
  if (response.status === 401 && !endpoint.includes("/auth/login") && !endpoint.includes("/auth/refresh")) {
    const refreshToken = getRefreshToken();
    if (refreshToken && !isRefreshing) {
      isRefreshing = true;
      try {
        const refreshResp = await fetch(`${API_BASE}/auth/refresh`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ refresh_token: refreshToken }),
        });
        if (refreshResp.ok) {
          const data = await refreshResp.json();
          setTokens(data.access_token, data.refresh_token);
          onRefreshed(data.access_token);
          headers["Authorization"] = `Bearer ${data.access_token}`;
          response = await fetch(`${API_BASE}${endpoint}`, { ...options, headers });
        } else {
          removeToken();
          if (typeof window !== "undefined" && !window.location.pathname.includes("/login")) {
            window.location.href = "/login";
          }
        }
      } catch (_) {
        removeToken();
      } finally {
        isRefreshing = false;
      }
    } else if (!refreshToken) {
      if (typeof window !== "undefined" && !window.location.pathname.includes("/login")) {
        removeToken();
        window.location.href = "/login";
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
    me: () => request<User>("/auth/me"),
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
    upload: (file: File, title?: string, syncProcess = true) => {
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
};
