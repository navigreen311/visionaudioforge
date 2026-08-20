"use client";

import { readWorkspaceId } from "@/lib/session";

import { useState, useEffect, useCallback } from "react";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface ReviewTask {
  task_id: string;
  title: string;
  review_type: string;
  priority: "critical" | "high" | "normal" | "low";
  status: "pending" | "assigned" | "in_review" | "completed" | "escalated";
  sla_deadline: string;
  assigned_to: string | null;
  reviews_count: number;
  required_reviews: number;
}

interface Reviewer {
  id: string;
  name: string;
  avatar: string | null;
}

interface TaskQueueProps {
  statusFilter?: string;
}

type SortField = "priority" | "title" | "status" | "sla_deadline";
type SortDir = "asc" | "desc";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const API = "/api/reviewops";

const PRIORITY_ORDER: Record<string, number> = {
  critical: 0,
  high: 1,
  normal: 2,
  low: 3,
};

const PRIORITY_DOT: Record<string, string> = {
  critical: "bg-red-500",
  high: "bg-orange-500",
  normal: "bg-blue-500",
  low: "bg-gray-400",
};

const STATUS_BADGE: Record<string, string> = {
  pending: "bg-yellow-100 text-yellow-800",
  assigned: "bg-blue-100 text-blue-800",
  in_review: "bg-purple-100 text-purple-800",
  completed: "bg-green-100 text-green-800",
  escalated: "bg-red-100 text-red-800",
};

const TYPE_BADGE: Record<string, string> = {
  annotation_qa: "bg-indigo-50 text-indigo-700",
  detection_verify: "bg-teal-50 text-teal-700",
  model_output: "bg-pink-50 text-pink-700",
  data_quality: "bg-cyan-50 text-cyan-700",
  edge_case: "bg-amber-50 text-amber-700",
  safety_review: "bg-red-50 text-red-700",
};

// ---------------------------------------------------------------------------
// SLA Countdown
// ---------------------------------------------------------------------------

function SLACountdown({ deadline }: { deadline: string }) {
  const [remaining, setRemaining] = useState("");
  const [color, setColor] = useState("bg-green-50 text-green-700");

  useEffect(() => {
    const update = () => {
      const diff = new Date(deadline).getTime() - Date.now();
      if (diff <= 0) {
        const abs = Math.abs(diff);
        const h = Math.floor(abs / 3_600_000);
        const m = Math.floor((abs % 3_600_000) / 60_000);
        setRemaining(`-${h}h ${m}m`);
        setColor("bg-red-100 text-red-700 animate-pulse");
      } else {
        const h = Math.floor(diff / 3_600_000);
        const m = Math.floor((diff % 3_600_000) / 60_000);
        setRemaining(`${h}h ${m}m`);
        if (h < 1) {
          setColor("bg-red-100 text-red-700");
        } else if (h < 4) {
          setColor("bg-amber-100 text-amber-700");
        } else {
          setColor("bg-green-50 text-green-700");
        }
      }
    };
    update();
    const interval = setInterval(update, 60_000);
    return () => clearInterval(interval);
  }, [deadline]);

  return (
    <span className={`text-xs font-mono px-2 py-0.5 rounded ${color}`}>
      {remaining}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Assignee Avatar
// ---------------------------------------------------------------------------

function AssigneeAvatar({ name }: { name: string | null }) {
  if (!name) {
    return (
      <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-gray-200 text-[10px] text-gray-500">
        ?
      </span>
    );
  }
  const initials = name
    .split(" ")
    .map((n) => n[0])
    .join("")
    .toUpperCase()
    .slice(0, 2);

  return (
    <span
      className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-brand-100 text-[10px] font-medium text-brand-700"
      title={name}
    >
      {initials}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Toast
// ---------------------------------------------------------------------------

function Toast({
  message,
  onClose,
}: {
  message: string;
  onClose: () => void;
}) {
  useEffect(() => {
    const timer = setTimeout(onClose, 3000);
    return () => clearTimeout(timer);
  }, [onClose]);

  return (
    <div className="fixed bottom-6 right-6 z-50 flex items-center gap-2 rounded-lg bg-gray-900 px-4 py-2.5 text-sm text-white shadow-lg">
      <svg className="w-4 h-4 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
      </svg>
      {message}
    </div>
  );
}

// ---------------------------------------------------------------------------
// TaskQueue Component
// ---------------------------------------------------------------------------

export default function TaskQueue({ statusFilter }: TaskQueueProps) {
  const [tasks, setTasks] = useState<ReviewTask[]>([]);
  const [reviewers, setReviewers] = useState<Reviewer[]>([]);
  const [loading, setLoading] = useState(true);
  const [toast, setToast] = useState<string | null>(null);

  // Filters
  const [filterStatus, setFilterStatus] = useState(statusFilter ?? "");
  const [filterPriority, setFilterPriority] = useState("");
  const [filterAssignee, setFilterAssignee] = useState("");

  // Sort
  const [sortField, setSortField] = useState<SortField>("sla_deadline");
  const [sortDir, setSortDir] = useState<SortDir>("asc");

  // Hover
  const [hoveredRow, setHoveredRow] = useState<string | null>(null);

  // Sync external filter prop
  useEffect(() => {
    if (statusFilter !== undefined) {
      setFilterStatus(statusFilter);
    }
  }, [statusFilter]);

  const fetchTasks = useCallback(async () => {
    try {
      const params = new URLSearchParams({ workspace_id: readWorkspaceId() ?? "" });
      if (filterStatus) params.set("status", filterStatus);
      if (filterPriority) params.set("priority", filterPriority);
      if (filterAssignee) params.set("assignee", filterAssignee);
      const res = await fetch(`${API}/tasks?${params}`);
      if (res.ok) {
        const data: ReviewTask[] = await res.json();
        setTasks(data);
      }
    } catch {
      /* network error */
    } finally {
      setLoading(false);
    }
  }, [filterStatus, filterPriority, filterAssignee]);

  const fetchReviewers = useCallback(async () => {
    try {
      const res = await fetch(`${API}/reviewers?workspace_id=${readWorkspaceId()}`);
      if (res.ok) {
        const data: Reviewer[] = await res.json();
        setReviewers(data);
      }
    } catch {
      /* network error */
    }
  }, []);

  useEffect(() => {
    fetchTasks();
    fetchReviewers();
  }, [fetchTasks, fetchReviewers]);

  // Sort tasks
  const sorted = [...tasks].sort((a, b) => {
    let cmp = 0;
    switch (sortField) {
      case "priority":
        cmp = (PRIORITY_ORDER[a.priority] ?? 99) - (PRIORITY_ORDER[b.priority] ?? 99);
        break;
      case "title":
        cmp = a.title.localeCompare(b.title);
        break;
      case "status":
        cmp = a.status.localeCompare(b.status);
        break;
      case "sla_deadline":
        cmp = new Date(a.sla_deadline).getTime() - new Date(b.sla_deadline).getTime();
        break;
    }
    return sortDir === "asc" ? cmp : -cmp;
  });

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortField(field);
      setSortDir("asc");
    }
  };

  const handleAutoAssign = async () => {
    try {
      const res = await fetch(`${API}/auto-assign?workspace_id=${readWorkspaceId()}`, {
        method: "POST",
      });
      if (res.ok) {
        const data = await res.json();
        setToast(`Auto-assigned ${data.assigned_count ?? 0} tasks`);
        fetchTasks();
      } else {
        setToast("Auto-assign failed");
      }
    } catch {
      setToast("Auto-assign failed");
    }
  };

  const truncate = (s: string, max: number) =>
    s.length > max ? s.slice(0, max) + "..." : s;

  const sortIcon = (field: SortField) => {
    if (sortField !== field) return null;
    return (
      <svg
        className={`inline w-3 h-3 ml-0.5 ${sortDir === "desc" ? "rotate-180" : ""}`}
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        strokeWidth={2}
      >
        <path strokeLinecap="round" strokeLinejoin="round" d="M5 15l7-7 7 7" />
      </svg>
    );
  };

  const reviewerName = (id: string | null): string | null => {
    if (!id) return null;
    const r = reviewers.find((rv) => rv.id === id);
    return r?.name ?? id.slice(0, 8);
  };

  return (
    <div className="space-y-4">
      {/* Filter bar */}
      <div className="flex flex-wrap items-center gap-3">
        <select
          value={filterStatus}
          onChange={(e) => setFilterStatus(e.target.value)}
          className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm"
        >
          <option value="">All Statuses</option>
          <option value="pending">Pending</option>
          <option value="assigned">Assigned</option>
          <option value="in_review">In Review</option>
          <option value="completed">Completed</option>
          <option value="escalated">Escalated</option>
        </select>

        <select
          value={filterPriority}
          onChange={(e) => setFilterPriority(e.target.value)}
          className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm"
        >
          <option value="">All Priorities</option>
          <option value="critical">Critical</option>
          <option value="high">High</option>
          <option value="normal">Normal</option>
          <option value="low">Low</option>
        </select>

        <select
          value={filterAssignee}
          onChange={(e) => setFilterAssignee(e.target.value)}
          className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm"
        >
          <option value="">All Assignees</option>
          {reviewers.map((r) => (
            <option key={r.id} value={r.id}>
              {r.name}
            </option>
          ))}
        </select>

        <div className="flex-1" />

        <button
          onClick={() => fetchTasks()}
          className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-50"
        >
          Refresh
        </button>

        <button
          onClick={handleAutoAssign}
          className="rounded-lg bg-brand-600 px-4 py-1.5 text-sm text-white hover:bg-brand-700 transition-colors"
        >
          Auto-Assign All
        </button>
      </div>

      {/* Task table */}
      {loading ? (
        <div className="text-center py-12 text-gray-400">Loading tasks...</div>
      ) : sorted.length === 0 ? (
        <div className="text-center py-12 text-gray-400">No review tasks found</div>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th
                  className="px-4 py-3 text-left font-medium text-gray-500 cursor-pointer select-none"
                  onClick={() => handleSort("priority")}
                >
                  Priority {sortIcon("priority")}
                </th>
                <th
                  className="px-4 py-3 text-left font-medium text-gray-500 cursor-pointer select-none"
                  onClick={() => handleSort("title")}
                >
                  Task {sortIcon("title")}
                </th>
                <th className="px-4 py-3 text-left font-medium text-gray-500">Type</th>
                <th className="px-4 py-3 text-left font-medium text-gray-500">Assignee</th>
                <th
                  className="px-4 py-3 text-left font-medium text-gray-500 cursor-pointer select-none"
                  onClick={() => handleSort("sla_deadline")}
                >
                  SLA {sortIcon("sla_deadline")}
                </th>
                <th
                  className="px-4 py-3 text-left font-medium text-gray-500 cursor-pointer select-none"
                  onClick={() => handleSort("status")}
                >
                  Status {sortIcon("status")}
                </th>
                <th className="px-4 py-3 text-right font-medium text-gray-500">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {sorted.map((t) => (
                <tr
                  key={t.task_id}
                  className="hover:bg-gray-50 transition-colors"
                  onMouseEnter={() => setHoveredRow(t.task_id)}
                  onMouseLeave={() => setHoveredRow(null)}
                >
                  {/* Priority dot */}
                  <td className="px-4 py-3">
                    <span
                      className={`inline-block w-2.5 h-2.5 rounded-full ${PRIORITY_DOT[t.priority] ?? "bg-gray-300"}`}
                      title={t.priority}
                    />
                  </td>

                  {/* Task name */}
                  <td className="px-4 py-3 font-medium text-gray-900" title={t.title}>
                    {truncate(t.title, 40)}
                  </td>

                  {/* Type badge */}
                  <td className="px-4 py-3">
                    <span
                      className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                        TYPE_BADGE[t.review_type] ?? "bg-gray-100 text-gray-700"
                      }`}
                    >
                      {t.review_type.replace(/_/g, " ")}
                    </span>
                  </td>

                  {/* Assignee avatar */}
                  <td className="px-4 py-3">
                    <AssigneeAvatar name={reviewerName(t.assigned_to)} />
                  </td>

                  {/* SLA countdown */}
                  <td className="px-4 py-3">
                    <SLACountdown deadline={t.sla_deadline} />
                  </td>

                  {/* Status badge */}
                  <td className="px-4 py-3">
                    <span
                      className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                        STATUS_BADGE[t.status] ?? "bg-gray-100 text-gray-700"
                      }`}
                    >
                      {t.status.replace(/_/g, " ")}
                    </span>
                  </td>

                  {/* Hover actions */}
                  <td className="px-4 py-3 text-right">
                    {hoveredRow === t.task_id ? (
                      <div className="flex items-center justify-end gap-2">
                        {(t.status === "assigned" || t.status === "in_review") && (
                          <button className="text-xs font-medium text-green-600 hover:underline">
                            Review
                          </button>
                        )}
                        {t.status === "pending" && (
                          <button className="text-xs font-medium text-brand-600 hover:underline">
                            Assign
                          </button>
                        )}
                        <button className="text-xs font-medium text-gray-400 hover:text-gray-600 hover:underline">
                          Skip
                        </button>
                      </div>
                    ) : (
                      <span className="text-gray-300 text-xs">...</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Toast */}
      {toast && <Toast message={toast} onClose={() => setToast(null)} />}
    </div>
  );
}
