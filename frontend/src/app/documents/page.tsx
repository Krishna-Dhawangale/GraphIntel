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
import { toast } from "../../lib/toast";

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

  // Real-time polling for any documents currently in PROCESSING or UPLOADED state
  useEffect(() => {
    const hasPending = documents.some(
      (d) => d.status === "PROCESSING" || d.status === "UPLOADED"
    );
    if (!hasPending) return;

    const interval = setInterval(async () => {
      try {
        const pendingDocs = documents.filter(
          (d) => d.status === "PROCESSING" || d.status === "UPLOADED"
        );
        let anyChanged = false;

        const updated = await Promise.all(
          pendingDocs.map(async (doc) => {
            try {
              const statusData = await api.documents.status(doc.id);
              if (statusData.status !== doc.status) {
                anyChanged = true;
              }
              return {
                ...doc,
                status: statusData.status,
                chunks_count: statusData.total_chunks,
                error_message: statusData.error_message ?? null,
              };
            } catch {
              return doc;
            }
          })
        );

        if (anyChanged) {
          setDocuments((prev) =>
            prev.map((d) => {
              const match = updated.find((u) => u.id === d.id);
              return match || d;
            })
          );
        }
      } catch (err) {
        console.error("Status poll error:", err);
      }
    }, 2500);

    return () => clearInterval(interval);
  }, [documents]);

  const handleFileUpload = async (files: FileList | null) => {
    if (!files || files.length === 0) return;

    setUploading(true);
    setUploadProgress(15);
    setUploadError(null);
    setUploadSuccess(null);

    const progressInterval = setInterval(() => {
      setUploadProgress((prev) => (prev < 90 ? prev + 25 : prev));
    }, 150);

    try {
      const uploadList = Array.from(files);
      let successCount = 0;

      for (const file of uploadList) {
        // Fast non-blocking upload: server accepts file and runs ingestion asynchronously
        await api.documents.upload(file, undefined, false);
        successCount++;
      }

      setUploadProgress(100);
      const msg =
        successCount === 1
          ? `"${uploadList[0].name}" uploaded — ingesting in background...`
          : `${successCount} documents queued for ingestion.`;
      setUploadSuccess(msg);
      toast.success(msg, { duration: 4000 });

      // Instantly refresh list to show newly uploaded document(s) in PROCESSING state
      await fetchDocs();
    } catch (err: any) {
      const errMsg = err.message || "Failed to upload document. Please ensure valid format (PDF, DOCX, TXT, CSV, JSON).";
      setUploadError(errMsg);
      toast.error(errMsg, { duration: 6000 });
    } finally {
      clearInterval(progressInterval);
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
    if (!confirm(`Are you sure you want to delete "${name}" and prune its vectors?`)) {
      return;
    }
    try {
      await api.documents.delete(id);
      toast.success(`"${name}" deleted and vectors pruned.`, { duration: 3000 });
      await fetchDocs();
    } catch (err: any) {
      const errMsg = `Delete failed: ${err.message}`;
      toast.error(errMsg, { duration: 5000 });
    }
  };

  const filtered = documents.filter((d) =>
    d.title.toLowerCase().includes(searchFilter.toLowerCase()) ||
    d.filename.toLowerCase().includes(searchFilter.toLowerCase())
  );

  return (
    <div className="flex min-h-[calc(100vh-4rem)]">
      <Sidebar />
      <main className="flex-1 min-w-0 p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto space-y-6 sm:space-y-8 pb-20 lg:pb-8">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 sm:gap-4">
          <div>
            <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-white">Document Repository</h1>
            <p className="text-xs sm:text-sm text-slate-400 mt-1">
              Upload filings, reports, and industry analyses with automated vector embedding and graph synchronization.
            </p>
          </div>
          <button
            onClick={fetchDocs}
            className="self-start sm:self-auto p-2 sm:p-2.5 rounded-xl border border-border bg-slate-900/60 hover:bg-slate-800 text-slate-400 hover:text-white transition"
            title="Refresh List"
            aria-label="Refresh List"
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
          className={`glass-panel p-6 sm:p-8 rounded-2xl border-2 border-dashed transition-all text-center space-y-3 cursor-pointer ${
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
            multiple
            accept=".pdf,.docx,.txt,.md,.csv,.json"
          />

          <div className="w-12 h-12 sm:w-14 sm:h-14 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 mx-auto flex items-center justify-center">
            <UploadCloud className="w-6 h-6 sm:w-7 sm:h-7" />
          </div>

          <div>
            <p className="text-xs sm:text-sm font-semibold text-white">
              {uploading ? "Uploading document(s)..." : "Drag & drop files here, or click to browse"}
            </p>
            <p className="text-[11px] sm:text-xs text-slate-400 mt-1">
              Supports single or batch upload: PDF, DOCX, TXT, Markdown, CSV, JSON (up to 50MB)
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
              <p className="text-[11px] text-slate-400">{uploadProgress}% - Uploading & Queuing Pipeline</p>
            </div>
          )}
        </div>

        {uploadSuccess && (
          <div className="p-3.5 sm:p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs flex items-center space-x-2">
            <CheckCircle2 className="w-4 h-4 shrink-0" />
            <span>{uploadSuccess}</span>
          </div>
        )}

        {uploadError && (
          <div className="p-3.5 sm:p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs flex items-center space-x-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{uploadError}</span>
          </div>
        )}

        {/* Filter and List */}
        <div className="space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex items-center space-x-2">
              <FileText className="w-4 h-4 text-emerald-400" />
              <h2 className="text-sm sm:text-base font-bold text-white">Ingested Corpus ({filtered.length})</h2>
            </div>
            <div className="relative w-full sm:w-64">
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
                    className="p-3.5 sm:p-4 flex flex-col sm:flex-row sm:items-center justify-between hover:bg-slate-900/50 transition gap-3 sm:gap-4"
                  >
                    <div className="flex items-center space-x-3 min-w-0">
                      <div className="w-9 h-9 sm:w-10 sm:h-10 rounded-xl bg-slate-800 border border-slate-700/60 flex items-center justify-center text-slate-300 shrink-0">
                        <FileText className="w-4 h-4 sm:w-5 sm:h-5 text-cyan-400" />
                      </div>
                      <div className="min-w-0">
                        <Link
                          href={`/documents/${doc.id}`}
                          className="text-xs sm:text-sm font-semibold text-white hover:text-emerald-400 transition truncate block"
                        >
                          {doc.title || doc.filename}
                        </Link>
                        <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5 text-[11px] sm:text-xs text-slate-400 mt-0.5">
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

                    <div className="flex items-center justify-between sm:justify-end space-x-3 shrink-0 pt-2 sm:pt-0 border-t sm:border-t-0 border-border/30">
                      <span
                        className={`text-[9px] sm:text-[10px] px-2.5 py-0.5 rounded-full font-mono uppercase font-semibold inline-flex items-center space-x-1.5 ${
                          doc.status === "COMPLETED"
                            ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                            : doc.status === "PROCESSING" || doc.status === "UPLOADED"
                            ? "bg-amber-500/10 text-amber-400 border border-amber-500/20 animate-pulse"
                            : "bg-rose-500/10 text-rose-400 border border-rose-500/20"
                        }`}
                      >
                        {(doc.status === "PROCESSING" || doc.status === "UPLOADED") && (
                          <RefreshCw className="w-2.5 h-2.5 animate-spin mr-1 inline" />
                        )}
                        <span>{doc.status === "UPLOADED" ? "QUEUED" : doc.status}</span>
                      </span>

                      <div className="flex items-center space-x-1 sm:space-x-2">
                        <Link
                          href={`/documents/${doc.id}`}
                          className="p-1.5 sm:p-2 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition"
                          title="View Document Details & Chunks"
                          aria-label="View Document Details & Chunks"
                        >
                          <ArrowRight className="w-4 h-4" />
                        </Link>

                        <button
                          onClick={() => handleDelete(doc.id, doc.title || doc.filename)}
                          className="p-1.5 sm:p-2 text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 rounded-lg transition"
                          title="Delete Document"
                          aria-label="Delete Document"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
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

