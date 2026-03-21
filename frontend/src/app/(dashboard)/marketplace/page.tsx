"use client";

import { useState, useEffect } from "react";
import StarPicker from "@/components/marketplace/StarPicker";
import WidgetsTab from "@/components/marketplace/WidgetsTab";

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

interface BYOMAdapter {
  adapter_id: string;
  model_name: string;
  framework: string;
  status: string;
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

const FRAMEWORKS = ["pytorch", "tensorflow", "onnx", "sklearn", "custom"];

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
  const [adapters, setAdapters] = useState<BYOMAdapter[]>([]);

  // Plugin detail + review state
  const [detailPlugin, setDetailPlugin] = useState<Plugin | null>(null);
  const [reviewRating, setReviewRating] = useState(0);
  const [reviewText, setReviewText] = useState("");
  const [reviewSubmitting, setReviewSubmitting] = useState(false);
  const [reviewSuccess, setReviewSuccess] = useState(false);

  // BYOM form state
  const [byomName, setByomName] = useState("");
  const [byomFramework, setByomFramework] = useState(FRAMEWORKS[0]);
  const [byomUrl, setByomUrl] = useState("");

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

  const handleByomRegister = () => {
    if (!byomName || !byomUrl) return;
    const adapter: BYOMAdapter = {
      adapter_id: crypto.randomUUID(),
      model_name: byomName,
      framework: byomFramework,
      status: "registered",
    };
    setAdapters((prev) => [...prev, adapter]);
    setByomName("");
    setByomUrl("");
  };

  const handleSubmitReview = async () => {
    if (!detailPlugin || reviewRating === 0 || reviewText.length < 20) return;
    setReviewSubmitting(true);
    try {
      const pluginId = detailPlugin.plugin_id || detailPlugin.name;
      await fetch(`/api/plugins/${encodeURIComponent(pluginId)}/reviews`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ rating: reviewRating, text: reviewText }),
      });
      setReviewSuccess(true);
      setReviewRating(0);
      setReviewText("");
      setTimeout(() => setReviewSuccess(false), 3000);
    } catch {
      // silently handle — stub endpoint
    } finally {
      setReviewSubmitting(false);
    }
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

                  {/* Install + Review buttons */}
                  <div className="flex gap-2">
                    <button
                      onClick={() => handleInstall(plugin)}
                      disabled={isInstalled}
                      className={`flex-1 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                        isInstalled
                          ? "bg-gray-100 text-gray-400 cursor-not-allowed"
                          : "bg-brand-600 text-white hover:bg-brand-700"
                      }`}
                    >
                      {isInstalled ? "Installed" : "Install"}
                    </button>
                    <button
                      onClick={() => {
                        setDetailPlugin(plugin);
                        setReviewRating(0);
                        setReviewText("");
                        setReviewSuccess(false);
                      }}
                      className="px-3 py-1.5 rounded-lg text-sm font-medium border border-gray-300 text-gray-600 hover:bg-gray-50 transition-colors"
                    >
                      Review
                    </button>
                  </div>
                </div>
              );
            })}
          </div>

          {filtered.length === 0 && (
            <p className="text-center text-gray-400 py-12 text-sm">No plugins match your search.</p>
          )}

          {/* Write a Review panel */}
          {detailPlugin && (
            <div className="border border-gray-200 rounded-xl bg-white p-6 shadow-sm space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold text-gray-900">
                  Write a Review &mdash; {detailPlugin.name}
                </h2>
                <button
                  onClick={() => setDetailPlugin(null)}
                  className="text-gray-400 hover:text-gray-600 text-sm"
                >
                  Close
                </button>
              </div>

              <div className="space-y-1">
                <label className="block text-xs font-medium text-gray-600">
                  Your Rating
                </label>
                <StarPicker rating={reviewRating} onChange={setReviewRating} />
              </div>

              <div className="space-y-1">
                <label className="block text-xs font-medium text-gray-600">
                  Your Review (min 20 characters)
                </label>
                <textarea
                  value={reviewText}
                  onChange={(e) => setReviewText(e.target.value)}
                  rows={4}
                  placeholder="Share your experience with this plugin..."
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:ring-1 focus:ring-brand-500 focus:outline-none resize-none"
                />
                <p className="text-[10px] text-gray-400">
                  {reviewText.length}/20 characters minimum
                </p>
              </div>

              {reviewSuccess && (
                <p className="text-sm text-green-600 font-medium">
                  Review submitted successfully!
                </p>
              )}

              <button
                onClick={handleSubmitReview}
                disabled={
                  reviewRating === 0 ||
                  reviewText.length < 20 ||
                  reviewSubmitting
                }
                className="px-6 py-2 bg-brand-600 text-white text-sm font-medium rounded-lg hover:bg-brand-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
              >
                {reviewSubmitting ? "Submitting..." : "Submit Review"}
              </button>
            </div>
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
      {tab === "byom" && (
        <div className="space-y-6">
          {/* Register form */}
          <div className="border border-gray-200 rounded-xl bg-white p-6 shadow-sm space-y-4">
            <h2 className="text-lg font-semibold text-gray-900">Register a Model</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Model Name</label>
                <input
                  type="text"
                  value={byomName}
                  onChange={(e) => setByomName(e.target.value)}
                  placeholder="my-custom-model"
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:ring-1 focus:ring-brand-500 focus:outline-none"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Framework</label>
                <select
                  value={byomFramework}
                  onChange={(e) => setByomFramework(e.target.value)}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:ring-1 focus:ring-brand-500 focus:outline-none"
                >
                  {FRAMEWORKS.map((fw) => (
                    <option key={fw} value={fw}>
                      {fw}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Model URL or Path</label>
                <input
                  type="text"
                  value={byomUrl}
                  onChange={(e) => setByomUrl(e.target.value)}
                  placeholder="https://models.example.com/model.pt"
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:ring-1 focus:ring-brand-500 focus:outline-none"
                />
              </div>
            </div>
            <button
              onClick={handleByomRegister}
              disabled={!byomName || !byomUrl}
              className="px-6 py-2 bg-brand-600 text-white text-sm font-medium rounded-lg hover:bg-brand-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
            >
              Register Model
            </button>
          </div>

          {/* Adapter list */}
          <div className="space-y-3">
            <h2 className="text-lg font-semibold text-gray-900">Your Models</h2>
            {adapters.length === 0 && (
              <p className="text-sm text-gray-400">No models registered yet.</p>
            )}
            {adapters.map((a) => (
              <div
                key={a.adapter_id}
                className="flex items-center gap-4 border border-gray-200 rounded-xl bg-white p-4 shadow-sm"
              >
                <span className="text-2xl">🧠</span>
                <div className="flex-1 min-w-0">
                  <h3 className="text-sm font-semibold text-gray-900">{a.model_name}</h3>
                  <p className="text-xs text-gray-500">
                    Framework: {a.framework} | Status: {a.status}
                  </p>
                </div>
                <button className="px-3 py-1 text-xs border border-brand-300 rounded-lg text-brand-600 hover:bg-brand-50">
                  Test
                </button>
                <span className="text-[10px] text-gray-400 font-mono">{a.adapter_id.slice(0, 8)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ================================================================= */}
      {/* Widgets Tab                                                       */}
      {/* ================================================================= */}
      {tab === "widgets" && <WidgetsTab />}
    </div>
  );
}
