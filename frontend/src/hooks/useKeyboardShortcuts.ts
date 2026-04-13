"use client";

import { useEffect } from "react";

function isEditableTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  const tag = target.tagName.toLowerCase();
  if (tag === "input" || tag === "textarea") return true;
  if (target.isContentEditable) return true;
  return false;
}

export function useKeyboardShortcuts() {
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      // Ctrl+K → open command palette
      if ((e.ctrlKey || e.metaKey) && e.key === "k") {
        e.preventDefault();
        window.dispatchEvent(new CustomEvent("open-command-palette"));
        return;
      }

      // Escape → close modals
      if (e.key === "Escape") {
        window.dispatchEvent(new CustomEvent("close-modals"));
        return;
      }

      // Only fire / and ? when not in editable fields
      if (isEditableTarget(e.target)) return;

      if (e.key === "/") {
        e.preventDefault();
        window.dispatchEvent(new CustomEvent("focus-search"));
        return;
      }

      if (e.key === "?") {
        e.preventDefault();
        window.dispatchEvent(new CustomEvent("open-shortcuts-modal"));
        return;
      }
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);
}
