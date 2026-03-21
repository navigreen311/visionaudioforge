"use client";

import React, { useState, useEffect, useCallback } from "react";
import Button from "@/components/ui/Button";
import Badge from "@/components/ui/Badge";
import Modal from "@/components/ui/Modal";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface ApprovalData {
  id: string;
  case_id: string;
  requester_id: string;
  approver_ids: string[];
  description: string;
  deadline: string | null;
  status: "pending" | "approved" | "rejected";
  decided_by?: string;
  decided_at?: string;
  reject_reason?: string;
  timestamp: string | null;
}

interface ApprovalsTabProps {
  caseId: string;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const TEAM_MEMBERS = [
  "Alice Chen",
  "Bob Martinez",
  "Carol Wu",
  "Dan Okafor",
  "Eva Singh",
  "Frank Kim",
  "Grace Liu",
  "Hiro Tanaka",
];

const API_BASE = "/api/investigate";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function isOverdue(deadline: string | null): boolean {
  if (!deadline) return false;
  return new Date(deadline).getTime() < Date.now();
}

function formatDate(iso: string | null): string {
  if (!iso) return "";
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

// ---------------------------------------------------------------------------
// ApproverTagInput
// ---------------------------------------------------------------------------

function ApproverTagInput({
  selected,
  onChange,
}: {
  selected: string[];
  onChange: (tags: string[]) => void;
}) {
  const [input, setInput] = useState("");
  const [showDropdown, setShowDropdown] = useState(false);

  const available = TEAM_MEMBERS.filter(
    (m) =>
      !selected.includes(m) && m.toLowerCase().includes(input.toLowerCase())
  );

  const addTag = (name: string) => {
    onChange([...selected, name]);
    setInput("");
    setShowDropdown(false);
  };

  const removeTag = (name: string) => {
    onChange(selected.filter((t) => t !== name));
  };

  return (
    <div className="relative">
      <div className="flex flex-wrap gap-1 rounded-lg border border-gray-300 px-2 py-1.5 min-h-[38px] focus-within:ring-2 focus-within:ring-brand-500 focus-within:border-brand-500">
        {selected.map((name) => (
          <span
            key={name}
            className="inline-flex items-center gap-1 bg-brand-100 text-brand-700 rounded-full px-2 py-0.5 text-xs font-medium"
          >
            {name}
            <button
              onClick={() => removeTag(name)}
              className="text-brand-500 hover:text-brand-800"
            >
              &times;
            </button>
          </span>
        ))}
        <input
          type="text"
          value={input}
          onChange={(e) => {
            setInput(e.target.value);
            setShowDropdown(true);
          }}
          onFocus={() => setShowDropdown(true)}
          onBlur={() => setTimeout(() => setShowDropdown(false), 200)}
          placeholder={selected.length === 0 ? "Add approvers..." : ""}
          className="flex-1 min-w-[120px] outline-none text-sm placeholder-gray-400 bg-transparent"
        />
      </div>
      {showDropdown && available.length > 0 && (
        <div className="absolute top-full left-0 mt-1 w-full bg-white border border-gray-200 rounded-lg shadow-lg z-10 max-h-40 overflow-y-auto">
          {available.map((name) => (
            <button
              key={name}
              onMouseDown={(e) => e.preventDefault()}
              onClick={() => addTag(name)}
              className="w-full text-left px-3 py-2 text-sm text-gray-700 hover:bg-gray-50"
            >
              {name}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// ApprovalCard
// ---------------------------------------------------------------------------

function ApprovalCard({
  approval,
  onApprove,
  onReject,
}: {
  approval: ApprovalData;
  onApprove: (id: string) => void;
  onReject: (id: string) => void;
}) {
  const overdue = approval.status === "pending" && isOverdue(approval.deadline);

  const statusBadge = () => {
    switch (approval.status) {
      case "approved":
        return (
          <Badge variant="success">
            <span className="flex items-center gap-1">
              <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              Approved
            </span>
          </Badge>
        );
      case "rejected":
        return (
          <Badge variant="error">
            <span className="flex items-center gap-1">
              <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
              Rejected
            </span>
          </Badge>
        );
      default:
        return <Badge variant="warning">Pending</Badge>;
    }
  };

  return (
    <div className="rounded-lg border border-gray-200 p-4 bg-white">
      <div className="flex items-start justify-between mb-2">
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-gray-900">
            {approval.description}
          </p>
          <div className="flex items-center gap-3 mt-1 text-xs text-gray-500">
            <span>Requested by {approval.requester_id}</span>
            <span>{formatDate(approval.timestamp)}</span>
          </div>
        </div>
        {statusBadge()}
      </div>

      {/* Approvers */}
      <div className="flex flex-wrap gap-1 mt-2">
        {approval.approver_ids.map((name) => (
          <span
            key={name}
            className="inline-flex items-center bg-gray-100 text-gray-600 rounded-full px-2 py-0.5 text-xs"
          >
            {name}
          </span>
        ))}
      </div>

      {/* Deadline */}
      {approval.deadline && (
        <div className="mt-2">
          <span
            className={`text-xs font-medium ${
              overdue ? "text-red-600" : "text-gray-500"
            }`}
          >
            Deadline: {formatDate(approval.deadline)}
            {overdue && " (overdue)"}
          </span>
        </div>
      )}

      {/* Rejection reason */}
      {approval.status === "rejected" && approval.reject_reason && (
        <div className="mt-2 p-2 bg-red-50 border border-red-100 rounded text-xs text-red-700">
          <span className="font-medium">Reason:</span> {approval.reject_reason}
        </div>
      )}

      {/* Action buttons for pending */}
      {approval.status === "pending" && (
        <div className="flex items-center gap-2 mt-3">
          <Button size="sm" onClick={() => onApprove(approval.id)}>
            Approve
          </Button>
          <Button
            size="sm"
            variant="danger"
            onClick={() => onReject(approval.id)}
          >
            Reject
          </Button>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

export default function ApprovalsTab({ caseId }: ApprovalsTabProps) {
  const [approvals, setApprovals] = useState<ApprovalData[]>([]);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  // Request form state
  const [description, setDescription] = useState("");
  const [approvers, setApprovers] = useState<string[]>([]);
  const [deadline, setDeadline] = useState("");

  // Reject modal state
  const [rejectModalOpen, setRejectModalOpen] = useState(false);
  const [rejectTargetId, setRejectTargetId] = useState<string | null>(null);
  const [rejectReason, setRejectReason] = useState("");

  // Fetch approvals
  const fetchApprovals = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/cases/${caseId}/approvals`);
      if (res.ok) {
        const data: ApprovalData[] = await res.json();
        setApprovals(data);
      }
    } catch {
      // silently handle
    } finally {
      setLoading(false);
    }
  }, [caseId]);

  useEffect(() => {
    fetchApprovals();
  }, [fetchApprovals]);

  // Submit approval request
  const handleRequestApproval = async () => {
    if (!description.trim() || approvers.length === 0) return;
    setSubmitting(true);
    try {
      // Create one approval request per approver
      const requests = approvers.map((approver) =>
        fetch(`${API_BASE}/cases/${caseId}/approval`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            user_id: "current-user",
            approver_id: approver,
            reason: description.trim(),
          }),
        })
      );
      await Promise.all(requests);
      setDescription("");
      setApprovers([]);
      setDeadline("");
      await fetchApprovals();
    } catch {
      // silently handle
    } finally {
      setSubmitting(false);
    }
  };

  // Approve
  const handleApprove = async (approvalId: string) => {
    try {
      await fetch(`${API_BASE}/approvals/${approvalId}/process`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: "current-user",
          decision: "approved",
        }),
      });
      await fetchApprovals();
    } catch {
      // silently handle
    }
  };

  // Reject (open modal)
  const handleRejectClick = (approvalId: string) => {
    setRejectTargetId(approvalId);
    setRejectReason("");
    setRejectModalOpen(true);
  };

  // Confirm reject
  const handleConfirmReject = async () => {
    if (!rejectTargetId || !rejectReason.trim()) return;
    try {
      await fetch(`${API_BASE}/approvals/${rejectTargetId}/process`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: "current-user",
          decision: "rejected",
          notes: rejectReason.trim(),
        }),
      });
      setRejectModalOpen(false);
      setRejectTargetId(null);
      setRejectReason("");
      await fetchApprovals();
    } catch {
      // silently handle
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Request form (top) */}
      <div className="p-4 border-b border-gray-200 bg-gray-50">
        <h3 className="text-sm font-semibold text-gray-900 mb-3">
          Request Approval
        </h3>
        <div className="space-y-3">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">
              Description
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Describe what needs approval..."
              rows={2}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm placeholder-gray-400 focus:ring-2 focus:ring-brand-500 focus:border-brand-500 resize-none"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">
              Approvers
            </label>
            <ApproverTagInput selected={approvers} onChange={setApprovers} />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">
              Deadline
            </label>
            <input
              type="date"
              value={deadline}
              onChange={(e) => setDeadline(e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
            />
          </div>
          <Button
            size="sm"
            onClick={handleRequestApproval}
            loading={submitting}
            disabled={!description.trim() || approvers.length === 0}
          >
            Request Approval
          </Button>
        </div>
      </div>

      {/* Approval list */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin h-6 w-6 border-2 border-brand-600 border-t-transparent rounded-full" />
          </div>
        ) : approvals.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <p className="text-sm text-gray-500">No approval requests</p>
            <p className="text-xs text-gray-400 mt-1">
              Use the form above to request approval from team members
            </p>
          </div>
        ) : (
          approvals.map((approval) => (
            <ApprovalCard
              key={approval.id}
              approval={approval}
              onApprove={handleApprove}
              onReject={handleRejectClick}
            />
          ))
        )}
      </div>

      {/* Reject reason modal */}
      <Modal
        isOpen={rejectModalOpen}
        onClose={() => setRejectModalOpen(false)}
        title="Reject Approval"
        footer={
          <>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setRejectModalOpen(false)}
            >
              Cancel
            </Button>
            <Button
              variant="danger"
              size="sm"
              onClick={handleConfirmReject}
              disabled={!rejectReason.trim()}
            >
              Reject
            </Button>
          </>
        }
      >
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Reason for rejection
          </label>
          <textarea
            value={rejectReason}
            onChange={(e) => setRejectReason(e.target.value)}
            placeholder="Explain why this is being rejected..."
            rows={3}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm placeholder-gray-400 focus:ring-2 focus:ring-brand-500 focus:border-brand-500 resize-none"
            autoFocus
          />
        </div>
      </Modal>
    </div>
  );
}
