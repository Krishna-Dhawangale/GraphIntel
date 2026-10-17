"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  Activity,
  ArrowRight,
  BarChart3,
  BookOpen,
  BrainCircuit,
  CheckCircle2,
  ChevronDown,
  Clock,
  Compass,
  Cpu,
  Database,
  ExternalLink,
  FileCheck,
  FileCode,
  FileSearch,
  FileText,
  HardDrive,
  HelpCircle,
  Layers,
  Lock,
  MessageSquare,
  Network,
  RefreshCw,
  Search,
  Server,
  Share2,
  Shield,
  ShieldCheck,
  Sparkles,
  Terminal,
  UserCheck,
  Users,
  Zap,
} from "lucide-react";
import { isAuthenticated } from "../lib/auth";

export default function Home() {
  const [activeDemoTab, setActiveDemoTab] = useState<"answer" | "graph" | "evidence">("answer");
  const [selectedDemoQuery, setSelectedDemoQuery] = useState(0);
  const [openFaq, setOpenFaq] = useState<number | null>(null);
  const [isLoggedIn, setIsLoggedIn] = useState(false);

  useEffect(() => {
    setIsLoggedIn(isAuthenticated());
  }, []);

  const demoQueries = [
    {
      question: "Which companies acquired AI startups founded by former Google researchers?",
      answer:
        "Based on ingested SEC filings and knowledge graph linkages, Microsoft acquired Beta AI in 2024 for $650M. Beta AI was co-founded by Dr. Elena Vance, previously Principal Researcher at Google DeepMind. Furthermore, Alphabet acquired DeepVision Labs in Q3 2023, founded by ex-Google Brain engineers.",
      latency: "185ms",
      sources: [
        { name: "Microsoft_10K_FY2024.pdf", page: 42, score: "96% Match" },
        { name: "Alphabet_Acquisition_Disclosures_2024.pdf", page: 18, score: "93% Match" },
      ],
      nodes: ["Google", "Dr. Elena Vance", "Beta AI", "Microsoft", "Alphabet"],
      edges: [
        { from: "Dr. Elena Vance", rel: "FORMER_RESEARCHER_AT", to: "Google" },
        { from: "Dr. Elena Vance", rel: "CO_FOUNDED", to: "Beta AI" },
        { from: "Microsoft", rel: "ACQUIRED ($650M)", to: "Beta AI" },
      ],
    },
    {
      question: "What was Microsoft's revenue and AI infrastructure capital expenditure in 2024?",
      answer:
        "Microsoft reported FY2024 total revenue of $245.1 billion, representing a 16% YoY increase. Capital expenditures dedicated to cloud infrastructure, GPU clusters, and datacenter buildouts reached $55.7 billion, driven primarily by demand for Azure OpenAI and enterprise copilots.",
      latency: "210ms",
      sources: [
        { name: "Microsoft_Annual_Report_2024.pdf", page: 14, score: "98% Match" },
        { name: "Cloud_Capex_Quarterly_Breakdown.pdf", page: 6, score: "94% Match" },
      ],
      nodes: ["Microsoft", "Azure OpenAI", "Datacenter Capex", "Cloud Revenue"],
      edges: [
        { from: "Microsoft", rel: "REPORTED_REVENUE ($245.1B)", to: "Cloud Revenue" },
        { from: "Microsoft", rel: "ALLOCATED_CAPEX ($55.7B)", to: "Datacenter Capex" },
        { from: "Datacenter Capex", rel: "POWERS", to: "Azure OpenAI" },
      ],
    },
    {
      question: "Which institutional investors participated in enterprise AI Series B rounds between 2023 and 2024?",
      answer:
        "Sequoia Capital and Andreessen Horowitz co-led Series B rounds in enterprise foundation models and semantic vector indexing platforms. Key funding syndicates linked Sequoia to 4 investments in 2024 totaling $420M in private equity deployment.",
      latency: "195ms",
      sources: [
        { name: "VC_Funding_Database_2024.pdf", page: 88, score: "95% Match" },
        { name: "Series_B_Syndicate_Filings.json", page: 1, score: "91% Match" },
      ],
      nodes: ["Sequoia Capital", "Andreessen Horowitz", "Foundation Models", "Series B Syndicate"],
      edges: [
        { from: "Sequoia Capital", rel: "CO_LED_ROUND", to: "Foundation Models" },
        { from: "Andreessen Horowitz", rel: "PARTICIPATED_IN", to: "Series B Syndicate" },
      ],
    },
  ];

  const currentDemo = demoQueries[selectedDemoQuery];

  const capabilities = [
    {
      title: "Hybrid GraphRAG Fusion",
      desc: "Simultaneously query dense cosine vector embeddings in Qdrant and multi-hop Cypher relationships in Neo4j with reciprocal rank fusion.",
      icon: Layers,
      color: "from-emerald-500/20 to-teal-500/20",
      badge: "Hybrid Engine",
    },
    {
      title: "Deep Multi-Format Parsers",
      desc: "Enterprise parsers for PDF (PyMuPDF), DOCX, HTML, TXT, CSV, and JSON with paragraph-aware and sentence-aware semantic chunking.",
      icon: HardDrive,
      color: "from-cyan-500/20 to-blue-500/20",
      badge: "Ingestion Engine",
    },
    {
      title: "Autonomous LangGraph Agent",
      desc: "Autonomous multi-step query planning, self-correction, iterative graph expansion, and tool-routed research synthesis.",
      icon: BrainCircuit,
      color: "from-purple-500/20 to-indigo-500/20",
      badge: "Agentic Reasoning",
    },
    {
      title: "Verifiable Page-Level Citations",
      desc: "Eliminate hallucinations with verifiable source citations, relevance scores, and interactive text-snippet evidence inspectors.",
      icon: FileCheck,
      color: "from-emerald-500/20 to-cyan-500/20",
      badge: "Zero Hallucination",
    },
    {
      title: "Interactive Topology Canvas",
      desc: "Visual touch-friendly SVG network graph with interactive circular layout, zoom & pan, and real-time node & relationship exploration.",
      icon: Network,
      color: "from-amber-500/20 to-orange-500/20",
      badge: "Visual Graph",
    },
    {
      title: "Enterprise Multi-Tenant Isolation",
      desc: "Strict tenant data boundaries, Redis semantic query caching, sliding-window rate limiting, and immutable security audit logs.",
      icon: ShieldCheck,
      color: "from-rose-500/20 to-pink-500/20",
      badge: "Enterprise Security",
    },
  ];

  const comparisonRows = [
    {
      feature: "Cross-Entity Relationship Discovery",
      keyword: "None (Text match only)",
      vector: "Limited (Proximity only)",
      graphIntel: "Multi-Hop Cypher Traversal in Neo4j",
      highlight: true,
    },
    {
      feature: "Fact Grounding & Citation Proof",
      keyword: "Document names only",
      vector: "Coarse chunk text",
      graphIntel: "Verifiable Page & Chunk Citations with Scores",
      highlight: true,
    },
    {
      feature: "Complex Multi-Step Synthesis",
      keyword: "Manual analyst review",
      vector: "Single-turn prompt",
      graphIntel: "Autonomous LangGraph Planner with Self-Correction",
      highlight: true,
    },
    {
      feature: "Query Latency & Scalability",
      keyword: "Fast (100ms)",
      vector: "Moderate (300-600ms)",
      graphIntel: "Sub-250ms with Redis Semantic Caching",
      highlight: false,
    },
    {
      feature: "Enterprise Multi-Tenancy & RBAC",
      keyword: "Basic index filters",
      vector: "Metadata tags only",
      graphIntel: "Cryptographic Scopes across PostgreSQL, Qdrant & Neo4j",
      highlight: true,
    },
  ];

  const faqs = [
    {
      q: "How does GraphIntel eliminate hallucinations in market intelligence?",
      a: "Standard RAG queries only retrieve isolated text chunks based on semantic similarity. GraphIntel fuses dense vector retrieval (Qdrant) with explicit entity-relationship knowledge graphs (Neo4j). Every single synthesized fact is grounded in ingested document chunks and mapped to verifiable citations with exact page numbers.",
    },
    {
      q: "What file formats and document types are supported for ingestion?",
      a: "GraphIntel supports PDF (including scanned filings via PyMuPDF), Word Documents (DOCX), HTML reports, Plain Text (TXT), Markdown (MD), CSV tabular data, and structured JSON files up to 50MB per upload.",
    },
    {
      q: "How is multi-tenant security and data isolation enforced?",
      a: "All database records, vector collection points, and graph subgraphs are tagged with unique Tenant IDs. SQLAlchemy async session scopes, Qdrant payload filters, and Neo4j Cypher queries enforce strict isolation so no cross-tenant data leakage is possible.",
    },
    {
      q: "What is the difference between Vector, Graph, and Hybrid retrieval modes?",
      a: "Vector mode retrieves dense similarity chunks from Qdrant. Graph mode executes multi-hop Cypher traversals in Neo4j to find relationship paths. Hybrid mode combines both using reciprocal rank fusion, providing both contextual evidence and structured relationship chains.",
    },
    {
      q: "How do I get started with GraphIntel?",
      a: "Click the 'Get Started' button on this page to create your workspace account. You will immediately land on your intelligence dashboard, where you can ingest filings, explore knowledge graphs, and run research queries.",
    },
  ];

  return (
    <main className="min-h-screen bg-[#090d16] text-slate-100 selection:bg-emerald-500/30 selection:text-emerald-300 relative overflow-hidden pb-24 lg:pb-16">
      {/* Dynamic Ambient Background Glows */}
      <div className="absolute top-12 left-1/2 -translate-x-1/2 w-[350px] sm:w-[800px] h-[320px] sm:h-[500px] bg-gradient-to-tr from-emerald-500/15 via-teal-500/15 to-cyan-500/10 blur-[120px] sm:blur-[160px] pointer-events-none rounded-full" />
      <div className="absolute top-[850px] -left-48 w-[450px] h-[450px] bg-purple-500/10 blur-[140px] pointer-events-none rounded-full" />
      <div className="absolute top-[1500px] -right-48 w-[500px] h-[500px] bg-cyan-500/10 blur-[150px] pointer-events-none rounded-full" />

      {/* Subtle Grid Pattern Overlay */}
      <div
        className="absolute inset-0 opacity-[0.03] pointer-events-none"
        style={{
          backgroundImage: "radial-gradient(#10b981 1px, transparent 1px)",
          backgroundSize: "32px 32px",
        }}
      />

      {/* ================= HERO SECTION ================= */}
      <section className="max-w-6xl mx-auto px-4 sm:px-6 pt-12 sm:pt-20 pb-16 text-center relative z-10 space-y-6">
        {/* Status Pill Badge */}
        <div className="inline-flex items-center space-x-2 px-3.5 py-1.5 rounded-full bg-emerald-500/10 border border-emerald-500/25 text-emerald-400 text-xs font-mono shadow-lg shadow-emerald-500/5 hover:border-emerald-500/40 transition">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
          <span>GRAPHINTEL 2.0 • ENTERPRISE MARKET INTELLIGENCE & HYBRID GRAPHRAG</span>
        </div>

        {/* Hero Title */}
        <h1 className="text-3xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight text-white leading-[1.12] max-w-4xl mx-auto">
          Turn Unstructured Filings into Grounded{" "}
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-emerald-400 via-teal-300 to-cyan-400">
            Market Intelligence
          </span>
        </h1>

        {/* Hero Subtitle */}
        <p className="text-sm sm:text-lg lg:text-xl text-slate-400 max-w-3xl mx-auto leading-relaxed">
          Ingest complex corporate filings, financial disclosures, and analyst dossiers. Query across dense vector embeddings in Qdrant, Neo4j multi-hop knowledge graph topologies, and LangGraph autonomous reasoning with verifiable citations.
        </p>

        {/* Hero Primary Action CTA Buttons */}
        <div className="flex flex-col sm:flex-row items-center justify-center gap-3 sm:gap-4 pt-4">
          <Link
            href="/dashboard"
            className="w-full sm:w-auto flex items-center justify-center space-x-2.5 bg-gradient-to-r from-emerald-500 to-teal-400 hover:from-emerald-400 hover:to-teal-300 text-slate-950 font-bold px-7 py-3.5 rounded-xl shadow-xl shadow-emerald-500/25 transition-all hover:scale-105 active:scale-95 group"
          >
            <BarChart3 className="w-5 h-5 group-hover:rotate-6 transition-transform" />
            <span>Go to Intelligence Dashboard</span>
            <ArrowRight className="w-4 h-4 ml-1 group-hover:translate-x-1 transition-transform" />
          </Link>

          {!isLoggedIn && (
            <Link
              href="/login"
              className="w-full sm:w-auto flex items-center justify-center space-x-2 bg-slate-900/90 hover:bg-slate-800 text-white font-semibold px-6 py-3.5 rounded-xl border border-slate-700/80 transition shadow hover:border-slate-500 hover:scale-105 active:scale-95"
            >
              <Lock className="w-4 h-4 text-emerald-400" />
              <span>Sign In</span>
            </Link>
          )}

          <Link
            href="#demo"
            className="w-full sm:w-auto flex items-center justify-center space-x-2 bg-slate-900/60 hover:bg-slate-800/80 text-cyan-400 font-semibold px-6 py-3.5 rounded-xl border border-cyan-500/30 transition shadow hover:border-cyan-500/60"
          >
            <Terminal className="w-4 h-4 text-cyan-400" />
            <span>Interactive Demo</span>
          </Link>
        </div>

        {/* 4 Trust & Performance Metrics Badges */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 max-w-4xl mx-auto pt-8 text-left">
          <div className="glass-panel p-4 rounded-xl border border-border/80 hover:border-emerald-500/30 transition">
            <div className="flex items-center space-x-2 text-emerald-400 mb-1">
              <FileCheck className="w-4 h-4" />
              <span className="text-xs font-bold font-mono">100% Grounded</span>
            </div>
            <p className="text-[11px] sm:text-xs text-slate-400">Verifiable page & token citations for every fact</p>
          </div>

          <div className="glass-panel p-4 rounded-xl border border-border/80 hover:border-cyan-500/30 transition">
            <div className="flex items-center space-x-2 text-cyan-400 mb-1">
              <Zap className="w-4 h-4" />
              <span className="text-xs font-bold font-mono">&lt; 250ms Latency</span>
            </div>
            <p className="text-[11px] sm:text-xs text-slate-400">Sub-second hybrid vector and graph retrieval</p>
          </div>

          <div className="glass-panel p-4 rounded-xl border border-border/80 hover:border-purple-500/30 transition">
            <div className="flex items-center space-x-2 text-purple-400 mb-1">
              <Network className="w-4 h-4" />
              <span className="text-xs font-bold font-mono">Multi-Hop Chains</span>
            </div>
            <p className="text-[11px] sm:text-xs text-slate-400">Uncover indirect acquisition & executive linkages</p>
          </div>

          <div className="glass-panel p-4 rounded-xl border border-border/80 hover:border-rose-500/30 transition">
            <div className="flex items-center space-x-2 text-rose-400 mb-1">
              <Shield className="w-4 h-4" />
              <span className="text-xs font-bold font-mono">Tenant Isolation</span>
            </div>
            <p className="text-[11px] sm:text-xs text-slate-400">Strict workspace data boundaries & RBAC control</p>
          </div>
        </div>
      </section>

      {/* ================= INTERACTIVE WORKSPACE DEMO PREVIEW ================= */}
      <section id="demo" className="max-w-6xl mx-auto px-4 sm:px-6 py-12 relative z-10 space-y-6 scroll-mt-20">
        <div className="text-center space-y-2">
          <div className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full bg-cyan-500/10 border border-cyan-500/20 text-cyan-400 text-xs font-mono">
            <Sparkles className="w-3.5 h-3.5" />
            <span>LIVE INTELLIGENCE WORKSPACE SIMULATOR</span>
          </div>
          <h2 className="text-2xl sm:text-3xl font-bold text-white tracking-tight">
            Experience Hybrid GraphRAG in Action
          </h2>
          <p className="text-xs sm:text-sm text-slate-400 max-w-xl mx-auto">
            Select a sample intelligence query below to inspect how GraphIntel harmonizes vector similarity with multi-hop graph reasoning.
          </p>
        </div>

        {/* Query Presets Chips */}
        <div className="flex flex-wrap items-center justify-center gap-2 max-w-3xl mx-auto">
          {demoQueries.map((item, idx) => (
            <button
              key={idx}
              onClick={() => {
                setSelectedDemoQuery(idx);
                setActiveDemoTab("answer");
              }}
              className={`px-3.5 py-2 rounded-xl text-xs font-medium transition text-left ${
                selectedDemoQuery === idx
                  ? "bg-emerald-500/15 text-emerald-300 border border-emerald-500/50 shadow-md shadow-emerald-500/10"
                  : "glass-panel text-slate-400 hover:text-slate-200 border-border hover:border-slate-700"
              }`}
            >
              <span className="font-bold text-emerald-400">Query #{idx + 1}: </span>
              <span className="text-slate-300 font-normal">
                "{item.question.length > 40 ? item.question.slice(0, 40) + "..." : item.question}"
              </span>
            </button>
          ))}
        </div>

        {/* Mock Intelligence Terminal Window */}
        <div className="glass-panel rounded-2xl border border-border/90 shadow-2xl overflow-hidden max-w-4xl mx-auto bg-slate-950/70">
          {/* Terminal Window Header */}
          <div className="p-3.5 sm:p-4 bg-slate-950/90 border-b border-border/80 flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center space-x-2">
              <span className="w-3 h-3 rounded-full bg-rose-500/80 inline-block" />
              <span className="w-3 h-3 rounded-full bg-amber-500/80 inline-block" />
              <span className="w-3 h-3 rounded-full bg-emerald-500/80 inline-block" />
              <span className="text-xs font-mono text-slate-400 ml-2 font-semibold truncate max-w-[200px] sm:max-w-none">
                GraphIntel Hybrid Query Terminal
              </span>
            </div>

            {/* Tab Switches */}
            <div className="flex items-center space-x-1 bg-slate-900 p-1 rounded-lg border border-border/60 text-xs">
              <button
                onClick={() => setActiveDemoTab("answer")}
                className={`px-3 py-1 rounded-md text-xs font-medium transition ${
                  activeDemoTab === "answer"
                    ? "bg-emerald-500 text-slate-950 font-bold shadow-sm"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                Grounded Answer
              </button>
              <button
                onClick={() => setActiveDemoTab("graph")}
                className={`px-3 py-1 rounded-md text-xs font-medium transition ${
                  activeDemoTab === "graph"
                    ? "bg-emerald-500 text-slate-950 font-bold shadow-sm"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                Graph Paths
              </button>
              <button
                onClick={() => setActiveDemoTab("evidence")}
                className={`px-3 py-1 rounded-md text-xs font-medium transition ${
                  activeDemoTab === "evidence"
                    ? "bg-emerald-500 text-slate-950 font-bold shadow-sm"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                Source Citations
              </button>
            </div>
          </div>

          {/* Terminal Body */}
          <div className="p-5 sm:p-6 space-y-4 text-xs sm:text-sm">
            {/* User Prompt */}
            <div className="flex items-start space-x-3 text-slate-300 bg-slate-900/50 p-3 rounded-xl border border-border/50">
              <span className="text-emerald-400 font-mono font-bold shrink-0 mt-0.5">query&gt;</span>
              <p className="font-semibold text-white">{currentDemo.question}</p>
            </div>

            {/* Dynamic Content View */}
            {activeDemoTab === "answer" && (
              <div className="space-y-4 pt-1 animate-in fade-in duration-200">
                <div className="p-4 rounded-xl bg-slate-950/80 border border-border/70 leading-relaxed text-slate-200 font-mono text-xs sm:text-sm whitespace-pre-wrap">
                  {currentDemo.answer}
                </div>

                <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-slate-400 font-mono pt-1">
                  <div className="flex items-center space-x-2">
                    <span className="text-emerald-400 font-bold">HYBRID GRAPHRAG</span>
                    <span>•</span>
                    <span>Response Time: {currentDemo.latency}</span>
                  </div>
                  <span className="text-cyan-400 font-medium">{currentDemo.sources.length} verifiable citations attached</span>
                </div>
              </div>
            )}

            {activeDemoTab === "graph" && (
              <div className="space-y-3 pt-1 animate-in fade-in duration-200">
                <p className="text-xs text-slate-400">
                  Discovered Neo4j Multi-Hop Traversal Chain:
                </p>
                <div className="space-y-2">
                  {currentDemo.edges.map((edge, idx) => (
                    <div
                      key={idx}
                      className="p-3 rounded-xl bg-slate-950/80 border border-border/70 flex flex-wrap items-center justify-between gap-2 font-mono text-xs"
                    >
                      <span className="px-2.5 py-1 rounded bg-blue-500/10 text-blue-300 border border-blue-500/20 font-semibold">
                        {edge.from}
                      </span>
                      <span className="text-emerald-400 text-[11px] font-bold">
                        ──[{edge.rel}]──▶
                      </span>
                      <span className="px-2.5 py-1 rounded bg-purple-500/10 text-purple-300 border border-purple-500/20 font-semibold">
                        {edge.to}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {activeDemoTab === "evidence" && (
              <div className="space-y-3 pt-1 animate-in fade-in duration-200">
                <p className="text-xs text-slate-400">
                  Verifiable Source Documents & Vector Chunks:
                </p>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {currentDemo.sources.map((src, idx) => (
                    <div
                      key={idx}
                      className="p-3.5 rounded-xl bg-slate-950/80 border border-border/70 space-y-1.5"
                    >
                      <div className="flex items-center justify-between text-xs text-slate-400 font-mono">
                        <span className="text-emerald-400 font-bold">[Citation #{idx + 1}]</span>
                        <span className="text-cyan-400 font-semibold">{src.score}</span>
                      </div>
                      <p className="text-xs font-semibold text-white truncate">{src.name}</p>
                      <p className="text-[11px] text-slate-500 font-mono">Document Page {src.page}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Quick Action inside Terminal */}
            <div className="pt-2 flex items-center justify-end">
              <Link
                href={isLoggedIn ? "/dashboard" : "/register"}
                className="inline-flex items-center space-x-1.5 text-xs text-emerald-400 hover:text-emerald-300 font-medium transition"
              >
                <span>Run live queries in full workspace</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* ================= CORE CAPABILITIES BENTO GRID ================= */}
      <section id="capabilities" className="max-w-6xl mx-auto px-4 sm:px-6 py-12 relative z-10 space-y-6 scroll-mt-20">
        <div className="text-center space-y-2">
          <div className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-mono">
            <Layers className="w-3.5 h-3.5" />
            <span>ENTERPRISE ARCHITECTURE</span>
          </div>
          <h2 className="text-2xl sm:text-3xl font-bold text-white tracking-tight">
            Six Pillars of Grounded Intelligence
          </h2>
          <p className="text-xs sm:text-sm text-slate-400 max-w-xl mx-auto">
            Engineered from the ground up to ingest, index, reason, and verify enterprise market intelligence.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6">
          {capabilities.map((c) => {
            const Icon = c.icon;
            return (
              <div
                key={c.title}
                className="glass-panel p-5 sm:p-6 rounded-2xl border border-border/80 hover:border-emerald-500/40 transition flex flex-col justify-between space-y-4 group hover:-translate-y-0.5 shadow-lg"
              >
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="w-10 h-10 rounded-xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center justify-center shrink-0 group-hover:scale-110 transition-transform">
                      <Icon className="w-5 h-5" />
                    </div>
                    <span className="text-[10px] font-mono font-semibold px-2 py-0.5 rounded-full border bg-emerald-500/10 text-emerald-400 border-emerald-500/20">
                      {c.badge}
                    </span>
                  </div>

                  <h3 className="text-base font-bold text-white leading-snug group-hover:text-emerald-300 transition-colors">
                    {c.title}
                  </h3>
                  <p className="text-xs sm:text-sm text-slate-400 leading-relaxed">{c.desc}</p>
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* ================= HOW IT WORKS WORKFLOW ================= */}
      <section id="workflow" className="max-w-6xl mx-auto px-4 sm:px-6 py-12 relative z-10 space-y-8 scroll-mt-20">
        <div className="text-center space-y-2">
          <div className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full bg-purple-500/10 border border-purple-500/20 text-purple-400 text-xs font-mono">
            <Compass className="w-3.5 h-3.5" />
            <span>PIPELINE WORKFLOW</span>
          </div>
          <h2 className="text-2xl sm:text-3xl font-bold text-white tracking-tight">
            How GraphIntel Works
          </h2>
          <p className="text-xs sm:text-sm text-slate-400 max-w-xl mx-auto">
            From raw, messy corporate filings to verified multi-hop synthesized intelligence.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="glass-panel p-5 rounded-2xl border border-border space-y-3 hover:border-blue-500/40 transition">
            <div className="w-8 h-8 rounded-lg bg-blue-500/10 border border-blue-500/20 text-blue-400 flex items-center justify-center font-bold text-xs font-mono">
              01
            </div>
            <h3 className="text-sm font-bold text-white">Ingest & Parse</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Upload PDF 10-Ks, earnings reports, DOCX, CSV, and JSON with semantic paragraph chunking and PyMuPDF extractors.
            </p>
          </div>

          <div className="glass-panel p-5 rounded-2xl border border-border space-y-3 hover:border-cyan-500/40 transition">
            <div className="w-8 h-8 rounded-lg bg-cyan-500/10 border border-cyan-500/20 text-cyan-400 flex items-center justify-center font-bold text-xs font-mono">
              02
            </div>
            <h3 className="text-sm font-bold text-white">Dual Indexing</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Generate dense cosine vectors in Qdrant and extract multi-entity relationship graph nodes in Neo4j with tenant isolation.
            </p>
          </div>

          <div className="glass-panel p-5 rounded-2xl border border-border space-y-3 hover:border-purple-500/40 transition">
            <div className="w-8 h-8 rounded-lg bg-purple-500/10 border border-purple-500/20 text-purple-400 flex items-center justify-center font-bold text-xs font-mono">
              03
            </div>
            <h3 className="text-sm font-bold text-white">Hybrid Reasoning</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Traverse multi-hop indirect linkages combined with dense similarity using LangGraph planning and reciprocal rank fusion.
            </p>
          </div>

          <div className="glass-panel p-5 rounded-2xl border border-border space-y-3 hover:border-emerald-500/40 transition">
            <div className="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 flex items-center justify-center font-bold text-xs font-mono">
              04
            </div>
            <h3 className="text-sm font-bold text-white">Verified Synthesis</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Deliver grounded answers with page-level citations and export dossiers in Markdown, JSON, and PDF formats.
            </p>
          </div>
        </div>
      </section>

      {/* ================= ARCHITECTURAL COMPARISON MATRIX ================= */}
      <section id="comparison" className="max-w-6xl mx-auto px-4 sm:px-6 py-12 relative z-10 space-y-6 scroll-mt-20">
        <div className="text-center space-y-2">
          <div className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-mono">
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>WHY GRAPHINTEL</span>
          </div>
          <h2 className="text-2xl sm:text-3xl font-bold text-white tracking-tight">
            Comparison: Keyword vs Vector RAG vs GraphIntel
          </h2>
          <p className="text-xs sm:text-sm text-slate-400 max-w-xl mx-auto">
            Why leading analysts choose hybrid knowledge graph fusion over traditional search engines.
          </p>
        </div>

        <div className="glass-panel rounded-2xl border border-border/80 overflow-x-auto shadow-2xl">
          <table className="w-full text-left text-xs sm:text-sm">
            <thead className="bg-slate-950/80 border-b border-border/80 text-xs uppercase text-slate-400 font-mono">
              <tr>
                <th className="p-4 sm:p-5">Capability</th>
                <th className="p-4 sm:p-5 text-slate-500">Keyword Search</th>
                <th className="p-4 sm:p-5 text-slate-500">Standard Vector RAG</th>
                <th className="p-4 sm:p-5 text-emerald-400 font-bold bg-emerald-500/5">
                  GraphIntel Hybrid GraphRAG
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/60">
              {comparisonRows.map((row, idx) => (
                <tr key={idx} className="hover:bg-slate-900/40 transition">
                  <td className="p-4 sm:p-5 font-semibold text-white whitespace-nowrap">
                    {row.feature}
                  </td>
                  <td className="p-4 sm:p-5 text-slate-400">{row.keyword}</td>
                  <td className="p-4 sm:p-5 text-slate-400">{row.vector}</td>
                  <td className="p-4 sm:p-5 text-emerald-300 font-medium bg-emerald-500/5">
                    <div className="flex items-center space-x-1.5">
                      <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                      <span>{row.graphIntel}</span>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>


      {/* ================= INTERACTIVE FAQ SECTION ================= */}
      <section id="faq" className="max-w-4xl mx-auto px-4 sm:px-6 py-12 relative z-10 space-y-6 scroll-mt-20">
        <div className="text-center space-y-2">
          <div className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full bg-slate-800 border border-slate-700 text-slate-300 text-xs font-mono">
            <HelpCircle className="w-3.5 h-3.5 text-emerald-400" />
            <span>QUESTIONS & ANSWERS</span>
          </div>
          <h2 className="text-2xl sm:text-3xl font-bold text-white tracking-tight">
            Frequently Asked Questions
          </h2>
          <p className="text-xs sm:text-sm text-slate-400">
            Key details about GraphIntel's architecture, security, and verification guarantees.
          </p>
        </div>

        <div className="space-y-3">
          {faqs.map((faq, idx) => {
            const isOpen = openFaq === idx;
            return (
              <div
                key={idx}
                className="glass-panel rounded-xl border border-border overflow-hidden transition"
              >
                <button
                  onClick={() => setOpenFaq(isOpen ? null : idx)}
                  className="w-full p-4 sm:p-5 flex items-center justify-between text-left hover:bg-slate-900/50 transition gap-4"
                >
                  <span className="text-xs sm:text-sm font-semibold text-white">{faq.q}</span>
                  <ChevronDown
                    className={`w-4 h-4 text-slate-400 transition-transform shrink-0 ${
                      isOpen ? "rotate-180 text-emerald-400" : ""
                    }`}
                  />
                </button>
                {isOpen && (
                  <div className="px-4 sm:px-5 pb-4 sm:pb-5 text-xs sm:text-sm text-slate-300 leading-relaxed border-t border-border/40 pt-3 animate-in fade-in">
                    {faq.a}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </section>

      {/* ================= BOTTOM CTA BANNER ================= */}
      <section className="max-w-6xl mx-auto px-4 sm:px-6 py-12 relative z-10">
        <div className="glass-panel p-8 sm:p-14 rounded-3xl border border-emerald-500/30 text-center space-y-6 bg-gradient-to-b from-slate-900/90 via-[#0a1122] to-[#070b14] relative overflow-hidden shadow-2xl">
          {/* Subtle Ambient Glow behind CTA */}
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-emerald-500/10 blur-[100px] pointer-events-none rounded-full" />

          <div className="w-14 h-14 rounded-2xl bg-gradient-to-tr from-emerald-500 to-cyan-500 flex items-center justify-center mx-auto text-black shadow-lg shadow-emerald-500/25">
            <Activity className="w-7 h-7" />
          </div>

          <div className="space-y-2 max-w-2xl mx-auto relative z-10">
            <h2 className="text-2xl sm:text-4xl font-extrabold text-white tracking-tight">
              Start Researching with GraphIntel Today
            </h2>
            <p className="text-xs sm:text-sm text-slate-400">
              Ingest your corporate filings, query with multi-hop GraphRAG, and generate executive dossiers with zero hallucination.
            </p>
          </div>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-3 pt-2 relative z-10">
            <Link
              href="/dashboard"
              className="w-full sm:w-auto px-8 py-3.5 bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold rounded-xl shadow-xl shadow-emerald-500/20 transition-all hover:scale-105 active:scale-95 flex items-center justify-center space-x-2"
            >
              <BarChart3 className="w-4 h-4" />
              <span>Launch Intelligence Dashboard</span>
              <ArrowRight className="w-4 h-4 ml-1" />
            </Link>

            {!isLoggedIn && (
              <Link
                href="/login"
                className="w-full sm:w-auto px-8 py-3.5 bg-slate-800 hover:bg-slate-700 text-white font-semibold rounded-xl border border-slate-700 transition flex items-center justify-center space-x-2"
              >
                <Lock className="w-4 h-4 text-emerald-400" />
                <span>Sign In to Account</span>
              </Link>
            )}
          </div>

          <div className="flex flex-wrap items-center justify-center gap-4 text-[11px] text-slate-500 font-mono pt-2 relative z-10">
            <span>✓ Instant Tenant Provisioning</span>
            <span>•</span>
            <span>✓ Multi-Tenant Isolation</span>
            <span>•</span>
            <span>✓ Zero Setup Fees</span>
          </div>
        </div>
      </section>

      {/* ================= FOOTER ================= */}
      <footer className="max-w-6xl mx-auto px-4 sm:px-6 pt-12 pb-6 border-t border-border/60 text-xs text-slate-500 flex flex-col sm:flex-row items-center justify-between gap-4 relative z-10">
        <div className="flex items-center space-x-2">
          <Activity className="w-4 h-4 text-emerald-400" />
          <span className="font-semibold text-slate-300">GraphIntel Platform</span>
          <span>•</span>
          <span>Enterprise Market Intelligence & Document RAG</span>
        </div>

        <div className="flex items-center space-x-4 text-slate-400">
          <Link href="/dashboard" className="hover:text-white transition">Dashboard</Link>
          <Link href="/documents" className="hover:text-white transition">Documents</Link>
          <Link href="/graph" className="hover:text-white transition">Knowledge Graph</Link>
          <Link href="/chat" className="hover:text-white transition">Research</Link>
          <Link href="/reports" className="hover:text-white transition">Reports</Link>
          <a
            href="https://graphintel-api-mrbj.onrender.com/api/v1/docs"
            target="_blank"
            rel="noreferrer"
            className="text-cyan-400 hover:underline inline-flex items-center space-x-1"
          >
            <span>API Docs</span>
            <ExternalLink className="w-3 h-3" />
          </a>
        </div>
      </footer>
    </main>
  );
}
