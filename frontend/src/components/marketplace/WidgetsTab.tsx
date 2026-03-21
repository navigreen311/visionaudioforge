"use client";

import { useState } from "react";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface WidgetCard {
  id: string;
  title: string;
  description: string;
  icon: string;
}

type EmbedMode = "iframe" | "script";

interface WidgetConfig {
  theme: "light" | "dark";
  width: number;
  height: number;
  refreshInterval: number;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const WIDGETS: WidgetCard[] = [
  {
    id: "live_feed",
    title: "Live Feed Viewer",
    description: "Stream real-time camera feeds with overlay annotations.",
    icon: "📹",
  },
  {
    id: "alert_dashboard",
    title: "Alert Dashboard",
    description: "Display active alerts and incident history in a compact panel.",
    icon: "🚨",
  },
  {
    id: "analytics_chart",
    title: "Analytics Chart",
    description: "Embed interactive charts for detection metrics and trends.",
    icon: "📊",
  },
  {
    id: "search_bar",
    title: "Search Bar",
    description: "Add a semantic search box powered by your VAF index.",
    icon: "🔍",
  },
];

const DEFAULT_CONFIG: WidgetConfig = {
  theme: "dark",
  width: 480,
  height: 320,
  refreshInterval: 5,
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function generateEmbedUrl(widgetId: string, token: string): string {
  return `https://app.vaf.io/embed/${widgetId}?token=${token}`;
}

function generateIframeCode(url: string, cfg: WidgetConfig): string {
  return `<iframe\n  src="${url}"\n  width="${cfg.width}"\n  height="${cfg.height}"\n  frameborder="0"\n  allowtransparency="true"\n  style="border:0;border-radius:8px;"\n></iframe>`;
}

function generateScriptCode(url: string, cfg: WidgetConfig): string {
  return `<div id="vaf-widget"></div>\n<script src="https://cdn.vaf.io/embed.js"></script>\n<script>\n  VAF.embed({\n    target: "#vaf-widget",\n    src: "${url}",\n    width: ${cfg.width},\n    height: ${cfg.height},\n    theme: "${cfg.theme}",\n    refreshInterval: ${cfg.refreshInterval}\n  });\n</script>`;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function WidgetsTab() {
  const [selectedWidget, setSelectedWidget] = useState<string | null>(null);
  const [config, setConfig] = useState<WidgetConfig>({ ...DEFAULT_CONFIG });
  const [embedMode, setEmbedMode] = useState<EmbedMode>("iframe");
  const [generatedCode, setGeneratedCode] = useState<string>("");
  const [copied, setCopied] = useState(false);

  // -- Step 1: select a widget
  // -- Step 2: configure it
  // -- Step 3: generate embed code

  const handleGenerate = () => {
    if (!selectedWidget) return;
    const token = btoa(crypto.randomUUID());
    const url = generateEmbedUrl(selectedWidget, token);
    const code =
      embedMode === "iframe"
        ? generateIframeCode(url, config)
        : generateScriptCode(url, config);
    setGeneratedCode(code);
    setCopied(false);
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(generatedCode);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const previewUrl = selectedWidget
    ? generateEmbedUrl(
        selectedWidget,
        btoa(`preview-${selectedWidget}`)
      )
    : "";

  return (
    <div className="space-y-6">
      {/* ----------------------------------------------------------------- */}
      {/* Step 1 — Widget Cards                                             */}
      {/* ----------------------------------------------------------------- */}
      <div className="border border-gray-200 rounded-xl bg-white p-6 shadow-sm space-y-4">
        <h2 className="text-lg font-semibold text-gray-900">
          1. Choose a Widget
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {WIDGETS.map((w) => (
            <button
              key={w.id}
              onClick={() => {
                setSelectedWidget(w.id);
                setGeneratedCode("");
              }}
              className={`text-left p-4 rounded-xl border transition-all ${
                selectedWidget === w.id
                  ? "border-brand-600 bg-brand-50 ring-1 ring-brand-600"
                  : "border-gray-200 hover:border-gray-300 hover:shadow-sm"
              }`}
            >
              <span className="text-3xl">{w.icon}</span>
              <h3 className="mt-2 text-sm font-semibold text-gray-900">
                {w.title}
              </h3>
              <p className="mt-1 text-xs text-gray-500">{w.description}</p>
            </button>
          ))}
        </div>
      </div>

      {/* ----------------------------------------------------------------- */}
      {/* Step 2 — Per-widget Config                                        */}
      {/* ----------------------------------------------------------------- */}
      {selectedWidget && (
        <div className="border border-gray-200 rounded-xl bg-white p-6 shadow-sm space-y-4">
          <h2 className="text-lg font-semibold text-gray-900">
            2. Configure
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">
                Theme
              </label>
              <select
                value={config.theme}
                onChange={(e) =>
                  setConfig((c) => ({
                    ...c,
                    theme: e.target.value as "light" | "dark",
                  }))
                }
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:ring-1 focus:ring-brand-500 focus:outline-none"
              >
                <option value="light">Light</option>
                <option value="dark">Dark</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">
                Width (px)
              </label>
              <input
                type="number"
                min={200}
                max={1920}
                value={config.width}
                onChange={(e) =>
                  setConfig((c) => ({ ...c, width: Number(e.target.value) }))
                }
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:ring-1 focus:ring-brand-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">
                Height (px)
              </label>
              <input
                type="number"
                min={100}
                max={1080}
                value={config.height}
                onChange={(e) =>
                  setConfig((c) => ({ ...c, height: Number(e.target.value) }))
                }
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:ring-1 focus:ring-brand-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">
                Refresh (sec)
              </label>
              <input
                type="number"
                min={1}
                max={300}
                value={config.refreshInterval}
                onChange={(e) =>
                  setConfig((c) => ({
                    ...c,
                    refreshInterval: Number(e.target.value),
                  }))
                }
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:ring-1 focus:ring-brand-500 focus:outline-none"
              />
            </div>
          </div>
        </div>
      )}

      {/* ----------------------------------------------------------------- */}
      {/* Step 3 — Embed Code                                               */}
      {/* ----------------------------------------------------------------- */}
      {selectedWidget && (
        <div className="border border-gray-200 rounded-xl bg-white p-6 shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-900">
              3. Embed Code
            </h2>
            <div className="flex gap-1 rounded-lg border border-gray-200 p-0.5">
              {(["iframe", "script"] as const).map((mode) => (
                <button
                  key={mode}
                  onClick={() => {
                    setEmbedMode(mode);
                    setGeneratedCode("");
                  }}
                  className={`px-3 py-1 rounded-md text-xs font-medium transition-colors ${
                    embedMode === mode
                      ? "bg-brand-600 text-white"
                      : "text-gray-500 hover:text-gray-700"
                  }`}
                >
                  {mode === "iframe" ? "iFrame" : "Script Tag"}
                </button>
              ))}
            </div>
          </div>

          <button
            onClick={handleGenerate}
            className="px-6 py-2 bg-brand-600 text-white text-sm font-medium rounded-lg hover:bg-brand-700 transition-colors"
          >
            Generate Embed Code
          </button>

          {generatedCode && (
            <div className="space-y-3">
              {/* Code block */}
              <div className="relative">
                <pre className="bg-gray-900 text-green-400 text-xs font-mono p-4 rounded-lg overflow-x-auto whitespace-pre-wrap">
                  {generatedCode}
                </pre>
                <button
                  onClick={handleCopy}
                  className="absolute top-2 right-2 px-3 py-1 bg-gray-700 text-gray-200 text-xs rounded hover:bg-gray-600 transition-colors"
                >
                  {copied ? "Copied!" : "Copy Code"}
                </button>
              </div>

              {/* Live preview */}
              <div className="space-y-2">
                <h3 className="text-sm font-medium text-gray-700">
                  Live Preview
                </h3>
                <div className="rounded-lg border border-gray-200 overflow-hidden bg-gray-100 flex items-center justify-center">
                  <iframe
                    src={previewUrl}
                    width={Math.min(config.width, 600)}
                    height={Math.min(config.height, 400)}
                    frameBorder="0"
                    title="Widget preview"
                    className="rounded"
                    sandbox="allow-scripts allow-same-origin"
                  />
                </div>
              </div>

              {/* API key notice */}
              <p className="text-xs text-gray-500">
                Widgets require a valid API key.{" "}
                <a
                  href="/settings?tab=api-keys"
                  className="text-brand-600 underline hover:text-brand-700"
                >
                  Manage your API keys
                </a>
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
