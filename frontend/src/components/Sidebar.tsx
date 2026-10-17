"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  BarChart3,
  FileCode,
  FileText,
  History,
  Settings,
  Share2,
  Sparkles,
} from "lucide-react";
import ThemeToggle from "./ThemeToggle";

export default function Sidebar() {
  const pathname = usePathname();

  const links = [
    { href: "/dashboard", label: "Dashboard", icon: BarChart3 },
    { href: "/documents", label: "Documents", icon: FileText },
    { href: "/graph", label: "Knowledge Graph", icon: Share2 },
    { href: "/chat", label: "Research", icon: Sparkles },
    { href: "/conversations", label: "Conversations", icon: History },
    { href: "/reports", label: "Reports", icon: FileCode },
    { href: "/settings", label: "Settings", icon: Settings },
  ];

  const mobileQuickLinks = [
    { href: "/dashboard", label: "Dash", icon: BarChart3 },
    { href: "/documents", label: "Docs", icon: FileText },
    { href: "/graph", label: "Graph", icon: Share2 },
    { href: "/chat", label: "Research", icon: Sparkles },
    { href: "/reports", label: "Reports", icon: FileCode },
    { href: "/settings", label: "Settings", icon: Settings },
  ];

  return (
    <>
      {/* Desktop Sidebar (visible on lg: screens and up) */}
      <aside className="hidden lg:flex w-64 shrink-0 border-r border-border bg-[#0b101d] flex-col justify-between p-4 min-h-[calc(100vh-4rem)]">
        <div className="space-y-6">
          <div>
            <p className="px-3 text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">
              Intelligence Suite
            </p>
            <nav className="space-y-1">
              {links.map((link) => {
                const Icon = link.icon;
                const isActive = pathname === link.href || (link.href !== "/" && pathname.startsWith(link.href + "/"));
                return (
                  <Link
                    key={link.href}
                    href={link.href}
                    className={`flex items-center space-x-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all ${
                      isActive
                        ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                        : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/60"
                    }`}
                  >
                    <Icon className={`w-4 h-4 ${isActive ? "text-emerald-400" : "text-slate-400"}`} />
                    <span>{link.label}</span>
                  </Link>
                );
              })}
            </nav>
          </div>
        </div>

        <div className="pt-4 border-t border-border/60">
          <ThemeToggle showLabel className="w-full justify-center py-2" />
        </div>
      </aside>

      {/* Mobile Bottom Navigation Bar (visible on mobile / tablet < lg) */}
      <nav className="lg:hidden fixed bottom-0 left-0 right-0 z-40 bg-slate-950/95 backdrop-blur-md border-t border-border px-1 py-1 flex items-center justify-around shadow-2xl safe-area-bottom">
        {mobileQuickLinks.map((link) => {
          const Icon = link.icon;
          const isActive = pathname === link.href || (link.href !== "/" && pathname.startsWith(link.href + "/"));
          return (
            <Link
              key={link.href}
              href={link.href}
              className={`flex flex-col items-center justify-center py-1.5 px-1.5 rounded-lg text-[9px] sm:text-[10px] font-medium transition min-w-0 flex-1 ${
                isActive
                  ? "text-emerald-400"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              <Icon className={`w-4 h-4 mb-0.5 shrink-0 ${isActive ? "text-emerald-400" : "text-slate-400"}`} />
              <span className="truncate w-full text-center">{link.label}</span>
            </Link>
          );
        })}
        {/* Theme toggle in mobile bottom nav (hidden in navbar on mobile) */}
        <div className="sm:hidden flex flex-col items-center justify-center py-1.5 px-1.5 min-w-0 flex-1">
          <ThemeToggle className="!border-0 !bg-transparent !shadow-none !p-0 !rounded-none" />
          <span className="text-[9px] text-slate-400 mt-0.5">Theme</span>
        </div>
      </nav>
    </>
  );
}

