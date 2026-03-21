"use client";

import { useState, useEffect } from "react";
import BYOMTab from "@/components/marketplace/BYOMTab";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface Plugin {
  name: string;
  category: string;
  description: string;
  version: string;
  author?: string;
  install_count?: number;
  avg_rating?: number;
  plugin_id?: string;
  enabled?: boolean;
}


// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const CATEGORIES = [
  "all",
  "vision",
  "audio",
  "transform",
  "pipeline_node",
  "integration",
  "analytics",
  "model",
];

const CATEGORY_COLORS: Record<string, string> = {
  vision: "bg-purple-100 text-purple-700",
  audio: "bg-blue-100 text-blue-700",
  transform: "bg-green-100 text-green-700",
  pipeline_node: "bg-yellow-100 text-yellow-700",
  integration: "bg-pink-100 text-pink-700",
  analytics: "bg-indigo-100 text-indigo-700",
  model: "bg-red-100 text-red-700",
};

const CATEGORY_ICONS: Record<string, string> = {
  vision: "👁",
  audio: "🎧",
  transform: "🔄",
  pipeline_node: "⚙️",
  integration: "🔗",
  analytics: "📊",
  model: "🧠",
};

const WIDGET_TYPES = [
  "live_feed",
  "alert_badge",
  "search_bar",
  "metric_card",
  "chart",
  "copilot_mini",
];


// ---------------------------------------------------------------------------
// Helper: star rating display
// ---------------------------------------------------------------------------

function Stars({ rating }: { rating: number }) {
  return (
    <span className="flex items-center gap-0.5">
      {[1, 2, 3, 4, 5].map((n) => (
        <svg
          key={n}
          className={`h-4 w-4 ${n <= Math.round(rating) ? "text-yellow-400" : "text-gray-300"}`}
          fill="currentColor"
          viewBox="0 0 20 20"
        >
          <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
        </svg>
      ))}
      <span className="ml-1 text-xs text-gray-500">{rating > 0 ? rating.toFixed(1) : "N/A"}</span>
    </span>
  );
}

// ---------------------------------------------------------------------------
// Main Page
// ---------------------------------------------------------------------------

export default function MarketplacePage() {
  const [tab, setTab] = useState<"browse" | "installed" | "byom" | "widgets">("browse");
  const [category, setCategory] = useState("all");
  const [search, setSearch] = useState("");
  const [plugins, setPlugins] = useState<Plugin[]>([]);
  const [installed, setInstalled] = useState<Plugin[]>([]);
  const [embedCode, setEmbedCode] = useState("");
  const [selectedWidget, setSelectedWidget] = useState(WIDGET_TYPES[0]);

  // Marketplace data — seeded from built-in list
  useEffect(() => {
    const builtIn: Plugin[] = [
      { name: "CSV Exporter", category: "integration", description: "Export any data as CSV", version: "1.0", install_count: 342, avg_rating: 4.2 },
      { name: "Slack Notifier", category: "integration", description: "Send alerts to Slack", version: "1.0", install_count: 510, avg_rating: 4.5 },
      { name: "Image Watermarker", category: "transform", description: "Add watermarks to images", version: "1.0", install_count: 128, avg_rating: 3.9 },
      { name: "Audio Normalizer", category: "transform", description: "Batch normalize audio files", version: "1.0", install_count: 95, avg_rating: 4.0 },
      { name: "YOLO Detector", category: "vision", description: "Object detection with YOLOv8", version: "1.0", install_count: 876, avg_rating: 4.8 },
      { name: "Whisper Transcriber", category: "audio", description: "Speech-to-text with Whisper", version: "1.0", install_count: 654, avg_rating: 4.7 },
      { name: "Sentiment Analyzer", category: "analytics", description: "Text sentiment analysis", version: "1.0", install_count: 231, avg_rating: 4.1 },
      { name: "Report Generator", category: "analytics", description: "Auto-generate PDF reports", version: "1.0", install_count: 189, avg_rating: 3.8 },
    ];
    setPlugins(builtIn);
  }, []);

  // -- filtered plugins for browse tab
  const filtered = plugins.filter((p) => {
    if (category !== "all" && p.category !== category) return false;
    if (search && !p.name.toLowerCase().includes(search.toLowerCase()) && !p.description.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  // -- handlers
  const handleInstall = (plugin: Plugin) => {
    if (installed.find((i) => i.name === plugin.name)) return;
    setInstalled((prev) => [...prev, { ...plugin, enabled: true, plugin_id: crypto.randomUUID() }]);
  };

  const handleToggle = (pluginId: string) => {
    setInstalled((prev) =>
      prev.map((p) => (p.plugin_id === pluginId ? { ...p, enabled: !p.enabled } : p))
    );
  };

  const handleUninstall = (pluginId: string) => {
    setInstalled((prev) => prev.filter((p) => p.plugin_id !== pluginId));
  };

  const handleGenerateEmbed = () => {
    const token = btoa(crypto.randomUUID());
    const url = `https://app.vaf.io/embed/${selectedWidget}?token=${token}`;
    setEmbedCode(`<iframe src="${url}" width="400" height="300" frameborder="0" allowtransparency="true"></iframe>`);
  };

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Plugin Marketplace</h1>
        <p className="text-sm text-gray-500 mt-1">
          Browse, install, and manage plugins. Bring your own models or embed widgets anywhere.
        </p>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-gray-200">
        {(["browse", "installed", "byom", "widgets"] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              tab === t
                ? "border-brand-600 text-brand-600"
                : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
          >
            {t === "browse" ? "Browse" : t === "installed" ? "Installed" : t === "byom" ? "BYOM" : "Widgets"}
          </button>
        ))}
      </div>

      {/* ================================================================= */}
      {/* Browse Tab                                                        */}
      {/* ================================================================= */}
      {tab === "browse" && (
        <div className="space-y-4">
          {/* Filters */}
          <div className="flex flex-wrap gap-3 items-center">
            <input
              type="text"
              placeholder="Search plugins..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="rounded-lg border border-gray-300 px-4 py-2 text-sm w-64 focus:border-brand-500 focus:ring-1 focus:ring-brand-500 focus:outline-none"
            />
            <div className="flex gap-1 flex-wrap">
              {CATEGORIES.map((cat) => (
                <button
                  key={cat}
                  onClick={() => setCategory(cat)}
                  className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
                    category === cat
                      ? "bg-brand-600 text-white"
                      : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                  }`}
                >
                  {cat === "all" ? "All" : cat.replace("_", " ")}
                </button>
              ))}
            </div>
          </div>

          {/* Plugin Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {filtered.map((plugin) => {
              const isInstalled = installed.some((i) => i.name === plugin.name);
              return (
                <div
                  key={plugin.name}
                  className="border border-gray-200 rounded-xl bg-white p-4 flex flex-col gap-3 shadow-sm hover:shadow-md transition-shadow"
                >
                  {/* Icon + Category */}
                  <div className="flex items-start justify-between">
                    <span className="text-3xl">
                      {CATEGORY_ICONS[plugin.category] || "🔌"}
                    </span>
                    <span
                      className={`px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase ${
                        CATEGORY_COLORS[plugin.category] || "bg-gray-100 text-gray-600"
                      }`}
                    >
                      {plugin.category}
                    </span>
                  </div>

                  {/* Name + version */}
                  <div>
                    <h3 className="text-sm font-semibold text-gray-900">{plugin.name}</h3>
                    <p className="text-xs text-gray-400">v{plugin.version}</p>
                  </div>

                  {/* Description */}
                  <p className="text-xs text-gray-600 flex-1">{plugin.description}</p>

                  {/* Rating + installs */}
                  <div className="flex items-center justify-between">
                    <Stars rating={plugin.avg_rating || 0} />
                    <span className="text-[10px] text-gray-400">
                      {plugin.install_count?.toLocaleString() || 0} installs
                    </span>
                  </div>

                  {/* Install button */}
                  <button
                    onClick={() => handleInstall(plugin)}
                    disabled={isInstalled}
                    className={`w-full py-1.5 rounded-lg text-sm font-medium transition-colors ${
                      isInstalled
                        ? "bg-gray-100 text-gray-400 cursor-not-allowed"
                        : "bg-brand-600 text-white hover:bg-brand-700"
                    }`}
                  >
                    {isInstalled ? "Installed" : "Install"}
                  </button>
                </div>
              );
            })}
          </div>

          {filtered.length === 0 && (
            <p className="text-center text-gray-400 py-12 text-sm">No plugins match your search.</p>
          )}
        </div>
      )}

      {/* ================================================================= */}
      {/* Installed Tab                                                     */}
      {/* ================================================================= */}
      {tab === "installed" && (
        <div className="space-y-3">
          {installed.length === 0 && (
            <p className="text-center text-gray-400 py-12 text-sm">
              No plugins installed yet. Browse the marketplace to get started.
            </p>
          )}
          {installed.map((plugin) => (
            <div
              key={plugin.plugin_id}
              className="flex items-center gap-4 border border-gray-200 rounded-xl bg-white p-4 shadow-sm"
            >
              <span className="text-2xl">{CATEGORY_ICONS[plugin.category] || "🔌"}</span>
              <div className="flex-1 min-w-0">
                <h3 className="text-sm font-semibold text-gray-900">{plugin.name}</h3>
                <p className="text-xs text-gray-500">{plugin.description}</p>
              </div>
              <span
                className={`px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase ${
                  CATEGORY_COLORS[plugin.category] || "bg-gray-100 text-gray-600"
                }`}
              >
                {plugin.category}
              </span>

              {/* Enable/Disable toggle */}
              <button
                onClick={() => handleToggle(plugin.plugin_id!)}
                className={`relative w-10 h-5 rounded-full transition-colors ${
                  plugin.enabled ? "bg-brand-600" : "bg-gray-300"
                }`}
              >
                <span
                  className={`absolute top-0.5 left-0.5 h-4 w-4 rounded-full bg-white shadow transition-transform ${
                    plugin.enabled ? "translate-x-5" : ""
                  }`}
                />
              </button>

              {/* Configure */}
              <button className="px-3 py-1 text-xs border border-gray-300 rounded-lg text-gray-600 hover:bg-gray-50">
                Configure
              </button>

              {/* Uninstall */}
              <button
                onClick={() => handleUninstall(plugin.plugin_id!)}
                className="px-3 py-1 text-xs border border-red-200 rounded-lg text-red-600 hover:bg-red-50"
              >
                Uninstall
              </button>
            </div>
          ))}
        </div>
      )}

      {/* ================================================================= */}
      {/* BYOM Tab                                                          */}
      {/* ================================================================= */}
      {tab === "byom" && <BYOMTab />}

      {/* ================================================================= */}
      {/* Widgets Tab                                                       */}
      {/* ================================================================= */}
      {tab === "widgets" && (
        <div className="space-y-6">
          <div className="border border-gray-200 rounded-xl bg-white p-6 shadow-sm space-y-4">
            <h2 className="text-lg font-semibold text-gray-900">Widget Builder</h2>
            <p className="text-sm text-gray-500">
              Generate embeddable widgets to integrate VAF into any webpage.
            </p>

            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
              {WIDGET_TYPES.map((wt) => (
                <button
                  key={wt}
                  onClick={() => setSelectedWidget(wt)}
                  className={`p-3 rounded-xl border text-center text-sm transition-colors ${
                    selectedWidget === wt
                      ? "border-brand-600 bg-brand-50 text-brand-700 font-semibold"
                      : "border-gray-200 text-gray-600 hover:border-gray-300"
                  }`}
                >
                  {wt.replace("_", " ")}
                </button>
              ))}
            </div>

            <button
              onClick={handleGenerateEmbed}
              className="px-6 py-2 bg-brand-600 text-white text-sm font-medium rounded-lg hover:bg-brand-700 transition-colors"
            >
              Generate Embed Code
            </button>

            {embedCode && (
              <div className="space-y-2">
                <label className="block text-xs font-medium text-gray-600">
                  Embed Code (copy and paste into your page)
                </label>
                <div className="relative">
                  <pre className="bg-gray-900 text-green-400 text-xs p-4 rounded-lg overflow-x-auto">
                    {embedCode}
                  </pre>
                  <button
                    onClick={() => navigator.clipboard.writeText(embedCode)}
                    className="absolute top-2 right-2 px-2 py-1 bg-gray-700 text-gray-200 text-[10px] rounded hover:bg-gray-600"
                  >
                    Copy
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
