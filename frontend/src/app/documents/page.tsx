"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import {
  AlertCircle,
  ArrowRight,
  CheckCircle2,
  Clock,
  ExternalLink,
  FileText,
  Filter,
  Layers,
  Plus,
  RefreshCw,
  Search,
  Trash2,
  UploadCloud,
} from "lucide-react";
import Sidebar from "../../components/Sidebar";
import { api } from "../../lib/api";
import { formatBytes, formatDate } from "../../lib/utils";
import { Document } from "../../types";

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<number>(0);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadSuccess, setUploadSuccess] = useState<string | null>(null);
  const [searchFilter, setSearchFilter] = useState("");
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const fetchDocs = async () => {
    try {
      const data = await api.documents.list(0, 100);
      setDocuments(data.items);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDocs();
  }, []);

  const handleFileUpload = async (files: FileList | null) => {
    const file = files?.[0];
    if (!file) return;

    setUploading(true);
    setUploadProgress(25);
    setUploadError(null);
    setUploadSuccess(null);

    const progressTimer = setInterval(() => {
      setUploadProgress((p) => (p < 85 ? p + 15 : p));
    }, 200);

    try {
      await api.documents.upload(file, undefined, true);
      setUploadProgress(100);
      setUploadSuccess(`Successfully ingested "${file.name}" with vector and knowledge graph indexing.`);
      await fetchDocs();
    } catch (err: any) {
      setUploadError(err.message || "Failed to upload document. Please ensure valid format (PDF, DOCX, TXT, CSV, JSON).");
    } finally {
      clearInterval(progressTimer);
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileUpload(e.dataTransfer.files);
    }
  };

  const handleDelete = async (id: string, name: string) => {
    if (!confirm(`Are you sure you want to soft-delete "${name}" and prune its vectors?`)) {
      return;
    }
    try {
      await api.documents.delete(id);
      await fetchDocs();
    } catch (err: any) {
      alert(`Delete failed: ${err.message}`);
    }
  };

  const filtered = documents.filter((d) =>
    d.title.toLowerCase().includes(searchFilter.toLowerCase()) ||
    d.filename.toLowerCase().includes(searchFilter.toLowerCase())
  );

  return (
    <div className="flex">
      <Sidebar />
      <main className="flex-1 p-8 max-w-7xl mx-auto space-y-8">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-3xl font-extrabold tracking-tight text-white">Document Repository</h1>
            <p className="text-sm text-slate-400 mt-1">
              Upload filings, reports, and industry analyses with automated vector embedding and graph synchronization.
            </p>
          </div>
          <button
            onClick={fetchDocs}
            className="self-start sm:self-auto p-2.5 rounded-lg border border-border bg-slate-900/60 hover:bg-slate-800 text-slate-400 hover:text-white transition"
            title="Refresh List"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          </button>
        </div>

        {/* Drag & Drop Upload Zone */}
        <div
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`glass-panel p-8 rounded-2xl border-2 border-dashed transition-all text-center space-y-3 cursor-pointer ${
            dragActive
              ? "border-emerald-500 bg-emerald-500/5 scale-[1.005]"
              : "border-border/80 hover:border-emerald-500/50"
          }`}
        >
          <input
            type="file"
            ref={fileInputRef}
            onChange={(e) => handleFileUpload(e.target.files)}
            className="hidden"
            accept=".pdf,.docx,.txt,.md,.csv,.json"
          />

          <div className="w-14 h-14 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 mx-auto flex items-center justify-center">
            <UploadCloud className="w-7 h-7" />
          </div>

          <div>
            <p className="text-sm font-semibold text-white">
              {uploading ? "Ingesting and indexing document..." : "Drag & drop your files here, or click to browse"}
            </p>
            <p className="text-xs text-slate-400 mt-1">
              Supported formats: PDF, DOCX, TXT, Markdown, CSV, JSON (up to 50MB)
            </p>
          </div>

          {uploading && (
            <div className="max-w-xs mx-auto mt-4 space-y-1">
              <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden">
                <div
                  className="bg-emerald-500 h-2 transition-all duration-300 rounded-full"
                  style={{ width: `${uploadProgress}%` }}
                />
              </div>
              <p className="text-[11px] text-slate-400">{uploadProgress}% - Parsing & Graph Synchronization</p>
            </div>
          )}
        </div>

        {uploadSuccess && (
          <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs flex items-center space-x-2">
            <CheckCircle2 className="w-4 h-4 shrink-0" />
            <span>{uploadSuccess}</span>
          </div>
        )}

        {uploadError && (
          <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs flex items-center space-x-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{uploadError}</span>
          </div>
        )}

        {/* Filter and List */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <FileText className="w-4 h-4 text-emerald-400" />
              <h2 className="text-base font-bold text-white">Ingested Corpus ({filtered.length})</h2>
            </div>
            <div className="relative w-64">
              <Search className="w-4 h-4 text-slate-500 absolute left-3 top-2.5 pointer-events-none" />
              <input
                type="text"
                value={searchFilter}
                onChange={(e) => setSearchFilter(e.target.value)}
                placeholder="Filter documents..."
                className="w-full pl-9 pr-3 py-1.5 bg-slate-900/80 border border-border rounded-lg text-xs text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
              />
            </div>
          </div>

          {loading ? (
            <div className="p-12 text-center text-slate-500 text-xs">Loading corpus...</div>
          ) : filtered.length === 0 ? (
            <div className="p-12 text-center glass-panel rounded-2xl border border-border text-slate-500 text-xs">
              No matching documents found in your tenant workspace.
            </div>
          ) : (
            <div className="glass-panel rounded-2xl border border-border overflow-hidden">
              <div className="divide-y divide-border/60">
                {filtered.map((doc) => (
                  <div
                    key={doc.id}
                    className="p-4 flex items-center justify-between hover:bg-slate-900/50 transition gap-4"
                  >
                    <div className="flex items-center space-x-3.5 min-w-0">
                      <div className="w-10 h-10 rounded-xl bg-slate-800 border border-slate-700/60 flex items-center justify-center text-slate-300 shrink-0">
                        <FileText className="w-5 h-5 text-cyan-400" />
                      </div>
                      <div className="min-w-0">
                        <Link
                          href={`/documents/${doc.id}`}
                          className="text-sm font-semibold text-white hover:text-emerald-400 transition truncate block"
                        >
                          {doc.title || doc.filename}
                        </Link>
                        <div className="flex items-center space-x-3 text-xs text-slate-400 mt-0.5">
                          <span>{formatBytes(doc.file_size)}</span>
                          <span>•</span>
                          <span>{formatDate(doc.created_at)}</span>
                          {doc.chunks_count !== undefined && (
                            <>
                              <span>•</span>
                              <span>{doc.chunks_count} chunks</span>
                            </>
                          )}
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center space-x-4 shrink-0">
                      <span
                        className={`text-[10px] px-2.5 py-1 rounded-full font-mono uppercase font-semibold ${
                          doc.status === "COMPLETED"
                            ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                            : doc.status === "PROCESSING"
                            ? "bg-amber-500/10 text-amber-400 border border-amber-500/20 animate-pulse"
                            : "bg-rose-500/10 text-rose-400 border border-rose-500/20"
                        }`}
                      >
                        {doc.status}
                      </span>

                      <Link
                        href={`/documents/${doc.id}`}
                        className="p-2 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition"
                        title="View Document Details & Chunks"
                      >
                        <ArrowRight className="w-4 h-4" />
                      </Link>

                      <button
                        onClick={() => handleDelete(doc.id, doc.title || doc.filename)}
                        className="p-2 text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 rounded-lg transition"
                        title="Delete Document"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
