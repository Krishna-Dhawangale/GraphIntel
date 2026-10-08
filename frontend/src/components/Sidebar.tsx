"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  BarChart3,
  ExternalLink,
  FileCode,
  FileText,
  History,
  MessageSquare,
  Settings,
  Share2,
  Shield,
  Sparkles,
} from "lucide-react";

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

  return (
    <aside className="w-64 border-r border-border bg-[#0b101d] flex flex-col justify-between p-4 min-h-[calc(100vh-4rem)]">
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

        <div className="pt-4 border-t border-border/60">
          <p className="px-3 text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">
            Architecture
          </p>
          <div className="space-y-2 px-3 text-xs text-slate-400">
            <div className="flex items-center justify-between py-1 border-b border-border/30">
              <span>Vector Store</span>
              <span className="text-emerald-400 font-mono">Qdrant</span>
            </div>
            <div className="flex items-center justify-between py-1 border-b border-border/30">
              <span>Graph Store</span>
              <span className="text-cyan-400 font-mono">Neo4j</span>
            </div>
            <div className="flex items-center justify-between py-1 border-b border-border/30">
              <span>Cache & Limit</span>
              <span className="text-rose-400 font-mono">Redis</span>
            </div>
            <div className="flex items-center justify-between py-1 border-b border-border/30">
              <span>Relational DB</span>
              <span className="text-blue-400 font-mono">PostgreSQL</span>
            </div>
            <div className="flex items-center justify-between py-1">
              <span>Agentic Workflow</span>
              <span className="text-emerald-400 font-mono">LangGraph</span>
            </div>
          </div>
        </div>
      </div>

      <div className="p-3 bg-slate-900/80 rounded-xl border border-border/70 text-xs">
        <div className="flex items-center space-x-2 text-emerald-400 mb-1">
          <Shield className="w-4 h-4" />
          <span className="font-semibold">Security Isolation</span>
        </div>
        <p className="text-slate-400 text-[11px] leading-relaxed">
          Tenant-isolated vector retrieval with strict prompt injection boundaries.
        </p>
        <a
          href="http://localhost:8000/api/v1/docs"
          target="_blank"
          rel="noreferrer"
          className="mt-2.5 inline-flex items-center space-x-1 text-cyan-400 hover:underline"
        >
          <span>FastAPI Swagger Docs</span>
          <ExternalLink className="w-3 h-3" />
        </a>
      </div>
    </aside>
  );
}
