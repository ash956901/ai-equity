import { X } from "lucide-react";

type ToastTone = "info" | "success" | "warning";

interface ToastItem {
  id: string;
  message: string;
  tone: ToastTone;
}

interface ToastStackProps {
  toasts: ToastItem[];
  onRemove: (id: string) => void;
}

export function ToastStack(props: ToastStackProps) {
  if (!props.toasts.length) return null;

  return (
    <div className="toast-stack" aria-live="polite" aria-atomic="false">
      {props.toasts.map((toast) => (
        <div key={toast.id} className={`toast-item toast-${toast.tone}`}>
          <p>{toast.message}</p>
          <button
            type="button"
            className="toast-close"
            onClick={() => props.onRemove(toast.id)}
            aria-label="Dismiss toast"
          >
            <X size={14} />
          </button>
        </div>
      ))}
    </div>
  );
}
