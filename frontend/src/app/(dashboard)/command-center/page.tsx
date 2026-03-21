"use client";

import React, { useState, useEffect, useCallback } from "react";
import VideoWall from "@/components/command-center/VideoWall";
import IncidentSidebar from "@/components/command-center/IncidentSidebar";
import OperatorPanel from "@/components/command-center/OperatorPanel";
import TimelineFeed from "@/components/command-center/TimelineFeed";
import KPICards from "@/components/command-center/KPICards";
import LayoutSelector from "@/components/command-center/LayoutSelector";
import AddStreamModal from "@/components/command-center/AddStreamModal";
import type {
  GridLayout,
  Stream,
  Incident,
  Shift,
  CockpitOverview,
  KPIs,
  TimelineEvent,
} from "@/lib/api";
import {
  listStreams,
  getCockpitOverview,
  getKPIs,
  getTimelineFeed,
  getIncidentQueue,
  removeStream,
  setLayout as setLayoutApi,
} from "@/lib/api";

const statusColors: Record<string, string> = {
  green: "bg-green-500",
  yellow: "bg-yellow-500",
  red: "bg-red-500",
};

function formatShiftTimer(startedAt: string): string {
  const diff = Date.now() - new Date(startedAt).getTime();
  const h = Math.floor(diff / 3600000);
  const m = Math.floor((diff % 3600000) / 60000);
  return `${h}h ${m}m`;
}

export default function CommandCenterPage() {
  // State
  const [layout, setLayout] = useState<GridLayout>("2x2");
  const [streams, setStreams] = useState<Stream[]>([]);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [overview, setOverview] = useState<CockpitOverview | null>(null);
  const [kpis, setKpis] = useState<KPIs | null>(null);
  const [timeline, setTimeline] = useState<TimelineEvent[]>([]);
  const [currentShift, setCurrentShift] = useState<Shift | null>(null);
  const [showAddStream, setShowAddStream] = useState(false);
  const [leftOpen, setLeftOpen] = useState(true);
  const [rightOpen, setRightOpen] = useState(true);
  const [copilotInput, setCopilotInput] = useState("");
  const [copilotResponses, setCopilotResponses] = useState<string[]>([]);
  const [shiftTimer, setShiftTimer] = useState("");

  // Fetch all data
  const fetchAll = useCallback(async () => {
    try {
      const [s, o, k, t, i] = await Promise.allSettled([
        listStreams(),
        getCockpitOverview(),
        getKPIs(),
        getTimelineFeed(),
        getIncidentQueue(),
      ]);
      if (s.status === "fulfilled") setStreams(s.value);
      if (o.status === "fulfilled") {
        setOverview(o.value);
        setLayout(o.value.current_layout);
      }
      if (k.status === "fulfilled") setKpis(k.value);
      if (t.status === "fulfilled") setTimeline(t.value);
      if (i.status === "fulfilled") setIncidents(i.value);
    } catch {
      // silent
    }
  }, []);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  // Clean up streams on unmount
  useEffect(() => {
    return () => {
      setStreams([]);
    };
  }, []);

  // Shift timer tick
  useEffect(() => {
    if (!currentShift || currentShift.ended_at) {
      setShiftTimer("");
      return;
    }
    const tick = () => setShiftTimer(formatShiftTimer(currentShift.started_at));
    tick();
    const interval = setInterval(tick, 30000);
    return () => clearInterval(interval);
  }, [currentShift]);

  const handleLayoutChange = async (newLayout: GridLayout) => {
    setLayout(newLayout);
    try {
      await setLayoutApi(newLayout);
    } catch {
      // revert on error
    }
  };

  const handleRemoveStream = async (streamId: string) => {
    try {
      await removeStream(streamId);
      setStreams((prev) => prev.filter((s) => s.id !== streamId));
    } catch {
      // silent
    }
  };

  const handleCopilotSend = () => {
    if (!copilotInput.trim()) return;
    setCopilotResponses((prev) =>
      [`Analyzing: "${copilotInput.trim()}"...`, ...prev].slice(0, 3)
    );
    setCopilotInput("");
  };

  return (
    <div className="flex flex-col h-[calc(100vh-64px)] -m-4 lg:-m-8">
      {/* ===== TOP BAR ===== */}
      <div className="flex items-center justify-between gap-4 border-b border-gray-200 bg-white px-4 py-2 flex-shrink-0">
        <div className="flex items-center gap-4">
          {/* System status dot */}
          <div className="flex items-center gap-2">
            <span className="relative flex h-3 w-3">
              {overview?.system_status === "green" && (
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-green-400 opacity-75" />
              )}
              <span
                className={`relative inline-flex h-3 w-3 rounded-full ${
                  statusColors[overview?.system_status || "green"] || "bg-gray-400"
                }`}
              />
            </span>
            <span className="text-sm font-medium text-gray-700 hidden sm:inline">
              System{" "}
              <span className="capitalize">{overview?.system_status || "..."}</span>
            </span>
          </div>

          <div className="hidden md:flex items-center gap-3 text-xs text-gray-500">
            <span className="flex items-center gap-1">
              <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
              </svg>
              <span className="font-medium text-gray-700">
                {overview?.active_streams ?? 0}
              </span>{" "}
              streams
            </span>
            <span className="flex items-center gap-1">
              <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
              </svg>
              <span className="font-medium text-gray-700">
                {overview?.open_incidents ?? 0}
              </span>{" "}
              incidents
            </span>
            <span className="flex items-center gap-1">
              <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
              <span className="font-medium text-gray-700">
                {overview?.active_operators ?? 0}
              </span>{" "}
              operators
            </span>
            {shiftTimer && (
              <span className="flex items-center gap-1 text-brand-600 font-medium">
                <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                {shiftTimer}
              </span>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Mobile sidebar toggles */}
          <button
            onClick={() => setLeftOpen((o) => !o)}
            className="lg:hidden rounded p-1.5 text-gray-500 hover:bg-gray-100"
            title="Toggle incidents"
          >
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h7" />
            </svg>
          </button>
          <button
            onClick={() => setRightOpen((o) => !o)}
            className="lg:hidden rounded p-1.5 text-gray-500 hover:bg-gray-100"
            title="Toggle timeline"
          >
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </button>
          <LayoutSelector value={layout} onChange={handleLayoutChange} />
        </div>
      </div>

      {/* ===== MAIN CONTENT: 3-column ===== */}
      <div className="flex flex-1 overflow-hidden relative">
        {/* LEFT SIDEBAR */}
        <aside
          className={`
            ${leftOpen ? "translate-x-0" : "-translate-x-full"}
            lg:translate-x-0
            fixed lg:static inset-y-0 left-0 z-40 lg:z-auto
            w-[280px] flex-shrink-0 bg-white border-r border-gray-200
            flex flex-col overflow-hidden
            transition-transform duration-200
          `}
        >
          {/* Mobile close */}
          <button
            onClick={() => setLeftOpen(false)}
            className="lg:hidden absolute top-2 right-2 rounded p-1 text-gray-400 hover:bg-gray-100 z-10"
          >
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>

          {/* Incident Queue */}
          <div className="flex-1 overflow-hidden flex flex-col">
            <IncidentSidebar incidents={incidents} onRefresh={fetchAll} />
          </div>

          {/* Stream List */}
          <div className="border-t border-gray-200">
            <div className="px-3 py-2">
              <h3 className="text-sm font-semibold text-gray-900 mb-2">
                Streams ({streams.length})
              </h3>
              <div className="space-y-1 max-h-32 overflow-y-auto">
                {streams.map((s) => (
                  <div
                    key={s.id}
                    className="flex items-center gap-2 rounded px-2 py-1 text-xs hover:bg-gray-50 cursor-pointer"
                  >
                    <span
                      className={`h-2 w-2 rounded-full flex-shrink-0 ${
                        s.status === "online"
                          ? "bg-green-500"
                          : s.status === "degraded"
                          ? "bg-yellow-500"
                          : "bg-gray-400"
                      }`}
                    />
                    <span className="truncate text-gray-700">{s.name}</span>
                  </div>
                ))}
                {streams.length === 0 && (
                  <p className="text-xs text-gray-400 py-1">No streams connected</p>
                )}
              </div>
            </div>
          </div>

          {/* Quick Actions */}
          <div className="border-t border-gray-200 p-3 space-y-1.5">
            <button
              onClick={() => setShowAddStream(true)}
              className="w-full rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50 transition-colors text-left"
            >
              + Add Stream
            </button>
            <OperatorPanel
              currentShift={currentShift}
              onShiftChange={fetchAll}
            />
          </div>
        </aside>

        {/* Overlay backdrop for mobile left sidebar */}
        {leftOpen && (
          <div
            className="fixed inset-0 bg-black/30 z-30 lg:hidden"
            onClick={() => setLeftOpen(false)}
          />
        )}

        {/* CENTER: VIDEO WALL */}
        <main className="flex-1 bg-gray-950 p-1 overflow-hidden">
          <VideoWall
            layout={layout}
            streams={streams}
            onRemoveStream={handleRemoveStream}
            onAddStream={() => setShowAddStream(true)}
          />
        </main>

        {/* RIGHT SIDEBAR */}
        <aside
          className={`
            ${rightOpen ? "translate-x-0" : "translate-x-full"}
            lg:translate-x-0
            fixed lg:static inset-y-0 right-0 z-40 lg:z-auto
            w-[300px] flex-shrink-0 bg-white border-l border-gray-200
            flex flex-col overflow-hidden
            transition-transform duration-200
          `}
        >
          {/* Mobile close */}
          <button
            onClick={() => setRightOpen(false)}
            className="lg:hidden absolute top-2 left-2 rounded p-1 text-gray-400 hover:bg-gray-100 z-10"
          >
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>

          {/* Live Copilot mini-panel */}
          <div className="border-b border-gray-200 p-3">
            <h3 className="text-sm font-semibold text-gray-900 mb-2">
              Copilot
            </h3>
            <div className="space-y-1.5 mb-2 max-h-24 overflow-y-auto">
              {copilotResponses.length === 0 && (
                <p className="text-xs text-gray-400">Ask the copilot anything...</p>
              )}
              {copilotResponses.map((r, i) => (
                <div
                  key={i}
                  className="rounded bg-gray-50 px-2 py-1.5 text-xs text-gray-600"
                >
                  {r}
                </div>
              ))}
            </div>
            <div className="flex gap-1.5">
              <input
                type="text"
                value={copilotInput}
                onChange={(e) => setCopilotInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleCopilotSend()}
                placeholder="Ask copilot..."
                className="flex-1 rounded border border-gray-300 px-2 py-1 text-xs placeholder-gray-400 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
              />
              <button
                onClick={handleCopilotSend}
                className="rounded bg-brand-600 px-2 py-1 text-xs font-medium text-white hover:bg-brand-700"
              >
                Send
              </button>
            </div>
          </div>

          {/* Timeline Feed */}
          <div className="flex-1 overflow-hidden flex flex-col">
            <TimelineFeed events={timeline} />
          </div>

          {/* KPIs */}
          <div className="border-t border-gray-200">
            <KPICards kpis={kpis} />
          </div>
        </aside>

        {/* Overlay backdrop for mobile right sidebar */}
        {rightOpen && (
          <div
            className="fixed inset-0 bg-black/30 z-30 lg:hidden"
            onClick={() => setRightOpen(false)}
          />
        )}
      </div>

      {/* Add Stream Modal */}
      <AddStreamModal
        isOpen={showAddStream}
        onClose={() => setShowAddStream(false)}
        onStreamAdded={fetchAll}
      />
    </div>
  );
}
