"use client";

import { useState, useEffect, useCallback } from "react";

// ------------------------------------------------------------------
// Types
// ------------------------------------------------------------------

interface ReviewTask {
  task_id: string;
  review_type: string;
  priority: string;
  status: string;
  sla_deadline: string;
  assigned_to: string | null;
  reviews_count: number;
  required_reviews: number;
}

interface ReviewerScore {
  reviewer_id: string;
  total_reviews: number;
  avg_quality_score: number;
  avg_review_time_s: number;
  sla_compliance_pct: number;
  agreement_rate: number;
  overall_grade: string;
}

interface QualityTrend {
  period: string;
  avg_score: number;
  review_count: number;
  sla_compliance: number;
}

interface Shift {
  shift_id: string;
  reviewer_id: string;
  start_time: string;
  end_time: string;
  review_types: string[] | null;
  active: boolean;
}

// ------------------------------------------------------------------
// Constants
// ------------------------------------------------------------------

const TABS = ["Review Queue", "Leaderboard", "Quality", "Shifts"] as const;
type Tab = (typeof TABS)[number];

const API = "/api/reviewops";
const WS_ID = "00000000-0000-0000-0000-000000000001";

const PRIORITY_COLORS: Record<string, string> = {
  critical: "bg-red-100 text-red-800",
  high: "bg-orange-100 text-orange-800",
  normal: "bg-blue-100 text-blue-800",
  low: "bg-gray-100 text-gray-700",
};

const STATUS_COLORS: Record<string, string> = {
  pending: "bg-yellow-100 text-yellow-800",
  assigned: "bg-blue-100 text-blue-800",
  in_review: "bg-purple-100 text-purple-800",
  completed: "bg-green-100 text-green-800",
  escalated: "bg-red-100 text-red-800",
};

const GRADE_COLORS: Record<string, string> = {
  A: "text-green-600 bg-green-50",
  B: "text-blue-600 bg-blue-50",
  C: "text-yellow-600 bg-yellow-50",
  D: "text-orange-600 bg-orange-50",
  F: "text-red-600 bg-red-50",
};

// ------------------------------------------------------------------
// Helper: SLA countdown
// ------------------------------------------------------------------

function SLACountdown({ deadline }: { deadline: string }) {
  const [remaining, setRemaining] = useState("");
  const [overdue, setOverdue] = useState(false);

  useEffect(() => {
    const update = () => {
      const diff = new Date(deadline).getTime() - Date.now();
      if (diff <= 0) {
        setOverdue(true);
        const absDiff = Math.abs(diff);
        const h = Math.floor(absDiff / 3600000);
        const m = Math.floor((absDiff % 3600000) / 60000);
        setRemaining(`-${h}h ${m}m`);
      } else {
        setOverdue(false);
        const h = Math.floor(diff / 3600000);
        const m = Math.floor((diff % 3600000) / 60000);
        setRemaining(`${h}h ${m}m`);
      }
    };
    update();
    const interval = setInterval(update, 60000);
    return () => clearInterval(interval);
  }, [deadline]);

  return (
    <span
      className={`text-xs font-mono px-2 py-0.5 rounded ${
        overdue ? "bg-red-100 text-red-700" : "bg-green-50 text-green-700"
      }`}
    >
      {remaining}
    </span>
  );
}

// ------------------------------------------------------------------
// Badge
// ------------------------------------------------------------------

function Badge({ className, children }: { className: string; children: React.ReactNode }) {
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${className}`}>
      {children}
    </span>
  );
}

// ------------------------------------------------------------------
// Metric bar
// ------------------------------------------------------------------

function MetricBar({ label, value, max = 100 }: { label: string; value: number; max?: number }) {
  const pct = Math.min((value / max) * 100, 100);
  return (
    <div className="flex items-center gap-2 text-xs">
      <span className="w-28 text-gray-500 truncate">{label}</span>
      <div className="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden">
        <div
          className="h-full bg-brand-500 rounded-full transition-all"
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="w-12 text-right text-gray-600">{value.toFixed(1)}</span>
    </div>
  );
}

// ------------------------------------------------------------------
// Tab: Review Queue
// ------------------------------------------------------------------

function ReviewQueueTab() {
  const [tasks, setTasks] = useState<ReviewTask[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<string>("");

  const fetchTasks = useCallback(async () => {
    try {
      const params = new URLSearchParams({ workspace_id: WS_ID });
      if (filter) params.set("status", filter);
      const res = await fetch(`${API}/tasks?${params}`);
      if (res.ok) setTasks(await res.json());
    } catch {
      /* empty */
    } finally {
      setLoading(false);
    }
  }, [filter]);

  useEffect(() => {
    fetchTasks();
  }, [fetchTasks]);

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex items-center gap-3">
        <select
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm"
        >
          <option value="">All statuses</option>
          <option value="pending">Pending</option>
          <option value="assigned">Assigned</option>
          <option value="in_review">In Review</option>
          <option value="completed">Completed</option>
          <option value="escalated">Escalated</option>
        </select>
        <button
          onClick={fetchTasks}
          className="rounded-lg bg-brand-600 px-4 py-1.5 text-sm text-white hover:bg-brand-700"
        >
          Refresh
        </button>
        <button
          onClick={async () => {
            await fetch(`${API}/tasks/auto-assign?workspace_id=${WS_ID}`, { method: "POST" });
            fetchTasks();
          }}
          className="rounded-lg border border-brand-600 px-4 py-1.5 text-sm text-brand-600 hover:bg-brand-50"
        >
          Auto-Assign All
        </button>
      </div>

      {/* Task table */}
      {loading ? (
        <div className="text-center py-12 text-gray-400">Loading...</div>
      ) : tasks.length === 0 ? (
        <div className="text-center py-12 text-gray-400">No review tasks found</div>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-gray-500">Type</th>
                <th className="px-4 py-3 text-left font-medium text-gray-500">Priority</th>
                <th className="px-4 py-3 text-left font-medium text-gray-500">Status</th>
                <th className="px-4 py-3 text-left font-medium text-gray-500">Reviews</th>
                <th className="px-4 py-3 text-left font-medium text-gray-500">SLA</th>
                <th className="px-4 py-3 text-left font-medium text-gray-500">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {tasks.map((t) => (
                <tr key={t.task_id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium">{t.review_type.replace(/_/g, " ")}</td>
                  <td className="px-4 py-3">
                    <Badge className={PRIORITY_COLORS[t.priority] || "bg-gray-100"}>{t.priority}</Badge>
                  </td>
                  <td className="px-4 py-3">
                    <Badge className={STATUS_COLORS[t.status] || "bg-gray-100"}>{t.status}</Badge>
                  </td>
                  <td className="px-4 py-3 text-gray-600">
                    {t.reviews_count}/{t.required_reviews}
                  </td>
                  <td className="px-4 py-3">
                    <SLACountdown deadline={t.sla_deadline} />
                  </td>
                  <td className="px-4 py-3 space-x-2">
                    {t.status === "pending" && (
                      <button className="text-xs text-brand-600 hover:underline">Assign</button>
                    )}
                    {(t.status === "assigned" || t.status === "in_review") && (
                      <button className="text-xs text-green-600 hover:underline">Review</button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ------------------------------------------------------------------
// Tab: Leaderboard
// ------------------------------------------------------------------

function LeaderboardTab() {
  const [scores, setScores] = useState<ReviewerScore[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const res = await fetch(`${API}/leaderboard?workspace_id=${WS_ID}`);
        if (res.ok) setScores(await res.json());
      } catch {
        /* empty */
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  if (loading) return <div className="text-center py-12 text-gray-400">Loading...</div>;

  return (
    <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white">
      <table className="min-w-full divide-y divide-gray-200 text-sm">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-4 py-3 text-left font-medium text-gray-500">Rank</th>
            <th className="px-4 py-3 text-left font-medium text-gray-500">Reviewer</th>
            <th className="px-4 py-3 text-center font-medium text-gray-500">Grade</th>
            <th className="px-4 py-3 text-left font-medium text-gray-500">Quality</th>
            <th className="px-4 py-3 text-left font-medium text-gray-500">SLA</th>
            <th className="px-4 py-3 text-left font-medium text-gray-500">Agreement</th>
            <th className="px-4 py-3 text-right font-medium text-gray-500">Reviews</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {scores.map((s, i) => (
            <tr key={s.reviewer_id} className="hover:bg-gray-50">
              <td className="px-4 py-3 font-medium text-gray-600">#{i + 1}</td>
              <td className="px-4 py-3 font-mono text-xs text-gray-700">{s.reviewer_id.slice(0, 8)}...</td>
              <td className="px-4 py-3 text-center">
                <span className={`inline-block w-8 h-8 leading-8 rounded-full text-sm font-bold ${GRADE_COLORS[s.overall_grade] || ""}`}>
                  {s.overall_grade}
                </span>
              </td>
              <td className="px-4 py-3 w-40">
                <MetricBar label="Quality" value={s.avg_quality_score} />
              </td>
              <td className="px-4 py-3 w-40">
                <MetricBar label="SLA" value={s.sla_compliance_pct} />
              </td>
              <td className="px-4 py-3 w-40">
                <MetricBar label="Agreement" value={s.agreement_rate} />
              </td>
              <td className="px-4 py-3 text-right text-gray-600">{s.total_reviews}</td>
            </tr>
          ))}
          {scores.length === 0 && (
            <tr>
              <td colSpan={7} className="text-center py-8 text-gray-400">No reviewer data yet</td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

// ------------------------------------------------------------------
// Tab: Quality
// ------------------------------------------------------------------

function QualityTab() {
  const [trends, setTrends] = useState<QualityTrend[]>([]);
  const [agreement, setAgreement] = useState<{ agreement_rate: number; total_double_reviewed: number; disagreements: number } | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const [tRes, aRes] = await Promise.all([
          fetch(`${API}/quality-trends?workspace_id=${WS_ID}`),
          fetch(`${API}/agreement?workspace_id=${WS_ID}`),
        ]);
        if (tRes.ok) setTrends(await tRes.json());
        if (aRes.ok) setAgreement(await aRes.json());
      } catch {
        /* empty */
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  if (loading) return <div className="text-center py-12 text-gray-400">Loading...</div>;

  return (
    <div className="space-y-6">
      {/* Agreement stats */}
      {agreement && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="rounded-lg border border-gray-200 bg-white p-4">
            <p className="text-sm text-gray-500">Agreement Rate</p>
            <p className="text-2xl font-bold text-gray-900">{agreement.agreement_rate.toFixed(1)}%</p>
          </div>
          <div className="rounded-lg border border-gray-200 bg-white p-4">
            <p className="text-sm text-gray-500">Double-Reviewed</p>
            <p className="text-2xl font-bold text-gray-900">{agreement.total_double_reviewed}</p>
          </div>
          <div className="rounded-lg border border-gray-200 bg-white p-4">
            <p className="text-sm text-gray-500">Disagreements</p>
            <p className="text-2xl font-bold text-red-600">{agreement.disagreements}</p>
          </div>
        </div>
      )}

      {/* Trend chart (simple bar chart) */}
      <div className="rounded-lg border border-gray-200 bg-white p-6">
        <h3 className="text-sm font-medium text-gray-700 mb-4">Quality Trends</h3>
        {trends.length === 0 ? (
          <p className="text-center text-gray-400 py-8">No trend data available</p>
        ) : (
          <div className="space-y-3">
            {trends.map((t) => (
              <div key={t.period} className="flex items-center gap-3 text-sm">
                <span className="w-24 text-gray-500 font-mono">{t.period}</span>
                <div className="flex-1 h-5 bg-gray-100 rounded-full overflow-hidden relative">
                  <div
                    className="h-full bg-brand-500 rounded-full"
                    style={{ width: `${(t.avg_score / 5) * 100}%` }}
                  />
                  <span className="absolute inset-0 flex items-center justify-center text-[10px] text-gray-600">
                    {t.avg_score.toFixed(1)} / 5
                  </span>
                </div>
                <span className="w-16 text-right text-gray-500">{t.review_count} reviews</span>
                <span className="w-20 text-right text-gray-500">{t.sla_compliance.toFixed(0)}% SLA</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ------------------------------------------------------------------
// Tab: Shifts
// ------------------------------------------------------------------

function ShiftsTab() {
  const [shifts, setShifts] = useState<Shift[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ reviewer_id: "", start: "", end: "", review_types: "" });

  const fetchShifts = useCallback(async () => {
    try {
      const res = await fetch(`${API}/shifts?workspace_id=${WS_ID}`);
      if (res.ok) setShifts(await res.json());
    } catch {
      /* empty */
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchShifts();
  }, [fetchShifts]);

  const handleCreateShift = async () => {
    try {
      await fetch(`${API}/shifts?workspace_id=${WS_ID}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          reviewer_id: form.reviewer_id,
          start: form.start,
          end: form.end,
          review_types: form.review_types ? form.review_types.split(",").map((s) => s.trim()) : null,
        }),
      });
      setShowForm(false);
      setForm({ reviewer_id: "", start: "", end: "", review_types: "" });
      fetchShifts();
    } catch {
      /* empty */
    }
  };

  if (loading) return <div className="text-center py-12 text-gray-400">Loading...</div>;

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <button
          onClick={() => setShowForm(!showForm)}
          className="rounded-lg bg-brand-600 px-4 py-1.5 text-sm text-white hover:bg-brand-700"
        >
          {showForm ? "Cancel" : "Create Shift"}
        </button>
      </div>

      {/* Create shift form */}
      {showForm && (
        <div className="rounded-lg border border-gray-200 bg-white p-4 space-y-3">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-gray-500 mb-1">Reviewer ID</label>
              <input
                type="text"
                value={form.reviewer_id}
                onChange={(e) => setForm({ ...form, reviewer_id: e.target.value })}
                className="w-full rounded border border-gray-300 px-3 py-1.5 text-sm"
                placeholder="UUID"
              />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Review Types (comma separated)</label>
              <input
                type="text"
                value={form.review_types}
                onChange={(e) => setForm({ ...form, review_types: e.target.value })}
                className="w-full rounded border border-gray-300 px-3 py-1.5 text-sm"
                placeholder="annotation_qa, detection_verify"
              />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Start</label>
              <input
                type="datetime-local"
                value={form.start}
                onChange={(e) => setForm({ ...form, start: e.target.value })}
                className="w-full rounded border border-gray-300 px-3 py-1.5 text-sm"
              />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">End</label>
              <input
                type="datetime-local"
                value={form.end}
                onChange={(e) => setForm({ ...form, end: e.target.value })}
                className="w-full rounded border border-gray-300 px-3 py-1.5 text-sm"
              />
            </div>
          </div>
          <button
            onClick={handleCreateShift}
            className="rounded-lg bg-green-600 px-4 py-1.5 text-sm text-white hover:bg-green-700"
          >
            Save Shift
          </button>
        </div>
      )}

      {/* Shift calendar/list */}
      <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white">
        <table className="min-w-full divide-y divide-gray-200 text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left font-medium text-gray-500">Reviewer</th>
              <th className="px-4 py-3 text-left font-medium text-gray-500">Start</th>
              <th className="px-4 py-3 text-left font-medium text-gray-500">End</th>
              <th className="px-4 py-3 text-left font-medium text-gray-500">Types</th>
              <th className="px-4 py-3 text-left font-medium text-gray-500">Status</th>
              <th className="px-4 py-3 text-left font-medium text-gray-500">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {shifts.map((s) => (
              <tr key={s.shift_id} className="hover:bg-gray-50">
                <td className="px-4 py-3 font-mono text-xs">{s.reviewer_id.slice(0, 8)}...</td>
                <td className="px-4 py-3 text-gray-600">
                  {new Date(s.start_time).toLocaleString()}
                </td>
                <td className="px-4 py-3 text-gray-600">
                  {new Date(s.end_time).toLocaleString()}
                </td>
                <td className="px-4 py-3 text-gray-600">
                  {s.review_types?.join(", ") || "All"}
                </td>
                <td className="px-4 py-3">
                  <Badge className={s.active ? "bg-green-100 text-green-800" : "bg-gray-100 text-gray-600"}>
                    {s.active ? "Active" : "Ended"}
                  </Badge>
                </td>
                <td className="px-4 py-3">
                  {s.active && (
                    <button className="text-xs text-orange-600 hover:underline">Handoff</button>
                  )}
                </td>
              </tr>
            ))}
            {shifts.length === 0 && (
              <tr>
                <td colSpan={6} className="text-center py-8 text-gray-400">No shifts scheduled</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ------------------------------------------------------------------
// Main Page
// ------------------------------------------------------------------

export default function ReviewOpsPage() {
  const [activeTab, setActiveTab] = useState<Tab>("Review Queue");

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">ReviewOps</h1>
        <p className="text-sm text-gray-500 mt-1">
          Manage review assignments, track SLA compliance, and monitor quality.
        </p>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="flex gap-6" aria-label="Tabs">
          {TABS.map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`pb-3 text-sm font-medium border-b-2 transition-colors ${
                activeTab === tab
                  ? "border-brand-600 text-brand-600"
                  : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
              }`}
            >
              {tab}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab content */}
      {activeTab === "Review Queue" && <ReviewQueueTab />}
      {activeTab === "Leaderboard" && <LeaderboardTab />}
      {activeTab === "Quality" && <QualityTab />}
      {activeTab === "Shifts" && <ShiftsTab />}
    </div>
  );
}
