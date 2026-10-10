"use client";

import { useEffect, useState } from "react";
import {
  Activity,
  CheckCircle2,
  Database,
  Key,
  Lock,
  Monitor,
  Moon,
  RefreshCw,
  Settings,
  Shield,
  Sun,
  User as UserIcon,
} from "lucide-react";
import Sidebar from "../../components/Sidebar";
import { api } from "../../lib/api";
import { formatDate } from "../../lib/utils";
import { AuditLogItem, User } from "../../types";
import { toast } from "../../lib/toast";
import { useTheme } from "../../context/ThemeContext";

export default function SettingsPage() {
  const { theme, setTheme } = useTheme();
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
      toast.success(`Loaded ${logs.length} audit log entries.`, { duration: 2000 });
    } catch (e) {
      console.error(e);
      toast.error("Failed to fetch audit logs. Check admin privileges.", { duration: 4000 });
    } finally {
      setLoadingLogs(false);
    }
  };

  return (
    <div className="flex min-h-[calc(100vh-4rem)]">
      <Sidebar />
      <main className="flex-1 min-w-0 p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto space-y-6 sm:space-y-8 pb-20 lg:pb-8">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-white">System Settings & Security</h1>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            Manage your authenticated profile, tenant isolation credentials, and security compliance audit logs.
          </p>
        </div>

        {/* Profile & Tenant Card */}
        {user && (
          <div className="glass-panel p-4 sm:p-6 rounded-2xl border border-border space-y-4">
            <div className="flex items-center space-x-3">
              <div className="w-9 h-9 sm:w-10 sm:h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 flex items-center justify-center shrink-0">
                <UserIcon className="w-4 h-4 sm:w-5 sm:h-5" />
              </div>
              <div className="min-w-0">
                <h2 className="text-base sm:text-lg font-bold text-white">Authenticated Profile</h2>
                <p className="text-xs text-slate-400">Current RBAC identity and multi-tenant scoping</p>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4 pt-4 border-t border-border/60 text-xs">
              <div>
                <span className="text-slate-500 uppercase tracking-wider block text-[10px] sm:text-xs">Full Name</span>
                <span className="text-white font-semibold mt-0.5 block">{user.full_name || "Enterprise User"}</span>
              </div>
              <div>
                <span className="text-slate-500 uppercase tracking-wider block text-[10px] sm:text-xs">Email Address</span>
                <span className="text-white font-mono mt-0.5 block truncate">{user.email}</span>
              </div>
              <div>
                <span className="text-slate-500 uppercase tracking-wider block text-[10px] sm:text-xs">Assigned Role</span>
                <span className="inline-flex items-center px-2 py-0.5 rounded font-mono text-cyan-400 bg-cyan-500/10 border border-cyan-500/20 font-bold mt-0.5">
                  {user.role}
                </span>
              </div>
              <div>
                <span className="text-slate-500 uppercase tracking-wider block text-[10px] sm:text-xs">Tenant Isolation ID</span>
                <span className="text-emerald-400 font-mono text-[11px] truncate mt-0.5 block" title={user.tenant_id}>
                  {user.tenant_id}
                </span>
              </div>
            </div>
          </div>
        )}

        {/* Appearance & Theme Settings Card */}
        <div className="glass-panel p-4 sm:p-6 rounded-2xl border border-border space-y-4">
          <div className="flex items-center space-x-3">
            <div className="w-9 h-9 sm:w-10 sm:h-10 rounded-xl bg-purple-500/10 border border-purple-500/20 text-purple-400 flex items-center justify-center shrink-0">
              <Sun className="w-4 h-4 sm:w-5 sm:h-5" />
            </div>
            <div className="min-w-0">
              <h2 className="text-base sm:text-lg font-bold text-white">Appearance & Workspace Theme</h2>
              <p className="text-xs text-slate-400">Choose your visual aesthetic, light / dark mode, and contrast style</p>
            </div>
          </div>

          <div className="pt-4 border-t border-border/60">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <button
                type="button"
                onClick={() => {
                  setTheme("light");
                  toast.info("Switched to Light Mode", { duration: 2000 });
                }}
                className={`p-3.5 rounded-xl border flex items-center space-x-3 transition-all text-left ${
                  theme === "light"
                    ? "border-emerald-500 bg-emerald-500/10 text-emerald-400 shadow-sm"
                    : "border-border bg-slate-900/60 hover:bg-slate-800/80 text-slate-300"
                }`}
              >
                <div className="p-2 rounded-lg bg-amber-500/10 text-amber-400 shrink-0">
                  <Sun className="w-4 h-4" />
                </div>
                <div>
                  <p className="text-xs font-bold text-white">Light Mode</p>
                  <p className="text-[10px] text-slate-400">Crisp daytime readability</p>
                </div>
              </button>

              <button
                type="button"
                onClick={() => {
                  setTheme("dark");
                  toast.info("Switched to Dark Mode", { duration: 2000 });
                }}
                className={`p-3.5 rounded-xl border flex items-center space-x-3 transition-all text-left ${
                  theme === "dark"
                    ? "border-emerald-500 bg-emerald-500/10 text-emerald-400 shadow-sm"
                    : "border-border bg-slate-900/60 hover:bg-slate-800/80 text-slate-300"
                }`}
              >
                <div className="p-2 rounded-lg bg-cyan-500/10 text-cyan-400 shrink-0">
                  <Moon className="w-4 h-4" />
                </div>
                <div>
                  <p className="text-xs font-bold text-white">Dark Mode</p>
                  <p className="text-[10px] text-slate-400">Deep blacks & glowing accents</p>
                </div>
              </button>

              <button
                type="button"
                onClick={() => {
                  setTheme("system");
                  toast.info("Theme set to match System preferences", { duration: 2000 });
                }}
                className={`p-3.5 rounded-xl border flex items-center space-x-3 transition-all text-left ${
                  theme === "system"
                    ? "border-emerald-500 bg-emerald-500/10 text-emerald-400 shadow-sm"
                    : "border-border bg-slate-900/60 hover:bg-slate-800/80 text-slate-300"
                }`}
              >
                <div className="p-2 rounded-lg bg-purple-500/10 text-purple-400 shrink-0">
                  <Monitor className="w-4 h-4" />
                </div>
                <div>
                  <p className="text-xs font-bold text-white">System Preference</p>
                  <p className="text-[10px] text-slate-400">Syncs with operating system</p>
                </div>
              </button>
            </div>
          </div>
        </div>



        {/* Admin Compliance Audit Log Inspector */}
        {(user?.role === "ADMIN" || user?.is_superuser) && (
          <div className="glass-panel p-4 sm:p-6 rounded-2xl border border-border space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div className="flex items-center space-x-3">
                <div className="w-9 h-9 sm:w-10 sm:h-10 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 flex items-center justify-center shrink-0">
                  <Shield className="w-4 h-4 sm:w-5 sm:h-5" />
                </div>
                <div>
                  <h2 className="text-base sm:text-lg font-bold text-white">System Audit & Compliance Log</h2>
                  <p className="text-xs text-slate-400">
                    Real-time immutable security event log tracking authentication, ingestion, and queries.
                  </p>
                </div>
              </div>

              <div className="flex items-center space-x-2 self-start sm:self-auto">
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
                  aria-label="Refresh Audit Logs"
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
              <div className="overflow-x-auto -mx-4 sm:mx-0 px-4 sm:px-0">
                <table className="w-full text-left text-xs min-w-[540px]">
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
                        <td className="py-2.5 text-slate-400 whitespace-nowrap">{formatDate(log.created_at)}</td>
                        <td className="py-2.5">
                          <span className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-bold">
                            {log.action}
                          </span>
                        </td>
                        <td className="py-2.5 text-slate-300 truncate max-w-[140px]">{log.resource_type || "N/A"}</td>
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

