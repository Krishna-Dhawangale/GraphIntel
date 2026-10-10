"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "../lib/api";
import { setTokens } from "../lib/auth";
import { toast } from "../lib/toast";

declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize: (config: {
            client_id: string;
            callback: (response: { credential: string }) => void;
            auto_select?: boolean;
            cancel_on_tap_outside?: boolean;
          }) => void;
          renderButton: (
            parent: HTMLElement,
            options: {
              type?: "standard" | "icon";
              theme?: "outline" | "filled_blue" | "filled_black";
              size?: "large" | "medium" | "small";
              text?: "signin_with" | "signup_with" | "continue_with" | "signin";
              shape?: "rectangular" | "pill" | "circle" | "square";
              logo_alignment?: "left" | "center";
              width?: string | number;
            }
          ) => void;
          prompt: (notification?: any) => void;
        };
      };
    };
  }
}

interface GoogleSignInButtonProps {
  mode?: "signin" | "signup";
  onSuccess?: () => void;
  onError?: (error: string) => void;
}

// Read the env var once at module load time (inlined by Next.js at build/compile time)
const ENV_CLIENT_ID = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID ?? "";

export default function GoogleSignInButton({
  mode = "signin",
  onSuccess,
  onError,
}: GoogleSignInButtonProps) {
  const router = useRouter();
  const buttonRef = useRef<HTMLDivElement>(null);
  const [loading, setLoading] = useState(false);
  const [gisReady, setGisReady] = useState(false);
  const [showManualModal, setShowManualModal] = useState(false);
  const [manualToken, setManualToken] = useState("");
  const clientIdRef = useRef<string>(ENV_CLIENT_ID);

  // If no env var, try fetching from backend once
  useEffect(() => {
    if (clientIdRef.current) return; // env var already present — skip API call

    api.auth
      .googleConfig()
      .then((res) => {
        if (res.enabled && res.client_id) {
          clientIdRef.current = res.client_id;
          initGis(res.client_id);
        }
      })
      .catch(() => {
        // Backend unreachable or not configured — leave clientId empty
      });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Load Google Identity Services script and render button
  useEffect(() => {
    if (!clientIdRef.current) return;
    initGis(clientIdRef.current);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function initGis(clientId: string) {
    const handleCredentialResponse = async (response: { credential: string }) => {
      if (!response.credential) {
        const msg = "No credential received from Google.";
        onError?.(msg);
        toast.error(msg);
        return;
      }
      setLoading(true);
      try {
        const res = await api.auth.googleLogin({ credential: response.credential });
        setTokens(res.access_token, res.refresh_token);
        toast.success(
          mode === "signup"
            ? "Account created and logged in with Google!"
            : "Welcome back! Logged in with Google.",
          { duration: 2500 }
        );
        onSuccess ? onSuccess() : router.push("/dashboard");
      } catch (err: any) {
        const msg = err.message || "Google authentication failed. Please try again.";
        onError?.(msg);
        toast.error(msg, { duration: 4000 });
      } finally {
        setLoading(false);
      }
    };

    const render = () => {
      if (!window.google?.accounts?.id || !buttonRef.current) return;
      try {
        window.google.accounts.id.initialize({
          client_id: clientId,
          callback: handleCredentialResponse,
        });
        buttonRef.current.innerHTML = "";
        window.google.accounts.id.renderButton(buttonRef.current, {
          theme: "outline",
          size: "large",
          width: buttonRef.current.offsetWidth || 340,
          text: mode === "signup" ? "signup_with" : "continue_with",
          shape: "rectangular",
        });
        setGisReady(true);
      } catch (e) {
        console.error("Failed to render Google button:", e);
      }
    };

    const existing = document.getElementById("google-gis-script") as HTMLScriptElement | null;
    if (!existing) {
      const script = document.createElement("script");
      script.id = "google-gis-script";
      script.src = "https://accounts.google.com/gsi/client";
      script.async = true;
      script.defer = true;
      script.onload = render;
      document.head.appendChild(script);
    } else if (window.google?.accounts?.id) {
      render();
    } else {
      existing.addEventListener("load", render, { once: true });
    }
  }

  const handleManualTokenSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!manualToken.trim()) return;
    setLoading(true);
    try {
      const res = await api.auth.googleLogin({ credential: manualToken.trim() });
      setTokens(res.access_token, res.refresh_token);
      toast.success("Authenticated with Google credential!");
      setShowManualModal(false);
      onSuccess ? onSuccess() : router.push("/dashboard");
    } catch (err: any) {
      toast.error(err.message || "Failed to authenticate with provided Google token.");
    } finally {
      setLoading(false);
    }
  };

  const noClientId = !clientIdRef.current;

  return (
    <div className="w-full">
      {/* Real Google GIS button — shown when GIS script loaded successfully */}
      <div
        ref={buttonRef}
        className={`w-full transition-opacity duration-300 ${gisReady && !loading ? "opacity-100 min-h-[44px]" : "opacity-0 h-0 overflow-hidden"}`}
      />

      {/* Fallback styled button — shown while GIS is loading or not configured */}
      {(!gisReady || loading) && (
        <button
          type="button"
          onClick={() => {
            if (noClientId) {
              setShowManualModal(true);
            } else if (window.google?.accounts?.id) {
              window.google.accounts.id.prompt();
            }
          }}
          disabled={loading}
          className="w-full flex items-center justify-center space-x-3 py-2.5 px-4 bg-slate-900/90 hover:bg-slate-800/90 active:scale-[0.99] border border-border hover:border-slate-600 rounded-xl text-sm font-medium text-white transition shadow-sm group disabled:opacity-60"
        >
          {loading ? (
            <>
              <div className="w-4 h-4 rounded-full border-2 border-emerald-400/30 border-t-emerald-400 animate-spin" />
              <span className="text-slate-300">Authenticating with Google...</span>
            </>
          ) : (
            <>
              <svg className="w-4 h-4 shrink-0" viewBox="0 0 24 24">
                <path fill="#4285F4" d="M23.745 12.27c0-.7-.06-1.4-.19-2.07H12v4.51h6.6c-.29 1.52-1.14 2.82-2.4 3.68v3.05h3.88c2.27-2.09 3.665-5.17 3.665-9.17Z" />
                <path fill="#34A853" d="M12 24c3.24 0 5.95-1.08 7.93-2.91l-3.88-3.05c-1.08.72-2.45 1.16-4.05 1.16-3.12 0-5.77-2.1-6.72-4.93H1.25v3.15C3.26 21.36 7.33 24 12 24Z" />
                <path fill="#FBBC05" d="M5.28 14.27c-.25-.72-.38-1.49-.38-2.27s.13-1.55.38-2.27V6.58H1.25C.45 8.21 0 10.05 0 12s.45 3.79 1.25 5.42l4.03-3.15Z" />
                <path fill="#EA4335" d="M12 4.75c1.77 0 3.35.61 4.6 1.8l3.42-3.42C17.94 1.19 15.23 0 12 0 7.33 0 3.26 2.64 1.25 6.58l4.03 3.15c.95-2.83 3.6-4.98 6.72-4.98Z" />
              </svg>
              <span>{mode === "signup" ? "Sign up with Google" : "Continue with Google"}</span>
            </>
          )}
        </button>
      )}

      {/* Manual token modal — only shown when GOOGLE_CLIENT_ID is completely absent */}
      {showManualModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-in fade-in">
          <div className="bg-slate-900 border border-slate-700 rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <div className="flex items-center space-x-2">
                <div className="w-8 h-8 rounded-lg bg-emerald-500/20 text-emerald-400 flex items-center justify-center font-bold">G</div>
                <h3 className="font-semibold text-white">Google OAuth Setup</h3>
              </div>
              <button type="button" onClick={() => setShowManualModal(false)} className="text-slate-400 hover:text-white px-2 py-1">✕</button>
            </div>

            <p className="text-xs text-slate-300 leading-relaxed">
              Google OAuth backend endpoint <code className="text-emerald-400 bg-slate-950 px-1 py-0.5 rounded">/api/v1/auth/google</code> is active and ready.
            </p>

            <div className="p-3 bg-slate-950/80 border border-slate-800 rounded-xl space-y-2 text-xs text-slate-400">
              <p className="font-semibold text-slate-200">To enable automatic one-click sign in:</p>
              <ol className="list-decimal list-inside space-y-1 pl-1">
                <li>Create OAuth 2.0 Client ID in Google Cloud Console.</li>
                <li>Add <code className="text-emerald-400">NEXT_PUBLIC_GOOGLE_CLIENT_ID</code> to your <code className="text-emerald-400">.env.local</code>.</li>
                <li>Restart the dev server.</li>
              </ol>
            </div>

            <form onSubmit={handleManualTokenSubmit} className="space-y-3 pt-1">
              <label className="block text-xs font-semibold text-slate-300">Or test with Google ID Token / Credential:</label>
              <textarea
                value={manualToken}
                onChange={(e) => setManualToken(e.target.value)}
                placeholder="Paste Google ID Token (eyJhbGciOiJSUzI1NiIs...)"
                rows={3}
                className="w-full p-2.5 bg-slate-950 border border-border rounded-xl text-xs text-white placeholder-slate-600 focus:outline-none focus:border-emerald-500"
              />
              <div className="flex justify-end space-x-2">
                <button type="button" onClick={() => setShowManualModal(false)} className="px-3 py-1.5 rounded-lg text-xs text-slate-400 hover:bg-slate-800">Close</button>
                <button type="submit" disabled={loading || !manualToken.trim()} className="px-4 py-1.5 rounded-lg text-xs font-medium bg-emerald-500 hover:bg-emerald-400 text-slate-950 disabled:opacity-50 transition">
                  {loading ? "Verifying..." : "Verify & Sign In"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
