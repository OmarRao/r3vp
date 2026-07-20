"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";

type Theme = "light" | "dark";

type ThemeContextValue = {
  theme: Theme;
  toggle: () => void;
  setTheme: (t: Theme) => void;
};

const ThemeContext = createContext<ThemeContextValue | null>(null);

/**
 * Reads the theme the no-flash inline script already applied to <html>, keeps
 * React state in sync, and persists changes to localStorage.
 */
export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setThemeState] = useState<Theme>("light");

  useEffect(() => {
    const current = document.documentElement.classList.contains("dark") ? "dark" : "light";
    setThemeState(current);
  }, []);

  const apply = useCallback((t: Theme) => {
    setThemeState(t);
    const root = document.documentElement;
    root.classList.toggle("dark", t === "dark");
    try {
      localStorage.setItem("r3vp-theme", t);
    } catch {
      /* localStorage unavailable (private mode) - non-fatal */
    }
  }, []);

  const toggle = useCallback(
    () => apply(document.documentElement.classList.contains("dark") ? "light" : "dark"),
    [apply],
  );

  return (
    <ThemeContext.Provider value={{ theme, toggle, setTheme: apply }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error("useTheme must be used within ThemeProvider");
  return ctx;
}

/** Inline script that sets the theme class before first paint (no flash). */
export const THEME_INIT_SCRIPT = `
(function(){
  try {
    var stored = localStorage.getItem('r3vp-theme');
    var t = stored || (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
    if (t === 'dark') document.documentElement.classList.add('dark');
  } catch (e) {}
})();
`;
