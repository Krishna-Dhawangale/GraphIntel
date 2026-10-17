"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import {
  AlertCircle,
  ArrowRight,
  Bot,
  BrainCircuit,
  Calendar,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Clock,
  Cpu,
  Database,
  ExternalLink,
  FileCode,
  FileText,
  Filter,
  History,
  Layers,
  MessageSquare,
  Network,
  RotateCcw,
  Search,
  Send,
  Share2,
  Sparkles,
  Trash2,
  User,
  X,
  Zap,
} from "lucide-react";
import Sidebar from "../../components/Sidebar";
import { api } from "../../lib/api";
import { formatDate } from "../../lib/utils";
import {
  QueryResponse,
  ResearchHistoryDetail,
  ResearchHistoryItem,
  SourceCitation,
} from "../../types";
import { toast } from "../../lib/toast";

interface ChatMessage {
  id: string;
  sender: "user" | "ai";
  content: string;
  timestamp: string;
  response?: QueryResponse;
}

export default function ChatPage() {
  const [activeTab, setActiveTab] = useState<"workspace" | "history">("workspace");
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [retrievalMode, setRetrievalMode] = useState<string>("hybrid");
  const [activeCitation, setActiveCitation] = useState<SourceCitation | null>(null);

  // History Tab State
  const [historyItems, setHistoryItems] = useState<ResearchHistoryItem[]>([]);
  const [historyTotal, setHistoryTotal] = useState(0);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historySearch, setHistorySearch] = useState("");
  const [historyModeFilter, setHistoryModeFilter] = useState("all");
  const [historyPage, setHistoryPage] = useState(0);
  const [selectedHistoryDetail, setSelectedHistoryDetail] = useState<ResearchHistoryDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);
  const [showClearConfirm, setShowClearConfirm] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const pageSize = 15;

  const fetchResearchHistory = async (page = historyPage, query = historySearch, mode = historyModeFilter) => {
    setHistoryLoading(true);
    try {
      const resp = await api.research.history({
        q: query.trim() || undefined,
        retrieval_mode: mode !== "all" ? mode : undefined,
        skip: page * pageSize,
        limit: pageSize,
      });
      setHistoryItems(resp.items || []);
      setHistoryTotal(resp.total || 0);
    } catch (err: any) {
      console.error("Failed to load research history:", err);
      // Fallback to legacy query history if needed
      try {
        const legacy = await api.query.history(0, 10);
        setHistoryItems(
          legacy.map((l) => ({
            id: l.id,
            question: l.question,
            answer: l.answer,
            answer_preview: l.answer.slice(0, 150) + "...",
            retrieval_mode: "hybrid",
            citations_count: l.sources_count,
            graph_paths_count: 0,
            status: "SUCCESS",
            created_at: l.created_at,
          }))
        );
        setHistoryTotal(legacy.length);
      } catch (_) {}
    } finally {
      setHistoryLoading(false);
    }
  };

  useEffect(() => {
    if (activeTab === "history") {
      fetchResearchHistory(historyPage, historySearch, historyModeFilter);
    }
  }, [activeTab, historyPage, historyModeFilter]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setHistoryPage(0);
    fetchResearchHistory(0, historySearch, historyModeFilter);
  };

  const handleOpenDetail = async (item: ResearchHistoryItem) => {
    setDetailLoading(true);
    try {
      const detail = await api.research.detail(item.id);
      setSelectedHistoryDetail(detail);
    } catch (err) {
      // Fallback with current item summary
      setSelectedHistoryDetail({
        id: item.id,
        question: item.question,
        answer: item.answer,
        retrieval_mode: item.retrieval_mode,
        citations: [],
        graph_paths: [],
        status: item.status,
        created_at: item.created_at,
        updated_at: item.created_at,
      });
    } finally {
      setDetailLoading(false);
    }
  };

  const handleDeleteItem = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await api.research.delete(id);
      toast.success("History item deleted.");
      setDeleteConfirmId(null);
      if (selectedHistoryDetail?.id === id) {
        setSelectedHistoryDetail(null);
      }
      fetchResearchHistory(historyPage, historySearch, historyModeFilter);
    } catch (err: any) {
      toast.error(err.message || "Failed to delete item.");
    }
  };

  const handleClearAllHistory = async () => {
    try {
      const res = await api.research.clear();
      toast.success(res.message || "Research history cleared.");
      setShowClearConfirm(false);
      setSelectedHistoryDetail(null);
      fetchResearchHistory(0, "", "all");
    } catch (err: any) {
      toast.error(err.message || "Failed to clear history.");
    }
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    if (activeTab === "workspace") {
      scrollToBottom();
    }
  }, [messages, loading, activeTab]);

  const handleSend = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!input.trim() || loading) return;

    const userQuestion = input.trim();
    setInput("");

    const userMsg: ChatMessage = {
      id: Date.now().toString(),
      sender: "user",
      content: userQuestion,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };
    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);

    try {
      let response: QueryResponse;
      if (retrievalMode === "agentic") {
        response = await api.query.agent({ question: userQuestion });
      } else {
        response = await api.query.execute({
          question: userQuestion,
          top_k: 5,
          retrieval_mode: retrievalMode,
          max_graph_hops: 3,
        });
      }

      const aiMsg: ChatMessage = {
        id: (Date.now() + 1).toString(),
        sender: "ai",
        content: response.answer,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        response,
      };

      setMessages((prev) => [...prev, aiMsg]);
      toast.success(`Analysis complete · ${response.metadata?.total_time_ms ?? "—"}ms`, { duration: 2500 });
    } catch (err: any) {
      const errorMsg = err.message || "Failed to process query. Please check network or credentials.";
      const errorChatMsg: ChatMessage = {
        id: (Date.now() + 1).toString(),
        sender: "ai",
        content: `Error: ${errorMsg}`,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };
      setMessages((prev) => [...prev, errorChatMsg]);
      toast.error(errorMsg, { duration: 5000 });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-[calc(100vh-4rem)]">
      <Sidebar />
      <main className="flex-1 min-w-0 flex flex-col h-[calc(100vh-4rem)] max-w-7xl mx-auto overflow-hidden pb-16 lg:pb-0">
        {/* Workspace Top Controls with Primary Tab Switcher */}
        <div className="p-3.5 sm:p-4 px-4 sm:px-6 border-b border-border glass-panel flex flex-col sm:flex-row sm:items-center justify-between gap-3 shrink-0">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 flex items-center justify-center shrink-0">
              <Sparkles className="w-4 h-4" />
            </div>
            <div className="min-w-0">
              <h1 className="text-sm sm:text-base font-bold text-white truncate">
                GraphIntel Research Workspace
              </h1>
              <p className="text-[11px] sm:text-xs text-slate-400 truncate">
                Multi-hop market intelligence with knowledge graph reasoning and verifiable citations.
              </p>
            </div>
          </div>

          {/* Primary View Switcher: Workspace vs History */}
          <div className="flex items-center space-x-1.5 self-start sm:self-auto">
            <div className="flex items-center bg-slate-900/90 p-1 rounded-xl border border-border">
              <button
                onClick={() => setActiveTab("workspace")}
                className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                  activeTab === "workspace"
                    ? "bg-emerald-500 text-slate-950 shadow-sm"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                <Sparkles className="w-3.5 h-3.5" />
                <span>Workspace</span>
              </button>

              <button
                onClick={() => {
                  setActiveTab("history");
                  fetchResearchHistory(0, historySearch, historyModeFilter);
                }}
                className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                  activeTab === "history"
                    ? "bg-emerald-500 text-slate-950 shadow-sm"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                <History className="w-3.5 h-3.5" />
                <span>History</span>
                {historyTotal > 0 && (
                  <span className={`text-[10px] px-1.5 py-0.2 rounded-full font-mono ${
                    activeTab === "history" ? "bg-slate-950/20 text-slate-950 font-bold" : "bg-slate-800 text-slate-300"
                  }`}>
                    {historyTotal}
                  </span>
                )}
              </button>
            </div>
          </div>
        </div>

        {/* TAB 1: WORKSPACE */}
        {activeTab === "workspace" && (
          <>
            {/* Retrieval Mode Selector */}
            <div className="px-4 sm:px-6 py-2.5 bg-slate-950/40 border-b border-border/60 flex items-center justify-between gap-3 shrink-0 overflow-x-auto">
              <span className="text-[11px] text-slate-500 font-medium uppercase tracking-wider shrink-0 hidden sm:inline">
                Retrieval Strategy:
              </span>
              <div className="flex items-center space-x-1.5 text-xs">
                {[
                  { id: "hybrid", label: "HYBRID", icon: Layers, desc: "Dense Vector + KG Fusion" },
                  { id: "agentic", label: "AGENTIC", icon: BrainCircuit, desc: "LangGraph Multi-Step Planner" },
                  { id: "graph", label: "GRAPH", icon: Share2, desc: "Neo4j Graph Traversal Only" },
                  { id: "vector", label: "VECTOR", icon: Database, desc: "Qdrant Dense Cosine Only" },
                ].map((mode) => {
                  const Icon = mode.icon;
                  const isSelected = retrievalMode === mode.id;
                  return (
                    <button
                      key={mode.id}
                      onClick={() => setRetrievalMode(mode.id)}
                      title={mode.desc}
                      className={`flex items-center space-x-1 sm:space-x-1.5 px-2.5 sm:px-3 py-1 sm:py-1 rounded-lg font-medium transition shrink-0 ${
                        isSelected
                          ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 font-semibold"
                          : "text-slate-400 hover:text-white hover:bg-slate-800/60"
                      }`}
                    >
                      <Icon className="w-3.5 h-3.5" />
                      <span className="text-[11px] sm:text-xs">{mode.label}</span>
                    </button>
                  );
                })}
              </div>

              <button
                onClick={() => {
                  setActiveTab("history");
                  fetchResearchHistory(0, "", "all");
                }}
                className="text-xs text-slate-400 hover:text-emerald-400 flex items-center space-x-1 shrink-0 ml-auto"
              >
                <History className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">View Past Sessions</span>
              </button>
            </div>

            {/* Chat / Research Feed */}
            <div className="flex-1 overflow-y-auto p-3.5 sm:p-6 space-y-4 sm:space-y-6">
              {messages.length === 0 ? (
                <div className="h-full flex flex-col items-center justify-center text-center max-w-md mx-auto space-y-4 my-auto px-2">
                  <div className="w-12 h-12 sm:w-14 sm:h-14 rounded-2xl bg-gradient-to-tr from-emerald-500/20 to-cyan-500/20 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
                    <BrainCircuit className="w-7 h-7 sm:w-8 sm:h-8" />
                  </div>
                  <h2 className="text-lg sm:text-xl font-bold text-white">Market Intelligence Inquiry</h2>
                  <p className="text-xs text-slate-400 leading-relaxed">
                    Ask simple facts, multi-hop relationship questions, or complex competitive intelligence. Every fact is validated with verifiable document citations.
                  </p>
                  <div className="grid grid-cols-1 gap-2 w-full pt-2">
                    {[
                      "What were NVIDIA's fiscal 2026 financial results?",
                      "How does NVIDIA connect its AI infrastructure, technology platforms, and enterprise ecosystem?",
                      "Show NVIDIA's documented relationships with companies mentioned in this report, with evidence for each edge.",
                      "Which company acquired a startup founded by a former Google employee?",
                    ].map((prompt, idx) => (
                      <button
                        key={idx}
                        onClick={() => {
                          setInput(prompt);
                        }}
                        className="text-left p-3 rounded-xl bg-slate-900/60 hover:bg-slate-800/80 border border-border hover:border-emerald-500/30 text-xs text-slate-300 transition group flex items-center justify-between"
                      >
                        <span className="truncate pr-2">{prompt}</span>
                        <ChevronRight className="w-3.5 h-3.5 text-slate-500 group-hover:text-emerald-400 shrink-0" />
                      </button>
                    ))}
                  </div>
                </div>
              ) : (
                messages.map((msg) => (
                  <div
                    key={msg.id}
                    className={`flex items-start space-x-2.5 sm:space-x-3.5 ${
                      msg.sender === "user" ? "justify-end" : "justify-start"
                    }`}
                  >
                    {msg.sender === "ai" && (
                      <div className="w-7 h-7 sm:w-8 sm:h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 flex items-center justify-center shrink-0 mt-0.5">
                        <Bot className="w-4 h-4" />
                      </div>
                    )}

                    <div
                      className={`max-w-[88%] sm:max-w-2xl rounded-2xl p-3.5 sm:p-5 text-xs sm:text-sm shadow-lg ${
                        msg.sender === "user"
                          ? "bg-emerald-500 text-slate-950 font-medium rounded-tr-none ml-auto"
                          : "glass-panel border border-border text-slate-100 rounded-tl-none space-y-4"
                      }`}
                    >
                      <div className="whitespace-pre-wrap leading-relaxed">{msg.content}</div>

                      {/* AI Response Metadata & Citations */}
                      {msg.response && msg.response.sources && msg.response.sources.length > 0 && (
                        <div className="pt-3 border-t border-border/60 space-y-2">
                          <div className="flex items-center justify-between text-[11px] text-slate-400">
                            <span className="font-semibold text-slate-300">Verifiable Document Citations</span>
                            <span className="font-mono text-emerald-400">
                              {msg.response.sources.length} sources · {msg.response.metadata?.total_time_ms ?? "—"}ms
                            </span>
                          </div>

                          <div className="flex flex-wrap gap-1.5">
                            {msg.response.sources.map((cit) => (
                              <button
                                key={cit.citation_order}
                                onClick={() => setActiveCitation(cit)}
                                className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-md bg-slate-900 border border-border hover:border-emerald-500/50 text-[11px] text-slate-300 hover:text-white transition group"
                              >
                                <span className="font-bold text-emerald-400">[{cit.citation_order}]</span>
                                <span className="max-w-[130px] sm:max-w-[180px] truncate">
                                  {cit.document_title || cit.filename}
                                </span>
                                {cit.page_number && (
                                  <span className="text-[10px] text-slate-500 font-mono">p.{cit.page_number}</span>
                                )}
                              </button>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Multi-Hop Graph Reasoning Path Visualization */}
                      {msg.response && msg.response.graph_paths && msg.response.graph_paths.length > 0 && (
                        <div className="pt-3 border-t border-border/60 space-y-2">
                          <div className="flex items-center space-x-1.5 text-[11px] font-semibold text-cyan-400">
                            <Network className="w-3.5 h-3.5" />
                            <span>Knowledge Graph Multi-Hop Reasoning</span>
                          </div>
                          <div className="space-y-1.5">
                            {msg.response.graph_paths.map((p, idx) => (
                              <div
                                key={idx}
                                className="p-2.5 rounded-lg bg-slate-900/60 border border-cyan-500/20 text-[11px] font-mono text-slate-300 flex items-center flex-wrap gap-1"
                              >
                                {p.nodes.map((node, nIdx) => (
                                  <span key={nIdx} className="flex items-center">
                                    <span className="px-1.5 py-0.5 rounded bg-cyan-500/10 text-cyan-300 border border-cyan-500/20 font-bold">
                                      {node}
                                    </span>
                                    {nIdx < p.relationships.length && (
                                      <span className="text-slate-500 px-1 text-[10px]">
                                        -[{p.relationships[nIdx]}]-&gt;
                                      </span>
                                    )}
                                  </span>
                                ))}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      <div className="flex items-center justify-between text-[10px] text-slate-500 pt-1">
                        <span>{msg.timestamp}</span>
                        {msg.sender === "ai" && msg.response?.metadata?.model_used && (
                          <span className="font-mono text-slate-400">
                            Model: {msg.response.metadata.model_used}
                          </span>
                        )}
                      </div>
                    </div>

                    {msg.sender === "user" && (
                      <div className="w-7 h-7 sm:w-8 sm:h-8 rounded-lg bg-emerald-500 flex items-center justify-center text-slate-950 font-bold shrink-0 mt-0.5 text-xs">
                        U
                      </div>
                    )}
                  </div>
                ))
              )}

              {loading && (
                <div className="flex items-start space-x-3 text-slate-400">
                  <div className="w-7 h-7 sm:w-8 sm:h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 flex items-center justify-center shrink-0 animate-pulse">
                    <Bot className="w-4 h-4" />
                  </div>
                  <div className="glass-panel border border-border rounded-2xl rounded-tl-none p-3.5 text-xs text-slate-300 flex items-center space-x-2">
                    <div className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
                    <span>Analyzing documents and executing knowledge graph reasoning...</span>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Prompt Input Box */}
            <div className="p-3.5 sm:p-4 border-t border-border glass-panel shrink-0">
              <form onSubmit={handleSend} className="relative flex items-center">
                <input
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder="Ask a question about financial results, company relationships, or technology platforms..."
                  disabled={loading}
                  className="w-full pl-4 pr-12 py-3 rounded-xl bg-slate-900 border border-border text-xs sm:text-sm text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500 transition shadow-inner disabled:opacity-50"
                />
                <button
                  type="submit"
                  disabled={loading || !input.trim()}
                  className="absolute right-2 p-2 rounded-lg bg-emerald-500 hover:bg-emerald-400 disabled:bg-slate-800 text-slate-950 disabled:text-slate-600 transition shadow"
                  aria-label="Send message"
                >
                  <Send className="w-4 h-4" />
                </button>
              </form>
            </div>
          </>
        )}

        {/* TAB 2: RESEARCH HISTORY */}
        {activeTab === "history" && (
          <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
            {/* History Filters & Actions Toolbar */}
            <div className="p-3.5 sm:p-4 px-4 sm:px-6 bg-slate-950/60 border-b border-border/70 flex flex-col md:flex-row md:items-center justify-between gap-3 shrink-0">
              {/* Search Form */}
              <form onSubmit={handleSearchSubmit} className="relative flex-1 max-w-md">
                <Search className="w-4 h-4 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
                <input
                  type="text"
                  value={historySearch}
                  onChange={(e) => setHistorySearch(e.target.value)}
                  placeholder="Search previous research queries or answers..."
                  className="w-full pl-9 pr-8 py-2 rounded-lg bg-slate-900 border border-border text-xs text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
                />
                {historySearch && (
                  <button
                    type="button"
                    onClick={() => {
                      setHistorySearch("");
                      fetchResearchHistory(0, "", historyModeFilter);
                    }}
                    className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-500 hover:text-white"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                )}
              </form>

              {/* Retrieval Mode Filter & Actions */}
              <div className="flex items-center space-x-2 shrink-0">
                <div className="flex items-center space-x-1 bg-slate-900 p-1 rounded-lg border border-border text-xs">
                  {["all", "hybrid", "agentic", "graph", "vector"].map((m) => (
                    <button
                      key={m}
                      onClick={() => {
                        setHistoryModeFilter(m);
                        setHistoryPage(0);
                      }}
                      className={`px-2.5 py-1 rounded text-[11px] font-medium uppercase transition ${
                        historyModeFilter === m
                          ? "bg-emerald-500 text-slate-950 font-bold"
                          : "text-slate-400 hover:text-white"
                      }`}
                    >
                      {m}
                    </button>
                  ))}
                </div>

                <button
                  onClick={() => fetchResearchHistory(historyPage, historySearch, historyModeFilter)}
                  className="p-2 rounded-lg border border-border bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-white transition"
                  title="Refresh History"
                >
                  <RotateCcw className="w-3.5 h-3.5" />
                </button>

                {historyItems.length > 0 && (
                  <button
                    onClick={() => setShowClearConfirm(true)}
                    className="px-3 py-1.5 rounded-lg border border-rose-500/30 bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 text-xs font-medium transition flex items-center space-x-1"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                    <span>Clear All</span>
                  </button>
                )}
              </div>
            </div>

            {/* Clear Confirmation Modal */}
            {showClearConfirm && (
              <div className="fixed inset-0 bg-slate-950/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
                <div className="glass-panel border border-border rounded-2xl max-w-sm w-full p-6 space-y-4 shadow-2xl animate-in fade-in-50 zoom-in-95">
                  <div className="flex items-center space-x-3 text-rose-400">
                    <AlertCircle className="w-5 h-5 shrink-0" />
                    <h3 className="font-bold text-sm text-white">Clear Research History?</h3>
                  </div>
                  <p className="text-xs text-slate-400 leading-relaxed">
                    This will permanently delete all research records for this session. This action cannot be undone.
                  </p>
                  <div className="flex items-center justify-end space-x-2 pt-2">
                    <button
                      onClick={() => setShowClearConfirm(false)}
                      className="px-3.5 py-2 rounded-lg text-xs font-medium text-slate-300 hover:bg-slate-800 transition"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={handleClearAllHistory}
                      className="px-4 py-2 rounded-lg text-xs font-semibold bg-rose-500 hover:bg-rose-600 text-white transition shadow"
                    >
                      Confirm Clear
                    </button>
                  </div>
                </div>
              </div>
            )}

            {/* Delete Single Item Modal */}
            {deleteConfirmId && (
              <div className="fixed inset-0 bg-slate-950/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
                <div className="glass-panel border border-border rounded-2xl max-w-sm w-full p-6 space-y-4 shadow-2xl animate-in fade-in-50 zoom-in-95">
                  <div className="flex items-center space-x-3 text-rose-400">
                    <AlertCircle className="w-5 h-5 shrink-0" />
                    <h3 className="font-bold text-sm text-white">Delete Research Item?</h3>
                  </div>
                  <p className="text-xs text-slate-400 leading-relaxed">
                    Remove this inquiry from your persistent research history.
                  </p>
                  <div className="flex items-center justify-end space-x-2 pt-2">
                    <button
                      onClick={() => setDeleteConfirmId(null)}
                      className="px-3.5 py-2 rounded-lg text-xs font-medium text-slate-300 hover:bg-slate-800 transition"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={(e) => handleDeleteItem(deleteConfirmId, e)}
                      className="px-4 py-2 rounded-lg text-xs font-semibold bg-rose-500 hover:bg-rose-600 text-white transition shadow"
                    >
                      Delete
                    </button>
                  </div>
                </div>
              </div>
            )}

            {/* History List Feed */}
            <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-3">
              {historyLoading ? (
                <div className="h-64 flex flex-col items-center justify-center text-slate-400 space-y-3">
                  <div className="w-8 h-8 rounded-full border-2 border-emerald-500/30 border-t-emerald-400 animate-spin" />
                  <span className="text-xs font-mono">Loading persistent research history...</span>
                </div>
              ) : historyItems.length === 0 ? (
                <div className="h-64 flex flex-col items-center justify-center text-center max-w-sm mx-auto space-y-3 my-auto">
                  <div className="w-12 h-12 rounded-2xl bg-slate-900/80 border border-border flex items-center justify-center text-slate-500">
                    <History className="w-6 h-6" />
                  </div>
                  <h3 className="text-sm font-bold text-white">No Research History Yet</h3>
                  <p className="text-xs text-slate-400 leading-relaxed">
                    Queries executed in the Research Workspace will automatically be saved and organized here.
                  </p>
                  <button
                    onClick={() => setActiveTab("workspace")}
                    className="mt-2 px-4 py-2 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-semibold text-xs transition"
                  >
                    Start a New Research Query
                  </button>
                </div>
              ) : (
                historyItems.map((item) => (
                  <div
                    key={item.id}
                    onClick={() => handleOpenDetail(item)}
                    className="p-4 rounded-xl glass-panel border border-border/80 hover:border-emerald-500/40 cursor-pointer transition-all hover:scale-[1.005] group space-y-2.5 relative"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="space-y-1 min-w-0 flex-1">
                        <div className="flex items-center space-x-2">
                          <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 uppercase font-bold">
                            {item.retrieval_mode}
                          </span>
                          <span className="text-[11px] text-slate-500 flex items-center space-x-1">
                            <Clock className="w-3 h-3" />
                            <span>{formatDate(item.created_at)}</span>
                          </span>
                        </div>
                        <h3 className="text-sm font-semibold text-white group-hover:text-emerald-300 transition truncate">
                          {item.question}
                        </h3>
                      </div>

                      <div className="flex items-center space-x-1.5 shrink-0">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setDeleteConfirmId(item.id);
                          }}
                          className="p-1.5 rounded-lg text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 transition"
                          title="Delete history item"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                        <ChevronRight className="w-4 h-4 text-slate-500 group-hover:text-emerald-400 group-hover:translate-x-0.5 transition" />
                      </div>
                    </div>

                    <p className="text-xs text-slate-400 line-clamp-2 leading-relaxed">
                      {item.answer_preview || item.answer}
                    </p>

                    <div className="flex items-center space-x-3 text-[11px] text-slate-500 pt-1 border-t border-border/40">
                      {item.citations_count > 0 && (
                        <span className="flex items-center space-x-1 text-slate-400">
                          <FileText className="w-3 h-3 text-emerald-400" />
                          <span>{item.citations_count} citations</span>
                        </span>
                      )}
                      {item.graph_paths_count > 0 && (
                        <span className="flex items-center space-x-1 text-slate-400">
                          <Network className="w-3 h-3 text-cyan-400" />
                          <span>{item.graph_paths_count} reasoning paths</span>
                        </span>
                      )}
                      <span className="text-emerald-400 font-medium ml-auto text-[10px] uppercase tracking-wider group-hover:underline">
                        Open Detail View →
                      </span>
                    </div>
                  </div>
                ))
              )}

              {/* Pagination controls */}
              {historyTotal > pageSize && (
                <div className="flex items-center justify-between pt-4 border-t border-border/60 text-xs text-slate-400">
                  <span>
                    Showing {historyPage * pageSize + 1}–{Math.min((historyPage + 1) * pageSize, historyTotal)} of {historyTotal}
                  </span>
                  <div className="flex items-center space-x-2">
                    <button
                      onClick={() => setHistoryPage((p) => Math.max(0, p - 1))}
                      disabled={historyPage === 0}
                      className="px-3 py-1.5 rounded-lg border border-border bg-slate-900 disabled:opacity-40 hover:bg-slate-800 transition flex items-center space-x-1"
                    >
                      <ChevronLeft className="w-3.5 h-3.5" />
                      <span>Prev</span>
                    </button>
                    <button
                      onClick={() => setHistoryPage((p) => p + 1)}
                      disabled={(historyPage + 1) * pageSize >= historyTotal}
                      className="px-3 py-1.5 rounded-lg border border-border bg-slate-900 disabled:opacity-40 hover:bg-slate-800 transition flex items-center space-x-1"
                    >
                      <span>Next</span>
                      <ChevronRight className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </main>

      {/* History Detail Modal / Inspector Drawer */}
      {selectedHistoryDetail && (
        <>
          <div
            onClick={() => setSelectedHistoryDetail(null)}
            className="fixed inset-0 bg-slate-950/70 backdrop-blur-sm z-50"
          />
          <div className="fixed inset-y-0 right-0 w-full sm:w-[560px] max-w-full glass-panel border-l border-border z-50 shadow-2xl flex flex-col justify-between overflow-y-auto animate-in slide-in-from-right duration-200">
            <div className="p-5 sm:p-6 space-y-6">
              {/* Header */}
              <div className="flex items-start justify-between border-b border-border/60 pb-4">
                <div className="space-y-1 pr-2">
                  <div className="flex items-center space-x-2">
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 uppercase font-bold">
                      {selectedHistoryDetail.retrieval_mode}
                    </span>
                    <span className="text-[11px] text-slate-500">
                      {formatDate(selectedHistoryDetail.created_at)}
                    </span>
                  </div>
                  <h2 className="text-base sm:text-lg font-bold text-white pt-1">
                    {selectedHistoryDetail.question}
                  </h2>
                </div>

                <button
                  onClick={() => setSelectedHistoryDetail(null)}
                  className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition shrink-0"
                  aria-label="Close detail view"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              {/* Complete Answer */}
              <div className="space-y-2">
                <span className="text-[10px] uppercase tracking-wider text-slate-500 font-semibold block">
                  Synthesized Answer & Findings
                </span>
                <div className="p-4 rounded-xl bg-slate-950/80 border border-border/80 text-xs sm:text-sm text-slate-200 leading-relaxed whitespace-pre-wrap">
                  {selectedHistoryDetail.answer}
                </div>
              </div>

              {/* Citations Section */}
              {selectedHistoryDetail.citations && selectedHistoryDetail.citations.length > 0 && (
                <div className="space-y-2.5">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] uppercase tracking-wider text-slate-500 font-semibold">
                      Verifiable Evidence Citations ({selectedHistoryDetail.citations.length})
                    </span>
                  </div>
                  <div className="space-y-2">
                    {selectedHistoryDetail.citations.map((c, idx) => (
                      <div
                        key={idx}
                        className="p-3 rounded-lg bg-slate-900/60 border border-border text-xs space-y-1.5"
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-semibold text-white">
                            [{c.citation_order || idx + 1}] {c.document_title || c.filename}
                          </span>
                          {c.page_number && (
                            <span className="text-[10px] font-mono text-emerald-400">
                              Page {c.page_number}
                            </span>
                          )}
                        </div>
                        {c.claim && (
                          <p className="text-[11px] text-emerald-300 font-medium">
                            Claim: {c.claim}
                          </p>
                        )}
                        <p className="text-[11px] text-slate-400 font-mono bg-slate-950/60 p-2 rounded border border-border/40">
                          {c.supporting_excerpt || c.text_snippet || "Excerpt verified from chunk index."}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Graph Reasoning Paths */}
              {selectedHistoryDetail.graph_paths && selectedHistoryDetail.graph_paths.length > 0 && (
                <div className="space-y-2.5">
                  <span className="text-[10px] uppercase tracking-wider text-cyan-400 font-semibold block">
                    Knowledge Graph Reasoning Paths ({selectedHistoryDetail.graph_paths.length})
                  </span>
                  <div className="space-y-2">
                    {selectedHistoryDetail.graph_paths.map((p, idx) => (
                      <div
                        key={idx}
                        className="p-3 rounded-lg bg-slate-900/60 border border-cyan-500/20 text-xs font-mono space-y-1 text-slate-300"
                      >
                        <div className="flex items-center flex-wrap gap-1">
                          {p.nodes.map((node, nIdx) => (
                            <span key={nIdx} className="flex items-center">
                              <span className="px-1.5 py-0.5 rounded bg-cyan-500/10 text-cyan-300 border border-cyan-500/20 font-bold">
                                {node}
                              </span>
                              {nIdx < p.relationships.length && (
                                <span className="text-slate-500 px-1 text-[10px]">
                                  -[{p.relationships[nIdx]}]-&gt;
                                </span>
                              )}
                            </span>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Bottom Actions */}
            <div className="p-4 sm:p-5 border-t border-border/60 bg-slate-950/80 flex items-center justify-between gap-3">
              <button
                onClick={() => {
                  setInput(selectedHistoryDetail.question);
                  setSelectedHistoryDetail(null);
                  setActiveTab("workspace");
                }}
                className="px-4 py-2.5 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold text-xs flex items-center space-x-1.5 transition"
              >
                <Sparkles className="w-3.5 h-3.5" />
                <span>Re-run in Workspace</span>
              </button>

              <button
                onClick={(e) => handleDeleteItem(selectedHistoryDetail.id, e)}
                className="px-3 py-2 rounded-lg border border-rose-500/30 text-rose-400 hover:bg-rose-500/10 text-xs font-medium transition flex items-center space-x-1"
              >
                <Trash2 className="w-3.5 h-3.5" />
                <span>Delete</span>
              </button>
            </div>
          </div>
        </>
      )}

      {/* Citation Inspector Context Drawer */}
      {activeCitation && (
        <>
          <div
            onClick={() => setActiveCitation(null)}
            className="fixed inset-0 bg-slate-950/60 backdrop-blur-sm z-50 lg:hidden"
          />
          <div className="fixed inset-y-0 right-0 w-full sm:w-96 max-w-full glass-panel border-l border-border z-50 p-5 sm:p-6 shadow-2xl flex flex-col justify-between overflow-y-auto animate-in slide-in-from-right duration-200">
            <div className="space-y-4">
              <div className="flex items-center justify-between border-b border-border/60 pb-3">
                <div className="flex items-center space-x-2 text-emerald-400">
                  <FileText className="w-4 h-4" />
                  <span className="font-bold text-sm">Source Evidence Verification</span>
                </div>
                <button
                  onClick={() => setActiveCitation(null)}
                  className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
                  aria-label="Close citation details"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              <div className="space-y-3 text-xs">
                <div>
                  <span className="text-[10px] uppercase tracking-wider text-slate-500 font-semibold block">
                    Document Title
                  </span>
                  <span className="text-white font-medium block mt-0.5 break-words">
                    {activeCitation.document_title || activeCitation.filename}
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-2">
                  <div className="p-2.5 rounded-lg bg-slate-900/60 border border-border">
                    <span className="text-[10px] text-slate-500 block">Page Number</span>
                    <span className="text-white font-mono font-bold mt-0.5 block">
                      {activeCitation.page_number ? `Page ${activeCitation.page_number}` : "Page metadata unavailable"}
                    </span>
                  </div>
                  <div className="p-2.5 rounded-lg bg-slate-900/60 border border-border">
                    <span className="text-[10px] text-slate-500 block">Relevance Score</span>
                    <span className="text-emerald-400 font-mono font-bold mt-0.5 block">
                      {Math.round(activeCitation.relevance_score * 100)}%
                    </span>
                  </div>
                </div>

                {activeCitation.claim && (
                  <div>
                    <span className="text-[10px] uppercase tracking-wider text-slate-500 font-semibold block">
                      Claim Supported by Source
                    </span>
                    <p className="mt-1 p-2.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-[11px] leading-relaxed">
                      {activeCitation.claim}
                    </p>
                  </div>
                )}

                {activeCitation.section && (
                  <div>
                    <span className="text-[10px] uppercase tracking-wider text-slate-500 font-semibold block">
                      Section
                    </span>
                    <span className="text-slate-300 font-mono mt-0.5 block break-words">{activeCitation.section}</span>
                  </div>
                )}

                <div>
                  <span className="text-[10px] uppercase tracking-wider text-slate-500 font-semibold block mb-1">
                    Supporting Passage Excerpt
                  </span>
                  <p className="p-3 rounded-lg bg-slate-950/80 border border-border/60 text-slate-300 font-mono text-[11px] leading-relaxed whitespace-pre-wrap break-words overflow-x-auto max-h-60 overflow-y-auto">
                    {activeCitation.supporting_excerpt || activeCitation.text_snippet || "Verified context snippet retrieved from vector chunk index."}
                  </p>
                </div>
              </div>
            </div>

            <div className="pt-4 border-t border-border/60">
              <Link
                href={`/documents/${activeCitation.document_id}`}
                className="w-full py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs font-semibold flex items-center justify-center space-x-1.5 transition"
              >
                <span>Inspect Full Document Chunks</span>
                <ExternalLink className="w-3.5 h-3.5" />
              </Link>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
