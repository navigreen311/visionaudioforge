"use client";

import React, { useCallback, useEffect, useState } from "react";
import Badge from "@/components/ui/Badge";
import {
  getChainOfCustody,
  listAlerts,
  type Alert,
  type CustodyReport,
} from "@/lib/api";

const actionVariant: Record<string, "error" | "warning" | "info" | "success" | "neutral"> = {
  viewed: "info",
  downloaded: "warning",
  exported: "warning",
  modified: "error",
  shared: "neutral",
  deleted: "error",
};

const actionIcon: Record<string, string> = {
  viewed: "M15 12a3 3 0 11-6 0 3 3 0 016 0z M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z",
  downloaded: "M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4",
  exported: "M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z",
  modified: "M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z",
  shared: "M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z",
  deleted: "M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16",
};

export default function ChainOfCustodyDisplay() {
  // This rendered an invented chain - four accesses by "user-001".."user-003",
  // a hash that matched nothing, and "Shared with legal team" - on an
  // evidentiary screen, while GET /api/alerts/{id}/custody served the real
  // report the whole time. Of everything on this page that was fabricated,
  // this is the one someone might have relied on.
  //
  // The report is per-asset and this panel had no way to name one, which is
  // presumably why it was never wired. It picks from the workspace's alerts.
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [report, setReport] = useState<CustodyReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void (async () => {
      try {
        const { items } = await listAlerts({ limit: 50 });
        setAlerts(items);
        setSelected((current) => current ?? items[0]?.id ?? null);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Could not load alerts.");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const load = useCallback(async (alertId: string) => {
    setError(null);
    try {
      setReport(await getChainOfCustody(alertId));
    } catch (err) {
      setReport(null);
      setError(err instanceof Error ? err.message : "Could not load the report.");
    }
  }, []);

  useEffect(() => {
    if (selected) void load(selected);
  }, [selected, load]);

  if (loading) {
    return <p className="text-sm text-gray-500">Loading&hellip;</p>;
  }

  if (alerts.length === 0) {
    return (
      <p className="text-sm text-gray-500">
        No alerts in this workspace, so there is no evidence to trace.
      </p>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-900">Chain of Custody</h2>
        <p className="text-sm text-gray-500">
          Track who accessed and modified evidence
        </p>
      </div>

      <label className="block">
        <span className="text-xs uppercase tracking-wider text-gray-500">Alert</span>
        <select
          value={selected ?? ""}
          onChange={(e) => setSelected(e.target.value)}
          className="mt-1 block w-full rounded border-gray-300 text-sm"
        >
          {alerts.map((alert) => (
            <option key={alert.id} value={alert.id}>
              {alert.rule_name ?? alert.message ?? alert.id}
            </option>
          ))}
        </select>
      </label>

      {error && <p className="text-sm text-red-600">{error}</p>}

      {!report ? (
        <p className="text-sm text-gray-500">
          No custody record for this alert. Entries are written when evidence is
          viewed, downloaded, exported or shared.
        </p>
      ) : (
      <>

      {/* Summary stats */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <div className="rounded-lg border border-gray-200 bg-white p-4">
          <p className="text-xs text-gray-500 uppercase tracking-wider">Asset</p>
          <p className="mt-1 text-sm font-mono font-medium text-gray-900 truncate">
            {report.asset_id}
          </p>
        </div>
        <div className="rounded-lg border border-gray-200 bg-white p-4">
          <p className="text-xs text-gray-500 uppercase tracking-wider">Access Count</p>
          <p className="mt-1 text-2xl font-bold text-gray-900">{report.access_count}</p>
        </div>
        <div className="rounded-lg border border-gray-200 bg-white p-4">
          <p className="text-xs text-gray-500 uppercase tracking-wider">Unique Users</p>
          <p className="mt-1 text-2xl font-bold text-gray-900">{report.unique_users}</p>
        </div>
        <div className="rounded-lg border border-gray-200 bg-white p-4">
          <p className="text-xs text-gray-500 uppercase tracking-wider">Integrity</p>
          <div className="mt-1 flex items-center gap-2">
            <Badge variant={report.integrity.intact ? "success" : "error"}>
              {report.integrity.intact ? "Intact" : "Compromised"}
            </Badge>
          </div>
          <p className="mt-1 text-xs text-gray-500">{report.integrity.note}</p>
        </div>
      </div>

      {/* Hash display */}
      {report.integrity.hash && (
        <div className="rounded-lg border border-gray-200 bg-white p-4">
          <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">SHA-256 Hash</p>
          <p className="text-xs font-mono text-gray-600 break-all">{report.integrity.hash}</p>
        </div>
      )}

      {/* Custody timeline */}
      <div className="rounded-lg border border-gray-200 bg-white p-4">
        <h3 className="text-sm font-semibold text-gray-700 mb-4">Access Timeline</h3>
        <div className="relative pl-8">
          <div className="absolute left-3 top-0 bottom-0 w-px bg-gray-200" />
          {report.chain.map((entry, idx) => {
            const variant = actionVariant[entry.action] || "neutral";
            const iconPath = actionIcon[entry.action] || actionIcon.viewed;
            return (
              <div key={idx} className="relative mb-6 last:mb-0">
                {/* Timeline dot */}
                <div className="absolute -left-5 top-0 flex items-center justify-center h-6 w-6 rounded-full bg-white border-2 border-gray-200">
                  <svg
                    className="h-3.5 w-3.5 text-gray-500"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d={iconPath}
                    />
                  </svg>
                </div>

                {/* Content */}
                <div className="ml-2">
                  <div className="flex items-center gap-2 mb-1">
                    <Badge variant={variant}>{entry.action}</Badge>
                    <span className="text-xs text-gray-500">
                      {new Date(entry.timestamp).toLocaleString()}
                    </span>
                  </div>
                  <p className="text-sm text-gray-700">
                    <span className="font-medium">{entry.user.slice(0, 12)}</span>
                    {entry.details && (
                      <span className="text-gray-500"> &mdash; {entry.details}</span>
                    )}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {report.chain.length === 0 && (
        <div className="text-center py-12 text-gray-500">
          <p>No custody records found for this asset.</p>
        </div>
      )}
      </>
      )}
    </div>
  );
}
