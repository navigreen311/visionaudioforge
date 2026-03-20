"use client";

interface CaptureControlsProps {
  isCapturing: boolean;
  onStart: () => void;
  onStop: () => void;
  onSnapshot: () => void;
}

export default function CaptureControls({
  isCapturing,
  onStart,
  onStop,
  onSnapshot,
}: CaptureControlsProps) {
  return (
    <div className="flex items-center gap-3">
      {isCapturing ? (
        <button
          onClick={onStop}
          className="px-5 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-sm font-medium transition-colors"
        >
          Stop
        </button>
      ) : (
        <button
          onClick={onStart}
          className="px-5 py-2 bg-brand-600 hover:bg-brand-700 text-white rounded-lg text-sm font-medium transition-colors"
        >
          Start
        </button>
      )}
      <button
        onClick={onSnapshot}
        disabled={!isCapturing}
        className="px-4 py-2 bg-gray-200 hover:bg-gray-300 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg text-sm font-medium transition-colors"
      >
        Snapshot
      </button>
    </div>
  );
}
