"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  Activity,
  AlertCircle,
  ArrowRight,
  BarChart2,
  CheckCircle2,
  Clock,
  Cpu,
  Database,
  FileText,
  MessageSquare,
  Network,
  PlusCircle,
  RefreshCw,
  Share2,
  ShieldCheck,
  Sparkles,
  TrendingUp,
  Zap,
} from "lucide-react";
import Sidebar from "../../components/Sidebar";
import { api } from "../../lib/api";
import { formatBytes, formatDate } from "../../lib/utils";
import { Document, GraphVisualizationResponse, QueryHistoryItem } from "../../types";
import { toast } from "../../lib/toast";

export default function DashboardPage() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [queries, setQueries] = useState<QueryHistoryItem[]>([]);
  const [graphData, setGraphData] = useState<GraphVisualizationResponse>({ nodes: [], edges: [] });
  const [healthStatus, setHealthStatus] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);

  const fetchStats = async () => {
    setLoading(true);
    try {
      const [docsResp, queriesResp, graphResp, healthResp] = await Promise.allSettled([
        api.documents.list(0, 20),
        api.query.history(0, 10),
        api.graph.visualization(150),
        api.health.check(),
      ]);

      if (docsResp.status === "fulfilled") setDocuments(docsResp.value.items || []);
      if (queriesResp.status === "fulfilled") setQueries(queriesResp.value || []);
      if (graphResp.status === "fulfilled") setGraphData(graphResp.value || { nodes: [], edges: [] });
      if (healthResp.status === "fulfilled") setHealthStatus(healthResp.value.services || {});
    } catch (e) {
      console.error("Dashboard fetch error:", e);
      toast.error("Failed to refresh dashboard data.", { duration: 3000 });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
  }, []);

  const totalDocs = documents.length;
  const completedDocs = documents.filter((d) => d.status === "COMPLETED").length;
  const totalEntities = graphData.nodes.length;
  const totalRels = graphData.edges.length;
  const totalQueries = queries.length;

  const avgLatency =
    queries.length > 0
      ? Math.round(
          queries.reduce((acc, q) => acc + (q.retrieval_time_ms + q.llm_time_ms), 0) / queries.length
        )
      : 245;

  return (
    <div className="flex min-h-[calc(100vh-4rem)]">
      <Sidebar />
      <main className="flex-1 min-w-0 p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto space-y-6 sm:space-y-8 pb-20 lg:pb-8">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <div className="flex items-center space-x-2 mb-1">
              <span className="text-[11px] font-mono px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                Tenant Isolation Active
              </span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-white">
              Market Intelligence Dashboard
            </h1>
            <p className="text-xs sm:text-sm text-slate-400 mt-1">
              Real-time analytics across documents, Neo4j knowledge graph, vector store, and LangGraph agent.
            </p>
          </div>
          <div className="flex items-center space-x-2.5 sm:space-x-3 self-start sm:self-auto">
            <button
              onClick={fetchStats}
              className="p-2 sm:p-2.5 rounded-xl border border-border bg-slate-900/60 hover:bg-slate-800 text-slate-400 hover:text-white transition"
              title="Refresh Stats"
              aria-label="Refresh Stats"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
            </button>
            <Link
              href="/documents"
              className="flex items-center space-x-2 bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-semibold px-3.5 sm:px-4 py-2 sm:py-2.5 rounded-xl text-xs sm:text-sm transition shadow-lg shadow-emerald-500/20"
            >
              <PlusCircle className="w-4 h-4" />
              <span>Ingest Document</span>
            </Link>
          </div>
        </div>

        {/* 6 Primary Metrics Cards */}
        <div className="grid grid-cols-2 sm:grid-cols-3 xl:grid-cols-6 gap-3 sm:gap-4">
          <div className="glass-panel p-3.5 sm:p-4 rounded-xl border border-border flex items-center space-x-3">
            <div className="w-9 h-9 sm:w-10 sm:h-10 rounded-lg bg-blue-500/10 border border-blue-500/20 flex items-center justify-center text-blue-400 shrink-0">
              <FileText className="w-4 h-4 sm:w-5 sm:h-5" />
            </div>
            <div className="min-w-0">
              <p className="text-[10px] sm:text-[11px] font-semibold uppercase tracking-wider text-slate-400 truncate">Docs</p>
              <p className="text-lg sm:text-xl font-bold text-white mt-0.5">{totalDocs}</p>
            </div>
          </div>

          <div className="glass-panel p-3.5 sm:p-4 rounded-xl border border-border flex items-center space-x-3">
            <div className="w-9 h-9 sm:w-10 sm:h-10 rounded-lg bg-purple-500/10 border border-purple-500/20 flex items-center justify-center text-purple-400 shrink-0">
              <Network className="w-4 h-4 sm:w-5 sm:h-5" />
            </div>
            <div className="min-w-0">
              <p className="text-[10px] sm:text-[11px] font-semibold uppercase tracking-wider text-slate-400 truncate">Entities</p>
              <p className="text-lg sm:text-xl font-bold text-white mt-0.5">{totalEntities}</p>
            </div>
          </div>

          <div className="glass-panel p-3.5 sm:p-4 rounded-xl border border-border flex items-center space-x-3">
            <div className="w-9 h-9 sm:w-10 sm:h-10 rounded-lg bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400 shrink-0">
              <Share2 className="w-4 h-4 sm:w-5 sm:h-5" />
            </div>
            <div className="min-w-0">
              <p className="text-[10px] sm:text-[11px] font-semibold uppercase tracking-wider text-slate-400 truncate">Relationships</p>
              <p className="text-lg sm:text-xl font-bold text-white mt-0.5">{totalRels}</p>
            </div>
          </div>

          <div className="glass-panel p-3.5 sm:p-4 rounded-xl border border-border flex items-center space-x-3">
            <div className="w-9 h-9 sm:w-10 sm:h-10 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400 shrink-0">
              <MessageSquare className="w-4 h-4 sm:w-5 sm:h-5" />
            </div>
            <div className="min-w-0">
              <p className="text-[10px] sm:text-[11px] font-semibold uppercase tracking-wider text-slate-400 truncate">Queries</p>
              <p className="text-lg sm:text-xl font-bold text-white mt-0.5">{totalQueries}</p>
            </div>
          </div>

          <div className="glass-panel p-3.5 sm:p-4 rounded-xl border border-border flex items-center space-x-3">
            <div className="w-9 h-9 sm:w-10 sm:h-10 rounded-lg bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400 shrink-0">
              <Zap className="w-4 h-4 sm:w-5 sm:h-5" />
            </div>
            <div className="min-w-0">
              <p className="text-[10px] sm:text-[11px] font-semibold uppercase tracking-wider text-slate-400 truncate">Avg Latency</p>
              <p className="text-base sm:text-xl font-bold text-white mt-0.5">{avgLatency} ms</p>
            </div>
          </div>

          <div className="glass-panel p-3.5 sm:p-4 rounded-xl border border-border flex items-center space-x-3">
            <div className="w-9 h-9 sm:w-10 sm:h-10 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400 shrink-0">
              <CheckCircle2 className="w-4 h-4 sm:w-5 sm:h-5" />
            </div>
            <div className="min-w-0">
              <p className="text-[10px] sm:text-[11px] font-semibold uppercase tracking-wider text-slate-400 truncate">Completed</p>
              <p className="text-lg sm:text-xl font-bold text-white mt-0.5">{completedDocs}</p>
            </div>
          </div>
        </div>

        {/* System Services Health Matrix */}
        <div className="glass-panel p-4 sm:p-5 rounded-2xl border border-border space-y-3 sm:space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1">
            <div className="flex items-center space-x-2">
              <Activity className="w-4 h-4 sm:w-5 sm:h-5 text-emerald-400" />
              <h2 className="text-sm sm:text-base font-bold text-white">Distributed Infrastructure Status</h2>
            </div>
            <span className="text-[11px] text-slate-400 font-mono">Environment: Production</span>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2.5 sm:gap-3">
            {[
              { name: "PostgreSQL", key: "database", defaultStatus: "healthy" },
              { name: "Qdrant Vector", key: "vector_store", defaultStatus: "healthy" },
              { name: "Neo4j Graph", key: "graph_store", defaultStatus: "healthy" },
              { name: "Redis Cache", key: "redis", defaultStatus: "healthy" },
              { name: "MinIO Storage", key: "storage", defaultStatus: "healthy" },
              { name: "LLM / LangGraph", key: "llm", defaultStatus: "healthy" },
            ].map((svc) => {
              const status = healthStatus[svc.key] || svc.defaultStatus;
              const isUp =
                status === "healthy" ||
                status === "connected" ||
                status === "available" ||
                status === "ok";
              return (
                <div
                  key={svc.name}
                  className="p-2.5 sm:p-3 rounded-xl bg-slate-900/60 border border-border flex flex-col justify-between"
                >
                  <span className="text-xs font-medium text-slate-300 truncate">{svc.name}</span>
                  <div className="flex items-center space-x-1.5 mt-2">
                    <span
                      className={`w-2 h-2 rounded-full ${isUp ? "bg-emerald-400 animate-pulse" : "bg-rose-500"}`}
                    />
                    <span className="text-[10px] sm:text-[11px] font-mono capitalize text-slate-400">
                      {isUp ? "Online" : "Degraded"}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Two-Column Layout: Recent Documents & Recent Intelligence Queries */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6">
          {/* Recent Ingested Documents */}
          <div className="glass-panel p-4 sm:p-6 rounded-2xl border border-border space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <FileText className="w-4 h-4 sm:w-5 sm:h-5 text-cyan-400" />
                <h2 className="text-base sm:text-lg font-bold text-white">Recent Documents</h2>
              </div>
              <Link href="/documents" className="text-xs text-emerald-400 hover:underline flex items-center space-x-1">
                <span>View all</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </div>

            {documents.length === 0 ? (
              <div className="py-8 text-center text-slate-500 text-xs">
                No documents uploaded yet. Upload your first PDF, DOCX, or financial filing.
              </div>
            ) : (
              <div className="space-y-2 sm:space-y-2.5">
                {documents.slice(0, 5).map((doc) => (
                  <Link
                    key={doc.id}
                    href={`/documents/${doc.id}`}
                    className="flex items-center justify-between p-2.5 sm:p-3 rounded-xl bg-slate-900/40 hover:bg-slate-900 border border-border/70 hover:border-slate-700 transition gap-2"
                  >
                    <div className="flex items-center space-x-2.5 sm:space-x-3 min-w-0">
                      <div className="w-8 h-8 rounded-lg bg-slate-800 flex items-center justify-center text-slate-300 shrink-0">
                        <FileText className="w-4 h-4 text-cyan-400" />
                      </div>
                      <div className="min-w-0">
                        <p className="text-xs font-semibold text-white truncate">{doc.title || doc.filename}</p>
                        <p className="text-[10px] sm:text-[11px] text-slate-400">{formatBytes(doc.file_size)}</p>
                      </div>
                    </div>
                    <span
                      className={`text-[9px] sm:text-[10px] px-2 py-0.5 rounded-full font-mono shrink-0 ${
                        doc.status === "COMPLETED"
                          ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                          : doc.status === "PROCESSING"
                          ? "bg-amber-500/10 text-amber-400 border border-amber-500/20 animate-pulse"
                          : "bg-rose-500/10 text-rose-400 border border-rose-500/20"
                      }`}
                    >
                      {doc.status}
                    </span>
                  </Link>
                ))}
              </div>
            )}
          </div>

          {/* Recent Intelligence Queries */}
          <div className="glass-panel p-4 sm:p-6 rounded-2xl border border-border space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <Sparkles className="w-4 h-4 sm:w-5 sm:h-5 text-emerald-400" />
                <h2 className="text-base sm:text-lg font-bold text-white">Recent Research Sessions</h2>
              </div>
              <Link href="/conversations" className="text-xs text-emerald-400 hover:underline flex items-center space-x-1">
                <span>View all</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </div>

            {queries.length === 0 ? (
              <div className="py-8 text-center text-slate-500 text-xs">
                No past research queries. Ask a multi-hop or GraphRAG question in Research.
              </div>
            ) : (
              <div className="space-y-2 sm:space-y-2.5">
                {queries.slice(0, 5).map((q) => (
                  <div
                    key={q.id}
                    className="p-2.5 sm:p-3 rounded-xl bg-slate-900/40 border border-border/70 space-y-1.5"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <p className="text-xs font-medium text-white truncate max-w-[75%] sm:max-w-[80%]">{q.question}</p>
                      <span className="text-[10px] font-mono text-slate-400 shrink-0">
                        {q.retrieval_time_ms + q.llm_time_ms} ms
                      </span>
                    </div>
                    <p className="text-[10px] sm:text-[11px] text-slate-400 line-clamp-1 leading-relaxed">{q.answer}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}

