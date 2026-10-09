"use client";

import { useEffect, useState, useCallback } from "react";
import { CheckCircle2, AlertCircle, Info, AlertTriangle, X } from "lucide-react";
import { registerToastListener, registerDismissListener, ToastType } from "../lib/toast";

interface ToastItem {
  id: string;
  message: string;
  type: ToastType;
  duration: number;
  hiding?: boolean;
}

const ICONS = {
  success: CheckCircle2,
  error: AlertCircle,
  info: Info,
  warning: AlertTriangle,
};

const CLASSES = {
  success: "toast-success",
  error: "toast-error",
  info: "toast-info",
  warning: "toast-warning",
};

export default function ToastProvider() {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const dismiss = useCallback((id: string) => {
    setToasts((prev) =>
      prev.map((t) => (t.id === id ? { ...t, hiding: true } : t))
    );
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 280);
  }, []);

  useEffect(() => {
    registerToastListener((id: string, message: string, type: ToastType, duration: number) => {
      const newToast: ToastItem = { id, message, type, duration };
      setToasts((prev) => [...prev.slice(-4), newToast]);

      if (duration > 0) {
        setTimeout(() => dismiss(id), duration);
      }
    });

    registerDismissListener((id: string) => dismiss(id));
  }, [dismiss]);

  if (toasts.length === 0) return null;

  return (
    <div className="toast-container" role="region" aria-label="Notifications">
      {toasts.map((toast) => {
        const Icon = ICONS[toast.type];
        return (
          <div
            key={toast.id}
            className={`toast ${CLASSES[toast.type]} ${toast.hiding ? "hiding" : ""}`}
            role="alert"
          >
            <Icon className="w-4 h-4 shrink-0 mt-0.5" />
            <p className="text-xs font-medium flex-1 leading-relaxed">{toast.message}</p>
            <button
              onClick={() => dismiss(toast.id)}
              className="p-1 rounded-md hover:bg-white/10 transition shrink-0"
              aria-label="Dismiss notification"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        );
      })}
    </div>
  );
}
