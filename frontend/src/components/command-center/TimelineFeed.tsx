"use client";

import React, { useEffect, useRef } from "react";
import type { TimelineEvent } from "@/lib/api";

interface TimelineFeedProps {
  events: TimelineEvent[];
}

const typeIcons: Record<string, { icon: string; color: string }> = {
  alert: { icon: "!", color: "bg-red-500 text-white" },
  incident: { icon: "I", color: "bg-orange-500 text-white" },
  stream: { icon: "S", color: "bg-blue-500 text-white" },
  operator: { icon: "O", color: "bg-purple-500 text-white" },
  system: { icon: "G", color: "bg-gray-500 text-white" },
};

function formatTime(ts: string): string {
  const d = new Date(ts);
  return d.toLocaleTimeString(undefined, {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

export default function TimelineFeed({ events }: TimelineFeedProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = 0;
    }
  }, [events.length]);

  const sorted = [...events].sort(
    (a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
  );

  return (
    <div className="flex flex-col h-full">
      <div className="px-3 py-2 border-b border-gray-200">
        <h3 className="text-sm font-semibold text-gray-900">Timeline</h3>
      </div>
      <div ref={scrollRef} className="flex-1 overflow-y-auto">
        {sorted.length === 0 && (
          <div className="flex flex-col items-center justify-center py-8 text-gray-400">
            <span className="text-sm">No recent events</span>
          </div>
        )}
        {sorted.map((event) => {
          const cfg = typeIcons[event.type] || typeIcons.system;
          return (
            <div
              key={event.id}
              className="flex items-start gap-2.5 px-3 py-2 border-b border-gray-50 hover:bg-gray-50 transition-colors"
            >
              <span
                className={`flex-shrink-0 mt-0.5 flex h-5 w-5 items-center justify-center rounded-full text-[10px] font-bold ${cfg.color}`}
              >
                {cfg.icon}
              </span>
              <div className="flex-1 min-w-0">
                <p className="text-xs text-gray-800 leading-relaxed">
                  {event.description}
                </p>
                <p className="text-[10px] text-gray-400 mt-0.5 font-mono">
                  {formatTime(event.timestamp)}
                </p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
