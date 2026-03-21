"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface Detection {
  label: string;
  confidence: number;
  bbox: number[];
}

interface OcrRegion {
  text: string;
  confidence: number;
}

interface MotionVector {
  direction: string;
  magnitude: number;
}

export interface AnalysisResults {
  detections: Detection[];
  ocr_regions: OcrRegion[];
  motion_vectors: MotionVector[];
}

interface LiveResultsSidebarProps {
  results: AnalysisResults | null;
  isLoading?: boolean;
}

/* ------------------------------------------------------------------ */
/*  Constants                                                          */
/* ------------------------------------------------------------------ */

const CATEGORY_COLORS: Record<string, string> = {
  person: "#185FA5",
  vehicle: "#0F6E56",
  animal: "#D97706",
  object: "#6B7280",
};

const DIRECTION_ARROWS: Record<string, string> = {
  up: "\u2191",
  down: "\u2193",
  left: "\u2190",
  right: "\u2192",
  "up-left": "\u2196",
  "up-right": "\u2197",
  "down-left": "\u2199",
  "down-right": "\u2198",
};

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

function inferCategory(label: string): string {
  const lower = label.toLowerCase();
  if (
    lower.includes("person") ||
    lower.includes("human") ||
    lower.includes("face") ||
    lower.includes("pedestrian")
  )
    return "person";
  if (
    lower.includes("car") ||
    lower.includes("truck") ||
    lower.includes("bus") ||
    lower.includes("vehicle") ||
    lower.includes("motorcycle") ||
    lower.includes("bicycle")
  )
    return "vehicle";
  if (
    lower.includes("dog") ||
    lower.includes("cat") ||
    lower.includes("bird") ||
    lower.includes("animal") ||
    lower.includes("horse")
  )
    return "animal";
  return "object";
}

function getCategoryColor(label: string): string {
  const category = inferCategory(label);
  return CATEGORY_COLORS[category] ?? CATEGORY_COLORS.object;
}

function getDirectionArrow(direction: string): string {
  return DIRECTION_ARROWS[direction.toLowerCase()] ?? "\u2194";
}

function getDominantMotion(
  vectors: MotionVector[]
): { direction: string; magnitude: number } | null {
  if (vectors.length === 0) return null;
  const sorted = [...vectors].sort((a, b) => b.magnitude - a.magnitude);
  return { direction: sorted[0].direction, magnitude: sorted[0].magnitude };
}

function getConfidenceBadgeClasses(confidence: number): string {
  if (confidence >= 0.9)
    return "bg-emerald-900/50 text-emerald-400 border-emerald-700/50";
  if (confidence >= 0.7)
    return "bg-blue-900/50 text-blue-400 border-blue-700/50";
  if (confidence >= 0.5)
    return "bg-amber-900/50 text-amber-400 border-amber-700/50";
  return "bg-red-900/50 text-red-400 border-red-700/50";
}

/* ------------------------------------------------------------------ */
/*  Sub-components                                                     */
/* ------------------------------------------------------------------ */

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
        aria-expanded={open}
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
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M19 9l-7 7-7-7"
          />
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
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-1.5 min-w-0">
          <span
            className="w-2 h-2 rounded-full shrink-0"
            style={{ backgroundColor: color }}
          />
          <span className="text-xs text-gray-300 font-medium truncate">
            {label}
          </span>
        </div>
        <span className="text-[11px] font-mono text-gray-400 shrink-0">
          {pct}%
        </span>
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

function OcrItem({ region }: { region: OcrRegion }) {
  const pct = Math.round(region.confidence * 100);
  const badgeClasses = getConfidenceBadgeClasses(region.confidence);

  return (
    <div className="flex items-start justify-between gap-2 text-xs bg-gray-800 rounded px-2.5 py-2">
      <span className="text-gray-300 break-words min-w-0">{region.text}</span>
      <span
        className={`shrink-0 text-[10px] font-mono px-1.5 py-0.5 rounded border ${badgeClasses}`}
      >
        {pct}%
      </span>
    </div>
  );
}

function MotionDisplay({ vectors }: { vectors: MotionVector[] }) {
  const dominant = getDominantMotion(vectors);
  if (!dominant) return null;

  return (
    <div className="space-y-3">
      {/* Dominant direction with arrow */}
      <div className="flex items-center gap-3">
        <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-gray-800 border border-gray-700">
          <span className="text-xl text-[#185FA5]">
            {getDirectionArrow(dominant.direction)}
          </span>
        </div>
        <div className="space-y-0.5">
          <div className="text-xs text-gray-400">Dominant Direction</div>
          <div className="text-sm text-white font-medium capitalize">
            {dominant.direction}
          </div>
        </div>
      </div>

      {/* Magnitude bar */}
      <div className="space-y-1">
        <div className="flex items-center justify-between text-xs">
          <span className="text-gray-400">Magnitude</span>
          <span className="text-white font-mono text-[11px]">
            {dominant.magnitude.toFixed(2)}
          </span>
        </div>
        <div className="h-1.5 bg-gray-700 rounded-full overflow-hidden">
          <div
            className="h-full bg-[#185FA5] rounded-full transition-all duration-300"
            style={{
              width: `${Math.min(dominant.magnitude * 100, 100)}%`,
            }}
          />
        </div>
      </div>

      {/* Vector breakdown for multiple vectors */}
      {vectors.length > 1 && (
        <div className="space-y-1 pt-1 border-t border-gray-700/50">
          <div className="text-[10px] text-gray-500 uppercase tracking-wider">
            All vectors
          </div>
          {vectors.map((v, idx) => (
            <div
              key={`motion-${idx}`}
              className="flex items-center justify-between text-[11px]"
            >
              <div className="flex items-center gap-1.5 text-gray-400">
                <span className="text-[#185FA5]">
                  {getDirectionArrow(v.direction)}
                </span>
                <span className="capitalize">{v.direction}</span>
              </div>
              <span className="font-mono text-gray-500">
                {v.magnitude.toFixed(2)}
              </span>
            </div>
          ))}
        </div>
      )}
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

function LoadingSkeleton() {
  return (
    <div className="bg-gray-900 border border-gray-700 rounded-lg overflow-hidden">
      <div className="px-4 py-3 bg-gray-800 border-b border-gray-700">
        <div className="h-4 bg-gray-700 rounded w-28 animate-pulse" />
      </div>
      <div className="p-3 space-y-4">
        <SkeletonBlock lines={3} />
        <div className="h-px bg-gray-700" />
        <SkeletonBlock lines={2} />
        <div className="h-px bg-gray-700" />
        <SkeletonBlock lines={2} />
      </div>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-8 px-4 text-center">
      <svg
        className="w-10 h-10 text-gray-600 mb-3"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        strokeWidth={1.5}
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M9.75 3.104v5.714a2.25 2.25 0 0 1-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 0 1 4.5 0m0 0v5.714c0 .597.237 1.17.659 1.591L19.8 15.3M14.25 3.104c.251.023.501.05.75.082M19.8 15.3l-1.57.393A9.065 9.065 0 0 1 12 15a9.065 9.065 0 0 0-6.23.693L5 14.5m14.8.8 1.402 1.402c1.232 1.232.65 3.318-1.067 3.611A48.309 48.309 0 0 1 12 21c-2.773 0-5.491-.235-8.135-.687-1.718-.293-2.3-2.379-1.067-3.61L5 14.5"
        />
      </svg>
      <p className="text-xs text-gray-500 max-w-[200px]">
        AI analysis results will appear here when overlays are active
      </p>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Main component                                                     */
/* ------------------------------------------------------------------ */

export default function LiveResultsSidebar({
  results,
  isLoading = false,
}: LiveResultsSidebarProps) {
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
    const summary = {
      detections: results.detections.map((d) => ({
        label: d.label,
        confidence: d.confidence,
      })),
      ocrText: results.ocr_regions.map((r) => r.text),
      motionSummary: getDominantMotion(results.motion_vectors),
    };
    const context = encodeURIComponent(JSON.stringify(summary));
    router.push(`/agents?context=${context}`);
  }, [results, router]);

  /* Loading skeleton state */
  if (isLoading) {
    return <LoadingSkeleton />;
  }

  const hasDetections = results !== null && results.detections.length > 0;
  const hasOcr = results !== null && results.ocr_regions.length > 0;
  const hasMotion = results !== null && results.motion_vectors.length > 0;
  const hasAnyData = hasDetections || hasOcr || hasMotion;

  return (
    <div className="bg-gray-900 border border-gray-700 rounded-lg overflow-hidden w-full">
      {/* Header */}
      <div className="px-4 py-3 bg-gray-800 border-b border-gray-700 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-white tracking-wide uppercase">
          Live Results
        </h3>
        {hasAnyData && (
          <span className="relative flex h-2.5 w-2.5">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#0F6E56] opacity-75" />
            <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-[#0F6E56]" />
          </span>
        )}
      </div>

      <div className="p-3 space-y-3">
        {/* Empty state */}
        {!hasAnyData && <EmptyState />}

        {/* Detections Section */}
        {hasDetections && results && (
          <CollapsibleSection
            title="Detections"
            count={results.detections.length}
          >
            {results.detections.map((det, idx) => (
              <ConfidenceBar
                key={`${det.label}-${idx}`}
                label={det.label}
                confidence={det.confidence}
                color={getCategoryColor(det.label)}
              />
            ))}
          </CollapsibleSection>
        )}

        {/* OCR Section */}
        {hasOcr && results && (
          <CollapsibleSection
            title="OCR Text"
            count={results.ocr_regions.length}
          >
            <div className="space-y-1.5">
              {results.ocr_regions.map((region, idx) => (
                <OcrItem key={`ocr-${idx}`} region={region} />
              ))}
            </div>
          </CollapsibleSection>
        )}

        {/* Motion Section */}
        {hasMotion && results && (
          <CollapsibleSection
            title="Motion"
            count={results.motion_vectors.length}
          >
            <MotionDisplay vectors={results.motion_vectors} />
          </CollapsibleSection>
        )}

        {/* Action Buttons */}
        {hasAnyData && (
          <div className="flex flex-col sm:flex-row gap-2 pt-2 border-t border-gray-700">
            <button
              type="button"
              onClick={handleCopy}
              className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 text-xs font-medium text-gray-300 bg-gray-800 hover:bg-gray-700 border border-gray-600 rounded-lg transition-colors"
            >
              <svg
                className="w-3.5 h-3.5"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M15.666 3.888A2.25 2.25 0 0 0 13.5 2.25h-3c-1.03 0-1.9.693-2.166 1.638m7.332 0c.055.194.084.4.084.612v0a.75.75 0 0 1-.75.75H9.75a.75.75 0 0 1-.75-.75v0c0-.212.03-.418.084-.612m7.332 0c.646.049 1.288.11 1.927.184 1.1.128 1.907 1.077 1.907 2.185V19.5a2.25 2.25 0 0 1-2.25 2.25H6.75A2.25 2.25 0 0 1 4.5 19.5V6.257c0-1.108.806-2.057 1.907-2.185a48.208 48.208 0 0 1 1.927-.184"
                />
              </svg>
              {copyLabel}
            </button>
            <button
              type="button"
              onClick={handleSendToCopilot}
              className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 text-xs font-medium text-white bg-[#185FA5] hover:bg-[#14508a] rounded-lg transition-colors"
            >
              <svg
                className="w-3.5 h-3.5"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M6 12 3.269 3.125A59.769 59.769 0 0 1 21.485 12 59.768 59.768 0 0 1 3.27 20.875L5.999 12Zm0 0h7.5"
                />
              </svg>
              Send to Copilot
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
