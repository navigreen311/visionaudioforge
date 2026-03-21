'use client';

import { useCallback, useEffect, useRef, useState } from 'react';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type NodeRunState = 'pending' | 'running' | 'completed' | 'failed';

export interface NodeStatus {
  node_id: string;
  node_name: string;
  status: NodeRunState;
}

export interface RunProgressData {
  run_id: string;
  pipeline_status: 'pending' | 'running' | 'completed' | 'failed';
  nodes: NodeStatus[];
  started_at: string | null;
  elapsed_ms: number;
}

interface UseRunProgressReturn {
  /** Current progress data — null until first successful fetch. */
  progress: RunProgressData | null;
  /** Whether the run is still active (pending or running). */
  isActive: boolean;
  /** Completed node count. */
  completedCount: number;
  /** Total node count. */
  totalCount: number;
  /** Error message if polling fails. */
  error: string | null;
  /** Manually stop polling. */
  stop: () => void;
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

/**
 * Polls GET /api/pipeline/runs/{runId}/status every `intervalMs` (default 1 000 ms).
 * Automatically stops when the run reaches a terminal state (completed / failed).
 * Cleans up the interval on unmount.
 */
export function useRunProgress(
  runId: string | null,
  intervalMs = 1000,
): UseRunProgressReturn {
  const [progress, setProgress] = useState<RunProgressData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const stoppedRef = useRef(false);

  const stop = useCallback(() => {
    stoppedRef.current = true;
    if (intervalRef.current !== null) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  useEffect(() => {
    // Reset on runId change
    stoppedRef.current = false;
    setProgress(null);
    setError(null);

    if (!runId) return;

    const poll = async () => {
      if (stoppedRef.current) return;
      try {
        const resp = await fetch(`/api/pipeline/runs/${runId}/status`);
        if (!resp.ok) {
          setError(`Status fetch failed (${resp.status})`);
          return;
        }
        const data: RunProgressData = await resp.json();
        setProgress(data);
        setError(null);

        // Auto-stop on terminal states
        if (data.pipeline_status === 'completed' || data.pipeline_status === 'failed') {
          stop();
        }
      } catch {
        setError('Network error fetching run status');
      }
    };

    // Immediate first poll
    poll();

    intervalRef.current = setInterval(poll, intervalMs);

    return () => {
      stop();
    };
  }, [runId, intervalMs, stop]);

  const completedCount = progress
    ? progress.nodes.filter((n) => n.status === 'completed').length
    : 0;
  const totalCount = progress ? progress.nodes.length : 0;
  const isActive = progress
    ? progress.pipeline_status === 'pending' || progress.pipeline_status === 'running'
    : false;

  return { progress, isActive, completedCount, totalCount, error, stop };
}
