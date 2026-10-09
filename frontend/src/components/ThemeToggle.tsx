"use client";

import { useEffect, useState } from "react";
import { Moon, Sun } from "lucide-react";
import { useTheme } from "../context/ThemeContext";

interface ThemeToggleProps {
  className?: string;
  showLabel?: boolean;
}

export default function ThemeToggle({ className = "", showLabel = false }: ThemeToggleProps) {
  const { theme, resolvedTheme, toggleTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(false);
    setMounted(true);
  }, []);

  if (!mounted) {
    return (
      <div
        className={`w-9 h-9 rounded-xl border border-border bg-slate-900/60 flex items-center justify-center opacity-70 ${className}`}
        aria-hidden="true"
      >
        <Moon className="w-4 h-4 text-slate-400" />
      </div>
    );
  }

  const isDark = resolvedTheme === "dark";

  return (
    <button
      type="button"
      onClick={toggleTheme}
      className={`p-2 rounded-xl border border-border bg-slate-900/60 hover:bg-slate-800/80 active:scale-95 text-slate-400 hover:text-white transition-all shadow-sm flex items-center space-x-2 ${className}`}
      title={isDark ? "Switch to Light Mode" : "Switch to Dark Mode"}
      aria-label={isDark ? "Switch to Light Mode" : "Switch to Dark Mode"}
    >
      <div className="relative w-4 h-4">
        <Sun
          className={`w-4 h-4 text-amber-400 transition-all duration-300 absolute inset-0 ${
            isDark
              ? "opacity-0 rotate-90 scale-0 pointer-events-none"
              : "opacity-100 rotate-0 scale-100"
          }`}
        />
        <Moon
          className={`w-4 h-4 text-cyan-300 transition-all duration-300 absolute inset-0 ${
            isDark
              ? "opacity-100 rotate-0 scale-100"
              : "opacity-0 -rotate-90 scale-0 pointer-events-none"
          }`}
        />
      </div>
      {showLabel && (
        <span className="text-xs font-medium text-slate-300">
          {isDark ? "Dark Mode" : "Light Mode"}
        </span>
      )}
    </button>
  );
}
