"use client";

import React, { useState } from "react";
import Button from "@/components/ui/Button";
import Badge from "@/components/ui/Badge";
import { TimelineEventData } from "./TimelineEvent";

interface EvidencePanelProps {
  event: TimelineEventData | null;
  onAddNote: (content: string) => void;
  onPinToCase: (eventId: string) => void;
  notes: TimelineEventData[];
}

export default function EvidencePanel({
  event,
  onAddNote,
  onPinToCase,
  notes,
}: EvidencePanelProps) {
  const [noteText, setNoteText] = useState("");

  if (!event) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-center p-6">
        <div className="text-4xl mb-3 opacity-40">🔎</div>
        <p className="text-sm text-gray-500">Select an event from the timeline</p>
        <p className="text-xs text-gray-400 mt-1">
          Click on any event to view its details, media, and notes
        </p>
      </div>
    );
  }

  const payload = (event.payload || {}) as Record<string, string>;
  const hasAssets = event.linked_asset_ids.length > 0;

  const handleSubmitNote = () => {
    if (noteText.trim()) {
      onAddNote(noteText.trim());
      setNoteText("");
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="p-4 border-b border-gray-200">
        <div className="flex items-center justify-between mb-2">
          <Badge
            variant={
              event.type === "evidence"
                ? "success"
                : event.type === "alert"
                ? "warning"
                : event.type === "detection"
                ? "error"
                : "info"
            }
          >
            {event.type}
          </Badge>
          <span className="text-xs text-gray-500">
            {event.timestamp ? new Date(event.timestamp).toLocaleString() : ""}
          </span>
        </div>
        <h3 className="text-sm font-semibold text-gray-900">
          {payload.name || payload.content || payload.notes || `${event.type} event`}
        </h3>
      </div>

      {/* Content area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* Payload details */}
        <div>
          <h4 className="text-xs font-semibold text-gray-600 uppercase tracking-wider mb-2">
            Details
          </h4>
          <div className="bg-gray-50 rounded-lg p-3 space-y-1">
            {Object.entries(payload).map(([key, value]) => (
              <div key={key} className="flex justify-between text-sm">
                <span className="text-gray-500">{key}</span>
                <span className="text-gray-900 truncate ml-4 max-w-[60%] text-right">
                  {String(value)}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Media preview */}
        {hasAssets && (
          <div>
            <h4 className="text-xs font-semibold text-gray-600 uppercase tracking-wider mb-2">
              Linked Assets
            </h4>
            <div className="space-y-2">
              {event.linked_asset_ids.map((assetId) => (
                <div
                  key={assetId}
                  className="rounded-lg border border-gray-200 p-3 bg-gray-50"
                >
                  <div className="flex items-center gap-2">
                    <div className="w-16 h-16 bg-gray-200 rounded flex items-center justify-center text-gray-400 text-xs">
                      Preview
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-xs text-gray-500 truncate">
                        Asset: {assetId}
                      </p>
                      <div className="flex gap-2 mt-2">
                        <button className="text-xs text-brand-600 hover:text-brand-700">
                          View Full
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Pin to case button for unlinked events */}
        {!payload.case_id && (
          <Button
            variant="secondary"
            size="sm"
            onClick={() => onPinToCase(event.id)}
            className="w-full"
          >
            📌 Pin to Case
          </Button>
        )}

        {/* Notes section */}
        <div>
          <h4 className="text-xs font-semibold text-gray-600 uppercase tracking-wider mb-2">
            Notes ({notes.length})
          </h4>

          {notes.length > 0 && (
            <div className="space-y-2 mb-3">
              {notes.map((note) => {
                const notePayload = (note.payload || {}) as Record<string, string>;
                return (
                  <div
                    key={note.id}
                    className="bg-yellow-50 border border-yellow-200 rounded-lg p-3"
                  >
                    <p className="text-sm text-gray-800">
                      {notePayload.content}
                    </p>
                    <p className="text-xs text-gray-400 mt-1">
                      {note.timestamp
                        ? new Date(note.timestamp).toLocaleString()
                        : ""}
                    </p>
                  </div>
                );
              })}
            </div>
          )}

          {/* Add note */}
          <div className="flex gap-2">
            <input
              type="text"
              placeholder="Add a note..."
              value={noteText}
              onChange={(e) => setNoteText(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSubmitNote()}
              className="flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm placeholder-gray-400 focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
            />
            <Button size="sm" onClick={handleSubmitNote} disabled={!noteText.trim()}>
              Add
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
