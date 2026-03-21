"use client";

import { useState } from "react";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type FederationStatus = "waiting" | "ready" | "training" | "paused" | "completed" | "stopped";

interface TrainingControlsProps {
  federationId: string;
  status: FederationStatus;
  onStatusChange: (newStatus: FederationStatus) => void;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function TrainingControls({
  federationId,
  status,
  onStatusChange,
}: TrainingControlsProps) {
  const [busy, setBusy] = useState(false);
  const [confirmStop, setConfirmStop] = useState(false);

  const callAction = async (action: "pause" | "resume" | "stop" | "export" | "retrain") => {
    if (busy) return;
    setBusy(true);

    try {
      const endpoint = `/api/federated/federations/${federationId}/${action}`;
      const res = await fetch(endpoint, { method: "POST" });
      if (!res.ok) throw new Error(`Failed to ${action}`);
      const data: { status: FederationStatus } = await res.json();
      onStatusChange(data.status);
      setConfirmStop(false);
    } catch {
      // TODO: surface error via toast
    } finally {
      setBusy(false);
    }
  };

  // -----------------------------------------------------------------------
  // Stop button with confirmation
  // -----------------------------------------------------------------------
  const stopButton = confirmStop ? (
    <div className="flex items-center gap-2">
      <span className="text-xs text-red-600 font-medium">Stop training?</span>
      <button
        type="button"
        disabled={busy}
        onClick={() => callAction("stop")}
        className="rounded px-3 py-1.5 text-xs font-medium bg-red-600 text-white hover:bg-red-700 disabled:opacity-50 transition-colors"
      >
        Confirm
      </button>
      <button
        type="button"
        onClick={() => setConfirmStop(false)}
        className="rounded px-3 py-1.5 text-xs font-medium bg-gray-100 text-gray-700 hover:bg-gray-200 transition-colors"
      >
        Cancel
      </button>
    </div>
  ) : (
    <button
      type="button"
      disabled={busy}
      onClick={() => setConfirmStop(true)}
      className="rounded px-3 py-1.5 text-xs font-medium bg-red-100 text-red-700 hover:bg-red-200 disabled:opacity-50 transition-colors"
    >
      Stop
    </button>
  );

  // -----------------------------------------------------------------------
  // Render per status
  // -----------------------------------------------------------------------
  if (status === "training") {
    return (
      <div className="flex items-center gap-2 flex-wrap">
        <button
          type="button"
          disabled={busy}
          onClick={() => callAction("pause")}
          className="rounded px-3 py-1.5 text-xs font-medium bg-amber-100 text-amber-800 hover:bg-amber-200 disabled:opacity-50 transition-colors"
        >
          Pause
        </button>
        {stopButton}
      </div>
    );
  }

  if (status === "paused") {
    return (
      <div className="flex items-center gap-2 flex-wrap">
        <button
          type="button"
          disabled={busy}
          onClick={() => callAction("resume")}
          className="rounded px-3 py-1.5 text-xs font-medium bg-green-100 text-green-800 hover:bg-green-200 disabled:opacity-50 transition-colors"
        >
          Resume
        </button>
        {stopButton}
      </div>
    );
  }

  if (status === "completed") {
    return (
      <div className="flex items-center gap-2 flex-wrap">
        <button
          type="button"
          disabled={busy}
          onClick={() => callAction("export")}
          className="rounded px-3 py-1.5 text-xs font-medium bg-brand-100 text-brand-700 hover:bg-brand-200 disabled:opacity-50 transition-colors"
        >
          Export Global Model
        </button>
        <button
          type="button"
          disabled={busy}
          onClick={() => callAction("retrain")}
          className="rounded px-3 py-1.5 text-xs font-medium bg-green-100 text-green-800 hover:bg-green-200 disabled:opacity-50 transition-colors"
        >
          Re-train
        </button>
      </div>
    );
  }

  // waiting / ready / stopped -- no controls
  return null;
}
