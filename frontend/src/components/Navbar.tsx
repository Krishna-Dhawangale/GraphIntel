"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import {
  Activity,
  LogOut,
  Search,
  User as UserIcon,
  X,
} from "lucide-react";
import { api } from "../lib/api";
import { removeToken } from "../lib/auth";
import { User } from "../types";
import { toast } from "../lib/toast";
import ThemeToggle from "./ThemeToggle";

export default function Navbar() {
  const router = useRouter();
  const pathname = usePathname();
  const [user, setUser] = useState<User | null>(null);
  const [healthy, setHealthy] = useState<boolean>(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [mobileSearchOpen, setMobileSearchOpen] = useState(false);

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

  // Close mobile search on route change
  useEffect(() => {
    setMobileSearchOpen(false);
  }, [pathname]);

  const handleLogout = async () => {
    try {
      await api.auth.logout();
    } catch (_) {}
    removeToken();
    toast.success("Signed out successfully.", { duration: 2000 });
    setTimeout(() => router.push("/login"), 200);
  };

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      router.push(`/graph?q=${encodeURIComponent(searchQuery.trim())}`);
      setMobileSearchOpen(false);
    }
  };

  return (
    <header className="relative h-16 border-b border-border glass-panel sticky top-0 z-40 px-3 sm:px-6 flex items-center justify-between">
      {/* Left: Logo + Desktop Search */}
      <div className="flex items-center gap-3 sm:gap-6 min-w-0">
        <Link href="/dashboard" className="flex items-center gap-2 group shrink-0">
          <div className="w-8 h-8 sm:w-9 sm:h-9 rounded-lg bg-gradient-to-tr from-emerald-500 to-cyan-500 flex items-center justify-center shadow-lg shadow-emerald-500/20 group-hover:scale-105 transition-transform shrink-0">
            <Activity className="w-4 h-4 sm:w-5 sm:h-5 text-black" />
          </div>
          <span className="font-bold text-base sm:text-xl tracking-tight text-white whitespace-nowrap">
            Graph<span className="text-emerald-400">Intel</span>
          </span>
          <span className="hidden sm:inline-block text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-mono">
            Production
          </span>
        </Link>

        {/* Global Search Bar (Desktop only) */}
        <form onSubmit={handleSearchSubmit} className="hidden md:flex items-center relative">
          <Search className="w-4 h-4 text-slate-500 absolute left-3 pointer-events-none" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search entities, filings, intelligence..."
            className="pl-9 pr-4 py-1.5 rounded-lg bg-slate-900/80 border border-border text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-emerald-500/50 w-52 lg:w-80 transition"
          />
        </form>
      </div>

      {/* Right: Actions */}
      <div className="flex items-center gap-1.5 sm:gap-3 shrink-0">
        {/* Mobile Search Toggle */}
        <button
          onClick={() => setMobileSearchOpen(!mobileSearchOpen)}
          className="md:hidden p-2 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition"
          aria-label="Toggle search"
        >
          <Search className="w-4 h-4" />
        </button>

        {/* System Health Badge — hidden on mobile */}
        <div className="hidden sm:flex items-center gap-2 text-xs text-slate-400 bg-slate-900/60 px-3 py-1.5 rounded-full border border-border">
          <span className={`w-2 h-2 rounded-full shrink-0 ${healthy ? "bg-emerald-500 animate-pulse" : "bg-amber-500"}`} />
          <span className="text-[11px] font-medium whitespace-nowrap">{healthy ? "Operational" : "Degraded"}</span>
        </div>

        {/* Theme Toggle — hidden on mobile (available in bottom nav via Sidebar) */}
        <div className="hidden sm:block">
          <ThemeToggle />
        </div>

        {/* User section */}
        {user ? (
          <div className="flex items-center gap-1.5 sm:gap-2">
            {/* Avatar */}
            <div className="w-8 h-8 rounded-full bg-slate-800 flex items-center justify-center text-slate-300 border border-slate-700 shrink-0">
              <UserIcon className="w-4 h-4 text-emerald-400" />
            </div>

            {/* Name + role — desktop only */}
            <div className="hidden md:flex flex-col text-left text-xs text-slate-300">
              <span className="font-semibold text-white leading-tight max-w-[120px] truncate">
                {user.full_name || user.email.split("@")[0]}
              </span>
              <div className="flex items-center gap-1.5 mt-0.5">
                <span className="px-1.5 rounded text-[10px] font-mono bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
                  {user.role || "USER"}
                </span>
                {user.tenant_id && (
                  <span className="text-[10px] text-slate-500 font-mono" title={`Tenant: ${user.tenant_id}`}>
                    T-{user.tenant_id.slice(0, 4)}
                  </span>
                )}
              </div>
            </div>

            {/* Logout */}
            <button
              onClick={handleLogout}
              className="p-2 text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 rounded-lg transition-colors"
              title="Sign Out"
              aria-label="Sign Out"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        ) : (
          <div className="flex items-center gap-1.5 sm:gap-3">
            <Link
              href="/login"
              className="text-xs sm:text-sm text-slate-300 hover:text-white px-2.5 sm:px-3 py-1.5 rounded-md hover:bg-slate-800 transition whitespace-nowrap"
            >
              Sign In
            </Link>
            <Link
              href="/register"
              className="text-xs sm:text-sm font-medium bg-emerald-500 hover:bg-emerald-400 text-black px-3 py-1.5 rounded-md shadow transition whitespace-nowrap"
            >
              Register
            </Link>
          </div>
        )}
      </div>

      {/* Mobile Search Dropdown */}
      {mobileSearchOpen && (
        <div className="md:hidden absolute top-full left-0 right-0 p-3 bg-slate-950/95 border-b border-border shadow-xl z-50 animate-in slide-in-from-top-2">
          <form onSubmit={handleSearchSubmit} className="relative flex items-center">
            <Search className="w-4 h-4 text-slate-500 absolute left-3 pointer-events-none" />
            <input
              type="text"
              autoFocus
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search entities, filings, intelligence..."
              className="w-full pl-9 pr-10 py-2.5 rounded-lg bg-slate-900 border border-border text-sm text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
            />
            <button
              type="button"
              onClick={() => setMobileSearchOpen(false)}
              className="absolute right-2.5 p-1 text-slate-400 hover:text-white"
              aria-label="Close search"
            >
              <X className="w-4 h-4" />
            </button>
          </form>
        </div>
      )}
    </header>
  );
}
