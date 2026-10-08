import "./globals.css";
import type { Metadata } from "next";
import Navbar from "../components/Navbar";

export const metadata: Metadata = {
  title: "GraphIntel — Market Intelligence & Document RAG Platform",
  description:
    "Production-grade Market Intelligence platform powering semantic document ingestion, vector retrieval, and grounded RAG with real citations.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-[#090d16] text-slate-100 antialiased selection:bg-emerald-500/30 selection:text-emerald-300">
        <Navbar />
        {children}
      </body>
    </html>
  );
}
