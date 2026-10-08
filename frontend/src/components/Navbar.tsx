"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Activity, LogOut, Search, ShieldCheck, User as UserIcon } from "lucide-react";
import { api } from "../lib/api";
import { removeToken } from "../lib/auth";
import { User } from "../types";

export default function Navbar() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [healthy, setHealthy] = useState<boolean>(true);
  const [searchQuery, setSearchQuery] = useState("");

  useEffect(() => {
    api.auth
      .me()
      .then((data) => setUser(data))
      .catch(() => {});

    api.health
      .check()
      .then((res) => setHealthy(res.status === "healthy"))
      .catch(() => setHealthy(false));
  }, []);

  const handleLogout = async () => {
    try {
      await api.auth.logout();
    } catch (_) {}
    removeToken();
    router.push("/login");
  };

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      router.push(`/graph?q=${encodeURIComponent(searchQuery.trim())}`);
    }
  };

  return (
    <header className="h-16 border-b border-border glass-panel sticky top-0 z-40 px-6 flex items-center justify-between">
      <div className="flex items-center space-x-6">
        <Link href="/dashboard" className="flex items-center space-x-2.5 group">
          <div className="w-9 h-9 rounded-lg bg-gradient-to-tr from-emerald-500 to-cyan-500 flex items-center justify-center shadow-lg shadow-emerald-500/20 group-hover:scale-105 transition-transform">
            <Activity className="w-5 h-5 text-black" />
          </div>
          <span className="font-bold text-xl tracking-tight text-white">
            Graph<span className="text-emerald-400">Intel</span>
          </span>
          <span className="text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-mono">
            Production
          </span>
        </Link>

        {/* Global Search Bar */}
        <form onSubmit={handleSearchSubmit} className="hidden md:flex items-center relative">
          <Search className="w-4 h-4 text-slate-500 absolute left-3 pointer-events-none" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search entities, filings, intelligence..."
            className="pl-9 pr-4 py-1.5 rounded-lg bg-slate-900/80 border border-border text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-emerald-500/50 w-64 lg:w-80 transition"
          />
        </form>
      </div>

      <div className="flex items-center space-x-5">
        <div className="flex items-center space-x-2 text-xs text-slate-400 bg-slate-900/60 px-3 py-1.5 rounded-full border border-border">
          <span className={`w-2 h-2 rounded-full ${healthy ? "bg-emerald-500 animate-pulse" : "bg-amber-500"}`} />
          <span>{healthy ? "Systems Operational" : "Degraded"}</span>
        </div>

        {user ? (
          <div className="flex items-center space-x-3">
            <div className="flex items-center space-x-2.5 text-xs text-slate-300">
              <div className="w-8 h-8 rounded-full bg-slate-800 flex items-center justify-center text-slate-300 border border-slate-700">
                <UserIcon className="w-4 h-4 text-emerald-400" />
              </div>
              <div className="hidden md:flex flex-col text-left">
                <span className="font-semibold text-white leading-tight">
                  {user.full_name || user.email.split("@")[0]}
                </span>
                <div className="flex items-center space-x-1.5 mt-0.5">
                  <span className="px-1.5 py-0.2 rounded text-[10px] font-mono bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
                    {user.role || "USER"}
                  </span>
                  {user.tenant_id && (
                    <span className="text-[10px] text-slate-500 font-mono" title={`Tenant: ${user.tenant_id}`}>
                      T-{user.tenant_id.slice(0, 6)}
                    </span>
                  )}
                </div>
              </div>
            </div>
            <button
              onClick={handleLogout}
              className="p-2 text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 rounded-lg transition-colors"
              title="Sign Out"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        ) : (
          <div className="flex items-center space-x-3">
            <Link
              href="/login"
              className="text-sm text-slate-300 hover:text-white px-3 py-1.5 rounded-md hover:bg-slate-800 transition"
            >
              Sign In
            </Link>
            <Link
              href="/register"
              className="text-sm font-medium bg-emerald-500 hover:bg-emerald-600 text-black px-3.5 py-1.5 rounded-md shadow transition"
            >
              Register
            </Link>
          </div>
        )}
      </div>
    </header>
  );
}
