"use client";

import { API_BASE_URL } from "@/lib/api";
import { readWorkspaceId } from "@/lib/session";

import React, { useState, useCallback, useEffect } from "react";
import CaseList, { CaseData } from "@/components/investigate/CaseList";
import EventTimeline from "@/components/investigate/EventTimeline";
import EvidencePanel from "@/components/investigate/EvidencePanel";
import ReportTab from "@/components/investigate/ReportTab";
import type { Comment as ReportComment, Approval as ReportApproval } from "@/components/investigate/ReportTab";
import Modal from "@/components/ui/Modal";
import Button from "@/components/ui/Button";
import Badge from "@/components/ui/Badge";
import { TimelineEventData } from "@/components/investigate/TimelineEvent";
import axios from "axios";

const API_BASE = API_BASE_URL;

function getDefaultDateRange() {
  const end = new Date();
  const start = new Date();
  start.setDate(start.getDate() - 30);

  const fmt = (d: Date) => d.toISOString().slice(0, 16);
  return { start: fmt(start), end: fmt(end) };
}

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface Comment {
  id: string;
  user_id: string;
  content: string;
  parent_id: string | null;
  timestamp: string;
  replies: Comment[];
}

interface ApprovalItem {
  id: string;
  case_id: string;
  requester_id: string;
  approver_id: string;
  reason: string;
  timestamp: string;
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function CommentThread({ comment, onReply }: { comment: Comment; onReply: (parentId: string) => void }) {
  return (
    <div className="border-l-2 border-gray-200 pl-3 mb-2">
      <div className="bg-white rounded-lg border border-gray-100 p-3">
        <div className="flex items-center gap-2 mb-1">
          <div className="w-6 h-6 rounded-full bg-brand-100 text-brand-700 flex items-center justify-center text-xs font-semibold">
            {comment.user_id.charAt(0).toUpperCase()}
          </div>
          <span className="text-xs font-medium text-gray-700">{comment.user_id}</span>
          <span className="text-xs text-gray-400">
            {comment.timestamp ? new Date(comment.timestamp).toLocaleString() : ""}
          </span>
        </div>
        <p className="text-sm text-gray-800 ml-8">{comment.content}</p>
        <button
          onClick={() => onReply(comment.id)}
          className="text-xs text-brand-600 hover:text-brand-700 ml-8 mt-1"
        >
          Reply
        </button>
      </div>
      {comment.replies.length > 0 && (
        <div className="ml-4 mt-1">
          {comment.replies.map((reply) => (
            <CommentThread key={reply.id} comment={reply} onReply={onReply} />
          ))}
        </div>
      )}
    </div>
  );
}

function CommentsSection({ caseId }: { caseId: string }) {
  const [comments, setComments] = useState<Comment[]>([]);
  const [newComment, setNewComment] = useState("");
  const [replyTo, setReplyTo] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const loadComments = useCallback(async () => {
    try {
      const resp = await axios.get(`${API_BASE}/api/investigate/cases/${caseId}/comments`);
      setComments(resp.data);
    } catch {
      setComments([]);
    }
  }, [caseId]);

  useEffect(() => {
    loadComments();
  }, [loadComments]);

  const handleSubmit = async () => {
    if (!newComment.trim()) return;
    setLoading(true);
    try {
      await axios.post(`${API_BASE}/api/investigate/cases/${caseId}/comments`, {
        user_id: "current-user",
        content: newComment.trim(),
        parent_id: replyTo,
      });
      setNewComment("");
      setReplyTo(null);
      await loadComments();
    } catch {
      // Handle silently
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-3">
      <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wider">
        Comments ({comments.length})
      </h3>
      <div className="space-y-1 max-h-64 overflow-y-auto">
        {comments.map((c) => (
          <CommentThread key={c.id} comment={c} onReply={(id) => setReplyTo(id)} />
        ))}
        {comments.length === 0 && (
          <p className="text-xs text-gray-400">No comments yet.</p>
        )}
      </div>
      {replyTo && (
        <div className="flex items-center gap-2 text-xs text-brand-600">
          <span>Replying to thread</span>
          <button onClick={() => setReplyTo(null)} className="text-gray-400 hover:text-gray-600">
            Cancel
          </button>
        </div>
      )}
      <div className="flex gap-2">
        <input
          type="text"
          placeholder={replyTo ? "Write a reply..." : "Add a comment..."}
          value={newComment}
          onChange={(e) => setNewComment(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
          className="flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm placeholder-gray-400 focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
        />
        <Button size="sm" onClick={handleSubmit} disabled={!newComment.trim()} loading={loading}>
          Post
        </Button>
      </div>
    </div>
  );
}

function ApprovalSection({ caseId }: { caseId: string }) {
  const [approvals, setApprovals] = useState<ApprovalItem[]>([]);
  const [showRequest, setShowRequest] = useState(false);
  const [approverId, setApproverId] = useState("");
  const [reason, setReason] = useState("");

  const loadApprovals = useCallback(async () => {
    try {
      const resp = await axios.get(`${API_BASE}/api/investigate/approvals`, {
        params: { workspace_id: readWorkspaceId() },
      });
      setApprovals(resp.data.filter((a: ApprovalItem) => a.case_id === caseId));
    } catch {
      setApprovals([]);
    }
  }, [caseId]);

  useEffect(() => {
    loadApprovals();
  }, [loadApprovals]);

  const handleRequestApproval = async () => {
    if (!approverId.trim() || !reason.trim()) return;
    try {
      await axios.post(`${API_BASE}/api/investigate/cases/${caseId}/approval`, {
        user_id: "current-user",
        approver_id: approverId.trim(),
        reason: reason.trim(),
      });
      setShowRequest(false);
      setApproverId("");
      setReason("");
      await loadApprovals();
    } catch {
      // Handle silently
    }
  };

  const handleProcess = async (approvalId: string, decision: string) => {
    try {
      await axios.post(`${API_BASE}/api/investigate/approvals/${approvalId}/process`, {
        user_id: "current-user",
        decision,
      });
      await loadApprovals();
    } catch {
      // Handle silently
    }
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wider">
          Approvals
          {approvals.length > 0 && (
            <Badge variant="warning" className="ml-2">{approvals.length} pending</Badge>
          )}
        </h3>
        <Button size="sm" variant="secondary" onClick={() => setShowRequest(!showRequest)}>
          Request Approval
        </Button>
      </div>

      {showRequest && (
        <div className="bg-gray-50 rounded-lg p-3 space-y-2">
          <input
            type="text"
            placeholder="Approver ID"
            value={approverId}
            onChange={(e) => setApproverId(e.target.value)}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
          />
          <input
            type="text"
            placeholder="Reason for approval"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
          />
          <Button size="sm" onClick={handleRequestApproval}>Submit Request</Button>
        </div>
      )}

      {approvals.map((a) => (
        <div key={a.id} className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-800">{a.reason}</p>
              <p className="text-xs text-gray-500">
                From {a.requester_id} to {a.approver_id}
              </p>
            </div>
            <div className="flex gap-2">
              <Button size="sm" onClick={() => handleProcess(a.id, "approved")}>
                Approve
              </Button>
              <Button size="sm" variant="secondary" onClick={() => handleProcess(a.id, "rejected")}>
                Reject
              </Button>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

// ReportTab is now imported from @/components/investigate/ReportTab

function SyncedPlaybackPanel() {
  const [currentTime, setCurrentTime] = useState(0);
  const [duration] = useState(120);

  const formatTime = (s: number) => {
    const m = Math.floor(s / 60);
    const sec = Math.floor(s % 60);
    return `${m}:${sec.toString().padStart(2, "0")}`;
  };

  return (
    <div className="space-y-3">
      <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wider">
        Synced Playback
      </h3>

      {/* Video player placeholder */}
      <div className="bg-black rounded-lg aspect-video flex items-center justify-center">
        <span className="text-gray-400 text-sm">Video Player</span>
      </div>

      {/* Audio waveform placeholder */}
      <div className="bg-gray-100 rounded-lg h-16 flex items-center justify-center">
        <span className="text-gray-400 text-xs">Audio Waveform</span>
      </div>

      {/* Timeline scrubber */}
      <div className="flex items-center gap-3">
        <span className="text-xs text-gray-500 w-10">{formatTime(currentTime)}</span>
        <input
          type="range"
          min={0}
          max={duration}
          value={currentTime}
          onChange={(e) => setCurrentTime(Number(e.target.value))}
          className="flex-1"
        />
        <span className="text-xs text-gray-500 w-10">{formatTime(duration)}</span>
      </div>

      {/* Transcript scroll area */}
      <div className="bg-gray-50 rounded-lg p-3 h-32 overflow-y-auto">
        <h4 className="text-xs font-semibold text-gray-600 mb-2">Transcript</h4>
        <p className="text-xs text-gray-400">
          Transcript segments will appear here, synced to the current playback timestamp at {formatTime(currentTime)}.
        </p>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

type TabKey = "evidence" | "comments" | "approvals" | "report" | "playback";

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

  // Right panel tab
  const [activeTab, setActiveTab] = useState<TabKey>("evidence");

  // Report tab data
  const [reportComments, setReportComments] = useState<ReportComment[]>([]);
  const [reportApprovals, setReportApprovals] = useState<ReportApproval[]>([]);

  // Load comments for report
  const loadReportComments = useCallback(async (caseId: string) => {
    try {
      const resp = await axios.get(`${API_BASE}/api/investigate/cases/${caseId}/comments`);
      setReportComments(resp.data);
    } catch {
      setReportComments([]);
    }
  }, []);

  // Load approvals for report
  const loadReportApprovals = useCallback(async (caseId: string) => {
    try {
      const resp = await axios.get(`${API_BASE}/api/investigate/approvals`, {
        params: { workspace_id: readWorkspaceId() },
      });
      const filtered = (resp.data as ReportApproval[]).filter((a) => a.case_id === caseId);
      setReportApprovals(filtered);
    } catch {
      setReportApprovals([]);
    }
  }, []);

  // Load cases
  const loadCases = useCallback(async () => {
    setCasesLoading(true);
    try {
      const resp = await axios.get(`${API_BASE}/api/investigate/cases`, {
        params: { workspace_id: readWorkspaceId() },
      });
      setCases(resp.data);
    } catch {
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
          workspace_id: readWorkspaceId(),
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
      loadReportComments(selectedCase.id);
      loadReportApprovals(selectedCase.id);
    }
  }, [selectedCase, loadTimeline, loadReportComments, loadReportApprovals]);

  // Create case
  const handleCreateCase = async () => {
    if (!newCaseName.trim()) return;
    setCreating(true);
    try {
      await axios.post(`${API_BASE}/api/investigate/cases`, {
        name: newCaseName.trim(),
        description: newCaseDesc.trim(),
        workspace_id: readWorkspaceId(),
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
    setActiveTab("evidence");
  };

  // Filter notes for selected event
  const eventNotes = selectedEvent
    ? notes.filter(
        (n) =>
          (n.payload as Record<string, string>)?.case_id ===
          (selectedEvent.payload as Record<string, string>)?.case_id
      )
    : [];

  // Filter checkpoint events for timeline markers
  const checkpoints = events.filter((e) => e.type === "checkpoint");

  const tabs: { key: TabKey; label: string }[] = [
    { key: "evidence", label: "Evidence" },
    { key: "playback", label: "Playback" },
    { key: "comments", label: "Comments" },
    { key: "approvals", label: "Approvals" },
    { key: "report", label: "Report" },
  ];

  return (
    <div className="flex h-[calc(100vh-4rem)] overflow-hidden">
      {/* Left panel — Case list */}
      <div className="w-80 flex-shrink-0 border-r border-gray-200 bg-white">
        <CaseList
          cases={cases}
          selectedId={selectedCase?.id || null}
          onSelect={(c) => {
            setSelectedCase(c);
            setSelectedEvent(null);
          }}
          onNewCase={() => setShowNewCase(true)}
          loading={casesLoading}
        />
      </div>

      {/* Center — Timeline */}
      <div className="flex-1 min-w-0 bg-gray-50">
        {/* Checkpoint markers */}
        {checkpoints.length > 0 && (
          <div className="px-4 py-2 bg-blue-50 border-b border-blue-100 flex items-center gap-2 overflow-x-auto">
            <span className="text-xs font-semibold text-blue-700 flex-shrink-0">Checkpoints:</span>
            {checkpoints.map((cp) => {
              const cpPayload = cp.payload as Record<string, string>;
              return (
                <Badge key={cp.id} variant="info" className="flex-shrink-0">
                  {cpPayload?.title || "Checkpoint"}
                </Badge>
              );
            })}
          </div>
        )}
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

      {/* Right panel — Tabbed detail area */}
      <div className="w-96 flex-shrink-0 border-l border-gray-200 bg-white flex flex-col">
        {/* Tab navigation */}
        <div className="flex border-b border-gray-200">
          {tabs.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`flex-1 py-2 text-xs font-medium text-center transition-colors ${
                activeTab === tab.key
                  ? "text-brand-600 border-b-2 border-brand-500 bg-brand-50"
                  : "text-gray-500 hover:text-gray-700 hover:bg-gray-50"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Tab content */}
        <div className="flex-1 overflow-y-auto p-4">
          {activeTab === "evidence" && (
            <EvidencePanel
              event={selectedEvent}
              onAddNote={handleAddNote}
              onPinToCase={handlePinToCase}
              notes={eventNotes}
            />
          )}

          {activeTab === "playback" && <SyncedPlaybackPanel />}

          {activeTab === "comments" && selectedCase && (
            <CommentsSection caseId={selectedCase.id} />
          )}
          {activeTab === "comments" && !selectedCase && (
            <p className="text-sm text-gray-400 text-center mt-8">
              Select a case to view comments.
            </p>
          )}

          {activeTab === "approvals" && selectedCase && (
            <ApprovalSection caseId={selectedCase.id} />
          )}
          {activeTab === "approvals" && !selectedCase && (
            <p className="text-sm text-gray-400 text-center mt-8">
              Select a case to manage approvals.
            </p>
          )}

          {activeTab === "report" && selectedCase && (
            <ReportTab
              caseId={selectedCase.id}
              caseData={selectedCase}
              events={events}
              comments={reportComments}
              approvals={reportApprovals}
            />
          )}
          {activeTab === "report" && !selectedCase && (
            <p className="text-sm text-gray-400 text-center mt-8">
              Select a case to generate a report.
            </p>
          )}
        </div>
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
