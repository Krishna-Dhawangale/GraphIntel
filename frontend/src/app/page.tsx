import Link from "next/link";
import { ArrowRight, Cpu, Database, FileSearch, HardDrive, Lock, ShieldCheck } from "lucide-react";

export default function Home() {
  return (
    <main className="flex min-h-[calc(100vh-4rem)] flex-col items-center justify-center px-6 py-16 relative overflow-hidden">
      {/* Background glow effects */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[350px] bg-gradient-to-tr from-emerald-500/10 via-cyan-500/15 to-transparent blur-[120px] pointer-events-none rounded-full" />

      <div className="max-w-4xl text-center z-10 space-y-6">
        <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-mono">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
          <span>PHASES 1–3 OPERATIONAL</span>
        </div>

        <h1 className="text-4xl sm:text-6xl font-extrabold tracking-tight text-white leading-tight">
          Next-Gen <span className="text-transparent bg-clip-text bg-gradient-to-r from-emerald-400 via-teal-300 to-cyan-400">Market Intelligence</span> & Document RAG
        </h1>

        <p className="text-lg sm:text-xl text-slate-400 max-w-2xl mx-auto leading-relaxed">
          Ingest unstructured financial filings, analyst reports, and competitive filings.
          Query with semantic vector retrieval and receive evidence-grounded answers with real citations.
        </p>

        <div className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-4">
          <Link
            href="/dashboard"
            className="flex items-center space-x-2 bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-semibold px-6 py-3 rounded-lg shadow-lg shadow-emerald-500/20 transition-all hover:scale-105"
          >
            <span>Open Intelligence Dashboard</span>
            <ArrowRight className="w-4 h-4" />
          </Link>
          <Link
            href="/chat"
            className="flex items-center space-x-2 bg-slate-800/80 hover:bg-slate-700 text-white font-medium px-6 py-3 rounded-lg border border-slate-700 transition"
          >
            <span>Research Assistant</span>
          </Link>
        </div>
      </div>

      {/* Feature Architecture Cards */}
      <div className="max-w-5xl w-full grid grid-cols-1 md:grid-cols-3 gap-6 mt-16 z-10">
        <div className="glass-panel p-6 rounded-xl border border-border/80 hover:border-emerald-500/40 transition">
          <div className="w-10 h-10 rounded-lg bg-emerald-500/10 flex items-center justify-center text-emerald-400 mb-4 border border-emerald-500/20">
            <Cpu className="w-5 h-5" />
          </div>
          <h2 className="text-lg font-bold text-white mb-2">Phase 1: Foundation</h2>
          <p className="text-sm text-slate-400 leading-relaxed">
            FastAPI 0.110+, SQLAlchemy 2.0 async ORM, PostgreSQL, MinIO storage, Qdrant vector DB, and JWT auth.
          </p>
        </div>

        <div className="glass-panel p-6 rounded-xl border border-border/80 hover:border-cyan-500/40 transition">
          <div className="w-10 h-10 rounded-lg bg-cyan-500/10 flex items-center justify-center text-cyan-400 mb-4 border border-cyan-500/20">
            <HardDrive className="w-5 h-5" />
          </div>
          <h2 className="text-lg font-bold text-white mb-2">Phase 2: Ingestion</h2>
          <p className="text-sm text-slate-400 leading-relaxed">
            Robust parsers for PDF (PyMuPDF), DOCX, HTML, TXT, CSV, JSON. Paragraph and sentence-aware chunking.
          </p>
        </div>

        <div className="glass-panel p-6 rounded-xl border border-border/80 hover:border-purple-500/40 transition">
          <div className="w-10 h-10 rounded-lg bg-purple-500/10 flex items-center justify-center text-purple-400 mb-4 border border-purple-500/20">
            <FileSearch className="w-5 h-5" />
          </div>
          <h2 className="text-lg font-bold text-white mb-2">Phase 3: Baseline RAG</h2>
          <p className="text-sm text-slate-400 leading-relaxed">
            Vector semantic retrieval, prompt-injection defense, grounded LLM answering, and verifiable citations.
          </p>
        </div>
      </div>
    </main>
  );
}
