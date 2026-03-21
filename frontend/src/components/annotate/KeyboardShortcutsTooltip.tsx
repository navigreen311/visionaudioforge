"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { AnnotationTool } from "../annotation/ToolPalette";

/* ------------------------------------------------------------------ */
/*  Shortcut definitions                                               */
/* ------------------------------------------------------------------ */

interface ShortcutEntry {
  keys: string;
  description: string;
}

const SHORTCUTS: ShortcutEntry[] = [
  { keys: "B", description: "Bounding box tool" },
  { keys: "P", description: "Polygon tool" },
  { keys: "K", description: "Keypoint tool" },
  { keys: "L", description: "Label tool" },
  { keys: "S", description: "Select / move" },
  { keys: "Del / Backspace", description: "Delete selected" },
  { keys: "Ctrl+Z", description: "Undo" },
  { keys: "Ctrl+Shift+Z", description: "Redo" },
  { keys: "Ctrl++", description: "Zoom in" },
  { keys: "Ctrl+-", description: "Zoom out" },
  { keys: "Ctrl+0", description: "Reset zoom" },
  { keys: "Ctrl+Scroll", description: "Zoom with wheel" },
  { keys: "?", description: "Toggle shortcuts" },
];

/* ------------------------------------------------------------------ */
/*  Keyboard listener hook                                             */
/* ------------------------------------------------------------------ */

interface KeyboardShortcutHandlers {
  onToolChange?: (tool: AnnotationTool) => void;
  onDelete?: () => void;
}

export function useAnnotationKeyboardShortcuts({
  onToolChange,
  onDelete,
}: KeyboardShortcutHandlers) {
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      // Skip when user is typing in a form field
      const tag = (e.target as HTMLElement)?.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;

      // Skip if modifier keys are held (those are handled by other hooks)
      if (e.ctrlKey || e.metaKey || e.altKey) return;

      switch (e.key.toLowerCase()) {
        case "b":
          e.preventDefault();
          onToolChange?.("bbox");
          break;
        case "p":
          e.preventDefault();
          onToolChange?.("polygon");
          break;
        case "k":
          e.preventDefault();
          onToolChange?.("keypoint");
          break;
        case "l":
          e.preventDefault();
          onToolChange?.("label");
          break;
        case "s":
          e.preventDefault();
          onToolChange?.("select");
          break;
        case "delete":
        case "backspace":
          e.preventDefault();
          onDelete?.();
          break;
        default:
          break;
      }
    };

    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onToolChange, onDelete]);
}

/* ------------------------------------------------------------------ */
/*  KeyboardShortcutsTooltip – "?" icon with popover                   */
/* ------------------------------------------------------------------ */

interface KeyboardShortcutsTooltipProps {
  /** Optional: wire tool switching directly */
  onToolChange?: (tool: AnnotationTool) => void;
  /** Optional: wire delete */
  onDelete?: () => void;
}

export default function KeyboardShortcutsTooltip({
  onToolChange,
  onDelete,
}: KeyboardShortcutsTooltipProps) {
  const [open, setOpen] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);

  // Activate keyboard listeners
  useAnnotationKeyboardShortcuts({ onToolChange, onDelete });

  // Toggle with "?" key
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement)?.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;
      if (e.ctrlKey || e.metaKey || e.altKey) return;

      if (e.key === "?") {
        e.preventDefault();
        setOpen((v) => !v);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  // Close on click outside
  const handleClickOutside = useCallback((e: MouseEvent) => {
    if (
      panelRef.current &&
      !panelRef.current.contains(e.target as Node) &&
      buttonRef.current &&
      !buttonRef.current.contains(e.target as Node)
    ) {
      setOpen(false);
    }
  }, []);

  useEffect(() => {
    if (open) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [open, handleClickOutside]);

  // Close on Escape
  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [open]);

  return (
    <div className="relative">
      <button
        ref={buttonRef}
        type="button"
        onClick={() => setOpen((v) => !v)}
        onMouseEnter={() => setOpen(true)}
        title="Keyboard shortcuts (?)"
        className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-gray-200 bg-white text-sm font-bold text-gray-500 transition-colors hover:bg-gray-100 hover:text-gray-700"
        aria-label="Keyboard shortcuts"
      >
        ?
      </button>

      {open && (
        <div
          ref={panelRef}
          role="tooltip"
          className="absolute left-0 top-10 z-50 w-64 rounded-lg border border-gray-200 bg-white p-3 shadow-lg"
        >
          <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-gray-500">
            Keyboard Shortcuts
          </h3>
          <ul className="space-y-1">
            {SHORTCUTS.map((s) => (
              <li key={s.keys} className="flex items-center justify-between text-sm">
                <span className="text-gray-600">{s.description}</span>
                <kbd className="ml-2 shrink-0 rounded border border-gray-200 bg-gray-50 px-1.5 py-0.5 font-mono text-xs text-gray-500">
                  {s.keys}
                </kbd>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
