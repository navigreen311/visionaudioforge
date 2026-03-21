"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { AnnotationItem } from "../annotation/AnnotationList";

/* ------------------------------------------------------------------ */
/*  useAnnotationHistory – tracks undo/redo state for annotations     */
/* ------------------------------------------------------------------ */

const MAX_HISTORY = 50;

interface AnnotationHistoryState {
  past: AnnotationItem[][];
  present: AnnotationItem[];
  future: AnnotationItem[][];
}

export interface AnnotationHistoryAPI {
  /** Push a new snapshot after draw / delete / move */
  push: (annotations: AnnotationItem[]) => void;
  /** Step backward */
  undo: () => void;
  /** Step forward */
  redo: () => void;
  /** Whether undo is available */
  canUndo: boolean;
  /** Whether redo is available */
  canRedo: boolean;
}

export function useAnnotationHistory(
  annotations: AnnotationItem[],
  onAnnotationsChange: (annotations: AnnotationItem[]) => void,
): AnnotationHistoryAPI {
  const stateRef = useRef<AnnotationHistoryState>({
    past: [],
    present: annotations,
    future: [],
  });

  // Keep present in sync when annotations change externally without going
  // through push (e.g. initial load).
  const lastPushedRef = useRef<AnnotationItem[]>(annotations);

  const [, forceRender] = useState(0);
  const rerender = useCallback(() => forceRender((n) => n + 1), []);

  const push = useCallback(
    (next: AnnotationItem[]) => {
      const s = stateRef.current;
      const newPast = [...s.past, s.present].slice(-MAX_HISTORY);
      stateRef.current = { past: newPast, present: next, future: [] };
      lastPushedRef.current = next;
      onAnnotationsChange(next);
      rerender();
    },
    [onAnnotationsChange, rerender],
  );

  const undo = useCallback(() => {
    const s = stateRef.current;
    if (s.past.length === 0) return;
    const previous = s.past[s.past.length - 1];
    const newPast = s.past.slice(0, -1);
    stateRef.current = { past: newPast, present: previous, future: [s.present, ...s.future] };
    lastPushedRef.current = previous;
    onAnnotationsChange(previous);
    rerender();
  }, [onAnnotationsChange, rerender]);

  const redo = useCallback(() => {
    const s = stateRef.current;
    if (s.future.length === 0) return;
    const next = s.future[0];
    const newFuture = s.future.slice(1);
    stateRef.current = { past: [...s.past, s.present], present: next, future: newFuture };
    lastPushedRef.current = next;
    onAnnotationsChange(next);
    rerender();
  }, [onAnnotationsChange, rerender]);

  // Keyboard shortcuts: Cmd/Ctrl+Z = undo, Cmd/Ctrl+Shift+Z = redo
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const mod = e.metaKey || e.ctrlKey;
      if (!mod || e.key.toLowerCase() !== "z") return;

      // Ignore when typing in an input / textarea
      const tag = (e.target as HTMLElement)?.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;

      e.preventDefault();
      if (e.shiftKey) {
        redo();
      } else {
        undo();
      }
    };

    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [undo, redo]);

  return {
    push,
    undo,
    redo,
    canUndo: stateRef.current.past.length > 0,
    canRedo: stateRef.current.future.length > 0,
  };
}

/* ------------------------------------------------------------------ */
/*  UndoRedoControls – toolbar buttons                                 */
/* ------------------------------------------------------------------ */

interface UndoRedoControlsProps {
  annotations: AnnotationItem[];
  onAnnotationsChange: (annotations: AnnotationItem[]) => void;
  /** Optionally pass an already-created history API (from useAnnotationHistory) */
  history?: AnnotationHistoryAPI;
}

export default function UndoRedoControls({
  annotations,
  onAnnotationsChange,
  history: externalHistory,
}: UndoRedoControlsProps) {
  const internalHistory = useAnnotationHistory(annotations, onAnnotationsChange);
  const history = externalHistory ?? internalHistory;

  return (
    <div className="flex items-center gap-1">
      {/* Undo */}
      <button
        type="button"
        onClick={history.undo}
        disabled={!history.canUndo}
        title="Undo (Ctrl+Z)"
        className="inline-flex items-center justify-center rounded-lg border border-gray-200 bg-white p-2 text-gray-700 transition-colors hover:bg-gray-100 disabled:cursor-not-allowed disabled:opacity-40"
      >
        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M3 10h10a5 5 0 015 5v2M3 10l4-4M3 10l4 4" />
        </svg>
      </button>

      {/* Redo */}
      <button
        type="button"
        onClick={history.redo}
        disabled={!history.canRedo}
        title="Redo (Ctrl+Shift+Z)"
        className="inline-flex items-center justify-center rounded-lg border border-gray-200 bg-white p-2 text-gray-700 transition-colors hover:bg-gray-100 disabled:cursor-not-allowed disabled:opacity-40"
      >
        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M21 10H11a5 5 0 00-5 5v2M21 10l-4-4M21 10l-4 4" />
        </svg>
      </button>
    </div>
  );
}
