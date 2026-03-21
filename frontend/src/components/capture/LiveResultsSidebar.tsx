"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";

interface Detection {
  label: string;
  confidence: number;
  category: string;
}

interface OcrRegion {
  text: string;
  boundingBox: [number, number, number, number];
  confidence: number;
}

interface MotionVector {
  direction: string;
  magnitude: number;
  region: string;
}

export interface AnalysisResults {
  detections: Detection[];
  ocr_regions: OcrRegion[];
  motion_vectors: MotionVector[];
}

interface LiveResultsSidebarProps {
  results: AnalysisResults | null;
}

const CATEGORY_COLORS: Record<string, string> = {
  person: "#185FA5",
  vehicle: "#0F6E56",
  animal: "#A32D2D",
  object: "#185FA5",
  text: "#0F6E56",
};

function getCategoryColor(category: string): string {
  return CATEGORY_COLORS[category.toLowerCase()] ?? "#185FA5";
}

function CollapsibleSection({
  title,
  count,
  defaultOpen = true,
  children,
}: {
  title: string;
  count: number;
  defaultOpen?: boolean;
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <div className="border border-gray-700 rounded-lg overflow-hidden">
      <button
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        className="w-full flex items-center justify-between px-3 py-2 bg-gray-800 hover:bg-gray-750 transition-colors"
      >
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold text-gray-300 uppercase tracking-wider">
            {title}
          </span>
          <span className="text-[10px] font-mono bg-gray-700 text-gray-400 px-1.5 py-0.5 rounded-full">
            {count}
          </span>
        </div>
        <svg
          className={`w-3.5 h-3.5 text-gray-500 transition-transform duration-200 ${
            open ? "rotate-0" : "-rotate-90"
          }`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      {open && <div className="px-3 py-2 space-y-2">{children}</div>}
    </div>
  );
}

function ConfidenceBar({
  label,
  confidence,
  color,
}: {
  label: string;
  confidence: number;
  color: string;
}) {
  const pct = Math.round(confidence * 100);
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between">
        <span className="text-xs text-gray-300 font-medium truncate max-w-[140px]">
          {label}
        </span>
        <span className="text-[11px] font-mono text-gray-400">{pct}%</span>
      </div>
      <div className="h-1.5 bg-gray-700 rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-300"
          style={{ width: `${pct}%`, backgroundColor: color }}
        />
      </div>
    </div>
  );
}

function SkeletonBlock({ lines }: { lines: number }) {
  return (
    <div className="space-y-3 animate-pulse">
      {Array.from({ length: lines }).map((_, i) => (
        <div key={i} className="space-y-1.5">
          <div className="flex justify-between">
            <div className="h-3 bg-gray-700 rounded w-24" />
            <div className="h-3 bg-gray-700 rounded w-10" />
          </div>
          <div className="h-1.5 bg-gray-700 rounded-full" />
        </div>
      ))}
    </div>
  );
}

function getDominantMotion(vectors: MotionVector[]): {
  direction: string;
  magnitude: number;
} | null {
  if (vectors.length === 0) return null;
  const sorted = [...vectors].sort((a, b) => b.magnitude - a.magnitude);
  return { direction: sorted[0].direction, magnitude: sorted[0].magnitude };
}

export default function LiveResultsSidebar({ results }: LiveResultsSidebarProps) {
  const router = useRouter();
  const [copyLabel, setCopyLabel] = useState("Copy Results");

  const handleCopy = useCallback(async () => {
    if (!results) return;
    try {
      await navigator.clipboard.writeText(JSON.stringify(results, null, 2));
      setCopyLabel("Copied!");
      setTimeout(() => setCopyLabel("Copy Results"), 2000);
    } catch {
      setCopyLabel("Copy failed");
      setTimeout(() => setCopyLabel("Copy Results"), 2000);
    }
  }, [results]);

  const handleSendToCopilot = useCallback(() => {
    if (!results) return;
    const context = encodeURIComponent(
      JSON.stringify({
        detections: results.detections,
        ocrText: results.ocr_regions.map((r) => r.text),
        motionSummary: getDominantMotion(results.motion_vectors),
      })
    );
    router.push(`/agents?context=${context}`);
  }, [results, router]);

  // Loading skeleton
  if (results === null) {
    return (
      <div className="bg-gray-900 border border-gray-700 rounded-lg p-4 space-y-4">
        <div className="h-4 bg-gray-700 rounded w-32 animate-pulse" />
        <SkeletonBlock lines={3} />
        <div className="h-px bg-gray-700" />
        <SkeletonBlock lines={2} />
        <div className="h-px bg-gray-700" />
        <SkeletonBlock lines={2} />
      </div>
    );
  }

  const hasDetections = results.detections.length > 0;
  const hasOcr = results.ocr_regions.length > 0;
  const hasMotion = results.motion_vectors.length > 0;
  const dominant = getDominantMotion(results.motion_vectors);
  const hasAnyData = hasDetections || hasOcr || hasMotion;

  return (
    <div className="bg-gray-900 border border-gray-700 rounded-lg overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 bg-gray-800 border-b border-gray-700">
        <h3 className="text-sm font-semibold text-white tracking-wide uppercase">
          Live Results
        </h3>
      </div>

      <div className="p-3 space-y-3">
        {!hasAnyData && (
          <p className="text-xs text-gray-500 text-center py-4">
            No analysis results yet. Enable overlays and start capture.
          </p>
        )}

        {/* Detections Section */}
        {hasDetections && (
          <CollapsibleSection title="Detections" count={results.detections.length}>
            {results.detections.map((det, idx) => (
              <ConfidenceBar
                key={`${det.label}-${idx}`}
                label={det.label}
                confidence={det.confidence}
                color={getCategoryColor(det.category)}
              />
            ))}
          </CollapsibleSection>
        )}

        {/* OCR Section */}
        {hasOcr && (
          <CollapsibleSection title="OCR Text" count={results.ocr_regions.length}>
            <div className="space-y-1.5">
              {results.ocr_regions.map((region, idx) => (
                <div
                  key={`ocr-${idx}`}
                  className="flex items-start gap-2 text-xs bg-gray-800 rounded px-2 py-1.5"
                >
                  <span className="text-[#0F6E56] font-mono shrink-0">TXT</span>
                  <span className="text-gray-300 break-all">{region.text}</span>
                </div>
              ))}
            </div>
          </CollapsibleSection>
        )}

        {/* Motion Section */}
        {hasMotion && dominant && (
          <CollapsibleSection title="Motion" count={results.motion_vectors.length}>
            <div className="space-y-2">
              <div className="flex items-center justify-between text-xs">
                <span className="text-gray-400">Dominant Direction</span>
                <span className="text-white font-medium">{dominant.direction}</span>
              </div>
              <div className="flex items-center justify-between text-xs">
                <span className="text-gray-400">Magnitude</span>
                <div className="flex items-center gap-2">
                  <div className="w-16 h-1.5 bg-gray-700 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-[#185FA5] rounded-full transition-all duration-300"
                      style={{ width: `${Math.min(dominant.magnitude * 100, 100)}%` }}
                    />
                  </div>
                  <span className="text-white font-mono text-[11px]">
                    {dominant.magnitude.toFixed(2)}
                  </span>
                </div>
              </div>
            </div>
          </CollapsibleSection>
        )}

        {/* Action Buttons */}
        {hasAnyData && (
          <div className="flex gap-2 pt-2 border-t border-gray-700">
            <button
              type="button"
              onClick={handleCopy}
              className="flex-1 px-3 py-2 text-xs font-medium text-gray-300 bg-gray-800 hover:bg-gray-700 border border-gray-600 rounded-lg transition-colors"
            >
              {copyLabel}
            </button>
            <button
              type="button"
              onClick={handleSendToCopilot}
              className="flex-1 px-3 py-2 text-xs font-medium text-white bg-[#185FA5] hover:bg-[#14508a] rounded-lg transition-colors"
            >
              Send to Copilot
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
