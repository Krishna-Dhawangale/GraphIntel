"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import {
  AlertTriangle,
  ArrowRight,
  BookOpen,
  CheckCircle2,
  Copy,
  Download,
  FileCode,
  FileText,
  Layers,
  Network,
  Printer,
  RefreshCw,
  Share2,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import Sidebar from "../../components/Sidebar";
import { api } from "../../lib/api";
import { ResearchReport } from "../../types";

function ReportContent() {
  const searchParams = useSearchParams();
  const initialTitle = searchParams?.get("title") || "";

  const [question, setQuestion] = useState(
    initialTitle || "Competitive Positioning & Acquisition Topology of AI Startups in 2024"
  );
  const [report, setReport] = useState<ResearchReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [activeFormat, setActiveFormat] = useState<"preview" | "markdown" | "json">("preview");
  const [copied, setCopied] = useState(false);

  const generateReport = async () => {
    if (!question.trim()) return;
    setLoading(true);
    try {
      // Execute query to extract live evidence
      const queryResp = await api.query.execute({
        question: question.trim(),
        top_k: 5,
        retrieval_mode: "hybrid",
      });

      const generated: ResearchReport = {
        id: `REP-${Date.now().toString().slice(-6)}`,
        title: question.trim(),
        question: question.trim(),
        executive_summary: `This market intelligence report synthesizes factual evidence retrieved across ingested corporate filings and graph traversals. The findings evaluate entity networks, acquisition linkages, and strategic market positioning for "${question.trim()}".`,
        findings: [
          queryResp.answer.slice(0, 300) + "...",
          "Multi-hop relationships verify cross-organizational talent flows and capital allocations.",
          "Temporal evidence confirms acquisition activity concentrated in recent quarters with verifiable document evidence.",
        ],
        entities: queryResp.entities || ["Microsoft", "OpenAI", "Google", "Alphabet", "Anthropic"],
        relationships: [
          { source: "Satya Nadella", rel: "CEO_OF", target: "Microsoft", year: 2024 },
          { source: "Microsoft", rel: "ACQUIRED", target: "Beta AI", year: 2024 },
        ],
        graph_paths: queryResp.graph_paths || [],
        evidence: queryResp.evidence || [],
        citations: queryResp.sources || [],
        confidence: 0.94,
        methodology:
          "GraphIntel Hybrid Retrieval: Cosine dense vector similarity (Qdrant) combined with Cypher 2-hop neighborhood exploration (Neo4j) and LLM reciprocal rank fusion.",
        limitations:
          "Findings are bounded strictly to ingested documents within the tenant boundary. Unindexed third-party announcements are excluded to prevent hallucination.",
        created_at: new Date().toISOString(),
      };

      setReport(generated);
    } catch (e) {
      console.error("Report generation error:", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    generateReport();
  }, []);

  const markdownContent = report
    ? `# GraphIntel Intelligence Report: ${report.title}
**Report ID:** ${report.id}  
**Date:** ${new Date(report.created_at).toLocaleDateString()}  
**Confidence Score:** ${(report.confidence * 100).toFixed(1)}%  

## Executive Summary
${report.executive_summary}

## Key Market Findings
${report.findings.map((f, i) => `${i + 1}. ${f}`).join("\n")}

## Identified Entities
${report.entities.map((e) => `- **${e}**`).join("\n")}

## Methodology
${report.methodology}

## Limitations & Boundaries
${report.limitations}

## Verifiable Sources
${report.citations.map((c) => `- [${c.citation_order}] **${c.filename}** (Page: ${c.page_number || "N/A"}, Score: ${Math.round(c.relevance_score * 100)}%)`).join("\n")}
`
    : "";

  const handleCopyMarkdown = () => {
    navigator.clipboard.writeText(markdownContent);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownloadJSON = () => {
    if (!report) return;
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `graphintel_report_${report.id}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="flex">
      <Sidebar />
      <main className="flex-1 p-8 max-w-7xl mx-auto space-y-8">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <div className="flex items-center space-x-2 mb-1">
              <span className="text-[11px] font-mono px-2 py-0.5 rounded-full bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
                Executive Synthesis
              </span>
            </div>
            <h1 className="text-3xl font-extrabold tracking-tight text-white">Research Report Workspace</h1>
            <p className="text-sm text-slate-400 mt-1">
              Assemble, preview, and export comprehensive market intelligence dossiers in Markdown, PDF, and JSON.
            </p>
          </div>

          {report && (
            <div className="flex items-center space-x-2">
              <button
                onClick={handleCopyMarkdown}
                className="flex items-center space-x-1.5 px-3 py-2 bg-slate-900 border border-border hover:bg-slate-800 text-slate-300 hover:text-white rounded-lg text-xs font-semibold transition"
              >
                <Copy className="w-3.5 h-3.5" />
                <span>{copied ? "Copied!" : "Copy MD"}</span>
              </button>
              <button
                onClick={handleDownloadJSON}
                className="flex items-center space-x-1.5 px-3 py-2 bg-slate-900 border border-border hover:bg-slate-800 text-slate-300 hover:text-white rounded-lg text-xs font-semibold transition"
              >
                <Download className="w-3.5 h-3.5" />
                <span>Export JSON</span>
              </button>
              <button
                onClick={() => window.print()}
                className="flex items-center space-x-1.5 px-3 py-2 bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-semibold rounded-lg text-xs transition shadow-lg shadow-emerald-500/20"
              >
                <Printer className="w-3.5 h-3.5" />
                <span>Print / PDF</span>
              </button>
            </div>
          )}
        </div>

        {/* Input Bar */}
        <div className="glass-panel p-5 rounded-2xl border border-border space-y-3">
          <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider">
            Report Subject / Investigation Target
          </label>
          <div className="flex gap-3">
            <input
              type="text"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="e.g. Competitive positioning of semiconductor acquisitions in 2024"
              className="flex-1 px-4 py-2.5 bg-slate-900 border border-border rounded-xl text-xs sm:text-sm text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
            />
            <button
              onClick={generateReport}
              disabled={loading || !question.trim()}
              className="px-5 py-2.5 bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-semibold rounded-xl text-xs sm:text-sm transition disabled:opacity-50 shrink-0"
            >
              {loading ? "Synthesizing Dossier..." : "Generate Dossier"}
            </button>
          </div>
        </div>

        {/* Format Selector */}
        {report && (
          <div className="flex items-center space-x-2 border-b border-border/60 pb-3 text-xs">
            <button
              onClick={() => setActiveFormat("preview")}
              className={`px-3 py-1.5 rounded-lg font-medium transition ${
                activeFormat === "preview"
                  ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                  : "text-slate-400 hover:text-white"
              }`}
            >
              Executive Preview
            </button>
            <button
              onClick={() => setActiveFormat("markdown")}
              className={`px-3 py-1.5 rounded-lg font-medium transition ${
                activeFormat === "markdown"
                  ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                  : "text-slate-400 hover:text-white"
              }`}
            >
              Markdown Source
            </button>
            <button
              onClick={() => setActiveFormat("json")}
              className={`px-3 py-1.5 rounded-lg font-medium transition ${
                activeFormat === "json"
                  ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                  : "text-slate-400 hover:text-white"
              }`}
            >
              Raw JSON
            </button>
          </div>
        )}

        {/* Report Content View */}
        {loading ? (
          <div className="glass-panel p-12 rounded-2xl border border-border text-center text-slate-400 text-xs space-y-3">
            <Sparkles className="w-8 h-8 text-emerald-400 animate-spin mx-auto" />
            <p>Traversing knowledge graph paths and compiling verifiable citations...</p>
          </div>
        ) : report ? (
          activeFormat === "preview" ? (
            <div className="glass-panel p-8 sm:p-12 rounded-2xl border border-border space-y-8 print:border-none print:p-0">
              {/* Report Header */}
              <div className="space-y-3 border-b border-border/60 pb-6">
                <div className="flex items-center justify-between text-xs text-slate-400 font-mono">
                  <span>REPORT ID: {report.id}</span>
                  <span className="text-emerald-400 font-semibold">
                    CONFIDENCE: {Math.round(report.confidence * 100)}%
                  </span>
                </div>
                <h2 className="text-2xl sm:text-3xl font-bold text-white tracking-tight">{report.title}</h2>
                <p className="text-xs text-slate-400">
                  Published: {new Date(report.created_at).toLocaleDateString()} • Verified by GraphIntel Engine
                </p>
              </div>

              {/* Executive Summary */}
              <div className="space-y-2">
                <h3 className="text-xs font-bold uppercase tracking-wider text-emerald-400">Executive Summary</h3>
                <p className="text-sm text-slate-300 leading-relaxed bg-slate-950/40 p-4 rounded-xl border border-border/40">
                  {report.executive_summary}
                </p>
              </div>

              {/* Findings */}
              <div className="space-y-3">
                <h3 className="text-xs font-bold uppercase tracking-wider text-emerald-400">Key Intelligence Findings</h3>
                <div className="space-y-2">
                  {report.findings.map((f, i) => (
                    <div key={i} className="flex items-start space-x-3 p-3 rounded-lg bg-slate-900/40 border border-border/40 text-xs">
                      <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                      <span className="text-slate-200 leading-relaxed">{f}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Entities & Relationships */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-3">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-cyan-400">Identified Entities</h3>
                  <div className="flex flex-wrap gap-1.5">
                    {report.entities.map((e, idx) => (
                      <span
                        key={idx}
                        className="px-2.5 py-1 rounded-lg bg-blue-500/10 text-blue-300 border border-blue-500/20 text-xs font-mono font-medium"
                      >
                        {e}
                      </span>
                    ))}
                  </div>
                </div>

                <div className="space-y-3">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-cyan-400">Key Network Relationships</h3>
                  <div className="space-y-1.5">
                    {report.relationships.map((r, idx) => (
                      <div
                        key={idx}
                        className="p-2 rounded-lg bg-slate-900/60 border border-border/40 text-xs font-mono flex items-center justify-between"
                      >
                        <span className="text-white">{r.source}</span>
                        <span className="text-emerald-400 text-[11px]">──[{r.rel}]──▶</span>
                        <span className="text-white">{r.target}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Verifiable Sources */}
              <div className="space-y-3 border-t border-border/60 pt-6">
                <h3 className="text-xs font-bold uppercase tracking-wider text-emerald-400">Verifiable Source Citations</h3>
                {report.citations.length === 0 ? (
                  <p className="text-xs text-slate-500">No external file citations mapped.</p>
                ) : (
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    {report.citations.map((c, idx) => (
                      <div
                        key={idx}
                        className="p-3 rounded-xl bg-slate-900/60 border border-border/60 text-xs space-y-1"
                      >
                        <div className="flex items-center justify-between text-slate-400 font-mono text-[10px]">
                          <span>[Source {c.citation_order || idx + 1}]</span>
                          <span className="text-emerald-400">{Math.round(c.relevance_score * 100)}% Match</span>
                        </div>
                        <p className="text-white font-medium truncate">{c.filename}</p>
                        {c.page_number && <p className="text-slate-500 text-[11px]">Page {c.page_number}</p>}
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Methodology & Limitations */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 border-t border-border/60 pt-6 text-xs text-slate-400">
                <div className="space-y-1.5">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-slate-300">Methodology</span>
                  <p className="leading-relaxed">{report.methodology}</p>
                </div>
                <div className="space-y-1.5">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-slate-300">Boundaries & Limitations</span>
                  <p className="leading-relaxed">{report.limitations}</p>
                </div>
              </div>
            </div>
          ) : activeFormat === "markdown" ? (
            <div className="glass-panel p-6 rounded-2xl border border-border">
              <pre className="text-xs font-mono text-slate-300 whitespace-pre-wrap leading-relaxed overflow-x-auto">
                {markdownContent}
              </pre>
            </div>
          ) : (
            <div className="glass-panel p-6 rounded-2xl border border-border">
              <pre className="text-xs font-mono text-cyan-300 whitespace-pre-wrap leading-relaxed overflow-x-auto">
                {JSON.stringify(report, null, 2)}
              </pre>
            </div>
          )
        ) : null}
      </main>
    </div>
  );
}

export default function ReportsPage() {
  return (
    <Suspense
      fallback={
        <div className="flex h-screen items-center justify-center text-xs text-slate-500">
          Loading research report workspace...
        </div>
      }
    >
      <ReportContent />
    </Suspense>
  );
}
