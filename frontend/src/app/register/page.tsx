"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowRight, Eye, EyeOff, Lock, Mail, Shield, User } from "lucide-react";
import { api } from "../../lib/api";
import { setTokens } from "../../lib/auth";
import { toast } from "../../lib/toast";
import GoogleSignInButton from "../../components/GoogleSignInButton";

export default function RegisterPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [role, setRole] = useState("ANALYST");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }
    setLoading(true);
    setError(null);

    try {
      // 1. Register with selected role
      await api.auth.register({ email, password, full_name: fullName, role });
      // 2. Automatically log in
      const res = await api.auth.login({ email, password });
      setTokens(res.access_token, res.refresh_token);
      toast.success("Account created! Redirecting to your workspace...", { duration: 2500 });
      setTimeout(() => router.push("/dashboard"), 400);
    } catch (err: any) {
      const msg = err.message || "Failed to create account.";
      setError(msg);
      toast.error(msg, { duration: 5000 });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-[calc(100vh-4rem)] flex items-center justify-center px-4 py-12">
      <div className="w-full max-w-md space-y-6">
        {/* Header */}
        <div className="text-center space-y-3">
          <div className="w-14 h-14 rounded-2xl bg-gradient-to-tr from-emerald-500/20 to-cyan-500/20 border border-emerald-500/30 text-emerald-400 mx-auto flex items-center justify-center shadow-lg shadow-emerald-500/10">
            <Shield className="w-7 h-7" />
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-white">Create an Account</h1>
            <p className="text-sm text-slate-400 mt-1">Deploy your intelligence workspace with tenant data isolation</p>
          </div>
        </div>

        {/* Form Card */}
        <div className="glass-panel p-8 rounded-2xl border border-border shadow-2xl space-y-5">
          {error && (
            <div className="p-3.5 text-sm text-rose-300 bg-rose-950/40 border border-rose-800/60 rounded-xl flex items-start space-x-2 animate-in fade-in">
              <span className="shrink-0 mt-0.5">⚠</span>
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                Full Name
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-500">
                  <User className="w-4 h-4" />
                </div>
                <input
                  type="text"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="Jane Doe"
                  autoComplete="name"
                  className="w-full pl-9 pr-3 py-2.5 bg-slate-900/80 border border-border rounded-xl text-sm text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500/70 transition hover:border-slate-600"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                Email Address
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-500">
                  <Mail className="w-4 h-4" />
                </div>
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="analyst@firm.com"
                  autoComplete="email"
                  className="w-full pl-9 pr-3 py-2.5 bg-slate-900/80 border border-border rounded-xl text-sm text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500/70 transition hover:border-slate-600"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                Workspace Role
              </label>
              <select
                value={role}
                onChange={(e) => setRole(e.target.value)}
                className="w-full px-3 py-2.5 bg-slate-900/80 border border-border rounded-xl text-sm text-white focus:outline-none focus:border-emerald-500/70 transition hover:border-slate-600 appearance-none cursor-pointer"
              >
                <option value="ANALYST">ANALYST — Graph, Research & Reports</option>
                <option value="USER">USER — Ingestion & Search</option>
                <option value="ADMIN">ADMIN — Full System Administration</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                Password
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-500">
                  <Lock className="w-4 h-4" />
                </div>
                <input
                  type={showPassword ? "text" : "password"}
                  required
                  minLength={8}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Min. 8 characters"
                  autoComplete="new-password"
                  className="w-full pl-9 pr-10 py-2.5 bg-slate-900/80 border border-border rounded-xl text-sm text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500/70 transition hover:border-slate-600"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute inset-y-0 right-0 pr-3 flex items-center text-slate-500 hover:text-slate-300 transition"
                  aria-label={showPassword ? "Hide password" : "Show password"}
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
              {password && password.length < 8 && (
                <p className="text-[11px] text-amber-400 mt-1 animate-in fade-in">
                  Password must be at least 8 characters.
                </p>
              )}
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full flex items-center justify-center space-x-2 py-2.5 px-4 bg-emerald-500 hover:bg-emerald-400 active:scale-[0.98] text-slate-950 font-semibold rounded-xl shadow-lg shadow-emerald-500/20 transition disabled:opacity-50"
            >
              {loading ? (
                <>
                  <div className="w-4 h-4 rounded-full border-2 border-slate-950/30 border-t-slate-950 animate-spin" />
                  <span>Provisioning Account...</span>
                </>
              ) : (
                <>
                  <span>Create Workspace</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </form>

          {/* Divider */}
          <div className="relative my-4">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-border"></div>
            </div>
            <div className="relative flex justify-center text-[11px] uppercase">
              <span className="bg-slate-900/90 px-3 text-slate-500 font-semibold tracking-wider">
                Or sign up with
              </span>
            </div>
          </div>

          {/* Google Sign In */}
          <GoogleSignInButton mode="signup" />

          <div className="text-center text-xs text-slate-400 pt-1">
            Already have an account?{" "}
            <Link href="/login" className="text-emerald-400 hover:text-emerald-300 hover:underline font-medium transition">
              Sign In here
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
