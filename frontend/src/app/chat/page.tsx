"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import {
  AlertCircle,
  ArrowRight,
  Bot,
  BrainCircuit,
  CheckCircle2,
  ChevronRight,
  Clock,
  Cpu,
  Database,
  ExternalLink,
  FileCode,
  FileText,
  History,
  Layers,
  MessageSquare,
  Network,
  Send,
  Share2,
  Sparkles,
  User,
  X,
  Zap,
} from "lucide-react";
import Sidebar from "../../components/Sidebar";
import { api } from "../../lib/api";
import { formatBytes } from "../../lib/utils";
import { QueryHistoryItem, QueryResponse, SourceCitation } from "../../types";
import { toast } from "../../lib/toast";

interface ChatMessage {
  id: string;
  sender: "user" | "ai";
  content: string;
  timestamp: string;
  response?: QueryResponse;
}

export default function ChatPage() {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [retrievalMode, setRetrievalMode] = useState<string>("hybrid");
  const [history, setHistory] = useState<QueryHistoryItem[]>([]);
  const [activeCitation, setActiveCitation] = useState<SourceCitation | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const fetchHistory = async () => {
    try {
      const pastQueries = await api.query.history(0, 10);
      setHistory(pastQueries);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    fetchHistory();
  }, []);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

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
      fetchHistory();
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
        {/* Workspace Top Controls */}
        <div className="p-3.5 sm:p-4 px-4 sm:px-6 border-b border-border glass-panel flex flex-col sm:flex-row sm:items-center justify-between gap-3 shrink-0">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 flex items-center justify-center shrink-0">
              <Sparkles className="w-4 h-4" />
            </div>
            <div className="min-w-0">
              <h1 className="text-sm sm:text-base font-bold text-white truncate">GraphIntel Research Workspace</h1>
              <p className="text-[11px] sm:text-xs text-slate-400 truncate">
                Multi-hop market intelligence with knowledge graph reasoning and verifiable citations.
              </p>
            </div>
          </div>

          {/* Mode Selector (scrollable on mobile) */}
          <div className="flex items-center space-x-1.5 bg-slate-900/80 p-1 rounded-xl border border-border text-xs overflow-x-auto max-w-full shrink-0">
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
                  className={`flex items-center space-x-1 sm:space-x-1.5 px-2.5 sm:px-3 py-1 sm:py-1.5 rounded-lg font-medium transition shrink-0 ${
                    isSelected
                      ? "bg-emerald-500 text-slate-950 font-semibold shadow-sm"
                      : "text-slate-400 hover:text-white hover:bg-slate-800"
                  }`}
                >
                  <Icon className="w-3.5 h-3.5" />
                  <span className="text-[11px] sm:text-xs">{mode.label}</span>
                </button>
              );
            })}
          </div>
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
                  "Which companies acquired startups founded by former Google researchers?",
                  "What was Microsoft's revenue and acquisition strategy in 2024?",
                  "Which investors participated in Series B funding rounds between 2022 and 2024?",
                ].map((prompt, idx) => (
                  <button
                    key={idx}
                    onClick={() => {
                      setInput(prompt);
                      // Auto-submit after setting input
                      setTimeout(() => {
                        const fakeEvent = { preventDefault: () => {} } as React.FormEvent;
                        setInput("");
                        const userMsg: ChatMessage = {
                          id: Date.now().toString(),
                          sender: "user",
                          content: prompt,
                          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
                        };
                        setMessages((prev) => [...prev, userMsg]);
                        setLoading(true);
                        api.query.execute({ question: prompt, top_k: 5, retrieval_mode: retrievalMode, max_graph_hops: 3 })
                          .then((response) => {
                            const aiMsg: ChatMessage = {
                              id: (Date.now() + 1).toString(),
                              sender: "ai",
                              content: response.answer,
                              timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
                              response,
                            };
                            setMessages((prev) => [...prev, aiMsg]);
                            fetchHistory();
                            toast.success(`Analysis complete · ${response.metadata?.total_time_ms ?? "—"}ms`, { duration: 2500 });
                          })
                          .catch((err: any) => {
                            const errorMsg = err.message || "Query failed.";
                            setMessages((prev) => [...prev, {
                              id: (Date.now() + 1).toString(),
                              sender: "ai",
                              content: `Error: ${errorMsg}`,
                              timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
                            }]);
                            toast.error(errorMsg, { duration: 5000 });
                          })
                          .finally(() => setLoading(false));
                      }, 50);
                    }}
                    className="p-2.5 text-left text-xs bg-slate-900/60 hover:bg-slate-800/80 border border-border/80 hover:border-emerald-500/40 rounded-xl text-slate-300 transition active:scale-[0.98]"
                  >
                    "{prompt}"
                  </button>
                ))}
              </div>
            </div>
          ) : (
            messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex gap-2.5 sm:gap-3.5 max-w-4xl ${
                  msg.sender === "user" ? "ml-auto flex-row-reverse" : "mr-auto"
                }`}
              >
                <div
                  className={`w-7 h-7 sm:w-8 sm:h-8 rounded-full flex items-center justify-center shrink-0 border ${
                    msg.sender === "user"
                      ? "bg-slate-800 border-slate-700 text-slate-300"
                      : "bg-emerald-500/10 border-emerald-500/20 text-emerald-400"
                  }`}
                >
                  {msg.sender === "user" ? <User className="w-3.5 h-3.5 sm:w-4 sm:h-4" /> : <Bot className="w-3.5 h-3.5 sm:w-4 sm:h-4" />}
                </div>

                <div className="space-y-2.5 sm:space-y-3 max-w-[90%] sm:max-w-[85%] min-w-0">
                  <div
                    className={`p-3.5 sm:p-4 rounded-2xl text-xs sm:text-sm leading-relaxed ${
                      msg.sender === "user"
                        ? "bg-emerald-500 text-slate-950 font-medium rounded-tr-none"
                        : "glass-panel border border-border text-slate-200 rounded-tl-none whitespace-pre-wrap break-words overflow-x-auto"
                    }`}
                  >
                    {msg.content}
                  </div>

                  {/* AI Response Metadata, Citations & Graph Evidence */}
                  {msg.response && (
                    <div className="glass-panel p-3.5 sm:p-4 rounded-xl border border-border space-y-3 text-xs">
                      {/* Latency & Mode Stats */}
                      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border/40 pb-2 text-[10px] sm:text-[11px] text-slate-400 font-mono">
                        <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5">
                          <span className="text-emerald-400 font-semibold uppercase">
                            MODE: {msg.response.retrieval_mode || retrievalMode}
                          </span>
                          <span>•</span>
                          <span>Retr: {msg.response.metadata.retrieval_time_ms}ms</span>
                          <span>•</span>
                          <span>LLM: {msg.response.metadata.llm_time_ms}ms</span>
                          <span>•</span>
                          <span>Total: {msg.response.metadata.total_time_ms}ms</span>
                        </div>
                        <Link
                          href={`/reports?title=${encodeURIComponent(msg.response.question)}`}
                          className="text-cyan-400 hover:underline flex items-center space-x-1 shrink-0"
                        >
                          <FileCode className="w-3.5 h-3.5" />
                          <span>Generate Report</span>
                        </Link>
                      </div>

                      {/* Clickable Source Citations */}
                      {msg.response.sources && msg.response.sources.length > 0 && (
                        <div className="space-y-1.5">
                          <div className="flex items-center space-x-1.5 text-slate-300 font-semibold text-[11px]">
                            <FileText className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                            <span>Verifiable Source Citations ({msg.response.sources.length})</span>
                          </div>
                          <div className="flex flex-wrap gap-1.5 sm:gap-2 pt-1">
                            {msg.response.sources.map((s, idx) => (
                              <button
                                key={idx}
                                onClick={() => setActiveCitation(s)}
                                className="px-2.5 py-1 rounded-lg bg-slate-900/80 hover:bg-slate-800 border border-emerald-500/30 hover:border-emerald-500 text-[10px] sm:text-[11px] text-emerald-400 flex items-center space-x-1.5 transition max-w-full"
                              >
                                <span>[Source {s.citation_order || idx + 1}]</span>
                                <span className="text-slate-400 text-[10px] truncate max-w-[100px] sm:max-w-[130px]">
                                  {s.filename}
                                </span>
                              </button>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Multi-Hop Reasoning Path Visualization */}
                      {msg.response.graph_paths && msg.response.graph_paths.length > 0 && (
                        <div className="space-y-1.5 pt-2 border-t border-border/40">
                          <div className="flex items-center space-x-1.5 text-slate-300 font-semibold text-[11px]">
                            <Network className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
                            <span>Multi-Hop Reasoning Paths ({msg.response.graph_paths.length})</span>
                          </div>
                          <div className="space-y-1.5">
                            {msg.response.graph_paths.map((p, pIdx) => (
                              <div
                                key={pIdx}
                                className="p-2.5 rounded-lg bg-slate-950/60 border border-border/50 text-[10px] sm:text-[11px] flex flex-wrap items-center gap-1.5 font-mono"
                              >
                                {p.nodes.map((n, nIdx) => (
                                  <div key={nIdx} className="flex items-center space-x-1.5">
                                    <span className="px-2 py-0.5 rounded bg-blue-500/10 text-blue-300 border border-blue-500/20">
                                      {n}
                                    </span>
                                    {p.relationships[nIdx] && (
                                      <span className="text-[10px] text-emerald-400 flex items-center">
                                        → {p.relationships[nIdx]} →
                                      </span>
                                    )}
                                  </div>
                                ))}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            ))
          )}
          {loading && (
            <div className="flex gap-2.5 sm:gap-3.5 max-w-xl mr-auto animate-in fade-in">
              <div className="w-7 h-7 sm:w-8 sm:h-8 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 flex items-center justify-center shrink-0">
                <Sparkles className="w-4 h-4 animate-spin" />
              </div>
              <div className="glass-panel p-3.5 sm:p-4 rounded-2xl border border-border space-y-2.5">
                <div className="flex items-center space-x-2 text-xs text-emerald-400 font-medium">
                  <Cpu className="w-3.5 h-3.5 animate-pulse shrink-0" />
                  <span>Traversing Knowledge Graph & Synthesizing Evidence...</span>
                </div>
                <div className="flex items-center space-x-1.5">
                  <div className="typing-dot" />
                  <div className="typing-dot" />
                  <div className="typing-dot" />
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Bar */}
        <div className="p-3 sm:p-4 border-t border-border glass-panel shrink-0">
          <form onSubmit={handleSend} className="relative flex items-center max-w-4xl mx-auto">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask an intelligence question across financial filings, acquisitions, or leadership..."
              className="w-full pl-3.5 sm:pl-4 pr-12 py-2.5 sm:py-3 bg-slate-900/80 border border-border rounded-xl text-xs sm:text-sm text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500/60 shadow-inner"
            />
            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="absolute right-1.5 sm:right-2 p-2 bg-emerald-500 hover:bg-emerald-400 text-slate-950 rounded-lg transition disabled:opacity-30 shadow"
              aria-label="Send Query"
            >
              <Send className="w-4 h-4" />
            </button>
          </form>
        </div>
      </main>

      {/* Citation Inspector Context Drawer */}
      {activeCitation && (
        <>
          {/* Backdrop on mobile */}
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
                  <span className="text-white font-medium block mt-0.5 break-words">{activeCitation.filename}</span>
                </div>

                <div className="grid grid-cols-2 gap-2">
                  <div className="p-2.5 rounded-lg bg-slate-900/60 border border-border">
                    <span className="text-[10px] text-slate-500 block">Page Number</span>
                    <span className="text-white font-mono font-bold mt-0.5 block">
                      {activeCitation.page_number ? `Page ${activeCitation.page_number}` : "N/A"}
                    </span>
                  </div>
                  <div className="p-2.5 rounded-lg bg-slate-900/60 border border-border">
                    <span className="text-[10px] text-slate-500 block">Relevance Score</span>
                    <span className="text-emerald-400 font-mono font-bold mt-0.5 block">
                      {Math.round(activeCitation.relevance_score * 100)}%
                    </span>
                  </div>
                </div>

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
                    Extracted Context Text
                  </span>
                  <p className="p-3 rounded-lg bg-slate-950/80 border border-border/60 text-slate-300 font-mono text-[11px] leading-relaxed whitespace-pre-wrap break-words overflow-x-auto max-h-60 overflow-y-auto">
                    {activeCitation.text_snippet || "Verified context snippet retrieved from vector chunk index."}
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

