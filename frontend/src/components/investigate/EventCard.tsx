"use client";

import React from "react";
import Badge from "@/components/ui/Badge";
import type { CaseEvent } from "./CaseTimeline";

interface EventCardProps {
  event: CaseEvent;
}

const typeLabels: Record<string, string> = {
  alert: "Alert",
  detection: "Detection",
  capture_frame: "Capture Frame",
  audio_clip: "Audio Clip",
  uploaded_file: "Uploaded File",
  text_note: "Text Note",
  evidence: "Evidence",
  note: "Note",
};

const typeBadgeVariant: Record<string, "error" | "info" | "success" | "warning" | "neutral"> = {
  alert: "error",
  detection: "error",
  capture_frame: "info",
  audio_clip: "info",
  uploaded_file: "success",
  text_note: "warning",
  evidence: "success",
  note: "neutral",
};

function isMediaType(type: string): boolean {
  return ["capture_frame", "audio_clip", "uploaded_file", "evidence"].includes(type);
}

export default function EventCard({ event }: EventCardProps) {
  const displayType = event.evidence_type || event.type;
  const label = typeLabels[displayType] || displayType;
  const variant = typeBadgeVariant[displayType] || "neutral";
  const payload = (event.payload || {}) as Record<string, unknown>;

  const summary =
    (payload.notes as string) ||
    (payload.content as string) ||
    (payload.name as string) ||
    (payload.description as string) ||
    `${label} event`;

  const formattedTime = event.timestamp
    ? new Date(event.timestamp).toLocaleString()
    : "Unknown time";

  const hasMedia = isMediaType(displayType) && event.linked_asset_ids.length > 0;

  return (
    <div className="bg-white rounded-lg p-4 space-y-3">
      {/* Header row */}
      <div className="flex items-center gap-3">
        <Badge variant={variant}>{label}</Badge>
        <span className="text-xs text-gray-500">{formattedTime}</span>
        {event.severity && (
          <span className="text-xs text-gray-400 ml-auto">
            Severity: {event.severity}/5
          </span>
        )}
      </div>

      {/* Summary */}
      <p className="text-sm text-gray-800">{summary}</p>

      {/* Thumbnail placeholder for media types */}
      {hasMedia && (
        <div className="flex items-start gap-3">
          <div className="w-24 h-16 rounded bg-gray-100 flex items-center justify-center text-xs text-gray-400 border border-gray-200 flex-shrink-0">
            {displayType === "audio_clip" ? "Audio" : "Preview"}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-xs text-gray-500">
              {event.linked_asset_ids.length} linked asset(s)
            </p>
            <p className="text-xs text-gray-400 truncate mt-0.5">
              {event.linked_asset_ids[0]}
            </p>
          </div>
        </div>
      )}

      {/* Action links */}
      <div className="flex items-center gap-4 pt-1">
        {hasMedia && (
          <>
            <button className="text-xs font-medium text-brand-600 hover:text-brand-700 transition-colors">
              View Evidence
            </button>
            <button className="text-xs font-medium text-brand-600 hover:text-brand-700 transition-colors">
              Open in Playback
            </button>
          </>
        )}
        {!hasMedia && displayType !== "text_note" && displayType !== "note" && (
          <button className="text-xs font-medium text-brand-600 hover:text-brand-700 transition-colors">
            View Evidence
          </button>
        )}
      </div>
    </div>
  );
}
