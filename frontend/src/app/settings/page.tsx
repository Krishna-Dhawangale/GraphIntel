"use client";

import { useEffect, useState } from "react";
import {
  Activity,
  CheckCircle2,
  Database,
  ExternalLink,
  Key,
  Lock,
  RefreshCw,
  Server,
  Settings,
  Shield,
  User as UserIcon,
} from "lucide-react";
import Sidebar from "../../components/Sidebar";
import { api } from "../../lib/api";
import { formatDate } from "../../lib/utils";
import { AuditLogItem, User } from "../../types";

export default function SettingsPage() {
  const [user, setUser] = useState<User | null>(null);
  const [auditLogs, setAuditLogs] = useState<AuditLogItem[]>([]);
  const [loadingLogs, setLoadingLogs] = useState(false);
  const [auditActionFilter, setAuditActionFilter] = useState("");

  useEffect(() => {
    api.auth
      .me()
      .then((data) => {
        setUser(data);
        if (data.role === "ADMIN" || data.is_superuser) {
          fetchAuditLogs();
        }
      })
      .catch(() => {});
  }, []);

  const fetchAuditLogs = async () => {
    setLoadingLogs(true);
    try {
      const logs = await api.admin.auditLogs(30, 0, auditActionFilter || undefined);
      setAuditLogs(logs);
    } catch (e) {
      console.error(e);
    } finally {
      setLoadingLogs(false);
    }
  };

  return (
    <div className="flex">
      <Sidebar />
      <main className="flex-1 p-8 max-w-7xl mx-auto space-y-8">
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight text-white">System Settings & Security</h1>
          <p className="text-sm text-slate-400 mt-1">
            Manage your authenticated profile, tenant isolation credentials, and security compliance audit logs.
          </p>
        </div>

        {/* Profile & Tenant Card */}
        {user && (
          <div className="glass-panel p-6 rounded-2xl border border-border space-y-4">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 flex items-center justify-center">
                <UserIcon className="w-5 h-5" />
              </div>
              <div>
                <h2 className="text-lg font-bold text-white">Authenticated Profile</h2>
                <p className="text-xs text-slate-400">Current RBAC identity and multi-tenant scoping</p>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4 pt-4 border-t border-border/60 text-xs">
              <div>
                <span className="text-slate-500 uppercase tracking-wider block">Full Name</span>
                <span className="text-white font-semibold mt-0.5 block">{user.full_name || "Enterprise User"}</span>
              </div>
              <div>
                <span className="text-slate-500 uppercase tracking-wider block">Email Address</span>
                <span className="text-white font-mono mt-0.5 block">{user.email}</span>
              </div>
              <div>
                <span className="text-slate-500 uppercase tracking-wider block">Assigned Role</span>
                <span className="inline-flex items-center px-2 py-0.5 rounded font-mono text-cyan-400 bg-cyan-500/10 border border-cyan-500/20 font-bold mt-0.5">
                  {user.role}
                </span>
              </div>
              <div>
                <span className="text-slate-500 uppercase tracking-wider block">Tenant Isolation ID</span>
                <span className="text-emerald-400 font-mono text-[11px] truncate mt-0.5 block" title={user.tenant_id}>
                  {user.tenant_id}
                </span>
              </div>
            </div>
          </div>
        )}

        {/* Distributed Endpoints & Architecture Links */}
        <div className="glass-panel p-6 rounded-2xl border border-border space-y-4">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-blue-500/10 border border-blue-500/20 text-blue-400 flex items-center justify-center">
              <Server className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white">Platform Infrastructure & Endpoints</h2>
              <p className="text-xs text-slate-400">Direct integration endpoints for SDK and automated workflows</p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-4 border-t border-border/60 text-xs">
            <div className="p-3.5 rounded-xl bg-slate-900/60 border border-border space-y-1">
              <span className="text-slate-400 font-semibold block">FastAPI OpenAPI Specification</span>
              <a
                href="http://localhost:8000/api/v1/docs"
                target="_blank"
                rel="noreferrer"
                className="text-emerald-400 hover:underline flex items-center space-x-1 font-mono text-[11px]"
              >
                <span>/api/v1/docs</span>
                <ExternalLink className="w-3 h-3" />
              </a>
            </div>

            <div className="p-3.5 rounded-xl bg-slate-900/60 border border-border space-y-1">
              <span className="text-slate-400 font-semibold block">Qdrant Vector Engine</span>
              <span className="text-white font-mono text-[11px] block">http://localhost:6333</span>
            </div>

            <div className="p-3.5 rounded-xl bg-slate-900/60 border border-border space-y-1">
              <span className="text-slate-400 font-semibold block">Neo4j Graph Browser</span>
              <a
                href="http://localhost:7474"
                target="_blank"
                rel="noreferrer"
                className="text-cyan-400 hover:underline flex items-center space-x-1 font-mono text-[11px]"
              >
                <span>http://localhost:7474</span>
                <ExternalLink className="w-3 h-3" />
              </a>
            </div>
          </div>
        </div>

        {/* Admin Compliance Audit Log Inspector */}
        {(user?.role === "ADMIN" || user?.is_superuser) && (
          <div className="glass-panel p-6 rounded-2xl border border-border space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div className="flex items-center space-x-3">
                <div className="w-10 h-10 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 flex items-center justify-center">
                  <Shield className="w-5 h-5" />
                </div>
                <div>
                  <h2 className="text-lg font-bold text-white">System Audit & Compliance Log</h2>
                  <p className="text-xs text-slate-400">
                    Real-time immutable security event log tracking authentication, ingestion, and queries.
                  </p>
                </div>
              </div>

              <div className="flex items-center space-x-2">
                <select
                  value={auditActionFilter}
                  onChange={(e) => setAuditActionFilter(e.target.value)}
                  className="px-3 py-1.5 bg-slate-900 border border-border rounded-lg text-xs text-slate-300 focus:outline-none focus:border-emerald-500"
                >
                  <option value="">All Actions</option>
                  <option value="LOGIN">LOGIN</option>
                  <option value="LOGOUT">LOGOUT</option>
                  <option value="DOCUMENT_UPLOAD">DOCUMENT_UPLOAD</option>
                  <option value="DOCUMENT_DELETE">DOCUMENT_DELETE</option>
                  <option value="QUERY">QUERY</option>
                  <option value="GRAPH_QUERY">GRAPH_QUERY</option>
                </select>

                <button
                  onClick={fetchAuditLogs}
                  disabled={loadingLogs}
                  className="p-2 rounded-lg bg-slate-900 border border-border text-slate-300 hover:text-white transition"
                  title="Refresh Audit Logs"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${loadingLogs ? "animate-spin" : ""}`} />
                </button>
              </div>
            </div>

            {loadingLogs ? (
              <div className="p-8 text-center text-xs text-slate-500">Querying security audit logs...</div>
            ) : auditLogs.length === 0 ? (
              <div className="p-8 text-center text-xs text-slate-500">No audit logs recorded for filter.</div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="text-[10px] uppercase tracking-wider text-slate-500 border-b border-border/60">
                    <tr>
                      <th className="pb-2">Timestamp</th>
                      <th className="pb-2">Action</th>
                      <th className="pb-2">Resource</th>
                      <th className="pb-2">Status</th>
                      <th className="pb-2">User / Tenant</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border/40 font-mono text-[11px]">
                    {auditLogs.map((log) => (
                      <tr key={log.id} className="hover:bg-slate-900/40">
                        <td className="py-2.5 text-slate-400">{formatDate(log.created_at)}</td>
                        <td className="py-2.5">
                          <span className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-bold">
                            {log.action}
                          </span>
                        </td>
                        <td className="py-2.5 text-slate-300">{log.resource_type || "N/A"}</td>
                        <td className="py-2.5">
                          <span
                            className={
                              log.status === "SUCCESS"
                                ? "text-emerald-400"
                                : log.status === "DENIED"
                                ? "text-amber-400"
                                : "text-rose-400"
                            }
                          >
                            {log.status}
                          </span>
                        </td>
                        <td className="py-2.5 text-slate-500 truncate max-w-[120px]">
                          {log.tenant_id ? `T-${log.tenant_id.slice(0, 6)}` : "System"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
