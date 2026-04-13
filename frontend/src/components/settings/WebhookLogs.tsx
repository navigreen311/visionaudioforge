"use client";

import React, { useEffect, useState } from "react";
import api from "@/lib/api";

interface WebhookLog {
  id: string;
  event: string;
  status: "delivered" | "failed" | "pending";
  response_code: number | null;
  latency_ms: number | null;
  timestamp: string;
  payload: Record<string, unknown>;
}

const STATUS_BADGE: Record<string, string> = {
  delivered: "bg-green-100 text-green-800",
  failed: "bg-red-100 text-red-800",
  pending: "bg-gray-100 text-gray-800",
};

function responseCodeColor(code: number | null): string {
  if (code === null) return "text-gray-400";
  if (code < 300) return "text-green-600";
  if (code < 500) return "text-amber-600";
  return "text-red-600";
}

export default function WebhookLogs() {
  const [logs, setLogs] = useState<WebhookLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedRow, setExpandedRow] = useState<string | null>(null);
  const [retrying, setRetrying] = useState<string | null>(null);

  useEffect(() => {
    api
      .get("/api/settings/integrations/webhook/logs")
      .then((res) => setLogs(res.data.logs))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const handleRetry = async (log: WebhookLog) => {
    setRetrying(log.id);
    try {
      await api.post("/api/settings/integrations/webhook/retry", {
        delivery_id: log.id,
      });
      // Optimistic update
      setLogs((prev) =>
        prev.map((l) =>
          l.id === log.id ? { ...l, status: "pending" as const, response_code: null, latency_ms: null } : l
        )
      );
    } catch {
      // ignore
    } finally {
      setRetrying(null);
    }
  };

  if (loading) {
    return (
      <div className="py-8 text-center text-sm text-gray-400">Loading webhook logs...</div>
    );
  }

  return (
    <div>
      <h2 className="text-lg font-semibold text-gray-900 mb-4">Webhook Delivery Log</h2>

      <div className="overflow-x-auto border border-gray-200 rounded-lg">
        <table className="min-w-full divide-y divide-gray-200 text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-2 text-left font-medium text-gray-500">Timestamp</th>
              <th className="px-4 py-2 text-left font-medium text-gray-500">Event</th>
              <th className="px-4 py-2 text-left font-medium text-gray-500">Status</th>
              <th className="px-4 py-2 text-left font-medium text-gray-500">Response Code</th>
              <th className="px-4 py-2 text-left font-medium text-gray-500">Latency</th>
              <th className="px-4 py-2 text-left font-medium text-gray-500">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 bg-white">
            {logs.map((log) => (
              <React.Fragment key={log.id}>
                <tr className="hover:bg-gray-50">
                  <td className="px-4 py-2 whitespace-nowrap text-gray-600">
                    {new Date(log.timestamp).toLocaleString()}
                  </td>
                  <td className="px-4 py-2 whitespace-nowrap font-mono text-gray-800">
                    {log.event}
                  </td>
                  <td className="px-4 py-2 whitespace-nowrap">
                    <span
                      className={`inline-block px-2 py-0.5 rounded text-xs font-medium capitalize ${
                        STATUS_BADGE[log.status] || ""
                      }`}
                    >
                      {log.status}
                    </span>
                  </td>
                  <td
                    className={`px-4 py-2 whitespace-nowrap font-mono font-medium ${responseCodeColor(
                      log.response_code
                    )}`}
                  >
                    {log.response_code ?? "--"}
                  </td>
                  <td className="px-4 py-2 whitespace-nowrap text-gray-600">
                    {log.latency_ms !== null ? `${log.latency_ms} ms` : "--"}
                  </td>
                  <td className="px-4 py-2 whitespace-nowrap space-x-2">
                    <button
                      onClick={() =>
                        setExpandedRow(expandedRow === log.id ? null : log.id)
                      }
                      className="text-blue-600 hover:text-blue-800 text-xs font-medium"
                    >
                      {expandedRow === log.id ? "Hide payload" : "View payload"}
                    </button>
                    {log.status === "failed" && (
                      <button
                        onClick={() => handleRetry(log)}
                        disabled={retrying === log.id}
                        className="text-amber-600 hover:text-amber-800 text-xs font-medium disabled:opacity-50"
                      >
                        {retrying === log.id ? "Retrying..." : "Retry"}
                      </button>
                    )}
                  </td>
                </tr>
                {expandedRow === log.id && (
                  <tr>
                    <td colSpan={6} className="px-4 py-3 bg-gray-50">
                      <pre className="text-xs font-mono text-gray-700 overflow-auto max-h-48">
                        {JSON.stringify(log.payload, null, 2)}
                      </pre>
                    </td>
                  </tr>
                )}
              </React.Fragment>
            ))}
            {logs.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-gray-400">
                  No webhook delivery logs found.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
