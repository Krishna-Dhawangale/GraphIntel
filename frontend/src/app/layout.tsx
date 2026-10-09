import "./globals.css";
import type { Metadata, Viewport } from "next";
import Navbar from "../components/Navbar";
import ToastProvider from "../components/ToastProvider";
import { ThemeProvider } from "../context/ThemeContext";

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
    <html lang="en" suppressHydrationWarning>
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <script
          dangerouslySetInnerHTML={{
            __html: `(function(){try{var t=localStorage.getItem('graphintel_theme');var m=window.matchMedia('(prefers-color-scheme: dark)').matches;var isDark=t==='dark'||(!t&&m)||(t==='system'&&m);if(isDark){document.documentElement.classList.add('dark');document.documentElement.classList.remove('light');}else{document.documentElement.classList.remove('dark');document.documentElement.classList.add('light');}}catch(e){}})();`,
          }}
        />
      </head>
      <body className="min-h-screen antialiased selection:bg-emerald-500/30 selection:text-emerald-300">
        <ThemeProvider>
          <Navbar />
          {children}
          <ToastProvider />
        </ThemeProvider>
      </body>
    </html>
  );
}
