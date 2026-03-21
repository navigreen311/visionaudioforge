"use client";

import React, { useState, useCallback } from "react";
import Button from "@/components/ui/Button";
import Badge from "@/components/ui/Badge";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface CaseEvent {
  id: string;
  type: "camera" | "audio" | "alert" | "note" | "detection" | "evidence";
  summary: string;
  timestamp: string;
  source: string;
  thumbnailUrl?: string;
  mediaUrl?: string;
  mimeType?: string;
  fileSize?: number;
  notes?: string;
}

interface EvidenceTabProps {
  caseId: string;
  events: CaseEvent[];
  onRemove?: (eventId: string) => void;
  onOpenInModule?: (event: CaseEvent) => void;
  onExport?: (event: CaseEvent) => void;
  onNotesChange?: (eventId: string, notes: string) => void;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const typeIcons: Record<CaseEvent["type"], string> = {
  camera: "\uD83D\uDCF7",
  audio: "\uD83C\uDFA4",
  alert: "\u26A0\uFE0F",
  note: "\uD83D\uDCDD",
  detection: "\uD83C\uDFAF",
  evidence: "\uD83D\uDD0D",
};

const typeBadgeVariant: Record<CaseEvent["type"], string> = {
  camera: "info",
  audio: "success",
  alert: "warning",
  note: "neutral",
  detection: "error",
  evidence: "info",
};

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function isImageMime(mime?: string): boolean {
  return !!mime && mime.startsWith("image/");
}

function isVideoMime(mime?: string): boolean {
  return !!mime && mime.startsWith("video/");
}

function isAudioMime(mime?: string): boolean {
  return !!mime && mime.startsWith("audio/");
}

// ---------------------------------------------------------------------------
// Evidence Item Row
// ---------------------------------------------------------------------------

interface EvidenceItemRowProps {
  event: CaseEvent;
  isSelected: boolean;
  onSelect: (event: CaseEvent) => void;
  onRemove: (id: string) => void;
}

function EvidenceItemRow({ event, isSelected, onSelect, onRemove }: EvidenceItemRowProps) {
  return (
    <div
      onClick={() => onSelect(event)}
      className={`flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-all hover:shadow-sm ${
        isSelected
          ? "border-brand-500 bg-brand-50 shadow-sm"
          : "border-gray-200 bg-white hover:border-gray-300"
      }`}
    >
      {/* Type icon */}
      <div className="w-10 h-10 rounded-lg bg-gray-100 flex items-center justify-center text-lg flex-shrink-0">
        {typeIcons[event.type]}
      </div>

      {/* Thumbnail */}
      {event.thumbnailUrl && (isImageMime(event.mimeType) || isVideoMime(event.mimeType)) ? (
        <div className="w-12 h-12 rounded bg-gray-200 flex-shrink-0 overflow-hidden">
          <img
            src={event.thumbnailUrl}
            alt={event.summary}
            className="w-full h-full object-cover"
          />
        </div>
      ) : null}

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-0.5">
          <Badge variant={typeBadgeVariant[event.type]}>{event.type}</Badge>
          <span className="text-xs text-gray-400">
            {new Date(event.timestamp).toLocaleString()}
          </span>
        </div>
        <p className="text-sm text-gray-900 truncate">{event.summary}</p>
      </div>

      {/* Remove */}
      <button
        onClick={(e) => {
          e.stopPropagation();
          onRemove(event.id);
        }}
        className="flex-shrink-0 p-1 rounded text-gray-400 hover:text-red-500 hover:bg-red-50 transition-colors"
        title="Remove evidence"
      >
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
        </svg>
      </button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Full-Size Preview Panel
// ---------------------------------------------------------------------------

interface PreviewPanelProps {
  event: CaseEvent;
  notes: string;
  onNotesChange: (notes: string) => void;
  onOpenInModule: () => void;
  onExport: () => void;
  onClose: () => void;
}

function PreviewPanel({
  event,
  notes,
  onNotesChange,
  onOpenInModule,
  onExport,
  onClose,
}: PreviewPanelProps) {
  return (
    <div className="flex flex-col h-full">
      {/* Preview header */}
      <div className="flex items-center justify-between p-3 border-b border-gray-200">
        <div className="flex items-center gap-2">
          <span className="text-lg">{typeIcons[event.type]}</span>
          <h3 className="text-sm font-semibold text-gray-900 truncate">{event.summary}</h3>
        </div>
        <button
          onClick={onClose}
          className="p-1 rounded text-gray-400 hover:text-gray-600 hover:bg-gray-100"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      {/* Media preview */}
      <div className="flex-shrink-0">
        {isImageMime(event.mimeType) && event.mediaUrl ? (
          <div className="bg-black flex items-center justify-center max-h-64">
            <img
              src={event.mediaUrl}
              alt={event.summary}
              className="max-w-full max-h-64 object-contain"
            />
          </div>
        ) : isVideoMime(event.mimeType) && event.mediaUrl ? (
          <div className="bg-black">
            <video
              src={event.mediaUrl}
              controls
              className="w-full max-h-64"
              preload="metadata"
            >
              Your browser does not support the video element.
            </video>
          </div>
        ) : isAudioMime(event.mimeType) && event.mediaUrl ? (
          <div className="bg-gray-50 p-4">
            <audio src={event.mediaUrl} controls className="w-full" preload="metadata">
              Your browser does not support the audio element.
            </audio>
          </div>
        ) : (
          <div className="bg-gray-100 h-32 flex items-center justify-center">
            <span className="text-gray-400 text-sm">No media preview available</span>
          </div>
        )}
      </div>

      {/* Metadata + Notes */}
      <div className="flex-1 overflow-y-auto p-3 space-y-4">
        {/* Metadata */}
        <div>
          <h4 className="text-xs font-semibold text-gray-600 uppercase tracking-wider mb-2">
            Metadata
          </h4>
          <div className="bg-gray-50 rounded-lg p-3 space-y-1.5 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-500">Source</span>
              <span className="text-gray-900">{event.source}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Timestamp</span>
              <span className="text-gray-900">
                {new Date(event.timestamp).toLocaleString()}
              </span>
            </div>
            {event.fileSize !== undefined && (
              <div className="flex justify-between">
                <span className="text-gray-500">File Size</span>
                <span className="text-gray-900">{formatFileSize(event.fileSize)}</span>
              </div>
            )}
            {event.mimeType && (
              <div className="flex justify-between">
                <span className="text-gray-500">Type</span>
                <span className="text-gray-900">{event.mimeType}</span>
              </div>
            )}
          </div>
        </div>

        {/* Editable notes */}
        <div>
          <h4 className="text-xs font-semibold text-gray-600 uppercase tracking-wider mb-2">
            Notes
          </h4>
          <textarea
            value={notes}
            onChange={(e) => onNotesChange(e.target.value)}
            placeholder="Add investigation notes..."
            rows={4}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm placeholder-gray-400 focus:ring-2 focus:ring-brand-500 focus:border-brand-500 resize-none"
          />
        </div>

        {/* Action buttons */}
        <div className="flex gap-2">
          <Button size="sm" variant="secondary" onClick={onOpenInModule} className="flex-1">
            Open in Module
          </Button>
          <Button size="sm" variant="secondary" onClick={onExport} className="flex-1">
            Export
          </Button>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main EvidenceTab component
// ---------------------------------------------------------------------------

export default function EvidenceTab({
  caseId,
  events,
  onRemove,
  onOpenInModule,
  onExport,
  onNotesChange,
}: EvidenceTabProps) {
  const [selectedEvent, setSelectedEvent] = useState<CaseEvent | null>(null);
  const [editedNotes, setEditedNotes] = useState<Record<string, string>>({});

  const handleSelect = useCallback((event: CaseEvent) => {
    setSelectedEvent(event);
    if (editedNotes[event.id] === undefined && event.notes) {
      setEditedNotes((prev) => ({ ...prev, [event.id]: event.notes ?? "" }));
    }
  }, [editedNotes]);

  const handleNotesUpdate = useCallback(
    (notes: string) => {
      if (!selectedEvent) return;
      setEditedNotes((prev) => ({ ...prev, [selectedEvent.id]: notes }));
      onNotesChange?.(selectedEvent.id, notes);
    },
    [selectedEvent, onNotesChange]
  );

  const handleRemove = useCallback(
    (eventId: string) => {
      onRemove?.(eventId);
      if (selectedEvent?.id === eventId) {
        setSelectedEvent(null);
      }
    },
    [onRemove, selectedEvent]
  );

  if (events.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-center p-6">
        <div className="text-4xl mb-3 opacity-40">{"\uD83D\uDCC1"}</div>
        <p className="text-sm text-gray-500">No evidence for this case</p>
        <p className="text-xs text-gray-400 mt-1">
          Pin events from the timeline to add evidence (Case {caseId})
        </p>
      </div>
    );
  }

  // Show preview panel when an item is selected
  if (selectedEvent) {
    return (
      <PreviewPanel
        event={selectedEvent}
        notes={editedNotes[selectedEvent.id] ?? selectedEvent.notes ?? ""}
        onNotesChange={handleNotesUpdate}
        onOpenInModule={() => onOpenInModule?.(selectedEvent)}
        onExport={() => onExport?.(selectedEvent)}
        onClose={() => setSelectedEvent(null)}
      />
    );
  }

  // Evidence list view
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wider">
          Evidence ({events.length})
        </h3>
      </div>
      {events.map((event) => (
        <EvidenceItemRow
          key={event.id}
          event={event}
          isSelected={false}
          onSelect={handleSelect}
          onRemove={handleRemove}
        />
      ))}
    </div>
  );
}
