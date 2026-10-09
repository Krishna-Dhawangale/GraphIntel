import "./globals.css";
import type { Metadata, Viewport } from "next";
import Navbar from "../components/Navbar";
import ToastProvider from "../components/ToastProvider";

export const metadata: Metadata = {
  title: "GraphIntel — Market Intelligence & Document RAG Platform",
  description:
    "Production-grade Market Intelligence platform powering semantic document ingestion, vector retrieval, and grounded RAG with real citations.",
  keywords: "GraphRAG, knowledge graph, market intelligence, Neo4j, Qdrant, LangGraph",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 5,
  themeColor: "#090d16",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
      </head>
      <body className="min-h-screen bg-[#090d16] text-slate-100 antialiased selection:bg-emerald-500/30 selection:text-emerald-300">
        <Navbar />
        {children}
        <ToastProvider />
      </body>
    </html>
  );
}
