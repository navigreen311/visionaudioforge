"use client";

import { useCallback, useEffect, useRef, useState } from "react";

interface LogEntry {
  timestamp: string;
  message: string;
}

interface ProcessingProgressProps {
  isProcessing: boolean;
  operationName?: string;
  onCancel?: () => void;
  fileSize?: number;
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function now(): string {
  return new Date().toLocaleTimeString("en-US", {
    hour12: false,
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

export default function ProcessingProgress({
  isProcessing,
  operationName = "Transform",
  onCancel,
  fileSize,
}: ProcessingProgressProps) {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [logOpen, setLogOpen] = useState(false);
  const [startTime, setStartTime] = useState<number | null>(null);
  const logEndRef = useRef<HTMLDivElement>(null);

  const addLog = useCallback((message: string) => {
    setLogs((prev) => [...prev, { timestamp: now(), message }]);
  }, []);

  // Generate log entries based on processing lifecycle
  useEffect(() => {
    if (isProcessing) {
      setLogs([]);
      setStartTime(Date.now());
      const sizeLabel = fileSize ? ` (${formatFileSize(fileSize)})` : "";
      addLog(`Uploading file${sizeLabel}...`);

      const t1 = setTimeout(() => {
        addLog(`Running ${operationName}...`);
      }, 800);

      return () => clearTimeout(t1);
    }

    if (!isProcessing && startTime) {
      const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
      addLog(`Complete \u2014 ${elapsed}s`);
      setStartTime(null);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isProcessing]);

  // Auto-scroll log
  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  if (!isProcessing && logs.length === 0) return null;

  return (
    <div className="w-full rounded-lg border border-gray-200 bg-white p-4 space-y-3">
      {/* Progress bar */}
      {isProcessing && (
        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="font-medium text-gray-700">
              {operationName}
              {fileSize ? ` \u00b7 ${formatFileSize(fileSize)}` : ""}
            </span>
            <span className="text-gray-500 text-xs">Processing...</span>
          </div>

          <div className="relative h-2 w-full overflow-hidden rounded-full bg-gray-200">
            <div
              className="absolute inset-y-0 left-0 w-1/3 rounded-full animate-pulse-slide"
              style={{ backgroundColor: "#185FA5" }}
            />
          </div>

          <style jsx>{`
            @keyframes pulse-slide {
              0% {
                transform: translateX(-100%);
                opacity: 0.6;
              }
              50% {
                opacity: 1;
              }
              100% {
                transform: translateX(300%);
                opacity: 0.6;
              }
            }
            .animate-pulse-slide {
              animation: pulse-slide 1.5s ease-in-out infinite;
            }
          `}</style>
        </div>
      )}

      {/* Completion badge */}
      {!isProcessing && logs.length > 0 && (
        <div className="flex items-center gap-2 text-sm text-green-700">
          <svg
            className="h-4 w-4"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M5 13l4 4L19 7"
            />
          </svg>
          <span className="font-medium">Transform complete</span>
        </div>
      )}

      {/* Collapsible Processing Log */}
      <div>
        <button
          type="button"
          onClick={() => setLogOpen((v) => !v)}
          className="flex items-center gap-1.5 text-xs font-medium text-gray-500 hover:text-gray-700 transition-colors"
        >
          <svg
            className={`h-3 w-3 transition-transform ${logOpen ? "rotate-90" : ""}`}
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
          Processing Log ({logs.length})
        </button>

        {logOpen && (
          <div className="mt-2 max-h-40 overflow-y-auto rounded bg-gray-50 p-2 text-xs font-mono space-y-0.5">
            {logs.map((entry, i) => (
              <div key={i} className="text-gray-600">
                <span className="text-gray-400 mr-2">[{entry.timestamp}]</span>
                {entry.message}
              </div>
            ))}
            <div ref={logEndRef} />
          </div>
        )}
      </div>

      {/* Cancel button */}
      {isProcessing && onCancel && (
        <button
          type="button"
          onClick={onCancel}
          className="inline-flex items-center gap-1.5 rounded-md border border-red-300 bg-white px-3 py-1.5 text-xs font-medium text-red-600 hover:bg-red-50 transition-colors"
        >
          <svg
            className="h-3.5 w-3.5"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M6 18L18 6M6 6l12 12"
            />
          </svg>
          Cancel
        </button>
      )}
    </div>
  );
}
