"use client";

import React, { useEffect, useState } from "react";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface SLAViolation {
  metric: string;
  current: number;
  target: number;
}

interface SLAData {
  compliant: boolean;
  violations: SLAViolation[];
  /** ISO timestamp when the violation started (only present when !compliant) */
  violationStartedAt?: string;
}

interface SLABannerProps {
  slaData: SLAData;
  onCreateAlertRule?: () => void;
  onSendToSlack?: () => void;
}

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

function formatDuration(ms: number): string {
  const totalSec = Math.floor(ms / 1000);
  const h = Math.floor(totalSec / 3600);
  const m = Math.floor((totalSec % 3600) / 60);
  const s = totalSec % 60;
  const parts: string[] = [];
  if (h > 0) parts.push(`${h}h`);
  if (m > 0 || h > 0) parts.push(`${m}m`);
  parts.push(`${s}s`);
  return parts.join(" ");
}

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export default function SLABanner({ slaData, onCreateAlertRule, onSendToSlack }: SLABannerProps) {
  const [elapsed, setElapsed] = useState(0);

  // Live timer for violation duration
  useEffect(() => {
    if (slaData.compliant || !slaData.violationStartedAt) {
      setElapsed(0);
      return;
    }

    const start = new Date(slaData.violationStartedAt).getTime();

    function tick() {
      setElapsed(Date.now() - start);
    }
    tick();

    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [slaData.compliant, slaData.violationStartedAt]);

  /* ---- Compliant state ---- */
  if (slaData.compliant) {
    return (
      <div className="flex items-center gap-2 rounded-lg border border-green-300 bg-green-50 px-4 py-3 text-sm font-medium text-green-800">
        <span className="text-lg" aria-hidden>&#x2713;</span>
        SLA Compliant
      </div>
    );
  }

  /* ---- Violation state ---- */
  return (
    <div className="rounded-lg border border-red-300 bg-red-50 px-4 py-4 space-y-3">
      {/* Header row */}
      <div className="flex items-center justify-between">
        <span className="flex items-center gap-2 text-sm font-bold text-red-700">
          <span className="text-base" aria-hidden>&#x26A0;</span>
          SLA VIOLATION
        </span>
        {slaData.violationStartedAt && (
          <span className="rounded-full bg-red-100 px-2.5 py-0.5 text-xs font-semibold text-red-700 tabular-nums">
            {formatDuration(elapsed)}
          </span>
        )}
      </div>

      {/* Violation details */}
      {slaData.violations.length > 0 && (
        <ul className="list-disc list-inside space-y-1 text-sm text-red-700">
          {slaData.violations.map((v) => (
            <li key={v.metric}>
              <span className="font-medium">{v.metric}</span>: current{" "}
              <span className="font-semibold">{v.current}</span> — target{" "}
              <span className="font-semibold">{v.target}</span>
            </li>
          ))}
        </ul>
      )}

      {/* Action buttons */}
      <div className="flex items-center gap-2 pt-1">
        <button
          type="button"
          onClick={onCreateAlertRule}
          className="rounded-md bg-red-600 px-3 py-1.5 text-xs font-medium text-white shadow-sm hover:bg-red-700 transition-colors"
        >
          Create Alert Rule
        </button>
        <button
          type="button"
          onClick={onSendToSlack}
          className="rounded-md border border-red-300 bg-white px-3 py-1.5 text-xs font-medium text-red-700 shadow-sm hover:bg-red-50 transition-colors"
        >
          Send to Slack
        </button>
      </div>
    </div>
  );
}
