"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface ChecklistStep {
  id: string;
  title: string;
  description: string;
  href: string;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const STORAGE_KEY = "vaf_visited_pages";
const DISMISSED_KEY = "vaf_getting_started_dismissed";

const STEPS: ChecklistStep[] = [
  {
    id: "capture",
    title: "Start your first capture",
    description: "Record video or audio from a connected device or file.",
    href: "/capture",
  },
  {
    id: "vision",
    title: "Analyze an image or audio file",
    description: "Run vision or audio analysis on uploaded media.",
    href: "/vision",
  },
  {
    id: "pipeline",
    title: "Build your first pipeline",
    description: "Chain processing steps into a reusable workflow.",
    href: "/pipeline",
  },
  {
    id: "camera",
    title: "Connect a camera or screen",
    description: "Stream live video from a webcam or screen capture.",
    href: "/capture?tab=camera",
  },
  {
    id: "agents",
    title: "Ask the Copilot a question",
    description: "Get AI-powered help for your projects.",
    href: "/agents",
  },
];

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function loadCompletedSteps(): Set<string> {
  if (typeof window === "undefined") return new Set<string>();
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return new Set<string>();
    const parsed: unknown = JSON.parse(raw);
    if (Array.isArray(parsed)) {
      return new Set<string>(parsed.filter((v): v is string => typeof v === "string"));
    }
    return new Set<string>();
  } catch {
    return new Set<string>();
  }
}

function saveCompletedSteps(steps: Set<string>): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(Array.from(steps)));
  } catch {
    // localStorage may be unavailable
  }
}

function loadDismissed(): boolean {
  if (typeof window === "undefined") return false;
  try {
    return localStorage.getItem(DISMISSED_KEY) === "true";
  } catch {
    return false;
  }
}

function saveDismissed(value: boolean): void {
  try {
    localStorage.setItem(DISMISSED_KEY, value ? "true" : "false");
  } catch {
    // localStorage may be unavailable
  }
}

// ---------------------------------------------------------------------------
// Chevron SVG
// ---------------------------------------------------------------------------

function ChevronIcon({ open }: { open: boolean }) {
  return (
    <svg
      className={`h-5 w-5 text-gray-500 transition-transform duration-200 ${
        open ? "rotate-180" : ""
      }`}
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth={2}
    >
      <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
    </svg>
  );
}

// ---------------------------------------------------------------------------
// Check icon SVG
// ---------------------------------------------------------------------------

function CheckCircleIcon() {
  return (
    <svg
      className="h-5 w-5 text-green-500 flex-shrink-0"
      fill="currentColor"
      viewBox="0 0 20 20"
    >
      <path
        fillRule="evenodd"
        d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
        clipRule="evenodd"
      />
    </svg>
  );
}

function CircleIcon() {
  return (
    <svg
      className="h-5 w-5 text-gray-300 flex-shrink-0"
      fill="none"
      viewBox="0 0 20 20"
      stroke="currentColor"
      strokeWidth={1.5}
    >
      <circle cx="10" cy="10" r="8" />
    </svg>
  );
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function GettingStarted() {
  const [completedSteps, setCompletedSteps] = useState<Set<string>>(new Set());
  const [isOpen, setIsOpen] = useState(true);
  const [dismissed, setDismissed] = useState(false);
  const [mounted, setMounted] = useState(false);

  // Hydrate from localStorage on mount
  useEffect(() => {
    setCompletedSteps(loadCompletedSteps());
    setDismissed(loadDismissed());
    setMounted(true);
  }, []);

  const completedCount = completedSteps.size;
  const totalSteps = STEPS.length;
  const allDone = completedCount >= totalSteps;

  const markComplete = useCallback(
    (stepId: string) => {
      setCompletedSteps((prev) => {
        const next = new Set(prev);
        next.add(stepId);
        saveCompletedSteps(next);
        return next;
      });
    },
    [],
  );

  const handleDismiss = useCallback(() => {
    setDismissed(true);
    saveDismissed(true);
  }, []);

  // Don't render during SSR or if dismissed or all steps completed and dismissed
  if (!mounted) return null;
  if (dismissed) return null;
  // Only show when completedSteps < 5 OR all done (to show congrats before dismiss)
  if (completedCount >= totalSteps && !allDone) return null;

  return (
    <div className="rounded-lg border border-gray-200 bg-white shadow-sm overflow-hidden">
      {/* Collapsible header */}
      <button
        type="button"
        onClick={() => setIsOpen((prev) => !prev)}
        className="flex w-full items-center justify-between px-6 py-4 text-left hover:bg-gray-50 transition-colors"
      >
        <div className="flex items-center gap-3">
          <span className="text-lg font-semibold text-gray-900">
            Getting Started
          </span>
          <span className="text-sm text-gray-500">
            {completedCount}/{totalSteps} completed
          </span>
        </div>
        <ChevronIcon open={isOpen} />
      </button>

      {/* Collapsible body */}
      {isOpen && (
        <div className="px-6 pb-5">
          {/* Progress bar */}
          <div className="mb-4">
            <div className="h-2 w-full rounded-full bg-gray-100 overflow-hidden">
              <div
                className="h-full rounded-full transition-all duration-500 ease-out"
                style={{
                  width: `${(completedCount / totalSteps) * 100}%`,
                  backgroundColor: "#185FA5",
                }}
              />
            </div>
          </div>

          {/* Congratulations message */}
          {allDone ? (
            <div className="flex flex-col items-center gap-3 py-4">
              <span className="text-2xl">&#127881;</span>
              <p className="text-sm font-medium text-gray-900">
                Congratulations! You&apos;ve completed all the getting started
                steps.
              </p>
              <button
                type="button"
                onClick={handleDismiss}
                className="rounded-md px-4 py-2 text-sm font-medium text-white transition-colors hover:opacity-90"
                style={{ backgroundColor: "#185FA5" }}
              >
                Dismiss
              </button>
            </div>
          ) : (
            /* Step list */
            <ul className="space-y-2">
              {STEPS.map((step) => {
                const done = completedSteps.has(step.id);
                return (
                  <li key={step.id}>
                    {done ? (
                      <div className="flex items-start gap-3 rounded-lg px-3 py-2.5 bg-gray-50">
                        <CheckCircleIcon />
                        <div className="min-w-0">
                          <p className="text-sm font-medium text-gray-400 line-through">
                            {step.title}
                          </p>
                          <p className="text-xs text-gray-400">
                            {step.description}
                          </p>
                        </div>
                      </div>
                    ) : (
                      <Link
                        href={step.href}
                        onClick={() => markComplete(step.id)}
                        className="flex items-start gap-3 rounded-lg px-3 py-2.5 hover:bg-blue-50 transition-colors group"
                      >
                        <CircleIcon />
                        <div className="min-w-0 flex-1">
                          <p className="text-sm font-medium text-gray-900 group-hover:text-[#185FA5]">
                            {step.title}
                          </p>
                          <p className="text-xs text-gray-500">
                            {step.description}
                          </p>
                        </div>
                        <svg
                          className="h-4 w-4 text-gray-400 group-hover:text-[#185FA5] mt-0.5 flex-shrink-0"
                          fill="none"
                          viewBox="0 0 24 24"
                          stroke="currentColor"
                          strokeWidth={2}
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            d="M9 5l7 7-7 7"
                          />
                        </svg>
                      </Link>
                    )}
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
