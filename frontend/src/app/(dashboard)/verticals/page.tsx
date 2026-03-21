"use client";

import React, { useState, useEffect, useCallback } from "react";
import Card from "@/components/ui/Card";
import Badge from "@/components/ui/Badge";
import CreatePackModal, {
  getCustomPacks,
} from "@/components/verticals/CreatePackModal";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface VerticalPack {
  slug: string;
  name: string;
  icon: string;
  description: string;
  category: string;
  pipelineCount: number;
  alertPresetCount: number;
  installed_version?: string;
  latest_version?: string;
  isCustom?: boolean;
}

interface CustomPackData {
  slug: string;
  name: string;
  description: string;
  category: string;
  icon: string;
  pipelineIds: string[];
  pipelineNames: string[];
  alertRuleIds: string[];
  alertRuleNames: string[];
  createdAt: string;
  isCustom: true;
}

interface RemotePackInfo {
  slug: string;
  installed_version?: string;
  latest_version?: string;
}

// ---------------------------------------------------------------------------
// Preset icon rendering (matches CreatePackModal ICON_MAP keys)
// ---------------------------------------------------------------------------

const CUSTOM_ICON_SVG: Record<string, React.ReactNode> = {
  shield: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="h-7 w-7 text-brand-600">
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
    </svg>
  ),
  eye: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="h-7 w-7 text-brand-600">
      <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
    </svg>
  ),
  cog: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="h-7 w-7 text-brand-600">
      <path strokeLinecap="round" strokeLinejoin="round" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.573-1.066z" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
    </svg>
  ),
  chart: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="h-7 w-7 text-brand-600">
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
    </svg>
  ),
  bell: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="h-7 w-7 text-brand-600">
      <path strokeLinecap="round" strokeLinejoin="round" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
    </svg>
  ),
  camera: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="h-7 w-7 text-brand-600">
      <path strokeLinecap="round" strokeLinejoin="round" d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M15 13a3 3 0 11-6 0 3 3 0 016 0z" />
    </svg>
  ),
  mic: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="h-7 w-7 text-brand-600">
      <path strokeLinecap="round" strokeLinejoin="round" d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
    </svg>
  ),
  cube: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="h-7 w-7 text-brand-600">
      <path strokeLinecap="round" strokeLinejoin="round" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
    </svg>
  ),
};

// ---------------------------------------------------------------------------
// Vertical pack definitions (mirrors backend AVAILABLE_PACKS)
// ---------------------------------------------------------------------------

const VERTICAL_PACKS: VerticalPack[] = [
  {
    slug: "security",
    name: "Security & Surveillance",
    icon: "\uD83D\uDEE1\uFE0F",
    description:
      "Perimeter monitoring, intrusion detection, license plate recognition, and incident management.",
    category: "Public Safety",
    pipelineCount: 2,
    alertPresetCount: 2,
    installed_version: "1.0.0",
    latest_version: "1.2.0",
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
    installed_version: "2.1.0",
    latest_version: "2.1.0",
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
    installed_version: "1.3.0",
    latest_version: "1.5.0",
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
    installed_version: "1.0.0",
    latest_version: "1.0.0",
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
  },
];

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function hasUpdate(pack: VerticalPack): boolean {
  return !!(
    pack.installed_version &&
    pack.latest_version &&
    pack.installed_version !== pack.latest_version
  );
}

function isInstalled(pack: VerticalPack, installedState: Record<string, boolean>): boolean {
  return !!installedState[pack.slug] || !!pack.installed_version;
}

function customPackToVertical(cp: CustomPackData): VerticalPack {
  return {
    slug: cp.slug,
    name: cp.name,
    icon: cp.icon,
    description: cp.description,
    category: cp.category,
    pipelineCount: cp.pipelineIds.length,
    alertPresetCount: cp.alertRuleIds.length,
    isCustom: true,
  };
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function VerticalsPage() {
  const [installed, setInstalled] = useState<Record<string, boolean>>({});
  const [loading, setLoading] = useState<string | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [customPacks, setCustomPacks] = useState<VerticalPack[]>([]);
  const [remoteVersions, setRemoteVersions] = useState<Record<string, RemotePackInfo>>({});

  // Load custom packs from localStorage on mount
  useEffect(() => {
    try {
      const stored = getCustomPacks();
      setCustomPacks(stored.map(customPackToVertical));
    } catch {
      // localStorage unavailable
    }
  }, []);

  // Fetch remote version info (VP6)
  useEffect(() => {
    const fetchVersions = async () => {
      try {
        const res = await fetch("/api/verticals/packs");
        if (res.ok) {
          const data: RemotePackInfo[] = await res.json();
          const map: Record<string, RemotePackInfo> = {};
          for (const item of data) {
            map[item.slug] = item;
          }
          setRemoteVersions(map);
        }
      } catch {
        // API unavailable - use static version data from VERTICAL_PACKS
      }
    };
    fetchVersions();
  }, []);

  // Merge remote version data into packs
  const getPackVersions = useCallback(
    (pack: VerticalPack) => {
      const remote = remoteVersions[pack.slug];
      return {
        installed_version: remote?.installed_version ?? pack.installed_version,
        latest_version: remote?.latest_version ?? pack.latest_version,
      };
    },
    [remoteVersions],
  );

  const handleInstall = async (slug: string) => {
    setLoading(slug);
    // Simulate install (in production this calls POST /api/verticals/{slug}/install)
    await new Promise((r) => setTimeout(r, 600));
    setInstalled((prev) => ({ ...prev, [slug]: true }));
    setLoading(null);
  };

  const handleUninstall = async (slug: string) => {
    setLoading(slug);
    await new Promise((r) => setTimeout(r, 400));
    setInstalled((prev) => ({ ...prev, [slug]: false }));
    setLoading(null);
  };

  const handleDeleteCustom = (slug: string) => {
    try {
      const stored = getCustomPacks();
      const filtered = stored.filter((p) => p.slug !== slug);
      localStorage.setItem("vaf_custom_packs", JSON.stringify(filtered));
      setCustomPacks(filtered.map(customPackToVertical));
    } catch {
      // localStorage unavailable
    }
  };

  const handlePackCreated = (pack: CustomPackData) => {
    setShowCreateModal(false);
    setCustomPacks((prev) => [...prev, customPackToVertical(pack)]);
  };

  const allPacks = [...VERTICAL_PACKS, ...customPacks];

  // ---------------------------------------------------------------------------
  // Render a single pack card
  // ---------------------------------------------------------------------------

  const renderPackCard = (pack: VerticalPack) => {
    const versions = getPackVersions(pack);
    const packWithVersions = { ...pack, ...versions };
    const packInstalled = isInstalled(packWithVersions, installed);
    const packHasUpdate = hasUpdate(packWithVersions);
    const isLoading = loading === pack.slug;

    return (
      <Card key={pack.slug}>
        <div className="flex flex-col gap-4">
          {/* Icon + Title + Badges */}
          <div className="flex items-center gap-3">
            {pack.isCustom && pack.icon in CUSTOM_ICON_SVG ? (
              <span>{CUSTOM_ICON_SVG[pack.icon]}</span>
            ) : (
              <span className="text-3xl">{pack.icon}</span>
            )}
            <div className="flex-1 min-w-0">
              <h3 className="text-lg font-semibold text-gray-900">
                {pack.name}
              </h3>
              <div className="flex flex-wrap items-center gap-1.5 mt-0.5">
                <Badge variant="info">{pack.category}</Badge>
                {pack.isCustom && (
                  <Badge
                    variant="warning"
                    className="bg-amber-100 text-amber-800"
                  >
                    CUSTOM
                  </Badge>
                )}
                {packHasUpdate && (
                  <Badge
                    variant="warning"
                    className="bg-amber-100 text-amber-800"
                  >
                    Update available
                  </Badge>
                )}
              </div>
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
            {packWithVersions.installed_version && (
              <span className="ml-auto">
                v{packWithVersions.installed_version}
                {packWithVersions.latest_version &&
                  packWithVersions.installed_version !== packWithVersions.latest_version && (
                    <span className="text-amber-600">
                      {" "}
                      &rarr; v{packWithVersions.latest_version}
                    </span>
                  )}
              </span>
            )}
          </div>

          {/* Action Buttons */}
          <div className="flex gap-2">
            {packInstalled ? (
              <>
                {packHasUpdate ? (
                  <button
                    onClick={() => handleInstall(pack.slug)}
                    disabled={isLoading}
                    className="flex-1 rounded-lg bg-amber-500 px-4 py-2 text-sm font-medium text-white hover:bg-amber-600 disabled:opacity-50 transition-colors"
                  >
                    {isLoading ? "Updating..." : "Update Pack"}
                  </button>
                ) : (
                  <div className="flex-1" />
                )}
                <button
                  onClick={() => handleUninstall(pack.slug)}
                  disabled={isLoading}
                  className="rounded-lg border border-red-200 bg-red-50 px-4 py-2 text-sm font-medium text-red-700 hover:bg-red-100 disabled:opacity-50 transition-colors"
                >
                  {isLoading && !packHasUpdate ? "Removing..." : "Uninstall"}
                </button>
              </>
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

          {/* Delete custom pack */}
          {pack.isCustom && (
            <button
              onClick={() => handleDeleteCustom(pack.slug)}
              className="text-xs text-gray-400 hover:text-red-500 transition-colors self-end"
            >
              Delete custom pack
            </button>
          )}
        </div>
      </Card>
    );
  };

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

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
        <button
          onClick={() => setShowCreateModal(true)}
          className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 transition-colors flex items-center gap-2"
        >
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
          </svg>
          Create Pack
        </button>
      </div>

      {/* Gallery Grid */}
      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
        {allPacks.map(renderPackCard)}
      </div>

      {/* Create Pack Modal */}
      <CreatePackModal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        onCreated={handlePackCreated}
      />
    </div>
  );
}
