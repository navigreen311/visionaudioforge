"use client";

import {
  useState,
  useCallback,
  useImperativeHandle,
  forwardRef,
} from "react";
import { useRouter } from "next/navigation";

interface Snapshot {
  id: string;
  dataUrl: string;
  timestamp: string;
}

export interface SnapshotStripHandle {
  addSnapshot: () => void;
}

interface SnapshotStripProps {
  canvasRef: React.RefObject<HTMLCanvasElement | null>;
}

const MAX_SNAPSHOTS = 20;
const THUMB_WIDTH = 120;
const THUMB_HEIGHT = 68;

function formatTimestamp(date: Date): string {
  return date.toLocaleTimeString("en-US", {
    hour12: false,
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

const SnapshotStrip = forwardRef<SnapshotStripHandle, SnapshotStripProps>(
  function SnapshotStrip({ canvasRef }, ref) {
    const [snapshots, setSnapshots] = useState<Snapshot[]>([]);
    const router = useRouter();

    const addSnapshot = useCallback(() => {
      const sourceCanvas = canvasRef.current;
      if (!sourceCanvas) return;

      // Create thumbnail canvas
      const thumbCanvas = document.createElement("canvas");
      thumbCanvas.width = THUMB_WIDTH;
      thumbCanvas.height = THUMB_HEIGHT;
      const ctx = thumbCanvas.getContext("2d");
      if (!ctx) return;

      ctx.drawImage(sourceCanvas, 0, 0, THUMB_WIDTH, THUMB_HEIGHT);
      const dataUrl = thumbCanvas.toDataURL("image/jpeg", 0.8);

      const snapshot: Snapshot = {
        id: `snap-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
        dataUrl,
        timestamp: formatTimestamp(new Date()),
      };

      setSnapshots((prev) => {
        const updated = [snapshot, ...prev];
        return updated.slice(0, MAX_SNAPSHOTS);
      });
    }, [canvasRef]);

    useImperativeHandle(ref, () => ({ addSnapshot }), [addSnapshot]);

    const handleDelete = useCallback((id: string) => {
      setSnapshots((prev) => prev.filter((s) => s.id !== id));
    }, []);

    const handleSendToVision = useCallback(
      (dataUrl: string) => {
        const base64 = dataUrl.split(",")[1];
        if (base64) {
          sessionStorage.setItem("capture_frame_b64", base64);
          router.push("/vision?autoload=1");
        }
      },
      [router]
    );

    const handleClearAll = useCallback(() => {
      setSnapshots([]);
    }, []);

    if (snapshots.length === 0) {
      return (
        <div className="flex items-center justify-center h-20 rounded-lg border border-dashed border-gray-700 bg-gray-900/40 text-sm text-gray-500">
          Snapshots will appear here
        </div>
      );
    }

    return (
      <div className="flex items-center gap-2">
        <div className="flex items-center gap-2 overflow-x-auto flex-nowrap flex-1 pb-1">
          {snapshots.map((snap) => (
            <div
              key={snap.id}
              className="relative flex-shrink-0 group rounded-md overflow-hidden border border-gray-700 hover:border-gray-500 transition-colors"
              style={{ width: THUMB_WIDTH, height: THUMB_HEIGHT }}
            >
              <img
                src={snap.dataUrl}
                alt={`Snapshot ${snap.timestamp}`}
                className="w-full h-full object-cover"
                draggable={false}
              />

              {/* Timestamp overlay */}
              <span className="absolute bottom-0 left-0 right-0 bg-black/70 text-[9px] text-gray-300 text-center py-0.5 font-mono">
                {snap.timestamp}
              </span>

              {/* Hover action buttons */}
              <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity flex flex-col items-center justify-center gap-1">
                <button
                  onClick={() => handleSendToVision(snap.dataUrl)}
                  className="px-2 py-0.5 bg-blue-600 hover:bg-blue-700 text-white text-[9px] rounded font-semibold transition-colors"
                >
                  Send to Vision
                </button>
                <button
                  onClick={() => handleDelete(snap.id)}
                  className="px-2 py-0.5 bg-red-600 hover:bg-red-700 text-white text-[9px] rounded font-semibold transition-colors"
                >
                  &times;
                </button>
              </div>
            </div>
          ))}
        </div>

        <button
          onClick={handleClearAll}
          className="flex-shrink-0 px-2 py-1 bg-gray-800 hover:bg-gray-700 text-gray-400 hover:text-white text-[10px] rounded font-medium transition-colors"
        >
          Clear All
        </button>
      </div>
    );
  }
);

export default SnapshotStrip;
