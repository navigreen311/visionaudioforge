"use client";

import React, { useState } from "react";
import TimelineEvent, { TimelineEventData } from "./TimelineEvent";

interface EventTimelineProps {
  events: TimelineEventData[];
  selectedEventId: string | null;
  onSelectEvent: (event: TimelineEventData) => void;
  startDate: string;
  endDate: string;
  onStartDateChange: (date: string) => void;
  onEndDateChange: (date: string) => void;
  onRefresh: () => void;
}

export default function EventTimeline({
  events,
  selectedEventId,
  onSelectEvent,
  startDate,
  endDate,
  onStartDateChange,
  onEndDateChange,
  onRefresh,
}: EventTimelineProps) {
  const [zoomLevel, setZoomLevel] = useState(1);

  const zoomIn = () => setZoomLevel((z) => Math.min(z + 0.25, 3));
  const zoomOut = () => setZoomLevel((z) => Math.max(z - 0.25, 0.5));

  return (
    <div className="flex flex-col h-full">
      {/* Time range filter bar */}
      <div className="flex items-center gap-3 p-4 border-b border-gray-200 bg-gray-50 flex-shrink-0">
        <label className="text-xs font-medium text-gray-600">From</label>
        <input
          type="datetime-local"
          value={startDate}
          onChange={(e) => onStartDateChange(e.target.value)}
          className="rounded border border-gray-300 px-2 py-1 text-sm focus:ring-brand-500 focus:border-brand-500"
        />
        <label className="text-xs font-medium text-gray-600">To</label>
        <input
          type="datetime-local"
          value={endDate}
          onChange={(e) => onEndDateChange(e.target.value)}
          className="rounded border border-gray-300 px-2 py-1 text-sm focus:ring-brand-500 focus:border-brand-500"
        />
        <button
          onClick={onRefresh}
          className="ml-2 rounded bg-brand-600 px-3 py-1 text-sm text-white hover:bg-brand-700 transition-colors"
        >
          Apply
        </button>

        <div className="ml-auto flex items-center gap-1">
          <button
            onClick={zoomOut}
            className="rounded border border-gray-300 px-2 py-1 text-sm hover:bg-gray-100"
            title="Zoom out"
          >
            -
          </button>
          <span className="text-xs text-gray-500 w-12 text-center">{Math.round(zoomLevel * 100)}%</span>
          <button
            onClick={zoomIn}
            className="rounded border border-gray-300 px-2 py-1 text-sm hover:bg-gray-100"
            title="Zoom in"
          >
            +
          </button>
        </div>
      </div>

      {/* Timeline events */}
      <div
        className="flex-1 overflow-y-auto p-4"
        style={{ fontSize: `${zoomLevel}rem` }}
      >
        {events.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <div className="text-4xl mb-3 opacity-40">📅</div>
            <p className="text-sm text-gray-500">No events in this time range</p>
            <p className="text-xs text-gray-400 mt-1">Adjust the date filters or add evidence to a case</p>
          </div>
        ) : (
          <div className="relative space-y-3">
            {/* Vertical line */}
            <div className="absolute left-9 top-0 bottom-0 w-px bg-gray-200" />
            {events.map((event) => (
              <TimelineEvent
                key={event.id}
                event={event}
                isSelected={event.id === selectedEventId}
                onClick={onSelectEvent}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
