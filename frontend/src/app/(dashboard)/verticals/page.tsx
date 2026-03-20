"use client";

import React, { useState } from "react";
import Card from "@/components/ui/Card";
import Badge from "@/components/ui/Badge";

// ---------------------------------------------------------------------------
// Vertical pack definitions (mirrors backend AVAILABLE_PACKS)
// ---------------------------------------------------------------------------

interface VerticalPack {
  slug: string;
  name: string;
  icon: string;
  description: string;
  category: string;
  pipelineCount: number;
  alertPresetCount: number;
}

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
// Component
// ---------------------------------------------------------------------------

export default function VerticalsPage() {
  const [installed, setInstalled] = useState<Record<string, boolean>>({});
  const [loading, setLoading] = useState<string | null>(null);

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

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Vertical Packs</h1>
        <p className="mt-1 text-sm text-gray-500">
          Industry-specific starter packs with pre-built pipelines, alert
          presets, dashboards, and reports.
        </p>
      </div>

      {/* Gallery Grid */}
      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
        {VERTICAL_PACKS.map((pack) => {
          const isInstalled = !!installed[pack.slug];
          const isLoading = loading === pack.slug;

          return (
            <Card key={pack.slug}>
              <div className="flex flex-col gap-4">
                {/* Icon + Title */}
                <div className="flex items-center gap-3">
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
    </div>
  );
}
