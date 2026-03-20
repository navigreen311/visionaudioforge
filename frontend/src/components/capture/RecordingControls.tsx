"use client";

import { useState, useEffect, useRef } from "react";

interface RecordingControlsProps {
  isCapturing: boolean;
  onRecordStart: () => void;
  onRecordStop: () => void;
  onSnapshot: () => void;
}

export default function RecordingControls({
  isCapturing,
  onRecordStart,
  onRecordStop,
  onSnapshot,
}: RecordingControlsProps) {
  const [isRecording, setIsRecording] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (isRecording) {
      setElapsed(0);
      timerRef.current = setInterval(() => {
        setElapsed((prev) => prev + 1);
      }, 1000);
    } else {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
      setElapsed(0);
    }
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [isRecording]);

  // Stop recording if capture stops
  useEffect(() => {
    if (!isCapturing && isRecording) {
      setIsRecording(false);
      onRecordStop();
    }
  }, [isCapturing, isRecording, onRecordStop]);

  const handleToggleRecord = () => {
    if (isRecording) {
      setIsRecording(false);
      onRecordStop();
    } else {
      setIsRecording(true);
      onRecordStart();
    }
  };

  const minutes = Math.floor(elapsed / 60)
    .toString()
    .padStart(2, "0");
  const seconds = (elapsed % 60).toString().padStart(2, "0");

  return (
    <div className="flex items-center gap-3">
      {/* Record button */}
      <button
        onClick={handleToggleRecord}
        disabled={!isCapturing}
        className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${
          isRecording
            ? "bg-red-600 hover:bg-red-700 text-white"
            : "bg-gray-200 hover:bg-gray-300 text-gray-700"
        }`}
      >
        {/* Red dot indicator */}
        <span
          className={`w-3 h-3 rounded-full ${
            isRecording ? "bg-white animate-pulse" : "bg-red-500"
          }`}
        />
        {isRecording ? "Stop Rec" : "Record"}
      </button>

      {/* Recording timer */}
      {isRecording && (
        <div className="flex items-center gap-2 text-sm">
          <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
          <span className="font-mono font-medium text-red-600">
            {minutes}:{seconds}
          </span>
        </div>
      )}

      {/* Snapshot button */}
      <button
        onClick={onSnapshot}
        disabled={!isCapturing}
        className="flex items-center gap-2 px-4 py-2 bg-gray-200 hover:bg-gray-300 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg text-sm font-medium transition-colors"
      >
        {/* Camera icon (SVG) */}
        <svg
          className="w-4 h-4"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z"
          />
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M15 13a3 3 0 11-6 0 3 3 0 016 0z"
          />
        </svg>
        Snapshot
      </button>
    </div>
  );
}
