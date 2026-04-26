"use client";

import { Moon, Sun } from "lucide-react";
import { useTheme } from "./ThemeProvider";

export function ThemeToggle() {
  const { theme, toggle } = useTheme();
  const isDark = theme === "dark";

  return (
    <button
      onClick={toggle}
      aria-label={isDark ? "Switch to light mode" : "Switch to dark mode"}
      title={isDark ? "Switch to light mode" : "Switch to dark mode"}
      className="
        relative flex h-9 w-9 items-center justify-center rounded-full
        border border-amber-500/20 bg-amber-500/10
        text-amber-700 transition-all duration-300
        hover:bg-amber-500/20 hover:border-amber-500/40 hover:scale-105
        dark:border-amber-400/20 dark:bg-amber-400/10 dark:text-amber-400
        dark:hover:bg-amber-400/20 dark:hover:border-amber-400/40
      "
    >
      <span
        className="absolute inset-0 flex items-center justify-center transition-all duration-300"
        style={{
          opacity: isDark ? 1 : 0,
          transform: isDark ? "rotate(0deg) scale(1)" : "rotate(-90deg) scale(0.5)",
        }}
      >
        <Sun className="h-4 w-4" />
      </span>
      <span
        className="absolute inset-0 flex items-center justify-center transition-all duration-300"
        style={{
          opacity: isDark ? 0 : 1,
          transform: isDark ? "rotate(90deg) scale(0.5)" : "rotate(0deg) scale(1)",
        }}
      >
        <Moon className="h-4 w-4" />
      </span>
    </button>
  );
}
