"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import type { Shift } from "@/lib/api";
import { createShift, endShift } from "@/lib/api";

interface ShiftControlProps {
  zone: string;
}

const ZONES = ["Zone A", "Zone B", "Zone C", "Zone D"] as const;

function formatElapsed(startIso: string): string {
  const diff = Date.now() - new Date(startIso).getTime();
  const h = Math.floor(diff / 3_600_000);
  const m = Math.floor((diff % 3_600_000) / 60_000);
  const s = Math.floor((diff % 60_000) / 1_000);
  return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

export default function ShiftControl({ zone: initialZone }: ShiftControlProps) {
  const [shift, setShift] = useState<Shift | null>(null);
  const [selectedZone, setSelectedZone] = useState(initialZone);
  const [elapsed, setElapsed] = useState("00:00:00");
  const [loading, setLoading] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Keep zone in sync if prop changes while no shift is active
  useEffect(() => {
    if (!shift) setSelectedZone(initialZone);
  }, [initialZone, shift]);

  // Timer tick
  useEffect(() => {
    if (shift && !shift.ended_at) {
      const tick = () => setElapsed(formatElapsed(shift.started_at));
      tick();
      timerRef.current = setInterval(tick, 1_000);
      return () => {
        if (timerRef.current) clearInterval(timerRef.current);
      };
    }
    setElapsed("00:00:00");
  }, [shift]);

  const handleStart = useCallback(async () => {
    setLoading(true);
    try {
      const newShift = await createShift(selectedZone);
      setShift(newShift);
    } catch {
      // fail silently — button re-enables
    } finally {
      setLoading(false);
    }
  }, [selectedZone]);

  const handleEnd = useCallback(async () => {
    if (!shift) return;
    setLoading(true);
    try {
      await endShift(shift.id);
      setShift(null);
      setShowConfirm(false);
    } catch {
      // fail silently
    } finally {
      setLoading(false);
    }
  }, [shift]);

  // Active shift view
  if (shift && !shift.ended_at) {
    return (
      <div className="space-y-3">
        <div className="rounded-lg bg-green-50 border border-green-200 p-3">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-medium text-green-700 uppercase tracking-wide">
              Shift Active
            </span>
            <span className="text-xs text-green-600">{shift.zone}</span>
          </div>
          <p className="text-2xl font-mono font-bold text-green-800">
            {elapsed}
          </p>
        </div>

        {/* Zone dropdown locked while on shift */}
        <select
          disabled
          value={shift.zone}
          className="w-full rounded-lg border border-gray-200 bg-gray-100 px-3 py-1.5 text-sm text-gray-500 cursor-not-allowed"
        >
          {ZONES.map((z) => (
            <option key={z} value={z}>
              {z}
            </option>
          ))}
        </select>

        {!showConfirm ? (
          <button
            onClick={() => setShowConfirm(true)}
            className="w-full rounded-lg bg-red-600 px-3 py-2 text-sm font-medium text-white hover:bg-red-700 transition-colors"
          >
            End Shift
          </button>
        ) : (
          <div className="flex gap-2">
            <button
              onClick={handleEnd}
              disabled={loading}
              className="flex-1 rounded-lg bg-red-600 px-3 py-2 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-50 transition-colors"
            >
              Confirm End
            </button>
            <button
              onClick={() => setShowConfirm(false)}
              className="flex-1 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 transition-colors"
            >
              Cancel
            </button>
          </div>
        )}
      </div>
    );
  }

  // No active shift view
  return (
    <div className="space-y-3">
      <div className="rounded-lg bg-gray-50 border border-gray-200 p-3 text-center">
        <p className="text-sm text-gray-500">No active shift</p>
      </div>

      <div>
        <label className="block text-xs font-medium text-gray-600 mb-1">
          Zone
        </label>
        <select
          value={selectedZone}
          onChange={(e) => setSelectedZone(e.target.value)}
          className="w-full rounded-lg border border-gray-300 px-3 py-1.5 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
        >
          {ZONES.map((z) => (
            <option key={z} value={z}>
              {z}
            </option>
          ))}
        </select>
      </div>

      <button
        onClick={handleStart}
        disabled={loading}
        className="w-full rounded-lg bg-brand-600 px-3 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50 transition-colors"
      >
        Start Shift
      </button>
    </div>
  );
}
