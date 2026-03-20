"use client";

import React from "react";
import Badge from "@/components/ui/Badge";

export interface TimelineEventData {
  id: string;
  type: string;
  timestamp: string | null;
  source: string;
  payload: Record<string, unknown> | null;
  linked_asset_ids: string[];
  workspace_id: string;
}

interface TimelineEventProps {
  event: TimelineEventData;
  isSelected: boolean;
  onClick: (event: TimelineEventData) => void;
}

const typeConfig: Record<string, { icon: string; badge: "info" | "warning" | "error" | "success" | "neutral" }> = {
  case: { icon: "📁", badge: "info" },
  evidence: { icon: "🔍", badge: "success" },
  note: { icon: "📝", badge: "neutral" },
  alert: { icon: "⚠️", badge: "warning" },
  detection: { icon: "🎯", badge: "error" },
};

export default function TimelineEvent({ event, isSelected, onClick }: TimelineEventProps) {
  const config = typeConfig[event.type] || { icon: "📌", badge: "neutral" as const };
  const description =
    (event.payload as Record<string, string>)?.name ||
    (event.payload as Record<string, string>)?.content ||
    (event.payload as Record<string, string>)?.notes ||
    event.type;

  const formattedTime = event.timestamp
    ? new Date(event.timestamp).toLocaleString()
    : "Unknown time";

  return (
    <div
      onClick={() => onClick(event)}
      className={`relative flex gap-4 p-4 rounded-lg border cursor-pointer transition-all hover:shadow-md ${
        isSelected
          ? "border-brand-500 bg-brand-50 shadow-sm"
          : "border-gray-200 bg-white hover:border-gray-300"
      }`}
    >
      {/* Timeline dot */}
      <div className="flex-shrink-0 flex flex-col items-center">
        <div className="w-10 h-10 rounded-full bg-gray-100 flex items-center justify-center text-lg">
          {config.icon}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <Badge variant={config.badge}>{event.type}</Badge>
          <span className="text-xs text-gray-500">{formattedTime}</span>
        </div>
        <p className="text-sm text-gray-900 truncate">{description}</p>
        {event.linked_asset_ids.length > 0 && (
          <p className="text-xs text-gray-400 mt-1">
            {event.linked_asset_ids.length} linked asset(s)
          </p>
        )}
      </div>
    </div>
  );
}
