"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  ArrowLeft,
  Calendar,
  CheckCircle2,
  ChevronRight,
  Database,
  FileText,
  Hash,
  Layers,
  Search,
  Sparkles,
} from "lucide-react";
import Sidebar from "../../../components/Sidebar";
import { api } from "../../../lib/api";
import { formatBytes, formatDate } from "../../../lib/utils";
import { Document, DocumentChunk } from "../../../types";

export default function DocumentDetailPage() {
  const params = useParams();
  const id = params?.id as string;

  const [document, setDocument] = useState<Document | null>(null);
  const [chunks, setChunks] = useState<DocumentChunk[]>([]);
  const [loading, setLoading] = useState(true);
  const [chunkFilter, setChunkFilter] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    setLoading(true);

    Promise.all([api.documents.get(id), api.documents.chunks(id)])
      .then(([docData, chunksData]) => {
        setDocument(docData);
        setChunks(chunksData);
      })
      .catch((err) => {
        setError(err.message || "Failed to load document chunks.");
      })
      .finally(() => {
        setLoading(false);
      });
  }, [id]);

  const filteredChunks = chunks.filter((c) =>
    c.text.toLowerCase().includes(chunkFilter.toLowerCase()) ||
    (c.section && c.section.toLowerCase().includes(chunkFilter.toLowerCase()))
  );

  return (
    <div className="flex">
      <Sidebar />
      <main className="flex-1 p-8 max-w-7xl mx-auto space-y-8">
        <Link
          href="/documents"
          className="inline-flex items-center space-x-1.5 text-xs text-slate-400 hover:text-emerald-400 transition"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Back to Document Repository</span>
        </Link>

        {error && (
          <div className="p-4 rounded-xl bg-rose-950/40 border border-rose-800 text-rose-300 text-sm">
            {error}
          </div>
        )}

        {loading ? (
          <div className="p-12 text-center text-slate-500 text-xs">Loading document details and indexed chunks...</div>
        ) : document ? (
          <>
            {/* Header info */}
            <div className="glass-panel p-6 rounded-2xl border border-border space-y-4">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                  <div className="flex items-center space-x-2 text-xs text-emerald-400 font-mono mb-1">
                    <Database className="w-3.5 h-3.5" />
                    <span>TENANT-ISOLATED ASSET</span>
                  </div>
                  <h1 className="text-2xl font-bold text-white">{document.title}</h1>
                  <p className="text-xs text-slate-400 font-mono mt-0.5">{document.filename}</p>
                </div>
                <div>
                  <span
                    className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-medium font-mono ${
                      document.status === "COMPLETED"
                        ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                        : "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                    }`}
                  >
                    {document.status}
                  </span>
                </div>
              </div>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 pt-4 border-t border-border/50 text-xs">
                <div>
                  <span className="text-slate-500 uppercase tracking-wider block">Total Chunks</span>
                  <span className="text-white font-bold text-sm mt-0.5 block">{chunks.length}</span>
                </div>
                <div>
                  <span className="text-slate-500 uppercase tracking-wider block">File Size</span>
                  <span className="text-white font-bold text-sm mt-0.5 block">{formatBytes(document.file_size)}</span>
                </div>
                <div>
                  <span className="text-slate-500 uppercase tracking-wider block">Content Type</span>
                  <span className="text-white font-mono text-sm mt-0.5 block">{document.content_type}</span>
                </div>
                <div>
                  <span className="text-slate-500 uppercase tracking-wider block">Ingested On</span>
                  <span className="text-white font-mono text-sm mt-0.5 block">{formatDate(document.created_at)}</span>
                </div>
              </div>
            </div>

            {/* Chunks Explorer */}
            <div className="space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div className="flex items-center space-x-2">
                  <Layers className="w-5 h-5 text-cyan-400" />
                  <h2 className="text-lg font-bold text-white">
                    Parsed Chunks ({filteredChunks.length} of {chunks.length})
                  </h2>
                </div>
                <div className="relative w-72">
                  <Search className="w-4 h-4 text-slate-500 absolute left-3 top-2.5 pointer-events-none" />
                  <input
                    type="text"
                    value={chunkFilter}
                    onChange={(e) => setChunkFilter(e.target.value)}
                    placeholder="Search chunk text or section..."
                    className="w-full pl-9 pr-3 py-1.5 bg-slate-900/80 border border-border rounded-lg text-xs text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
                  />
                </div>
              </div>

              <div className="space-y-3">
                {filteredChunks.map((chunk) => (
                  <div
                    key={chunk.id}
                    className="glass-panel p-5 rounded-xl border border-border space-y-3 hover:border-slate-700 transition"
                  >
                    <div className="flex items-center justify-between text-xs text-slate-400 border-b border-border/40 pb-2">
                      <div className="flex items-center space-x-3">
                        <span className="font-mono text-emerald-400 font-semibold">Chunk #{chunk.chunk_index}</span>
                        {chunk.page_number && (
                          <span className="px-2 py-0.5 bg-slate-800 rounded font-mono text-[11px]">
                            Page {chunk.page_number}
                          </span>
                        )}
                        {chunk.section && (
                          <span className="text-slate-300 font-medium">{chunk.section}</span>
                        )}
                      </div>
                      <span className="font-mono text-slate-500">{chunk.token_count} tokens</span>
                    </div>

                    <p className="text-xs text-slate-300 leading-relaxed font-mono whitespace-pre-wrap bg-slate-950/40 p-3 rounded-lg border border-border/30">
                      {chunk.text}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          </>
        ) : null}
      </main>
    </div>
  );
}
