'use client';

import { useRunProgress } from '@/hooks/useRunProgress';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface RunProgressBarProps {
  runId: string | null;
  /** Polling interval in ms. Defaults to 1000. */
  intervalMs?: number;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

/**
 * Mini progress bar that shows live run progress.
 * Displays "Running: X/Y nodes" with a colored bar and per-node status dots.
 */
export default function RunProgressBar({ runId, intervalMs = 1000 }: RunProgressBarProps) {
  const { progress, isActive, completedCount, totalCount, error } = useRunProgress(
    runId,
    intervalMs,
  );

  if (!runId || !progress) return null;

  const pct = totalCount > 0 ? Math.round((completedCount / totalCount) * 100) : 0;

  const statusColor: Record<string, string> = {
    pending: 'bg-gray-300',
    running: 'bg-blue-500 animate-pulse',
    completed: 'bg-green-500',
    failed: 'bg-red-500',
  };

  const barColor =
    progress.pipeline_status === 'failed'
      ? 'bg-red-500'
      : progress.pipeline_status === 'completed'
        ? 'bg-green-500'
        : 'bg-blue-500';

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-3 space-y-2">
      {/* Header */}
      <div className="flex items-center justify-between text-sm">
        <span className="font-medium text-gray-700">
          {isActive ? (
            <>
              <span className="inline-block w-2 h-2 rounded-full bg-blue-500 animate-pulse mr-1.5" />
              Running: {completedCount}/{totalCount} nodes
            </>
          ) : progress.pipeline_status === 'completed' ? (
            <>
              <span className="inline-block w-2 h-2 rounded-full bg-green-500 mr-1.5" />
              Completed: {completedCount}/{totalCount} nodes
            </>
          ) : (
            <>
              <span className="inline-block w-2 h-2 rounded-full bg-red-500 mr-1.5" />
              Failed at {completedCount}/{totalCount} nodes
            </>
          )}
        </span>
        <span className="text-xs text-gray-400">{pct}%</span>
      </div>

      {/* Progress bar */}
      <div className="w-full bg-gray-200 rounded-full h-1.5">
        <div
          className={`h-1.5 rounded-full transition-all duration-300 ${barColor}`}
          style={{ width: `${pct}%` }}
        />
      </div>

      {/* Node status dots */}
      <div className="flex gap-1.5 flex-wrap">
        {progress.nodes.map((node) => (
          <div
            key={node.node_id}
            title={`${node.node_name}: ${node.status}`}
            className={`w-3 h-3 rounded-full ${statusColor[node.status] ?? 'bg-gray-300'}`}
          />
        ))}
      </div>

      {/* Error */}
      {error && <p className="text-xs text-red-500">{error}</p>}
    </div>
  );
}
