import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import type { RunMode } from "./api/types";

const MODE_KEY = "hijacking-mode";

interface ModeContextValue {
  mode: RunMode;
  setMode: (m: RunMode) => void;
  toggleMode: () => void;
}

const ModeContext = createContext<ModeContextValue | null>(null);

export function ModeProvider({ children }: { children: ReactNode }) {
  const [mode, setModeState] = useState<RunMode>("demo");

  useEffect(() => {
    const stored = (typeof localStorage !== "undefined" && localStorage.getItem(MODE_KEY)) as RunMode | null;
    if (stored === "demo" || stored === "live") setModeState(stored);
  }, []);

  const setMode = useCallback((m: RunMode) => {
    setModeState(m);
    if (typeof localStorage !== "undefined") localStorage.setItem(MODE_KEY, m);
  }, []);

  const toggleMode = useCallback(() => setMode(mode === "demo" ? "live" : "demo"), [mode, setMode]);

  return <ModeContext.Provider value={{ mode, setMode, toggleMode }}>{children}</ModeContext.Provider>;
}

export function useMode() {
  const ctx = useContext(ModeContext);
  if (!ctx) throw new Error("useMode must be used within ModeProvider");
  return ctx;
}
