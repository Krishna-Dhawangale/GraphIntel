"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  Calendar,
  CheckCircle2,
  Clock,
  ExternalLink,
  History,
  MessageSquare,
  RefreshCw,
  Search,
  Sparkles,
} from "lucide-react";
import Sidebar from "../../components/Sidebar";
import { api } from "../../lib/api";
import { formatDate } from "../../lib/utils";
import { QueryHistoryItem } from "../../types";

export default function ConversationsPage() {
  const [history, setHistory] = useState<QueryHistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");

  const fetchHistory = async () => {
    setLoading(true);
    try {
      const items = await api.query.history(0, 50);
      setHistory(items);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHistory();
  }, []);

  const filtered = history.filter((h) =>
    h.question.toLowerCase().includes(search.toLowerCase()) ||
    h.answer.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="flex">
      <Sidebar />
      <main className="flex-1 p-8 max-w-7xl mx-auto space-y-8">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-3xl font-extrabold tracking-tight text-white">Research Sessions</h1>
            <p className="text-sm text-slate-400 mt-1">
              Historical record of past GraphRAG queries, synthesized insights, and citations.
            </p>
          </div>
          <button
            onClick={fetchHistory}
            className="p-2.5 rounded-lg border border-border bg-slate-900/60 hover:bg-slate-800 text-slate-400 hover:text-white transition"
            title="Refresh History"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          </button>
        </div>

        {/* Search */}
        <div className="relative max-w-md">
          <Search className="w-4 h-4 text-slate-500 absolute left-3 top-3 pointer-events-none" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search past conversations..."
            className="w-full pl-9 pr-3 py-2 bg-slate-900/80 border border-border rounded-xl text-xs text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
          />
        </div>

        {loading ? (
          <div className="p-12 text-center text-slate-500 text-xs">Loading past research sessions...</div>
        ) : filtered.length === 0 ? (
          <div className="p-12 text-center glass-panel rounded-2xl border border-border text-slate-500 text-xs">
            No research sessions found. Execute your first inquiry in the Research workspace.
          </div>
        ) : (
          <div className="space-y-4">
            {filtered.map((item) => (
              <div
                key={item.id}
                className="glass-panel p-6 rounded-2xl border border-border space-y-3 hover:border-slate-700 transition"
              >
                <div className="flex items-center justify-between text-xs text-slate-400 border-b border-border/40 pb-2">
                  <div className="flex items-center space-x-3">
                    <span className="font-semibold text-emerald-400">Research Query</span>
                    <span>•</span>
                    <span>{formatDate(item.created_at)}</span>
                  </div>
                  <div className="flex items-center space-x-2 font-mono text-[11px]">
                    <span>Retrieval: {item.retrieval_time_ms}ms</span>
                    <span>•</span>
                    <span>LLM: {item.llm_time_ms}ms</span>
                  </div>
                </div>

                <h3 className="text-sm font-bold text-white">{item.question}</h3>
                <p className="text-xs text-slate-300 leading-relaxed font-mono whitespace-pre-wrap bg-slate-950/40 p-4 rounded-xl border border-border/30">
                  {item.answer}
                </p>

                <div className="flex items-center justify-between pt-1 text-xs">
                  <span className="text-slate-400 text-[11px]">
                    {item.sources_count} verifiable citations attached
                  </span>
                  <Link
                    href={`/chat`}
                    className="text-emerald-400 hover:underline flex items-center space-x-1"
                  >
                    <span>Re-open in Research Workspace</span>
                    <ExternalLink className="w-3 h-3" />
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
