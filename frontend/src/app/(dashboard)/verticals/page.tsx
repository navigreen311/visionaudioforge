"use client";

import React, { useMemo, useState } from "react";
import Card from "@/components/ui/Card";
import Badge from "@/components/ui/Badge";
import Modal from "@/components/ui/Modal";
import Button from "@/components/ui/Button";
import PackFilterBar from "@/components/verticals/PackFilterBar";
import PackDetailPanel from "@/components/verticals/PackDetailPanel";
import type { VerticalPackDetail } from "@/components/verticals/PackDetailPanel";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type ViewMode = "all" | "installed";

// ---------------------------------------------------------------------------
// Pack data (mirrors backend AVAILABLE_PACKS with manifest detail)
// ---------------------------------------------------------------------------

const VERTICAL_PACKS: VerticalPackDetail[] = [
  {
    slug: "security",
    name: "Security & Surveillance",
    icon: "\uD83D\uDEE1\uFE0F",
    description:
      "Perimeter monitoring, intrusion detection, license plate recognition, and incident management.",
    category: "Public Safety",
    pipelineCount: 2,
    alertPresetCount: 2,
    pipelines: [
      { name: "Perimeter Monitor", nodes: 4, description: "Motion-triggered zone surveillance with intrusion classification." },
      { name: "LPR Pipeline", nodes: 3, description: "License plate detection, OCR, and database lookup." },
    ],
    alertRules: [
      { name: "Perimeter Breach", condition: "intrusion_score > 0.85", severity: "Critical" },
      { name: "Unrecognized Vehicle", condition: "plate_match == false", severity: "Warning" },
    ],
    dashboards: ["Perimeter Overview", "Incident Timeline"],
    models: ["YOLOv8-Security", "LPR-OCR-v2"],
    sampleData: ["perimeter_clips.zip", "plate_images.tar.gz"],
    requirements: { storage: "~2 GB", modules: ["vision", "alerts"], conflicts: [] },
  },
  {
    slug: "healthcare",
    name: "Healthcare",
    icon: "\uD83C\uDFE5",
    description:
      "Patient monitoring, fall detection, hand-hygiene compliance, and clinical workflow analytics.",
    category: "Healthcare",
    pipelineCount: 2,
    alertPresetCount: 2,
    pipelines: [
      { name: "Fall Detection", nodes: 3, description: "Pose estimation with fall-event classification." },
      { name: "Hand Hygiene", nodes: 4, description: "Entry/exit zone tracking with hand-wash verification." },
    ],
    alertRules: [
      { name: "Fall Detected", condition: "fall_confidence > 0.9", severity: "Critical" },
      { name: "Hygiene Violation", condition: "wash_duration < 20s", severity: "Warning" },
    ],
    dashboards: ["Patient Safety", "Compliance Report"],
    models: ["PoseNet-Fall-v3", "HandWash-Classifier"],
    sampleData: ["fall_scenarios.zip"],
    requirements: { storage: "~1.5 GB", modules: ["vision", "alerts"], conflicts: [] },
  },
  {
    slug: "callcenter",
    name: "Call Center",
    icon: "\uD83C\uDFA7",
    description:
      "Call transcription, sentiment analysis, agent coaching, and SLA monitoring.",
    category: "Customer Service",
    pipelineCount: 2,
    alertPresetCount: 2,
    pipelines: [
      { name: "Call Transcription", nodes: 3, description: "Real-time STT with speaker diarization." },
      { name: "Sentiment Analysis", nodes: 2, description: "Per-utterance sentiment scoring and trend tracking." },
    ],
    alertRules: [
      { name: "Negative Sentiment Spike", condition: "avg_sentiment < -0.6", severity: "Warning" },
      { name: "SLA Breach", condition: "hold_time > 300s", severity: "Critical" },
    ],
    dashboards: ["Agent Performance", "SLA Tracker"],
    models: ["Whisper-Large-v3", "Sentiment-BERT"],
    sampleData: ["sample_calls.zip"],
    requirements: { storage: "~3 GB", modules: ["audio", "alerts"], conflicts: [] },
  },
  {
    slug: "retail",
    name: "Retail Analytics",
    icon: "\uD83D\uDED2",
    description:
      "Customer counting, heat-map analytics, shelf monitoring, queue management, and loss-prevention.",
    category: "Retail",
    pipelineCount: 5,
    alertPresetCount: 4,
    pipelines: [
      { name: "People Counter", nodes: 2, description: "Bi-directional counting at entry zones." },
      { name: "Heat Map", nodes: 3, description: "Dwell-time aggregation for spatial analytics." },
      { name: "Shelf Monitor", nodes: 4, description: "Out-of-stock and planogram compliance detection." },
      { name: "Queue Manager", nodes: 3, description: "Queue length estimation with wait-time prediction." },
      { name: "Loss Prevention", nodes: 5, description: "Suspicious behavior detection and tracking." },
    ],
    alertRules: [
      { name: "Queue Overflow", condition: "queue_length > 8", severity: "Warning" },
      { name: "Out of Stock", condition: "shelf_empty == true", severity: "Info" },
      { name: "Suspicious Activity", condition: "suspicion_score > 0.8", severity: "Critical" },
      { name: "Occupancy Limit", condition: "occupancy > max_capacity", severity: "Warning" },
    ],
    dashboards: ["Store Overview", "Traffic Patterns", "Shelf Compliance"],
    models: ["YOLOv8-Retail", "PoseTrack-v2", "ShelfNet"],
    sampleData: ["store_footage.zip", "shelf_images.tar.gz"],
    requirements: { storage: "~4 GB", modules: ["vision", "alerts", "analytics"], conflicts: [] },
  },
  {
    slug: "industrial",
    name: "Industrial Inspection",
    icon: "\uD83C\uDFED",
    description:
      "Equipment defect detection, PPE compliance, vibration analysis, production-line monitoring, and environmental sound classification.",
    category: "Manufacturing",
    pipelineCount: 5,
    alertPresetCount: 4,
    pipelines: [
      { name: "Defect Detection", nodes: 4, description: "Surface anomaly detection on manufactured parts." },
      { name: "PPE Compliance", nodes: 3, description: "Hardhat, vest, and goggles detection per zone." },
      { name: "Vibration Analysis", nodes: 2, description: "Spectral analysis of equipment vibration signatures." },
      { name: "Production Line", nodes: 5, description: "Throughput counting and bottleneck detection." },
      { name: "Sound Classification", nodes: 3, description: "Environmental audio anomaly detection." },
    ],
    alertRules: [
      { name: "Defect Rate High", condition: "defect_rate > 0.05", severity: "Critical" },
      { name: "PPE Violation", condition: "ppe_missing == true", severity: "Warning" },
      { name: "Abnormal Vibration", condition: "vibration_rms > threshold", severity: "Warning" },
      { name: "Line Stopped", condition: "throughput == 0 for 5m", severity: "Critical" },
    ],
    dashboards: ["Quality Overview", "Safety Compliance", "Production KPIs"],
    models: ["AnomalyNet-v2", "PPE-Detector", "VibNet", "AudioCLS"],
    sampleData: ["defect_samples.zip", "vibration_data.csv", "factory_audio.zip"],
    requirements: { storage: "~5 GB", modules: ["vision", "audio", "alerts"], conflicts: [] },
  },
  {
    slug: "media",
    name: "Media Production",
    icon: "\uD83C\uDFAC",
    description:
      "Content moderation, auto-highlight extraction, podcast production, subtitle generation, and thumbnail creation.",
    category: "Media & Entertainment",
    pipelineCount: 5,
    alertPresetCount: 3,
    pipelines: [
      { name: "Content Moderation", nodes: 3, description: "NSFW and violence classification for uploaded media." },
      { name: "Highlight Extractor", nodes: 4, description: "Key-moment detection for auto-clip generation." },
      { name: "Podcast Producer", nodes: 3, description: "Noise reduction, leveling, and chapter markers." },
      { name: "Subtitle Generator", nodes: 2, description: "Multi-language transcription with SRT export." },
      { name: "Thumbnail Creator", nodes: 3, description: "Frame selection and composition scoring." },
    ],
    alertRules: [
      { name: "NSFW Content", condition: "nsfw_score > 0.7", severity: "Critical" },
      { name: "Processing Failure", condition: "pipeline_error == true", severity: "Warning" },
      { name: "Low Quality Upload", condition: "quality_score < 0.3", severity: "Info" },
    ],
    dashboards: ["Content Pipeline", "Moderation Queue"],
    models: ["NSFW-Classifier", "SceneDetect-v2", "Whisper-Large-v3"],
    sampleData: ["sample_videos.zip", "podcast_episodes.zip"],
    requirements: { storage: "~6 GB", modules: ["vision", "audio", "transform"], conflicts: [] },
  },
  {
    slug: "education",
    name: "Education",
    icon: "\uD83C\uDF93",
    description:
      "Lecture transcription, engagement monitoring, lab safety detection, and accessibility captioning.",
    category: "Education",
    pipelineCount: 4,
    alertPresetCount: 3,
    pipelines: [
      { name: "Lecture Transcriber", nodes: 3, description: "Real-time lecture transcription with speaker labels." },
      { name: "Engagement Monitor", nodes: 4, description: "Attention and participation scoring from classroom video." },
      { name: "Lab Safety", nodes: 3, description: "PPE and hazardous behavior detection in lab environments." },
      { name: "Accessibility Captions", nodes: 2, description: "Live captioning with sign-language overlay support." },
    ],
    alertRules: [
      { name: "Low Engagement", condition: "engagement_score < 0.3", severity: "Info" },
      { name: "Lab Safety Violation", condition: "safety_violation == true", severity: "Critical" },
      { name: "Caption Lag", condition: "caption_delay > 5s", severity: "Warning" },
    ],
    dashboards: ["Classroom Analytics", "Lab Safety Dashboard"],
    models: ["Whisper-Med-v3", "EngagementNet", "LabSafety-Detector"],
    sampleData: ["lecture_recordings.zip", "lab_footage.zip"],
    requirements: { storage: "~3 GB", modules: ["vision", "audio", "alerts"], conflicts: [] },
  },
];

// ---------------------------------------------------------------------------
// Install confirmation modal
// ---------------------------------------------------------------------------

function InstallModal({
  pack,
  isOpen,
  onClose,
  onConfirm,
  loading,
}: {
  pack: VerticalPackDetail | null;
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  loading: boolean;
}) {
  if (!pack) return null;

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={`Install "${pack.name}"?`}
      footer={
        <>
          <Button variant="ghost" size="sm" onClick={onClose} disabled={loading}>
            Cancel
          </Button>
          <Button size="sm" onClick={onConfirm} loading={loading}>
            Confirm Install
          </Button>
        </>
      }
    >
      <div className="space-y-3 text-sm text-gray-600">
        <p>
          This will install <strong>{pack.pipelineCount}</strong> pipeline
          {pack.pipelineCount !== 1 ? "s" : ""},{" "}
          <strong>{pack.alertPresetCount}</strong> alert preset
          {pack.alertPresetCount !== 1 ? "s" : ""}, and associated dashboards,
          models, and sample data.
        </p>
        <p>
          <span className="font-medium text-gray-700">Storage required:</span>{" "}
          {pack.requirements.storage}
        </p>
        {pack.requirements.conflicts.length > 0 && (
          <div className="rounded-md bg-amber-50 border border-amber-200 p-3">
            <p className="text-amber-800 font-medium">Potential conflicts:</p>
            <ul className="list-disc list-inside text-amber-700 mt-1">
              {pack.requirements.conflicts.map((c) => (
                <li key={c}>{c}</li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </Modal>
  );
}

// ---------------------------------------------------------------------------
// Installed packs view
// ---------------------------------------------------------------------------

function InstalledPacksView({
  packs,
  onUninstall,
  onViewDetail,
  loading,
}: {
  packs: VerticalPackDetail[];
  onUninstall: (slug: string) => void;
  onViewDetail: (pack: VerticalPackDetail) => void;
  loading: string | null;
}) {
  if (packs.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-400 text-sm">No packs installed yet.</p>
        <p className="text-gray-400 text-xs mt-1">
          Switch to "All Packs" to browse and install.
        </p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
      {packs.map((pack) => {
        const isLoading = loading === pack.slug;
        return (
          <Card key={pack.slug}>
            <div className="flex flex-col gap-4">
              <div
                className="flex items-center gap-3 cursor-pointer"
                onClick={() => onViewDetail(pack)}
              >
                <span className="text-3xl">{pack.icon}</span>
                <div>
                  <h3 className="text-lg font-semibold text-gray-900">
                    {pack.name}
                  </h3>
                  <Badge variant="info">{pack.category}</Badge>
                </div>
              </div>
              <p className="text-sm text-gray-600 leading-relaxed">
                {pack.description}
              </p>
              <div className="flex gap-4 text-xs text-gray-500">
                <span>{pack.pipelineCount} pipelines</span>
                <span>{pack.alertPresetCount} alert presets</span>
              </div>
              <button
                onClick={() => onUninstall(pack.slug)}
                disabled={isLoading}
                className="w-full rounded-lg border border-red-200 bg-red-50 px-4 py-2 text-sm font-medium text-red-700 hover:bg-red-100 disabled:opacity-50 transition-colors"
              >
                {isLoading ? "Removing..." : "Uninstall"}
              </button>
            </div>
          </Card>
        );
      })}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Create pack modal (placeholder)
// ---------------------------------------------------------------------------

function CreatePackModal({
  isOpen,
  onClose,
}: {
  isOpen: boolean;
  onClose: () => void;
}) {
  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Create Custom Pack">
      <div className="space-y-4 text-sm text-gray-600">
        <p>
          Custom pack creation is coming soon. You will be able to bundle your
          own pipelines, alert rules, and dashboards into reusable packs.
        </p>
      </div>
    </Modal>
  );
}

// ---------------------------------------------------------------------------
// Category matching helper
// ---------------------------------------------------------------------------

function matchesCategory(packCategory: string, filter: string): boolean {
  if (filter === "All") return true;
  // Handle partial matches (e.g., "Media" matches "Media & Entertainment")
  return packCategory.toLowerCase().startsWith(filter.toLowerCase());
}

// ---------------------------------------------------------------------------
// Main page component
// ---------------------------------------------------------------------------

export default function VerticalsPage() {
  const [installed, setInstalled] = useState<Record<string, boolean>>({});
  const [loading, setLoading] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [activeCategory, setActiveCategory] = useState("All");
  const [activeView, setActiveView] = useState<ViewMode>("all");
  const [selectedPack, setSelectedPack] = useState<VerticalPackDetail | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);
  const [installModalPack, setInstallModalPack] = useState<VerticalPackDetail | null>(null);
  const [createModalOpen, setCreateModalOpen] = useState(false);

  // ---- Filtering ----
  const filteredPacks = useMemo(() => {
    return VERTICAL_PACKS.filter((pack) => {
      // Category filter
      if (!matchesCategory(pack.category, activeCategory)) return false;

      // Search filter
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const searchable = `${pack.name} ${pack.description} ${pack.category}`.toLowerCase();
        if (!searchable.includes(q)) return false;
      }

      return true;
    });
  }, [activeCategory, searchQuery]);

  const installedPacks = useMemo(() => {
    return filteredPacks.filter((p) => installed[p.slug]);
  }, [filteredPacks, installed]);

  // ---- Handlers ----
  const handleInstall = async (slug: string) => {
    setLoading(slug);
    // Simulate install (in production this calls POST /api/verticals/{slug}/install)
    await new Promise((r) => setTimeout(r, 600));
    setInstalled((prev) => ({ ...prev, [slug]: true }));
    setLoading(null);
    setInstallModalPack(null);
    setDetailOpen(false);
  };

  const handleUninstall = async (slug: string) => {
    setLoading(slug);
    await new Promise((r) => setTimeout(r, 400));
    setInstalled((prev) => ({ ...prev, [slug]: false }));
    setLoading(null);
  };

  const handleCardClick = (pack: VerticalPackDetail) => {
    setSelectedPack(pack);
    setDetailOpen(true);
  };

  const handleDetailClose = () => {
    setDetailOpen(false);
  };

  const handleDetailInstall = (slug: string) => {
    const pack = VERTICAL_PACKS.find((p) => p.slug === slug);
    if (pack) {
      setInstallModalPack(pack);
    }
  };

  const displayPacks = activeView === "installed" ? installedPacks : filteredPacks;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Vertical Packs</h1>
          <p className="mt-1 text-sm text-gray-500">
            Industry-specific starter packs with pre-built pipelines, alert
            presets, dashboards, and reports.
          </p>
        </div>
        <Button variant="primary" size="sm" onClick={() => setCreateModalOpen(true)}>
          + Create Pack
        </Button>
      </div>

      {/* Filter Bar */}
      <PackFilterBar
        onSearchChange={setSearchQuery}
        onCategoryChange={setActiveCategory}
        onViewChange={setActiveView}
        totalCount={VERTICAL_PACKS.length}
        filteredCount={displayPacks.length}
        searchQuery={searchQuery}
        activeCategory={activeCategory}
        activeView={activeView}
      />

      {/* Content */}
      {activeView === "installed" ? (
        <InstalledPacksView
          packs={installedPacks}
          onUninstall={handleUninstall}
          onViewDetail={handleCardClick}
          loading={loading}
        />
      ) : (
        <>
          {displayPacks.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-gray-400 text-sm">
                No packs match your filters.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
              {displayPacks.map((pack) => {
                const isInstalled = !!installed[pack.slug];
                const isLoading = loading === pack.slug;

                return (
                  <Card key={pack.slug}>
                    <div className="flex flex-col gap-4">
                      {/* Clickable header area */}
                      <div
                        className="flex items-center gap-3 cursor-pointer"
                        onClick={() => handleCardClick(pack)}
                      >
                        <span className="text-3xl">{pack.icon}</span>
                        <div>
                          <h3 className="text-lg font-semibold text-gray-900">
                            {pack.name}
                          </h3>
                          <Badge variant="info">{pack.category}</Badge>
                        </div>
                      </div>

                      {/* Description */}
                      <p className="text-sm text-gray-600 leading-relaxed">
                        {pack.description}
                      </p>

                      {/* Stats */}
                      <div className="flex gap-4 text-xs text-gray-500">
                        <span>{pack.pipelineCount} pipelines</span>
                        <span>{pack.alertPresetCount} alert presets</span>
                      </div>

                      {/* Install / Uninstall Button */}
                      {isInstalled ? (
                        <button
                          onClick={() => handleUninstall(pack.slug)}
                          disabled={isLoading}
                          className="w-full rounded-lg border border-red-200 bg-red-50 px-4 py-2 text-sm font-medium text-red-700 hover:bg-red-100 disabled:opacity-50 transition-colors"
                        >
                          {isLoading ? "Removing..." : "Uninstall"}
                        </button>
                      ) : (
                        <button
                          onClick={() => handleInstall(pack.slug)}
                          disabled={isLoading}
                          className="w-full rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50 transition-colors"
                        >
                          {isLoading ? "Installing..." : "Install Pack"}
                        </button>
                      )}
                    </div>
                  </Card>
                );
              })}
            </div>
          )}
        </>
      )}

      {/* Pack Detail slide-over */}
      <PackDetailPanel
        pack={selectedPack}
        isOpen={detailOpen}
        onClose={handleDetailClose}
        onInstall={handleDetailInstall}
      />

      {/* Install confirmation modal */}
      <InstallModal
        pack={installModalPack}
        isOpen={installModalPack !== null}
        onClose={() => setInstallModalPack(null)}
        onConfirm={() => {
          if (installModalPack) handleInstall(installModalPack.slug);
        }}
        loading={loading === installModalPack?.slug}
      />

      {/* Create pack modal */}
      <CreatePackModal
        isOpen={createModalOpen}
        onClose={() => setCreateModalOpen(false)}
      />
    </div>
  );
}
