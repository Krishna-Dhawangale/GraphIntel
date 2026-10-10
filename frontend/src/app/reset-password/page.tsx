"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import {
  AlertCircle,
  ArrowLeft,
  CheckCircle2,
  Eye,
  EyeOff,
  KeyRound,
  Loader2,
  Lock,
  ShieldAlert,
} from "lucide-react";
import { api } from "../../lib/api";

function ResetPasswordForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get("token") ?? "";

  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [showPw, setShowPw] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) {
      setError("No reset token found. Please request a new password reset link.");
    }
  }, [token]);

  const passwordStrength = (() => {
    if (password.length === 0) return null;
    if (password.length < 8) return { label: "Too short", color: "bg-red-500", width: "25%" };
    if (password.length < 12 && !/[!@#$%^&*]/.test(password))
      return { label: "Weak", color: "bg-orange-500", width: "50%" };
    if (password.length >= 12 && /[!@#$%^&*]/.test(password) && /[0-9]/.test(password))
      return { label: "Strong", color: "bg-emerald-500", width: "100%" };
    return { label: "Fair", color: "bg-yellow-500", width: "75%" };
  })();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }
    if (password !== confirm) {
      setError("Passwords do not match.");
      return;
    }

    setLoading(true);
    try {
      await api.auth.resetPassword(token, password);
      setSuccess(true);
      setTimeout(() => router.push("/login"), 3000);
    } catch (err: any) {
      setError(err?.message || "Reset failed. The link may have expired — please request a new one.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-[calc(100vh-4rem)] flex items-center justify-center p-4">
      <div className="w-full max-w-md glass-panel p-8 rounded-2xl border border-border space-y-6 shadow-2xl">
        {/* Header */}
        <div className="text-center space-y-2">
          <div className="w-12 h-12 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 mx-auto flex items-center justify-center">
            <KeyRound className="w-6 h-6" />
          </div>
          <h1 className="text-2xl font-bold tracking-tight">Set New Password</h1>
          <p className="text-xs text-slate-400">
            Choose a strong password for your GraphIntel account.
          </p>
        </div>

        {/* No token error */}
        {!token && (
          <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 space-y-2 text-center">
            <ShieldAlert className="w-6 h-6 mx-auto" />
            <p className="text-sm font-semibold">Invalid Reset Link</p>
            <p className="text-xs text-slate-400">
              This link is missing a token. Please request a fresh password reset.
            </p>
            <Link
              href="/forgot-password"
              className="inline-flex items-center space-x-1 text-xs text-red-300 hover:underline mt-1"
            >
              <span>Request new link</span>
            </Link>
          </div>
        )}

        {/* Success state */}
        {success && (
          <div className="p-5 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 space-y-3 text-center">
            <CheckCircle2 className="w-8 h-8 mx-auto" />
            <p className="font-semibold">Password Updated!</p>
            <p className="text-xs text-slate-300 leading-relaxed">
              Your password has been reset successfully. Redirecting you to login…
            </p>
          </div>
        )}

        {/* Form */}
        {token && !success && (
          <form onSubmit={handleSubmit} className="space-y-4">
            {error && (
              <div className="flex items-start space-x-2 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-xs">
                <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                <span>{error}</span>
              </div>
            )}

            {/* New password */}
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                New Password
              </label>
              <div className="relative">
                <Lock className="w-4 h-4 text-slate-500 absolute left-3 top-3 pointer-events-none" />
                <input
                  type={showPw ? "text" : "password"}
                  required
                  minLength={8}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Min. 8 characters"
                  className="w-full pl-9 pr-10 py-2.5 bg-slate-900/80 border border-border rounded-lg text-sm placeholder-slate-500 focus:outline-none focus:border-emerald-500/60 transition"
                />
                <button
                  type="button"
                  onClick={() => setShowPw(!showPw)}
                  className="absolute right-3 top-2.5 text-slate-500 hover:text-white transition"
                >
                  {showPw ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
              {/* Strength bar */}
              {passwordStrength && (
                <div className="mt-2 space-y-1">
                  <div className="h-1 w-full bg-slate-800 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all duration-300 ${passwordStrength.color}`}
                      style={{ width: passwordStrength.width }}
                    />
                  </div>
                  <p className="text-[11px] text-slate-500">
                    Strength: <span className="text-slate-300">{passwordStrength.label}</span>
                  </p>
                </div>
              )}
            </div>

            {/* Confirm password */}
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                Confirm Password
              </label>
              <div className="relative">
                <Lock className="w-4 h-4 text-slate-500 absolute left-3 top-3 pointer-events-none" />
                <input
                  type={showConfirm ? "text" : "password"}
                  required
                  value={confirm}
                  onChange={(e) => setConfirm(e.target.value)}
                  placeholder="Repeat your password"
                  className={`w-full pl-9 pr-10 py-2.5 bg-slate-900/80 border rounded-lg text-sm placeholder-slate-500 focus:outline-none transition ${
                    confirm && confirm !== password
                      ? "border-red-500/50 focus:border-red-500"
                      : "border-border focus:border-emerald-500/60"
                  }`}
                />
                <button
                  type="button"
                  onClick={() => setShowConfirm(!showConfirm)}
                  className="absolute right-3 top-2.5 text-slate-500 hover:text-white transition"
                >
                  {showConfirm ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
              {confirm && confirm !== password && (
                <p className="text-[11px] text-red-400 mt-1">Passwords do not match.</p>
              )}
            </div>

            <button
              type="submit"
              disabled={loading || !password || !confirm}
              className="w-full py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white font-semibold rounded-lg text-sm transition shadow-lg shadow-emerald-500/20 disabled:opacity-50 flex items-center justify-center space-x-2"
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Updating password…</span>
                </>
              ) : (
                <span>Update Password</span>
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

export default function ResetPasswordPage() {
  return (
    <Suspense fallback={<div className="min-h-[calc(100vh-4rem)]" />}>
      <ResetPasswordForm />
    </Suspense>
  );
}
