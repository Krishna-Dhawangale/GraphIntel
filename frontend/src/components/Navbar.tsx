"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import {
  Activity,
  BarChart3,
  FileCode,
  FileText,
  History,
  LogOut,
  Menu,
  Search,
  Settings,
  Share2,
  ShieldCheck,
  Sparkles,
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
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
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

  // Close mobile menu on route change
  useEffect(() => {
    setMobileMenuOpen(false);
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
      setMobileMenuOpen(false);
    }
  };

  const navLinks = [
    { href: "/dashboard", label: "Dashboard", icon: BarChart3 },
    { href: "/documents", label: "Documents", icon: FileText },
    { href: "/graph", label: "Knowledge Graph", icon: Share2 },
    { href: "/chat", label: "Research", icon: Sparkles },
    { href: "/conversations", label: "Conversations", icon: History },
    { href: "/reports", label: "Reports", icon: FileCode },
    { href: "/settings", label: "Settings", icon: Settings },
  ];

  return (
    <header className="h-16 border-b border-border glass-panel sticky top-0 z-40 px-4 sm:px-6 flex items-center justify-between">
      <div className="flex items-center space-x-3 sm:space-x-6">
        {/* Mobile Menu Toggle Button */}
        <button
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          className="lg:hidden p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800/80 transition"
          aria-label="Toggle navigation menu"
        >
          {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </button>

        <Link href="/dashboard" className="flex items-center space-x-2.5 group">
          <div className="w-8 h-8 sm:w-9 sm:h-9 rounded-lg bg-gradient-to-tr from-emerald-500 to-cyan-500 flex items-center justify-center shadow-lg shadow-emerald-500/20 group-hover:scale-105 transition-transform">
            <Activity className="w-4 h-4 sm:w-5 sm:h-5 text-black" />
          </div>
          <span className="font-bold text-lg sm:text-xl tracking-tight text-white">
            Graph<span className="text-emerald-400">Intel</span>
          </span>
          <span className="hidden sm:inline-block text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-mono">
            Production
          </span>
        </Link>

        {/* Global Search Bar (Desktop) */}
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

      <div className="flex items-center space-x-2 sm:space-x-4">
        {/* Mobile Search Toggle */}
        <button
          onClick={() => setMobileSearchOpen(!mobileSearchOpen)}
          className="md:hidden p-2 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition"
          aria-label="Toggle search"
        >
          <Search className="w-4 h-4" />
        </button>

        {/* System Health Badge */}
        <div className="hidden sm:flex items-center space-x-2 text-xs text-slate-400 bg-slate-900/60 px-3 py-1.5 rounded-full border border-border">
          <span className={`w-2 h-2 rounded-full ${healthy ? "bg-emerald-500 animate-pulse" : "bg-amber-500"}`} />
          <span className="text-[11px] font-medium">{healthy ? "Operational" : "Degraded"}</span>
        </div>

        <ThemeToggle />

        {user ? (
          <div className="flex items-center space-x-2 sm:space-x-3">
            <div className="flex items-center space-x-2 text-xs text-slate-300">
              <div className="w-8 h-8 rounded-full bg-slate-800 flex items-center justify-center text-slate-300 border border-slate-700 shrink-0">
                <UserIcon className="w-4 h-4 text-emerald-400" />
              </div>
              <div className="hidden md:flex flex-col text-left">
                <span className="font-semibold text-white leading-tight max-w-[120px] truncate">
                  {user.full_name || user.email.split("@")[0]}
                </span>
                <div className="flex items-center space-x-1.5 mt-0.5">
                  <span className="px-1.5 py-0.2 rounded text-[10px] font-mono bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
                    {user.role || "USER"}
                  </span>
                  {user.tenant_id && (
                    <span className="text-[10px] text-slate-500 font-mono" title={`Tenant: ${user.tenant_id}`}>
                      T-{user.tenant_id.slice(0, 4)}
                    </span>
                  )}
                </div>
              </div>
            </div>
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
          <div className="flex items-center space-x-2 sm:space-x-3">
            <Link
              href="/login"
              className="text-xs sm:text-sm text-slate-300 hover:text-white px-2.5 sm:px-3 py-1.5 rounded-md hover:bg-slate-800 transition"
            >
              Sign In
            </Link>
            <Link
              href="/register"
              className="text-xs sm:text-sm font-medium bg-emerald-500 hover:bg-emerald-400 text-black px-3 sm:px-3.5 py-1.5 rounded-md shadow transition"
            >
              Register
            </Link>
          </div>
        )}
      </div>

      {/* Mobile Search Dropdown */}
      {mobileSearchOpen && (
        <div className="md:hidden absolute top-16 left-0 right-0 p-3 bg-slate-950/95 border-b border-border shadow-xl z-50 animate-in slide-in-from-top-2">
          <form onSubmit={handleSearchSubmit} className="relative flex items-center">
            <Search className="w-4 h-4 text-slate-500 absolute left-3 pointer-events-none" />
            <input
              type="text"
              autoFocus
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search entities, filings, intelligence..."
              className="w-full pl-9 pr-10 py-2 rounded-lg bg-slate-900 border border-border text-xs text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
            />
            <button
              type="button"
              onClick={() => setMobileSearchOpen(false)}
              className="absolute right-2.5 p-1 text-slate-400 hover:text-white"
            >
              <X className="w-4 h-4" />
            </button>
          </form>
        </div>
      )}

      {/* Mobile Navigation Drawer / Overlay */}
      {mobileMenuOpen && (
        <div className="lg:hidden fixed inset-x-0 top-16 bottom-0 z-50 bg-slate-950/90 backdrop-blur-md flex flex-col justify-between p-5 border-t border-border overflow-y-auto animate-in slide-in-from-left duration-200">
          <div className="space-y-5">
            <div>
              <p className="px-3 text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">
                Intelligence Suite
              </p>
              <nav className="space-y-1">
                {navLinks.map((link) => {
                  const Icon = link.icon;
                  const isActive = pathname === link.href || (link.href !== "/" && pathname.startsWith(link.href + "/"));
                  return (
                    <Link
                      key={link.href}
                      href={link.href}
                      onClick={() => setMobileMenuOpen(false)}
                      className={`flex items-center space-x-3 px-3.5 py-3 rounded-xl text-sm font-medium transition-all ${
                        isActive
                          ? "bg-emerald-500/15 text-emerald-400 border border-emerald-500/30"
                          : "text-slate-300 hover:text-white hover:bg-slate-900/80"
                      }`}
                    >
                      <Icon className={`w-5 h-5 ${isActive ? "text-emerald-400" : "text-slate-400"}`} />
                      <span>{link.label}</span>
                    </Link>
                  );
                })}
              </nav>
            </div>

            {/* Architecture Stack info on mobile */}
            <div className="pt-4 border-t border-border/60">
              <p className="px-3 text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">
                Architecture Engine
              </p>
              <div className="grid grid-cols-2 gap-2 px-3 text-xs">
                <div className="p-2 rounded-lg bg-slate-900/60 border border-border/60 flex items-center justify-between">
                  <span className="text-slate-400">Vector Store</span>
                  <span className="text-emerald-400 font-mono text-[11px]">Qdrant</span>
                </div>
                <div className="p-2 rounded-lg bg-slate-900/60 border border-border/60 flex items-center justify-between">
                  <span className="text-slate-400">Graph DB</span>
                  <span className="text-cyan-400 font-mono text-[11px]">Neo4j</span>
                </div>
                <div className="p-2 rounded-lg bg-slate-900/60 border border-border/60 flex items-center justify-between">
                  <span className="text-slate-400">Relational DB</span>
                  <span className="text-blue-400 font-mono text-[11px]">Postgres</span>
                </div>
                <div className="p-2 rounded-lg bg-slate-900/60 border border-border/60 flex items-center justify-between">
                  <span className="text-slate-400">Agentic</span>
                  <span className="text-emerald-400 font-mono text-[11px]">LangGraph</span>
                </div>
              </div>
            </div>
          </div>

          {/* Theme toggle & User profile / session in drawer footer */}
          <div className="pt-4 border-t border-border/60 space-y-3">
            <ThemeToggle showLabel className="w-full justify-center py-2.5" />
            {user ? (
              <div className="flex items-center justify-between p-3 rounded-xl bg-slate-900/80 border border-border">
                <div className="flex items-center space-x-3 min-w-0">
                  <div className="w-9 h-9 rounded-full bg-slate-800 flex items-center justify-center text-emerald-400 border border-slate-700 shrink-0">
                    <UserIcon className="w-4 h-4" />
                  </div>
                  <div className="min-w-0">
                    <p className="text-xs font-bold text-white truncate">
                      {user.full_name || user.email}
                    </p>
                    <p className="text-[10px] text-slate-400 font-mono">
                      Role: <span className="text-cyan-400">{user.role || "USER"}</span>
                    </p>
                  </div>
                </div>
                <button
                  onClick={handleLogout}
                  className="p-2 text-slate-400 hover:text-rose-400 rounded-lg hover:bg-rose-500/10 transition"
                  title="Logout"
                >
                  <LogOut className="w-4 h-4" />
                </button>
              </div>
            ) : (
              <div className="flex items-center space-x-2">
                <Link
                  href="/login"
                  onClick={() => setMobileMenuOpen(false)}
                  className="flex-1 py-2 text-center text-xs font-medium text-white bg-slate-900 border border-border rounded-lg"
                >
                  Sign In
                </Link>
                <Link
                  href="/register"
                  onClick={() => setMobileMenuOpen(false)}
                  className="flex-1 py-2 text-center text-xs font-semibold text-black bg-emerald-500 rounded-lg"
                >
                  Register
                </Link>
              </div>
            )}
          </div>
        </div>
      )}
    </header>
  );
}

