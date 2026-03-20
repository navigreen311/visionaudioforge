"use client";

import { useEffect, useState } from "react";

interface PackInfo {
  pack_name: string;
  name: string;
  version: string;
  description: string;
  modules_used: string[];
}

interface PackDetails {
  info: PackInfo;
  pipelines: { name: string; description: string }[];
  alert_presets: { name: string; description: string }[];
  dashboard: { widgets: { type: string }[]; kpis: string[] };
  report_templates: string[];
  model_configs: Record<string, unknown>;
}

const PACK_ICONS: Record<string, string> = {
  security: "\u{1F6E1}\uFE0F",
  healthcare: "\u{1FA7A}",
  retail: "\u{1F6D2}",
  manufacturing: "\u{1F3ED}",
};

export default function VerticalsPage() {
  const [packs, setPacks] = useState<PackInfo[]>([]);
  const [installed, setInstalled] = useState<PackInfo[]>([]);
  const [selected, setSelected] = useState<PackDetails | null>(null);
  const [loading, setLoading] = useState(true);

  const workspaceId = "00000000-0000-0000-0000-000000000001";

  useEffect(() => {
    fetchPacks();
  }, []);

  async function fetchPacks() {
    setLoading(true);
    try {
      const [availRes, instRes] = await Promise.all([
        fetch("/api/verticals"),
        fetch(`/api/verticals/installed?workspace_id=${workspaceId}`),
      ]);
      setPacks(await availRes.json());
      setInstalled(await instRes.json());
    } catch {
      /* swallow for demo */
    } finally {
      setLoading(false);
    }
  }

  async function handleInstall(name: string) {
    await fetch(`/api/verticals/${name}/install?workspace_id=${workspaceId}`, {
      method: "POST",
    });
    fetchPacks();
  }

  async function handleUninstall(name: string) {
    await fetch(`/api/verticals/${name}/uninstall?workspace_id=${workspaceId}`, {
      method: "POST",
    });
    fetchPacks();
  }

  async function handleDetails(name: string) {
    const res = await fetch(`/api/verticals/${name}`);
    setSelected(await res.json());
  }

  const installedNames = new Set(installed.map((p) => p.pack_name));

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Vertical Packs</h1>
        <p className="mt-1 text-sm text-gray-500">
          Pre-configured pipelines, alert rules, dashboards, and report
          templates for specific industries.
        </p>
      </div>

      {/* Installed packs */}
      {installed.length > 0 && (
        <section>
          <h2 className="text-lg font-semibold text-gray-800 mb-3">
            Installed Packs
          </h2>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {installed.map((pack) => (
              <div
                key={pack.pack_name}
                className="rounded-xl border border-green-200 bg-green-50 p-5 shadow-sm"
              >
                <div className="flex items-center gap-3 mb-2">
                  <span className="text-2xl">
                    {PACK_ICONS[pack.pack_name] || "\u{1F4E6}"}
                  </span>
                  <div>
                    <h3 className="font-semibold text-gray-900">
                      {pack.name}
                    </h3>
                    <span className="text-xs text-green-700 font-medium">
                      v{pack.version} — Active
                    </span>
                  </div>
                </div>
                <p className="text-sm text-gray-600 mb-4">
                  {pack.description}
                </p>
                <div className="flex gap-2">
                  <button
                    onClick={() => handleDetails(pack.pack_name)}
                    className="rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50"
                  >
                    Details
                  </button>
                  <button
                    onClick={() => handleUninstall(pack.pack_name)}
                    className="rounded-lg border border-red-300 bg-white px-3 py-1.5 text-sm font-medium text-red-600 hover:bg-red-50"
                  >
                    Uninstall
                  </button>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Available packs gallery */}
      <section>
        <h2 className="text-lg font-semibold text-gray-800 mb-3">
          Available Packs
        </h2>
        {loading ? (
          <p className="text-sm text-gray-500">Loading...</p>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {packs.map((pack) => (
              <div
                key={pack.pack_name}
                className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm hover:shadow-md transition-shadow"
              >
                <div className="flex items-center gap-3 mb-2">
                  <span className="text-2xl">
                    {PACK_ICONS[pack.pack_name] || "\u{1F4E6}"}
                  </span>
                  <div>
                    <h3 className="font-semibold text-gray-900">
                      {pack.name}
                    </h3>
                    <span className="text-xs text-gray-500">
                      v{pack.version}
                    </span>
                  </div>
                </div>
                <p className="text-sm text-gray-600 mb-2">
                  {pack.description}
                </p>
                <div className="flex flex-wrap gap-1 mb-4">
                  {pack.modules_used.map((m) => (
                    <span
                      key={m}
                      className="rounded-full bg-brand-50 px-2 py-0.5 text-xs font-medium text-brand-700"
                    >
                      {m}
                    </span>
                  ))}
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => handleDetails(pack.pack_name)}
                    className="rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50"
                  >
                    Details
                  </button>
                  {installedNames.has(pack.pack_name) ? (
                    <span className="rounded-lg bg-green-100 px-3 py-1.5 text-sm font-medium text-green-700">
                      Installed
                    </span>
                  ) : (
                    <button
                      onClick={() => handleInstall(pack.pack_name)}
                      className="rounded-lg bg-brand-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-brand-700"
                    >
                      Install
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Pack detail modal/panel */}
      {selected && (
        <section className="rounded-xl border border-gray-200 bg-white p-6 shadow">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-bold text-gray-900">
              {selected.info.name} — Details
            </h2>
            <button
              onClick={() => setSelected(null)}
              className="rounded p-1 text-gray-400 hover:text-gray-600"
            >
              Close
            </button>
          </div>

          {/* Pipelines */}
          <div className="mb-4">
            <h3 className="font-semibold text-gray-800 mb-1">
              Pipelines ({selected.pipelines.length})
            </h3>
            <ul className="list-disc list-inside text-sm text-gray-600 space-y-0.5">
              {selected.pipelines.map((p) => (
                <li key={p.name}>
                  <span className="font-medium text-gray-700">{p.name}</span>{" "}
                  — {p.description}
                </li>
              ))}
            </ul>
          </div>

          {/* Alert presets */}
          <div className="mb-4">
            <h3 className="font-semibold text-gray-800 mb-1">
              Alert Presets ({selected.alert_presets.length})
            </h3>
            <ul className="list-disc list-inside text-sm text-gray-600 space-y-0.5">
              {selected.alert_presets.map((a) => (
                <li key={a.name}>
                  <span className="font-medium text-gray-700">{a.name}</span>{" "}
                  — {a.description}
                </li>
              ))}
            </ul>
          </div>

          {/* Dashboard widgets */}
          <div className="mb-4">
            <h3 className="font-semibold text-gray-800 mb-1">
              Dashboard Widgets
            </h3>
            <div className="flex flex-wrap gap-2">
              {selected.dashboard.widgets.map((w) => (
                <span
                  key={w.type}
                  className="rounded bg-gray-100 px-2 py-1 text-xs text-gray-700"
                >
                  {w.type}
                </span>
              ))}
            </div>
          </div>

          {/* KPIs */}
          <div className="mb-4">
            <h3 className="font-semibold text-gray-800 mb-1">KPIs</h3>
            <div className="flex flex-wrap gap-2">
              {selected.dashboard.kpis.map((k) => (
                <span
                  key={k}
                  className="rounded bg-blue-50 px-2 py-1 text-xs text-blue-700"
                >
                  {k}
                </span>
              ))}
            </div>
          </div>

          {/* Report templates */}
          <div>
            <h3 className="font-semibold text-gray-800 mb-1">
              Report Templates
            </h3>
            <ul className="list-disc list-inside text-sm text-gray-600 space-y-0.5">
              {selected.report_templates.map((t) => (
                <li key={t}>{t}</li>
              ))}
            </ul>
          </div>
        </section>
      )}
    </div>
  );
}
