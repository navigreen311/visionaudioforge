"use client";

import React, { useState, useCallback, useEffect } from "react";
import CaseList, { CaseData } from "@/components/investigate/CaseList";
import EventTimeline from "@/components/investigate/EventTimeline";
import EvidencePanel from "@/components/investigate/EvidencePanel";
import Modal from "@/components/ui/Modal";
import Button from "@/components/ui/Button";
import { TimelineEventData } from "@/components/investigate/TimelineEvent";
import axios from "axios";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const DEFAULT_WORKSPACE_ID = "00000000-0000-0000-0000-000000000001";

function getDefaultDateRange() {
  const end = new Date();
  const start = new Date();
  start.setDate(start.getDate() - 30);

  const fmt = (d: Date) => d.toISOString().slice(0, 16);
  return { start: fmt(start), end: fmt(end) };
}

export default function InvestigatePage() {
  // Case state
  const [cases, setCases] = useState<CaseData[]>([]);
  const [selectedCase, setSelectedCase] = useState<CaseData | null>(null);
  const [casesLoading, setCasesLoading] = useState(false);

  // Timeline state
  const [events, setEvents] = useState<TimelineEventData[]>([]);
  const [selectedEvent, setSelectedEvent] = useState<TimelineEventData | null>(null);
  const [notes, setNotes] = useState<TimelineEventData[]>([]);

  // Date range
  const defaultRange = getDefaultDateRange();
  const [startDate, setStartDate] = useState(defaultRange.start);
  const [endDate, setEndDate] = useState(defaultRange.end);

  // New case modal
  const [showNewCase, setShowNewCase] = useState(false);
  const [newCaseName, setNewCaseName] = useState("");
  const [newCaseDesc, setNewCaseDesc] = useState("");
  const [creating, setCreating] = useState(false);

  // Load cases
  const loadCases = useCallback(async () => {
    setCasesLoading(true);
    try {
      const resp = await axios.get(`${API_BASE}/api/investigate/cases`, {
        params: { workspace_id: DEFAULT_WORKSPACE_ID },
      });
      setCases(resp.data);
    } catch {
      // Fallback: empty list on error
      setCases([]);
    } finally {
      setCasesLoading(false);
    }
  }, []);

  // Load timeline for selected case
  const loadTimeline = useCallback(async () => {
    if (!selectedCase) {
      setEvents([]);
      return;
    }
    try {
      const resp = await axios.get(
        `${API_BASE}/api/investigate/cases/${selectedCase.id}`
      );
      const data = resp.data;
      setEvents(data.events || []);
      setNotes(data.notes || []);
    } catch {
      setEvents([]);
      setNotes([]);
    }
  }, [selectedCase]);

  // Load workspace-wide timeline
  const loadWorkspaceTimeline = useCallback(async () => {
    try {
      const resp = await axios.get(`${API_BASE}/api/investigate/timeline`, {
        params: {
          workspace_id: DEFAULT_WORKSPACE_ID,
          start: new Date(startDate).toISOString(),
          end: new Date(endDate).toISOString(),
        },
      });
      setEvents(resp.data);
    } catch {
      setEvents([]);
    }
  }, [startDate, endDate]);

  useEffect(() => {
    loadCases();
  }, [loadCases]);

  useEffect(() => {
    if (selectedCase) {
      loadTimeline();
    }
  }, [selectedCase, loadTimeline]);

  // Create case
  const handleCreateCase = async () => {
    if (!newCaseName.trim()) return;
    setCreating(true);
    try {
      await axios.post(`${API_BASE}/api/investigate/cases`, {
        name: newCaseName.trim(),
        description: newCaseDesc.trim(),
        workspace_id: DEFAULT_WORKSPACE_ID,
      });
      setShowNewCase(false);
      setNewCaseName("");
      setNewCaseDesc("");
      await loadCases();
    } catch {
      // Handle silently
    } finally {
      setCreating(false);
    }
  };

  // Add note
  const handleAddNote = async (content: string) => {
    if (!selectedCase) return;
    try {
      await axios.post(
        `${API_BASE}/api/investigate/cases/${selectedCase.id}/notes`,
        { user_id: "current-user", content }
      );
      await loadTimeline();
    } catch {
      // Handle silently
    }
  };

  // Pin event to case
  const handlePinToCase = async (eventId: string) => {
    if (!selectedCase) return;
    try {
      await axios.post(
        `${API_BASE}/api/investigate/cases/${selectedCase.id}/evidence`,
        {
          asset_id: eventId,
          notes: "Pinned from timeline",
        }
      );
      await loadTimeline();
    } catch {
      // Handle silently
    }
  };

  // Select event
  const handleSelectEvent = (event: TimelineEventData) => {
    setSelectedEvent(event);
  };

  // Filter notes for selected event
  const eventNotes = selectedEvent
    ? notes.filter(
        (n) =>
          (n.payload as Record<string, string>)?.case_id ===
          (selectedEvent.payload as Record<string, string>)?.case_id
      )
    : [];

  return (
    <div className="flex h-[calc(100vh-4rem)] overflow-hidden">
      {/* Left panel — Case list */}
      <div className="w-80 flex-shrink-0 border-r border-gray-200 bg-white">
        <CaseList
          cases={cases}
          selectedCaseId={selectedCase?.id || null}
          onSelectCase={(c) => {
            setSelectedCase(c);
            setSelectedEvent(null);
          }}
          onNewCase={() => setShowNewCase(true)}
          loading={casesLoading}
        />
      </div>

      {/* Center — Timeline */}
      <div className="flex-1 min-w-0 bg-gray-50">
        <EventTimeline
          events={events}
          selectedEventId={selectedEvent?.id || null}
          onSelectEvent={handleSelectEvent}
          startDate={startDate}
          endDate={endDate}
          onStartDateChange={setStartDate}
          onEndDateChange={setEndDate}
          onRefresh={selectedCase ? loadTimeline : loadWorkspaceTimeline}
        />
      </div>

      {/* Right panel — Evidence detail */}
      <div className="w-96 flex-shrink-0 border-l border-gray-200 bg-white">
        <EvidencePanel
          event={selectedEvent}
          onAddNote={handleAddNote}
          onPinToCase={handlePinToCase}
          notes={eventNotes}
        />
      </div>

      {/* New Case Modal */}
      <Modal
        isOpen={showNewCase}
        onClose={() => setShowNewCase(false)}
        title="Create New Case"
        footer={
          <>
            <Button variant="secondary" onClick={() => setShowNewCase(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleCreateCase}
              loading={creating}
              disabled={!newCaseName.trim()}
            >
              Create Case
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Case Name
            </label>
            <input
              type="text"
              value={newCaseName}
              onChange={(e) => setNewCaseName(e.target.value)}
              placeholder="e.g., Intrusion Investigation Alpha"
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm placeholder-gray-400 focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
              autoFocus
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Description
            </label>
            <textarea
              value={newCaseDesc}
              onChange={(e) => setNewCaseDesc(e.target.value)}
              placeholder="Describe the investigation scope and objectives..."
              rows={3}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm placeholder-gray-400 focus:ring-2 focus:ring-brand-500 focus:border-brand-500 resize-none"
            />
          </div>
        </div>
      </Modal>
    </div>
  );
}
