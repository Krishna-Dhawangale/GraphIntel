// Simple toast notification system
export type ToastType = "success" | "error" | "info" | "warning";

interface ToastOptions {
  duration?: number;
}

type ToastListener = (id: string, message: string, type: ToastType, duration: number) => void;
type DismissListener = (id: string) => void;

let toastListener: ToastListener | null = null;
let dismissListener: DismissListener | null = null;

export function registerToastListener(listener: ToastListener) {
  toastListener = listener;
}

export function registerDismissListener(listener: DismissListener) {
  dismissListener = listener;
}

function show(message: string, type: ToastType, options: ToastOptions = {}) {
  const id = Math.random().toString(36).slice(2);
  const duration = options.duration ?? 4000;
  if (toastListener) {
    toastListener(id, message, type, duration);
  }
  return id;
}

export const toast = {
  success: (message: string, options?: ToastOptions) => show(message, "success", options),
  error: (message: string, options?: ToastOptions) => show(message, "error", options),
  info: (message: string, options?: ToastOptions) => show(message, "info", options),
  warning: (message: string, options?: ToastOptions) => show(message, "warning", options),
  dismiss: (id: string) => {
    if (dismissListener) dismissListener(id);
  },
};
