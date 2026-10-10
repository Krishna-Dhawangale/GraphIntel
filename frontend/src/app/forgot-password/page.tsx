"use client";

import { useState } from "react";
import Link from "next/link";
import { ArrowLeft, CheckCircle2, KeyRound, Mail, AlertCircle, Loader2 } from "lucide-react";
import { api } from "../../lib/api";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim()) return;
    setError(null);
    setLoading(true);
    try {
      await api.auth.forgotPassword(email.trim());
      setSubmitted(true);
    } catch (err: any) {
      setError(err?.message || "Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-[calc(100vh-4rem)] flex items-center justify-center p-4">
      <div className="w-full max-w-md glass-panel p-8 rounded-2xl border border-border space-y-6 shadow-2xl">
        <div className="text-center space-y-2">
          <div className="w-12 h-12 rounded-2xl bg-violet-500/10 border border-violet-500/20 text-violet-400 mx-auto flex items-center justify-center">
            <KeyRound className="w-6 h-6" />
          </div>
          <h1 className="text-2xl font-bold tracking-tight">Reset Password</h1>
          <p className="text-xs text-slate-400">
            Enter your work email to receive a secure password reset link.
          </p>
        </div>

        {submitted ? (
          <div className="p-5 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 space-y-3 text-center">
            <CheckCircle2 className="w-8 h-8 mx-auto" />
            <p className="font-semibold text-sm">Check Your Inbox</p>
            <p className="text-slate-300 text-xs leading-relaxed">
              If an account exists for{" "}
              <strong className="text-white">{email}</strong>, a reset link has
              been sent. It expires in <strong className="text-emerald-300">30 minutes</strong>.
            </p>
            <p className="text-xs text-slate-500">
              Don&apos;t see it? Check your spam folder.
            </p>
            <div className="pt-2">
              <Link
                href="/login"
                className="inline-flex items-center space-x-1.5 text-xs text-emerald-400 hover:underline"
              >
                <ArrowLeft className="w-3.5 h-3.5" />
                <span>Return to Sign In</span>
              </Link>
            </div>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            {error && (
              <div className="flex items-start space-x-2 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-xs">
                <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                <span>{error}</span>
              </div>
            )}

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                Work Email
              </label>
              <div className="relative">
                <Mail className="w-4 h-4 text-slate-500 absolute left-3 top-3 pointer-events-none" />
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="analyst@firm.com"
                  className="w-full pl-9 pr-3 py-2.5 bg-slate-900/80 border border-border rounded-lg text-sm placeholder-slate-500 focus:outline-none focus:border-violet-500/60 transition"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-2.5 bg-violet-600 hover:bg-violet-500 text-white font-semibold rounded-lg text-sm transition shadow-lg shadow-violet-500/20 disabled:opacity-50 flex items-center justify-center space-x-2"
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Sending link...</span>
                </>
              ) : (
                <span>Send Reset Instructions</span>
              )}
            </button>

            <div className="text-center pt-1">
              <Link
                href="/login"
                className="inline-flex items-center space-x-1.5 text-xs text-slate-400 hover:text-white transition"
              >
                <ArrowLeft className="w-3.5 h-3.5" />
                <span>Back to Login</span>
              </Link>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
