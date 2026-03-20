"use client";

import React, { useState, useEffect, useRef } from "react";
import type { Shift } from "@/lib/api";
import { createShift, endShift } from "@/lib/api";

interface OperatorPanelProps {
  currentShift?: Shift | null;
  onShiftChange?: () => void;
}

function formatDuration(startedAt: string): string {
  const diff = Date.now() - new Date(startedAt).getTime();
  const hours = Math.floor(diff / 3600000);
  const mins = Math.floor((diff % 3600000) / 60000);
  const secs = Math.floor((diff % 60000) / 1000);
  return `${String(hours).padStart(2, "0")}:${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
}

export default function OperatorPanel({
  currentShift,
  onShiftChange,
}: OperatorPanelProps) {
  const [shift, setShift] = useState<Shift | null>(currentShift || null);
  const [duration, setDuration] = useState("00:00:00");
  const [zone, setZone] = useState("Zone A");
  const [showEndConfirm, setShowEndConfirm] = useState(false);
  const [handoffNotes, setHandoffNotes] = useState("");
  const [loading, setLoading] = useState(false);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (currentShift !== undefined) setShift(currentShift);
  }, [currentShift]);

  useEffect(() => {
    if (shift && !shift.ended_at) {
      const tick = () => setDuration(formatDuration(shift.started_at));
      tick();
      timerRef.current = setInterval(tick, 1000);
      return () => {
        if (timerRef.current) clearInterval(timerRef.current);
      };
    } else {
      setDuration("00:00:00");
    }
  }, [shift]);

  const handleStartShift = async () => {
    setLoading(true);
    try {
      const newShift = await createShift(zone);
      setShift(newShift);
      onShiftChange?.();
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
  };

  const handleEndShift = async () => {
    if (!shift) return;
    setLoading(true);
    try {
      await endShift(shift.id, handoffNotes || undefined);
      setShift(null);
      setHandoffNotes("");
      setShowEndConfirm(false);
      onShiftChange?.();
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-3">
      {shift && !shift.ended_at ? (
        <>
          <div className="rounded-lg bg-green-50 border border-green-200 p-3">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-medium text-green-700 uppercase tracking-wide">
                On Shift
              </span>
              <span className="text-xs text-green-600">{shift.zone}</span>
            </div>
            <p className="text-2xl font-mono font-bold text-green-800">
              {duration}
            </p>
            <p className="text-xs text-green-600 mt-1">
              Started {new Date(shift.started_at).toLocaleTimeString()}
            </p>
          </div>

          {!showEndConfirm ? (
            <button
              onClick={() => setShowEndConfirm(true)}
              className="w-full rounded-lg bg-red-600 px-3 py-2 text-sm font-medium text-white hover:bg-red-700 transition-colors"
            >
              End Shift
            </button>
          ) : (
            <div className="space-y-2 rounded-lg border border-red-200 bg-red-50 p-3">
              <p className="text-xs font-medium text-red-800">
                Handoff notes (optional):
              </p>
              <textarea
                value={handoffNotes}
                onChange={(e) => setHandoffNotes(e.target.value)}
                rows={3}
                placeholder="Any notes for the next operator..."
                className="w-full rounded border border-red-200 px-2 py-1.5 text-sm placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-red-400"
              />
              <div className="flex gap-2">
                <button
                  onClick={handleEndShift}
                  disabled={loading}
                  className="flex-1 rounded bg-red-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-50"
                >
                  Confirm End
                </button>
                <button
                  onClick={() => setShowEndConfirm(false)}
                  className="flex-1 rounded border border-gray-300 bg-white px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}
        </>
      ) : (
        <div className="space-y-3">
          <div className="rounded-lg bg-gray-50 border border-gray-200 p-3 text-center">
            <p className="text-sm text-gray-500">No active shift</p>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">
              Zone Assignment
            </label>
            <select
              value={zone}
              onChange={(e) => setZone(e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-1.5 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
            >
              <option>Zone A</option>
              <option>Zone B</option>
              <option>Zone C</option>
              <option>Zone D</option>
            </select>
          </div>
          <button
            onClick={handleStartShift}
            disabled={loading}
            className="w-full rounded-lg bg-brand-600 px-3 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50 transition-colors"
          >
            Start Shift
          </button>
        </div>
      )}
    </div>
  );
}
