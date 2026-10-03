import { createContext, useCallback, useContext, useMemo, useState } from "react";
import { CheckCircle2, Info, TriangleAlert, X } from "lucide-react";

const ToastContext = createContext(null);

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);

  const push = useCallback((message, kind = "info") => {
    const id = crypto.randomUUID();
    setToasts((current) => [...current, { id, message, kind }]);
    setTimeout(() => {
      setToasts((current) => current.filter((t) => t.id !== id));
    }, 4200);
  }, []);

  const value = useMemo(() => ({ push }), [push]);
  const dismiss = (id) => setToasts((current) => current.filter((toast) => toast.id !== id));

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="toasts">
        {toasts.map((toast) => (
          <div key={toast.id} className={`toast toast-${toast.kind}`}>
            <span className="toast-icon">
              {toast.kind === "ok" ? <CheckCircle2 size={18} /> : toast.kind === "error" ? <TriangleAlert size={18} /> : <Info size={18} />}
            </span>
            <div><b>{toast.kind === "ok" ? "Success" : toast.kind === "error" ? "Action failed" : "Notice"}</b><p>{toast.message}</p></div>
            <button type="button" onClick={() => dismiss(toast.id)} aria-label="Dismiss notification"><X size={14} /></button>
            <i />
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  return useContext(ToastContext);
}
