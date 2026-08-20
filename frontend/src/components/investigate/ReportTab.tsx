"use client";

import { API_BASE_URL } from "@/lib/api";

import React, { useState, useCallback, useEffect } from "react";
import Button from "@/components/ui/Button";
import Badge from "@/components/ui/Badge";
import { CaseData } from "./CaseList";
import { TimelineEventData } from "./TimelineEvent";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface Comment {
  id: string;
  user_id: string;
  content: string;
  parent_id: string | null;
  timestamp: string;
  replies: Comment[];
}

export interface Approval {
  id: string;
  case_id: string;
  requester_id: string;
  approver_id: string;
  reason: string;
  status: string;
  decision_notes: string | null;
  timestamp: string;
}

interface ReportTabProps {
  caseId: string;
  caseData: CaseData;
  events: TimelineEventData[];
  comments: Comment[];
  approvals: Approval[];
}

type CaseEvent = TimelineEventData;

const API_BASE = API_BASE_URL;
const STORAGE_KEY_PREFIX = "vaf_report_draft_";

// ---------------------------------------------------------------------------
// localStorage helpers (SSR-safe)
// ---------------------------------------------------------------------------

function loadDraft(caseId: string): { findings: string; recommendations: string } {
  try {
    if (typeof window === "undefined") return { findings: "", recommendations: "" };
    const raw = localStorage.getItem(`${STORAGE_KEY_PREFIX}${caseId}`);
    if (!raw) return { findings: "", recommendations: "" };
    const parsed = JSON.parse(raw) as { findings?: string; recommendations?: string };
    return {
      findings: parsed.findings ?? "",
      recommendations: parsed.recommendations ?? "",
    };
  } catch {
    return { findings: "", recommendations: "" };
  }
}

function saveDraft(caseId: string, findings: string, recommendations: string): void {
  try {
    if (typeof window === "undefined") return;
    localStorage.setItem(
      `${STORAGE_KEY_PREFIX}${caseId}`,
      JSON.stringify({ findings, recommendations })
    );
  } catch {
    // Storage may be full or unavailable — fail silently
  }
}

// ---------------------------------------------------------------------------
// Section renderers
// ---------------------------------------------------------------------------

function CaseSummarySection({ caseData }: { caseData: CaseData }) {
  return (
    <div className="space-y-2">
      <h4 className="text-sm font-semibold text-gray-800">1. Case Summary</h4>
      <div className="bg-gray-50 rounded-lg p-3 space-y-1 text-sm">
        <div className="flex justify-between">
          <span className="text-gray-500">Title</span>
          <span className="text-gray-900 font-medium">{caseData.payload.name}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-500">Status</span>
          <Badge variant={caseData.payload.status === "open" ? "success" : "neutral"}>
            {caseData.payload.status}
          </Badge>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-500">Description</span>
          <span className="text-gray-900 text-right max-w-[60%] truncate">
            {caseData.payload.description || "N/A"}
          </span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-500">Created</span>
          <span className="text-gray-900">
            {caseData.timestamp
              ? new Date(caseData.timestamp).toLocaleDateString()
              : "N/A"}
          </span>
        </div>
        {caseData.evidenceCount !== undefined && (
          <div className="flex justify-between">
            <span className="text-gray-500">Evidence Items</span>
            <span className="text-gray-900">{caseData.evidenceCount}</span>
          </div>
        )}
      </div>
    </div>
  );
}

function TimelineSummarySection({ events }: { events: CaseEvent[] }) {
  const sorted = [...events].sort((a, b) => {
    const ta = a.timestamp ? new Date(a.timestamp).getTime() : 0;
    const tb = b.timestamp ? new Date(b.timestamp).getTime() : 0;
    return ta - tb;
  });

  return (
    <div className="space-y-2">
      <h4 className="text-sm font-semibold text-gray-800">2. Timeline Summary</h4>
      {sorted.length === 0 ? (
        <p className="text-xs text-gray-400">No events recorded.</p>
      ) : (
        <div className="bg-gray-50 rounded-lg p-3 space-y-2 max-h-48 overflow-y-auto">
          {sorted.map((evt) => {
            const payload = (evt.payload || {}) as Record<string, string>;
            const label =
              payload.name || payload.content || payload.notes || evt.type;
            return (
              <div key={evt.id} className="flex items-start gap-2 text-sm">
                <span className="text-gray-400 flex-shrink-0 text-xs w-36">
                  {evt.timestamp
                    ? new Date(evt.timestamp).toLocaleString()
                    : "Unknown"}
                </span>
                <Badge
                  variant={
                    evt.type === "evidence"
                      ? "success"
                      : evt.type === "alert"
                      ? "warning"
                      : evt.type === "detection"
                      ? "error"
                      : "info"
                  }
                >
                  {evt.type}
                </Badge>
                <span className="text-gray-700 truncate">{label}</span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function EvidenceListSection({ events }: { events: CaseEvent[] }) {
  const evidenceItems = events.filter((e) => e.type === "evidence");

  return (
    <div className="space-y-2">
      <h4 className="text-sm font-semibold text-gray-800">3. Evidence List</h4>
      {evidenceItems.length === 0 ? (
        <p className="text-xs text-gray-400">No evidence items attached.</p>
      ) : (
        <div className="bg-gray-50 rounded-lg p-3 space-y-3 max-h-48 overflow-y-auto">
          {evidenceItems.map((item) => {
            const payload = (item.payload || {}) as Record<string, string>;
            return (
              <div key={item.id} className="flex items-start gap-3">
                <div className="w-12 h-12 bg-gray-200 rounded flex items-center justify-center text-gray-400 text-xs flex-shrink-0">
                  Thumb
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-gray-900 truncate">
                    {payload.notes || payload.name || "Evidence"}
                  </p>
                  <p className="text-xs text-gray-500">
                    Type: {item.type}
                    {item.linked_asset_ids.length > 0 &&
                      ` | Assets: ${item.linked_asset_ids.length}`}
                  </p>
                  <p className="text-xs text-gray-400">
                    {item.timestamp
                      ? new Date(item.timestamp).toLocaleString()
                      : ""}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function CommentsSummarySection({ comments }: { comments: Comment[] }) {
  const flattenComments = (items: Comment[]): Comment[] => {
    const result: Comment[] = [];
    for (const c of items) {
      result.push(c);
      if (c.replies.length > 0) {
        result.push(...flattenComments(c.replies));
      }
    }
    return result;
  };

  const flat = flattenComments(comments);

  return (
    <div className="space-y-2">
      <h4 className="text-sm font-semibold text-gray-800">
        4. Comments Summary ({flat.length})
      </h4>
      {flat.length === 0 ? (
        <p className="text-xs text-gray-400">No comments.</p>
      ) : (
        <div className="bg-gray-50 rounded-lg p-3 space-y-2 max-h-48 overflow-y-auto">
          {flat.map((c) => (
            <div key={c.id} className="text-sm">
              <div className="flex items-center gap-2 mb-0.5">
                <div className="w-5 h-5 rounded-full bg-brand-100 text-brand-700 flex items-center justify-center text-xs font-semibold">
                  {c.user_id.charAt(0).toUpperCase()}
                </div>
                <span className="text-xs font-medium text-gray-700">
                  {c.user_id}
                </span>
                <span className="text-xs text-gray-400">
                  {c.timestamp ? new Date(c.timestamp).toLocaleString() : ""}
                </span>
                {c.parent_id && (
                  <Badge variant="neutral" className="text-[10px]">
                    reply
                  </Badge>
                )}
              </div>
              <p className="text-sm text-gray-800 ml-7">{c.content}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function ApprovalHistorySection({ approvals }: { approvals: Approval[] }) {
  return (
    <div className="space-y-2">
      <h4 className="text-sm font-semibold text-gray-800">
        5. Approval History ({approvals.length})
      </h4>
      {approvals.length === 0 ? (
        <p className="text-xs text-gray-400">No approval requests.</p>
      ) : (
        <div className="bg-gray-50 rounded-lg p-3 space-y-2 max-h-48 overflow-y-auto">
          {approvals.map((a) => (
            <div
              key={a.id}
              className="flex items-center justify-between text-sm"
            >
              <div className="flex-1 min-w-0">
                <p className="text-gray-800 truncate">{a.reason}</p>
                <p className="text-xs text-gray-500">
                  {a.requester_id} &rarr; {a.approver_id}
                </p>
              </div>
              <div className="flex items-center gap-2 flex-shrink-0">
                <Badge
                  variant={
                    a.status === "approved"
                      ? "success"
                      : a.status === "rejected"
                      ? "error"
                      : "warning"
                  }
                >
                  {a.status}
                </Badge>
                <span className="text-xs text-gray-400">
                  {a.timestamp
                    ? new Date(a.timestamp).toLocaleString()
                    : ""}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main ReportTab component
// ---------------------------------------------------------------------------

export default function ReportTab({
  caseId,
  caseData,
  events,
  comments,
  approvals,
}: ReportTabProps) {
  const [draft, setDraft] = useState(() => loadDraft(caseId));
  const [regenerateKey, setRegenerateKey] = useState(0);
  const [exporting, setExporting] = useState(false);
  const [copySuccess, setCopySuccess] = useState(false);

  // Reload draft when caseId changes
  useEffect(() => {
    setDraft(loadDraft(caseId));
  }, [caseId]);

  // Persist draft to localStorage on change
  const updateFindings = useCallback(
    (value: string) => {
      setDraft((prev) => {
        const next = { ...prev, findings: value };
        saveDraft(caseId, next.findings, next.recommendations);
        return next;
      });
    },
    [caseId]
  );

  const updateRecommendations = useCallback(
    (value: string) => {
      setDraft((prev) => {
        const next = { ...prev, recommendations: value };
        saveDraft(caseId, next.findings, next.recommendations);
        return next;
      });
    },
    [caseId]
  );

  // Regenerate: refresh view from current data (clears only the key)
  const handleRegenerate = () => {
    setRegenerateKey((k) => k + 1);
  };

  // Build plain-text summary of sections 1-3 for clipboard
  const buildSummaryText = useCallback((): string => {
    const lines: string[] = [];

    // Section 1: Case Summary
    lines.push("== Case Summary ==");
    lines.push(`Title: ${caseData.payload.name}`);
    lines.push(`Status: ${caseData.payload.status}`);
    lines.push(`Description: ${caseData.payload.description || "N/A"}`);
    lines.push(
      `Created: ${
        caseData.timestamp
          ? new Date(caseData.timestamp).toLocaleDateString()
          : "N/A"
      }`
    );
    if (caseData.evidenceCount !== undefined) {
      lines.push(`Evidence Items: ${caseData.evidenceCount}`);
    }
    lines.push("");

    // Section 2: Timeline Summary
    lines.push("== Timeline Summary ==");
    const sorted = [...events].sort((a, b) => {
      const ta = a.timestamp ? new Date(a.timestamp).getTime() : 0;
      const tb = b.timestamp ? new Date(b.timestamp).getTime() : 0;
      return ta - tb;
    });
    if (sorted.length === 0) {
      lines.push("No events recorded.");
    } else {
      for (const evt of sorted) {
        const payload = (evt.payload || {}) as Record<string, string>;
        const label =
          payload.name || payload.content || payload.notes || evt.type;
        const ts = evt.timestamp
          ? new Date(evt.timestamp).toLocaleString()
          : "Unknown";
        lines.push(`[${ts}] ${evt.type}: ${label}`);
      }
    }
    lines.push("");

    // Section 3: Evidence List
    lines.push("== Evidence List ==");
    const evidenceItems = events.filter((e) => e.type === "evidence");
    if (evidenceItems.length === 0) {
      lines.push("No evidence items attached.");
    } else {
      for (const item of evidenceItems) {
        const payload = (item.payload || {}) as Record<string, string>;
        const desc = payload.notes || payload.name || "Evidence";
        const ts = item.timestamp
          ? new Date(item.timestamp).toLocaleString()
          : "";
        lines.push(
          `- ${desc} (assets: ${item.linked_asset_ids.length}) ${ts}`
        );
      }
    }

    return lines.join("\n");
  }, [caseData, events]);

  // Copy Summary to clipboard (sections 1-3)
  const handleCopySummary = useCallback(async () => {
    const text = buildSummaryText();
    try {
      await navigator.clipboard.writeText(text);
      setCopySuccess(true);
      setTimeout(() => setCopySuccess(false), 2000);
    } catch {
      // Fallback: some browsers block clipboard in non-secure context
      setCopySuccess(false);
    }
  }, [buildSummaryText]);

  // Download PDF (stub — POST returns text/plain)
  const handleDownloadPdf = useCallback(async () => {
    setExporting(true);
    try {
      const resp = await fetch(
        `${API_BASE}/api/investigate/cases/${caseId}/report/export`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ format: "pdf" }),
        }
      );
      const text = await resp.text();
      const blob = new Blob([text], { type: "text/plain" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `report_${caseId}.txt`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch {
      // Export failed — fail silently
    } finally {
      setExporting(false);
    }
  }, [caseId]);

  // Download JSON — full case data
  const handleDownloadJson = useCallback(() => {
    const exportPayload = {
      caseData,
      events,
      comments,
      approvals,
      findings: draft.findings,
      recommendations: draft.recommendations,
      exportedAt: new Date().toISOString(),
    };
    const blob = new Blob([JSON.stringify(exportPayload, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `case_${caseId}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }, [caseId, caseData, events, comments, approvals, draft]);

  return (
    <div className="space-y-5" key={regenerateKey}>
      {/* Header with Regenerate */}
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wider">
          Investigation Report
        </h3>
        <Button size="sm" variant="secondary" onClick={handleRegenerate}>
          Regenerate
        </Button>
      </div>

      {/* Section 1: Case Summary */}
      <CaseSummarySection caseData={caseData} />

      {/* Section 2: Timeline Summary */}
      <TimelineSummarySection events={events} />

      {/* Section 3: Evidence List */}
      <EvidenceListSection events={events} />

      {/* Section 4: Comments Summary */}
      <CommentsSummarySection comments={comments} />

      {/* Section 5: Approval History */}
      <ApprovalHistorySection approvals={approvals} />

      {/* Section 6: Findings (editable) */}
      <div className="space-y-2">
        <h4 className="text-sm font-semibold text-gray-800">6. Findings</h4>
        <textarea
          value={draft.findings}
          onChange={(e) => updateFindings(e.target.value)}
          placeholder="Enter analyst conclusions and findings..."
          rows={4}
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm placeholder-gray-400 focus:ring-2 focus:ring-brand-500 focus:border-brand-500 resize-y"
        />
      </div>

      {/* Section 7: Recommendations (editable) */}
      <div className="space-y-2">
        <h4 className="text-sm font-semibold text-gray-800">
          7. Recommendations
        </h4>
        <textarea
          value={draft.recommendations}
          onChange={(e) => updateRecommendations(e.target.value)}
          placeholder="Enter recommended actions and next steps..."
          rows={4}
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm placeholder-gray-400 focus:ring-2 focus:ring-brand-500 focus:border-brand-500 resize-y"
        />
      </div>

      {/* Export row */}
      <div className="flex items-center gap-2 pt-2 border-t border-gray-200">
        <Button
          size="sm"
          onClick={handleDownloadPdf}
          loading={exporting}
        >
          Download PDF
        </Button>
        <Button size="sm" variant="secondary" onClick={handleDownloadJson}>
          Download JSON
        </Button>
        <Button
          size="sm"
          variant={copySuccess ? "ghost" : "secondary"}
          onClick={handleCopySummary}
        >
          {copySuccess ? "Copied!" : "Copy Summary"}
        </Button>
      </div>
    </div>
  );
}
