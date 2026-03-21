"use client";

import { useState } from "react";

// ---------------------------------------------------------------------------
// Node definition types
// ---------------------------------------------------------------------------

interface PaletteNode {
  type: string;
  name: string;
  description: string;
  icon: React.ReactNode;
}

interface PaletteCategory {
  key: string;
  label: string;
  borderColor: string;
  dotColor: string;
  nodes: PaletteNode[];
}

// ---------------------------------------------------------------------------
// SVG icon helpers (16x16, stroke-based)
// ---------------------------------------------------------------------------

const iconClass = "w-4 h-4 flex-shrink-0";

function CameraIcon() {
  return (
    <svg className={iconClass} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z" />
      <circle cx="12" cy="13" r="4" />
    </svg>
  );
}

function ScreenIcon() {
  return (
    <svg className={iconClass} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="2" y="3" width="20" height="14" rx="2" />
      <line x1="8" y1="21" x2="16" y2="21" />
      <line x1="12" y1="17" x2="12" y2="21" />
    </svg>
  );
}

function MicIcon() {
  return (
    <svg className={iconClass} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
      <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
      <line x1="12" y1="19" x2="12" y2="23" />
      <line x1="8" y1="23" x2="16" y2="23" />
    </svg>
  );
}

function UploadIcon() {
  return (
    <svg className={iconClass} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
      <polyline points="17 8 12 3 7 8" />
      <line x1="12" y1="3" x2="12" y2="15" />
    </svg>
  );
}

function ClockIcon() {
  return (
    <svg className={iconClass} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10" />
      <polyline points="12 6 12 12 16 14" />
    </svg>
  );
}

function WebhookInIcon() {
  return (
    <svg className={iconClass} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
      <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
    </svg>
  );
}

function PreprocessIcon() {
  return (
    <svg className={iconClass} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polygon points="12 2 2 7 12 12 22 7 12 2" />
      <polyline points="2 17 12 22 22 17" />
      <polyline points="2 12 12 17 22 12" />
    </svg>
  );
}

function ObjectDetectIcon() {
  return (
    <svg className={iconClass} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="3" width="18" height="18" rx="2" />
      <rect x="7" y="7" width="10" height="10" rx="1" strokeDasharray="3 2" />
      <circle cx="12" cy="12" r="2" />
    </svg>
  );
}

function FlowIcon() {
  return (
    <svg className={iconClass} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
    </svg>
  );
}

function OcrIcon() {
  return (
    <svg className={iconClass} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="4 7 4 4 20 4 20 7" />
      <line x1="9" y1="20" x2="15" y2="20" />
      <line x1="12" y1="4" x2="12" y2="20" />
    </svg>
  );
}

function SegmentIcon() {
  return (
    <svg className={iconClass} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="3" width="7" height="7" />
      <rect x="14" y="3" width="7" height="7" />
      <rect x="14" y="14" width="7" height="7" />
      <rect x="3" y="14" width="7" height="7" />
    </svg>
  );
}

function ScreenReadIcon() {
  return (
    <svg className={iconClass} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="2" y="3" width="20" height="14" rx="2" />
      <line x1="6" y1="8" x2="18" y2="8" />
      <line x1="6" y1="12" x2="14" y2="12" />
      <line x1="8" y1="21" x2="16" y2="21" />
      <line x1="12" y1="17" x2="12" y2="21" />
    </svg>
  );
}

function WaveformIcon() {
  return (
    <svg className={iconClass} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="4" y1="8" x2="4" y2="16" />
      <line x1="8" y1="4" x2="8" y2="20" />
      <line x1="12" y1="6" x2="12" y2="18" />
      <line x1="16" y1="9" x2="16" y2="15" />
      <line x1="20" y1="7" x2="20" y2="17" />
    </svg>
  );
}

function MfccIcon() {
  return (
    <svg className={iconClass} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="3" width="18" height="18" rx="2" />
      <line x1="7" y1="8" x2="7" y2="16" />
      <line x1="10" y1="6" x2="10" y2="18" />
      <line x1="13" y1="10" x2="13" y2="14" />
      <line x1="16" y1="7" x2="16" y2="17" />
    </svg>
  );
}

function TranscribeIcon() {
  return (
    <svg className={iconClass} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
    </svg>
  );
}

function DenoiseIcon() {
  return (
    <svg className={iconClass} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M11 5L6 9H2v6h4l5 4V5z" />
      <line x1="23" y1="9" x2="17" y2="15" />
      <line x1="17" y1="9" x2="23" y2="15" />
    </svg>
  );
}

function SplitIcon() {
  return (
    <svg className={iconClass} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="18" cy="5" r="3" />
      <circle cx="18" cy="19" r="3" />
      <circle cx="6" cy="12" r="3" />
      <line x1="8.59" y1="13.51" x2="15.42" y2="17.49" />
      <line x1="15.41" y1="6.51" x2="8.59" y2="10.49" />
    </svg>
  );
}

function BgRemoveIcon() {
  return (
    <svg className={iconClass} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="3" width="18" height="18" rx="2" />
      <circle cx="8.5" cy="8.5" r="1.5" />
      <path d="M21 15l-5-5L5 21" />
    </svg>
  );
}

function ZoomInIcon() {
  return (
    <svg className={iconClass} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="11" cy="11" r="8" />
      <line x1="21" y1="21" x2="16.65" y2="16.65" />
      <line x1="11" y1="8" x2="11" y2="14" />
      <line x1="8" y1="11" x2="14" y2="11" />
    </svg>
  );
}

function PaintIcon() {
  return (
    <svg className={iconClass} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 19l7-7 3 3-7 7-3-3z" />
      <path d="M18 13l-1.5-7.5L2 2l3.5 14.5L13 18l5-5z" />
      <path d="M2 2l7.586 7.586" />
      <circle cx="11" cy="11" r="2" />
    </svg>
  );
}

function AudioEnhanceIcon() {
  return (
    <svg className={iconClass} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" />
      <path d="M19.07 4.93a10 10 0 0 1 0 14.14" />
      <path d="M15.54 8.46a5 5 0 0 1 0 7.07" />
    </svg>
  );
}

function FilterIcon() {
  return (
    <svg className={iconClass} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3" />
    </svg>
  );
}

function BranchIcon() {
  return (
    <svg className={iconClass} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="6" y1="3" x2="6" y2="15" />
      <circle cx="18" cy="6" r="3" />
      <circle cx="6" cy="18" r="3" />
      <path d="M18 9a9 9 0 0 1-9 9" />
    </svg>
  );
}

function MergeIcon() {
  return (
    <svg className={iconClass} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="18" r="3" />
      <circle cx="6" cy="6" r="3" />
      <circle cx="18" cy="6" r="3" />
      <path d="M6 9v3a6 6 0 0 0 6 6" />
      <path d="M18 9v3a6 6 0 0 1-6 6" />
    </svg>
  );
}

function DelayIcon() {
  return (
    <svg className={iconClass} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10" />
      <polyline points="12 6 12 12 8 14" />
    </svg>
  );
}

function LoopIcon() {
  return (
    <svg className={iconClass} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="17 1 21 5 17 9" />
      <path d="M3 11V9a4 4 0 0 1 4-4h14" />
      <polyline points="7 23 3 19 7 15" />
      <path d="M21 13v2a4 4 0 0 1-4 4H3" />
    </svg>
  );
}

function SaveIcon() {
  return (
    <svg className={iconClass} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z" />
      <polyline points="17 21 17 13 7 13 7 21" />
      <polyline points="7 3 7 8 15 8" />
    </svg>
  );
}

function AlertIcon() {
  return (
    <svg className={iconClass} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
      <path d="M13.73 21a2 2 0 0 1-3.46 0" />
    </svg>
  );
}

function ExportIcon() {
  return (
    <svg className={iconClass} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
      <polyline points="7 10 12 15 17 10" />
      <line x1="12" y1="15" x2="12" y2="3" />
    </svg>
  );
}

function WebhookOutIcon() {
  return (
    <svg className={iconClass} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="22" y1="2" x2="11" y2="13" />
      <polygon points="22 2 15 22 11 13 2 9 22 2" />
    </svg>
  );
}

function CaseIcon() {
  return (
    <svg className={iconClass} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
      <line x1="12" y1="11" x2="12" y2="17" />
      <line x1="9" y1="14" x2="15" y2="14" />
    </svg>
  );
}

// ---------------------------------------------------------------------------
// Category definitions with nodes
// ---------------------------------------------------------------------------

const CATEGORIES: PaletteCategory[] = [
  {
    key: "input",
    label: "Input",
    borderColor: "border-l-blue-500",
    dotColor: "bg-blue-500",
    nodes: [
      { type: "camera_feed", name: "Camera Feed", description: "Live camera video stream input", icon: <CameraIcon /> },
      { type: "screen_capture", name: "Screen Capture", description: "Capture desktop or window region", icon: <ScreenIcon /> },
      { type: "microphone", name: "Microphone", description: "Live audio input from mic", icon: <MicIcon /> },
      { type: "file_upload", name: "File Upload", description: "Upload image, video, or audio files", icon: <UploadIcon /> },
      { type: "schedule_trigger", name: "Schedule Trigger", description: "Start pipeline on a timed schedule", icon: <ClockIcon /> },
      { type: "webhook_trigger", name: "Webhook Trigger", description: "Start pipeline from an HTTP webhook", icon: <WebhookInIcon /> },
    ],
  },
  {
    key: "vision",
    label: "Vision",
    borderColor: "border-l-teal-500",
    dotColor: "bg-teal-500",
    nodes: [
      { type: "preprocess", name: "Preprocess", description: "Resize, normalize, and color-convert", icon: <PreprocessIcon /> },
      { type: "object_detect", name: "Object Detect", description: "Detect and label objects in frames", icon: <ObjectDetectIcon /> },
      { type: "optical_flow", name: "Optical Flow", description: "Track motion between frames", icon: <FlowIcon /> },
      { type: "ocr_extract", name: "OCR Extract", description: "Extract text from images or video", icon: <OcrIcon /> },
      { type: "segment", name: "Segment", description: "Semantic or instance segmentation", icon: <SegmentIcon /> },
      { type: "screen_read", name: "Screen Read", description: "Parse structured UI elements", icon: <ScreenReadIcon /> },
    ],
  },
  {
    key: "audio",
    label: "Audio",
    borderColor: "border-l-purple-500",
    dotColor: "bg-purple-500",
    nodes: [
      { type: "stft_analyze", name: "STFT Analyze", description: "Short-time Fourier transform analysis", icon: <WaveformIcon /> },
      { type: "mfcc_extract", name: "MFCC Extract", description: "Extract MFCC audio features", icon: <MfccIcon /> },
      { type: "transcribe", name: "Transcribe", description: "Speech-to-text transcription", icon: <TranscribeIcon /> },
      { type: "denoise", name: "Denoise", description: "Remove noise from audio signal", icon: <DenoiseIcon /> },
      { type: "source_separate", name: "Source Separate", description: "Isolate vocals, instruments, etc.", icon: <SplitIcon /> },
    ],
  },
  {
    key: "transform",
    label: "Transform",
    borderColor: "border-l-amber-500",
    dotColor: "bg-amber-500",
    nodes: [
      { type: "background_remove", name: "Background Remove", description: "Remove or replace backgrounds", icon: <BgRemoveIcon /> },
      { type: "super_resolution", name: "Super Resolution", description: "Upscale image or video quality", icon: <ZoomInIcon /> },
      { type: "style_transfer", name: "Style Transfer", description: "Apply artistic style to frames", icon: <PaintIcon /> },
      { type: "audio_enhance", name: "Audio Enhance", description: "Boost clarity and loudness", icon: <AudioEnhanceIcon /> },
    ],
  },
  {
    key: "logic",
    label: "Logic",
    borderColor: "border-l-gray-500",
    dotColor: "bg-gray-500",
    nodes: [
      { type: "filter", name: "Filter", description: "Pass or block data by condition", icon: <FilterIcon /> },
      { type: "branch", name: "Branch", description: "Route data down different paths", icon: <BranchIcon /> },
      { type: "merge", name: "Merge", description: "Combine multiple streams into one", icon: <MergeIcon /> },
      { type: "delay", name: "Delay", description: "Pause pipeline for a set duration", icon: <DelayIcon /> },
      { type: "loop", name: "Loop", description: "Repeat a sub-pipeline N times", icon: <LoopIcon /> },
    ],
  },
  {
    key: "output",
    label: "Output",
    borderColor: "border-l-red-400",
    dotColor: "bg-red-400",
    nodes: [
      { type: "save_to_assets", name: "Save to Assets", description: "Store results in the asset library", icon: <SaveIcon /> },
      { type: "send_alert", name: "Send Alert", description: "Push notification or email alert", icon: <AlertIcon /> },
      { type: "export_file", name: "Export File", description: "Download result as a file", icon: <ExportIcon /> },
      { type: "post_webhook", name: "Post Webhook", description: "Send data to an external endpoint", icon: <WebhookOutIcon /> },
      { type: "add_to_case", name: "Add to Case", description: "Attach output to an investigation case", icon: <CaseIcon /> },
    ],
  },
];

// ---------------------------------------------------------------------------
// Map category key -> label for dataTransfer
// ---------------------------------------------------------------------------

const CATEGORY_MAP: Record<string, string> = {};
for (const cat of CATEGORIES) {
  for (const node of cat.nodes) {
    CATEGORY_MAP[node.type] = cat.label;
  }
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function NodePalette() {
  const [search, setSearch] = useState("");
  const [openCategories, setOpenCategories] = useState<Set<string>>(
    () => new Set(CATEGORIES.map((c) => c.key)),
  );

  const toggleCategory = (key: string) => {
    setOpenCategories((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  const onDragStart = (
    event: React.DragEvent<HTMLDivElement>,
    node: PaletteNode,
  ) => {
    const payload = {
      type: node.type,
      category: CATEGORY_MAP[node.type] ?? "Unknown",
      description: node.description,
      inputs: {},
      outputs: {},
    };
    event.dataTransfer.setData(
      "application/reactflow",
      JSON.stringify(payload),
    );
    event.dataTransfer.effectAllowed = "move";
  };

  const lowerSearch = search.toLowerCase();

  return (
    <aside className="w-64 bg-white border-r border-gray-200 overflow-y-auto flex-shrink-0 flex flex-col">
      {/* Search */}
      <div className="p-3 border-b border-gray-100">
        <div className="relative">
          <svg
            className="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <circle cx="11" cy="11" r="8" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search nodes..."
            className="w-full pl-8 pr-3 py-1.5 text-sm border border-gray-200 rounded-md focus:outline-none focus:ring-1 focus:ring-brand-500 focus:border-brand-500"
          />
        </div>
      </div>

      {/* Categories */}
      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        {CATEGORIES.map((category) => {
          const filteredNodes = category.nodes.filter(
            (n) =>
              !lowerSearch ||
              n.name.toLowerCase().includes(lowerSearch) ||
              n.description.toLowerCase().includes(lowerSearch),
          );

          if (lowerSearch && filteredNodes.length === 0) return null;

          const isOpen = openCategories.has(category.key);

          return (
            <div key={category.key}>
              {/* Category header */}
              <button
                onClick={() => toggleCategory(category.key)}
                className="w-full flex items-center justify-between px-2 py-1.5 text-sm font-medium text-gray-600 hover:bg-gray-50 rounded"
              >
                <span className="flex items-center gap-1.5">
                  <span
                    className={`w-2 h-2 rounded-full ${category.dotColor}`}
                  />
                  {category.label}
                  <span className="text-xs text-gray-400">
                    ({filteredNodes.length})
                  </span>
                </span>
                <span className="text-xs text-gray-400">
                  {isOpen ? "\u25BE" : "\u25B8"}
                </span>
              </button>

              {/* Nodes */}
              {isOpen && (
                <div className="ml-1 space-y-0.5">
                  {filteredNodes.map((node) => (
                    <div
                      key={node.type}
                      draggable
                      onDragStart={(e) => onDragStart(e, node)}
                      className={`flex items-start gap-2 px-2 py-1.5 text-sm rounded cursor-grab active:cursor-grabbing transition-colors border-l-[3px] ${category.borderColor} bg-gray-50 hover:bg-gray-100`}
                    >
                      <span className="text-gray-500 mt-0.5">{node.icon}</span>
                      <div className="min-w-0">
                        <div className="font-medium text-gray-800 leading-tight">
                          {node.name}
                        </div>
                        <div className="text-xs text-gray-400 leading-tight truncate">
                          {node.description}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </aside>
  );
}
