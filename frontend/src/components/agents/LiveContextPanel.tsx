"use client";

import { useCallback, useEffect, useRef, useState } from "react";

interface LiveContextPanelProps {
  onAddContext: (text: string) => void;
}

interface ContextCard {
  label: string;
  value: string;
  contextText: string;
}

interface StreamsData {
  active: number;
  total: number;
}

interface AlertSummary {
  open: number;
  severity: string;
}

interface LastAsset {
  filename: string;
  type: string;
  ago: string;
}

interface PipelineData {
  running: number;
}

async function fetchJson<T>(url: string, fallback: T): Promise<T> {
  try {
    const res = await fetch(url);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return (await res.json()) as T;
  } catch {
    return fallback;
  }
}

export default function LiveContextPanel({
  onAddContext,
}: LiveContextPanelProps) {
  const [collapsed, setCollapsed] = useState(true);
  const [cards, setCards] = useState<ContextCard[]>([]);

  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const refresh = useCallback(async () => {
    const [streamsData, alertData, assetData, pipelineData] = await Promise.all(
      [
        fetchJson<StreamsData>("/api/streams/status", {
          active: 0,
          total: 0,
        }),
        fetchJson<AlertSummary>("/api/alerts/summary", {
          open: 0,
          severity: "none",
        }),
        fetchJson<LastAsset>("/api/assets/latest", {
          filename: "N/A",
          type: "unknown",
          ago: "N/A",
        }),
        fetchJson<PipelineData>("/api/pipeline/summary", { running: 0 }),
      ],
    );

    setCards([
      {
        label: "Active Streams",
        value: `${streamsData.active}`,
        contextText: `Active streams: ${streamsData.active} of ${streamsData.total} total`,
      },
      {
        label: "Open Alerts",
        value: `${alertData.open} (${alertData.severity})`,
        contextText: `Open alerts: ${alertData.open}, highest severity: ${alertData.severity}`,
      },
      {
        label: "Last Asset",
        value: `${assetData.filename} (${assetData.type})`,
        contextText: `Last asset: ${assetData.filename} [${assetData.type}], ${assetData.ago}`,
      },
      {
        label: "Running Pipelines",
        value: `${pipelineData.running}`,
        contextText: `Running pipelines: ${pipelineData.running}`,
      },
    ]);
  }, []);

  // Auto-refresh every 60 seconds when expanded
  useEffect(() => {
    if (collapsed) return;

    refresh();

    intervalRef.current = setInterval(() => {
      refresh();
    }, 60_000);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [collapsed, refresh]);

  return (
    <div className="bg-white rounded-xl border border-gray-200">
      {/* Collapse toggle */}
      <button
        onClick={() => setCollapsed((prev) => !prev)}
        className="w-full flex items-center justify-between px-4 py-3 text-sm font-semibold text-gray-900 hover:bg-gray-50 transition-colors rounded-xl"
      >
        <span>Live Context</span>
        <svg
          className={`w-4 h-4 text-gray-400 transition-transform duration-200 ${
            collapsed ? "" : "rotate-180"
          }`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M19 9l-7 7-7-7"
          />
        </svg>
      </button>

      {/* Collapsible body */}
      <div
        className="overflow-hidden transition-all duration-300 ease-in-out"
        style={{
          maxHeight: collapsed ? "0px" : "400px",
          opacity: collapsed ? 0 : 1,
        }}
      >
        <div className="px-4 pb-4 space-y-2">
          {cards.map((card) => (
            <div
              key={card.label}
              className="flex items-center justify-between border border-gray-100 rounded-lg p-3 group hover:border-gray-300 transition-colors"
            >
              <div>
                <p className="text-[10px] text-gray-400 uppercase tracking-wide">
                  {card.label}
                </p>
                <p className="text-sm font-medium text-gray-800">
                  {card.value}
                </p>
              </div>
              <button
                onClick={() => onAddContext(card.contextText)}
                title={`Add "${card.label}" to next message`}
                className="w-6 h-6 flex items-center justify-center rounded text-gray-300 hover:text-brand-600 hover:bg-brand-50 opacity-0 group-hover:opacity-100 transition-all text-lg leading-none"
              >
                +
              </button>
            </div>
          ))}

          {cards.length === 0 && (
            <p className="text-gray-400 text-xs text-center py-4">
              Loading context...
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
