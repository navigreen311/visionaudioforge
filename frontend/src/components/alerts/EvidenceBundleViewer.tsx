"use client";

import React, { useState } from "react";
import Badge from "@/components/ui/Badge";
import Button from "@/components/ui/Button";

interface BundleAsset {
  asset_id: string;
  added_at: string;
  type?: string;
}

interface EvidenceBundle {
  bundle_id: string;
  alert_id: string;
  case_id: string | null;
  created_at: string;
  clips: BundleAsset[];
  snapshots: BundleAsset[];
  events: BundleAsset[];
}

/** Placeholder data — wired to API in production. */
const MOCK_BUNDLES: EvidenceBundle[] = [
  {
    bundle_id: "bundle-001",
    alert_id: "alert-001",
    case_id: "CASE-100",
    created_at: new Date(Date.now() - 1800000).toISOString(),
    clips: [
      { asset_id: "clip-001", added_at: new Date(Date.now() - 1700000).toISOString() },
    ],
    snapshots: [
      { asset_id: "snap-001", added_at: new Date(Date.now() - 1750000).toISOString() },
    ],
    events: [
      { asset_id: "event-001", added_at: new Date(Date.now() - 1600000).toISOString() },
    ],
  },
];

export default function EvidenceBundleViewer() {
  const [bundles] = useState<EvidenceBundle[]>(MOCK_BUNDLES);
  const [expandedBundle, setExpandedBundle] = useState<string | null>(null);

  const toggleExpand = (bundleId: string) => {
    setExpandedBundle(expandedBundle === bundleId ? null : bundleId);
  };

  const handleExport = (bundleId: string, format: string) => {
    // In production: GET /api/alerts/incidents/{id}/bundle?format=json
    alert(`Exporting bundle ${bundleId} as ${format}`);
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-900">Evidence Bundles</h2>
        <p className="text-sm text-gray-500">
          Collected evidence for alert investigations
        </p>
      </div>

      <div className="space-y-3">
        {bundles.map((bundle) => (
          <div
            key={bundle.bundle_id}
            className="rounded-lg border border-gray-200 bg-white shadow-sm"
          >
            {/* Bundle header */}
            <div
              className="p-4 cursor-pointer hover:bg-gray-50 transition-colors"
              onClick={() => toggleExpand(bundle.bundle_id)}
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-sm font-medium text-gray-900">
                      Bundle {bundle.bundle_id.slice(0, 8)}
                    </span>
                    {bundle.case_id && (
                      <Badge variant="info">{bundle.case_id}</Badge>
                    )}
                  </div>
                  <div className="flex items-center gap-3 text-xs text-gray-500">
                    <span>Alert: {bundle.alert_id.slice(0, 8)}</span>
                    <span>{new Date(bundle.created_at).toLocaleString()}</span>
                    <span>
                      {bundle.clips.length} clip{bundle.clips.length !== 1 ? "s" : ""},
                      {" "}{bundle.snapshots.length} snapshot{bundle.snapshots.length !== 1 ? "s" : ""},
                      {" "}{bundle.events.length} event{bundle.events.length !== 1 ? "s" : ""}
                    </span>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <svg
                    className={`h-4 w-4 text-gray-400 transition-transform ${
                      expandedBundle === bundle.bundle_id ? "rotate-180" : ""
                    }`}
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </div>
              </div>
            </div>

            {/* Expanded content */}
            {expandedBundle === bundle.bundle_id && (
              <div className="border-t border-gray-100 p-4 space-y-4">
                {/* Clips section */}
                {bundle.clips.length > 0 && (
                  <div>
                    <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
                      Video Clips
                    </h4>
                    <div className="space-y-1">
                      {bundle.clips.map((clip) => (
                        <div
                          key={clip.asset_id}
                          className="flex items-center gap-2 text-sm text-gray-700 p-2 rounded bg-gray-50"
                        >
                          <svg className="h-4 w-4 text-indigo-500 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                          </svg>
                          <span className="font-mono text-xs">{clip.asset_id.slice(0, 12)}</span>
                          <Badge variant="info">Auto-captured</Badge>
                          <span className="text-xs text-gray-400 ml-auto">
                            {new Date(clip.added_at).toLocaleTimeString()}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Snapshots section */}
                {bundle.snapshots.length > 0 && (
                  <div>
                    <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
                      Snapshots
                    </h4>
                    <div className="space-y-1">
                      {bundle.snapshots.map((snap) => (
                        <div
                          key={snap.asset_id}
                          className="flex items-center gap-2 text-sm text-gray-700 p-2 rounded bg-gray-50"
                        >
                          <svg className="h-4 w-4 text-green-500 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                          </svg>
                          <span className="font-mono text-xs">{snap.asset_id.slice(0, 12)}</span>
                          <span className="text-xs text-gray-400 ml-auto">
                            {new Date(snap.added_at).toLocaleTimeString()}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Events section */}
                {bundle.events.length > 0 && (
                  <div>
                    <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
                      Events
                    </h4>
                    <div className="space-y-1">
                      {bundle.events.map((evt) => (
                        <div
                          key={evt.asset_id}
                          className="flex items-center gap-2 text-sm text-gray-700 p-2 rounded bg-gray-50"
                        >
                          <svg className="h-4 w-4 text-amber-500 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                          </svg>
                          <span className="font-mono text-xs">{evt.asset_id.slice(0, 12)}</span>
                          <span className="text-xs text-gray-400 ml-auto">
                            {new Date(evt.added_at).toLocaleTimeString()}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Actions */}
                <div className="flex gap-2 pt-2 border-t border-gray-100">
                  <Button
                    variant="primary"
                    size="sm"
                    onClick={() => handleExport(bundle.bundle_id, "json")}
                  >
                    Export JSON
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleExport(bundle.bundle_id, "pdf_stub")}
                  >
                    Export PDF (stub)
                  </Button>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>

      {bundles.length === 0 && (
        <div className="text-center py-12 text-gray-500">
          <p>No evidence bundles yet. Create one from an incident or alert.</p>
        </div>
      )}
    </div>
  );
}
