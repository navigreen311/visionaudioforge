'use client';

import { useMemo } from 'react';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface LogEntry {
  timestamp: string;
  node_name: string;
  status: 'started' | 'completed' | 'failed' | 'skipped';
  message?: string;
}

interface RunLogPanelProps {
  logs: LogEntry[];
  onClose?: () => void;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const STATUS_STYLES: Record<LogEntry['status'], string> = {
  started: 'text-blue-600',
  completed: 'text-green-600',
  failed: 'text-red-600',
  skipped: 'text-gray-400',
};

const STATUS_LABELS: Record<LogEntry['status'], string> = {
  started: 'started',
  completed: 'completed',
  failed: 'FAILED',
  skipped: 'skipped',
};

function formatTimestamp(ts: string): string {
  try {
    const d = new Date(ts);
    return d.toLocaleTimeString('en-US', { hour12: false });
  } catch {
    return ts;
  }
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function RunLogPanel({ logs, onClose }: RunLogPanelProps) {
  const sortedLogs = useMemo(
    () => [...logs].sort((a, b) => a.timestamp.localeCompare(b.timestamp)),
    [logs],
  );

  return (
    <div className="bg-gray-900 rounded-lg border border-gray-700 overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 bg-gray-800 border-b border-gray-700">
        <h4 className="text-sm font-semibold text-gray-200">Run Logs</h4>
        {onClose && (
          <button
            type="button"
            onClick={onClose}
            className="text-gray-400 hover:text-gray-200 text-sm"
          >
            Close
          </button>
        )}
      </div>

      {/* Log entries */}
      <div className="max-h-64 overflow-y-auto p-3 font-mono text-xs leading-relaxed space-y-0.5">
        {sortedLogs.length === 0 ? (
          <p className="text-gray-500 text-center py-4">No log entries yet</p>
        ) : (
          sortedLogs.map((entry, i) => (
            <div key={i} className="flex gap-2">
              <span className="text-gray-500 flex-shrink-0">
                [{formatTimestamp(entry.timestamp)}]
              </span>
              <span className="text-gray-300 flex-shrink-0">{entry.node_name}</span>
              <span className="text-gray-600">&mdash;</span>
              <span className={STATUS_STYLES[entry.status]}>
                {STATUS_LABELS[entry.status]}
              </span>
              {entry.message && (
                <span className="text-gray-400 truncate">{entry.message}</span>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
