"use client";

import { useCallback, useEffect, useState } from "react";
import { usePathname } from "next/navigation";

const DISMISSED_KEY = "vaf_copilot_dismissed";

const SUGGESTIONS: Record<string, string> = {
  "/": "You have unreviewed assets. Want help prioritizing?",
  "/pipeline": "Pipeline success rate could improve. Ask Copilot to diagnose?",
  "/alerts": "Multiple open alerts. Ask Copilot to summarize?",
};

export function useProactiveSuggestions() {
  const pathname = usePathname();
  const [suggestion, setSuggestion] = useState<string | null>(null);

  useEffect(() => {
    try {
      const raw = localStorage.getItem(DISMISSED_KEY);
      if (raw) {
        const expiry = Number(raw);
        if (Date.now() < expiry) {
          setSuggestion(null);
          return;
        }
      }
    } catch {
      // localStorage unavailable — continue
    }

    setSuggestion(SUGGESTIONS[pathname] ?? null);
  }, [pathname]);

  const dismiss = useCallback(() => {
    setSuggestion(null);
    try {
      localStorage.setItem(DISMISSED_KEY, String(Date.now() + 86400000));
    } catch {
      // localStorage unavailable
    }
  }, []);

  return { suggestion, dismiss };
}
