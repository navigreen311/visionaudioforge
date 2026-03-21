'use client';

import { useCallback, useEffect, useState } from 'react';
import RunLogPanel, { type LogEntry } from './RunLogPanel';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type RunStatus = 'running' | 'completed' | 'failed' | 'cancelled' | 'pending';

export interface PipelineRunRecord {
  id: string;
  run_number: number;
  status: RunStatus;
  started_at: string;
  duration_ms: number | null;
  nodes_executed: number;
  nodes_total: number;
  output_summary: string | null;
  logs: LogEntry[];
}

interface RunHistoryProps {
  pipelineId: string;
  runs?: PipelineRunRecord[];
  onRerun?: (runId: string) => void;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const STATUS_BADGE: Record<RunStatus, { bg: string; text: string; animate?: string }> = {
  running:   { bg: 'bg-blue-100',   text: 'text-blue-700',   animate: 'animate-pulse' },
  completed: { bg: 'bg-green-100',  text: 'text-green-700' },
  failed:    { bg: 'bg-red-100',    text: 'text-red-700' },
  cancelled: { bg: 'bg-gray-100',   text: 'text-gray-500' },
  pending:   { bg: 'bg-yellow-100', text: 'text-yellow-700' },
};

function formatDuration(ms: number | null): string {
  if (ms === null) return '-';
  if (ms < 1000) return `${ms}ms`;
  const s = Math.round(ms / 1000);
  if (s < 60) return `${s}s`;
  const m = Math.floor(s / 60);
  return `${m}m ${s % 60}s`;
}

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function RunHistory({ pipelineId, runs: externalRuns, onRerun }: RunHistoryProps) {
  const [runs, setRuns] = useState<PipelineRunRecord[]>(externalRuns ?? []);
  const [expandedRunId, setExpandedRunId] = useState<string | null>(null);
  const [loading, setLoading] = useState(!externalRuns);

  // Fetch runs from API when not provided externally
  useEffect(() => {
    if (externalRuns) {
      setRuns(externalRuns);
      return;
    }

    let cancelled = false;
    const fetchRuns = async () => {
      setLoading(true);
      try {
        const resp = await fetch(`/api/pipeline/runs?pipeline_id=${pipelineId}`);
        if (resp.ok && !cancelled) {
          const data: PipelineRunRecord[] = await resp.json();
          setRuns(data);
        }
      } catch {
        // Silently fail — table stays empty
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    fetchRuns();
    return () => { cancelled = true; };
  }, [pipelineId, externalRuns]);

  const handleViewLog = useCallback((runId: string) => {
    setExpandedRunId((prev) => (prev === runId ? null : runId));
  }, []);

  const handleRerun = useCallback(
    async (runId: string) => {
      if (onRerun) {
        onRerun(runId);
        return;
      }
      try {
        await fetch('/api/pipeline/run', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ pipeline_id: pipelineId, rerun_of: runId }),
        });
      } catch {
        // fire-and-forget in stub mode
      }
    },
    [pipelineId, onRerun],
  );

  const handleDownload = useCallback((runId: string) => {
    window.open(`/api/pipeline/runs/${runId}/download`, '_blank');
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-20 text-sm text-gray-400">
        Loading run history...
      </div>
    );
  }

  if (runs.length === 0) {
    return (
      <div className="flex items-center justify-center h-20 text-sm text-gray-400">
        No pipeline runs yet
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-gray-500 border-b border-gray-100">
            <th className="px-4 py-1.5 font-medium">Run #</th>
            <th className="px-4 py-1.5 font-medium">Status</th>
            <th className="px-4 py-1.5 font-medium">Started</th>
            <th className="px-4 py-1.5 font-medium">Duration</th>
            <th className="px-4 py-1.5 font-medium">Nodes Executed</th>
            <th className="px-4 py-1.5 font-medium">Output</th>
            <th className="px-4 py-1.5 font-medium">Actions</th>
          </tr>
        </thead>
        <tbody>
          {runs.map((run) => {
            const badge = STATUS_BADGE[run.status] ?? STATUS_BADGE.pending;
            const isExpanded = expandedRunId === run.id;

            return (
              <tr key={run.id} className="group">
                <td colSpan={7} className="p-0">
                  {/* Main row */}
                  <div className="flex items-center border-b border-gray-50 hover:bg-gray-50 transition-colors">
                    <div className="px-4 py-2 w-20 font-mono text-xs text-gray-700">
                      #{run.run_number}
                    </div>
                    <div className="px-4 py-2 w-28">
                      <span
                        className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${badge.bg} ${badge.text} ${badge.animate ?? ''}`}
                      >
                        {run.status}
                      </span>
                    </div>
                    <div className="px-4 py-2 w-44 text-gray-500 text-xs">
                      {formatDate(run.started_at)}
                    </div>
                    <div className="px-4 py-2 w-24 text-xs">
                      {formatDuration(run.duration_ms)}
                    </div>
                    <div className="px-4 py-2 w-32 text-xs text-gray-600">
                      {run.nodes_executed}/{run.nodes_total}
                    </div>
                    <div className="px-4 py-2 flex-1 text-xs text-gray-500 truncate max-w-[200px]">
                      {run.output_summary ?? '-'}
                    </div>
                    <div className="px-4 py-2 flex items-center gap-2">
                      <button
                        type="button"
                        onClick={() => handleViewLog(run.id)}
                        className="text-xs text-blue-600 hover:text-blue-800 font-medium"
                      >
                        {isExpanded ? 'Hide Log' : 'View Log'}
                      </button>
                      <button
                        type="button"
                        onClick={() => handleRerun(run.id)}
                        className="text-xs text-purple-600 hover:text-purple-800 font-medium"
                      >
                        Re-run
                      </button>
                      <button
                        type="button"
                        onClick={() => handleDownload(run.id)}
                        className="text-xs text-gray-500 hover:text-gray-700 font-medium"
                      >
                        Download
                      </button>
                    </div>
                  </div>

                  {/* Expanded log panel */}
                  {isExpanded && (
                    <div className="px-4 py-3 bg-gray-50 border-b border-gray-100">
                      <RunLogPanel
                        logs={run.logs}
                        onClose={() => setExpandedRunId(null)}
                      />
                    </div>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
