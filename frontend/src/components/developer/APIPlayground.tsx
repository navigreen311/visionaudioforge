"use client";

import React, { useState } from "react";
import EndpointTester, { type EndpointDef } from "./EndpointTester";

interface APIModule {
  name: string;
  endpoints: EndpointDef[];
}

const API_MODULES: APIModule[] = [
  {
    name: "Health",
    endpoints: [
      { method: "GET", path: "/api/health", description: "Check API health status" },
    ],
  },
  {
    name: "Auth",
    endpoints: [
      { method: "POST", path: "/api/auth/login", description: "Authenticate and receive access tokens" },
      { method: "POST", path: "/api/auth/register", description: "Register a new user account" },
    ],
  },
  {
    name: "Vision",
    endpoints: [
      { method: "GET", path: "/api/vision/analyze", description: "Analyze images using vision models" },
    ],
  },
  {
    name: "Audio",
    endpoints: [
      { method: "POST", path: "/api/audio/analyze", description: "Analyze audio files and extract features" },
    ],
  },
  {
    name: "Pipeline",
    endpoints: [
      { method: "GET", path: "/api/pipeline/pipelines", description: "List all available pipelines" },
    ],
  },
  {
    name: "Alerts",
    endpoints: [
      { method: "GET", path: "/api/alerts", description: "Retrieve alert notifications" },
    ],
  },
  {
    name: "Search",
    endpoints: [
      { method: "GET", path: "/api/search/global", description: "Search across all resources globally" },
    ],
  },
  {
    name: "Assets",
    endpoints: [
      { method: "GET", path: "/api/assets", description: "List uploaded assets" },
    ],
  },
  {
    name: "Notifications",
    endpoints: [
      { method: "GET", path: "/api/notifications", description: "Retrieve user notifications" },
    ],
  },
];

function methodBadge(m: string) {
  const colors: Record<string, string> = {
    GET: "bg-green-100 text-green-800",
    POST: "bg-blue-100 text-blue-800",
    PATCH: "bg-amber-100 text-amber-800",
    DELETE: "bg-red-100 text-red-800",
  };
  return colors[m] || "bg-gray-100 text-gray-800";
}

export default function APIPlayground() {
  const [expandedModules, setExpandedModules] = useState<Set<string>>(new Set(["Health"]));
  const [selected, setSelected] = useState<EndpointDef | null>(null);

  const toggleModule = (name: string) => {
    setExpandedModules((prev) => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name);
      else next.add(name);
      return next;
    });
  };

  return (
    <div className="flex h-full">
      {/* Sidebar */}
      <div className="w-60 border-r border-gray-200 overflow-y-auto bg-white">
        <div className="p-4">
          <h2 className="text-xs font-semibold uppercase text-gray-400 tracking-wider mb-3">
            API Modules
          </h2>
          <nav className="space-y-1">
            {API_MODULES.map((mod) => (
              <div key={mod.name}>
                <button
                  onClick={() => toggleModule(mod.name)}
                  className="w-full flex items-center justify-between px-2 py-1.5 text-sm font-medium text-gray-700 rounded hover:bg-gray-50"
                >
                  <span>{mod.name}</span>
                  <svg
                    className={`w-4 h-4 text-gray-400 transition-transform ${
                      expandedModules.has(mod.name) ? "rotate-90" : ""
                    }`}
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                </button>
                {expandedModules.has(mod.name) && (
                  <div className="ml-2 mt-0.5 space-y-0.5">
                    {mod.endpoints.map((ep) => (
                      <button
                        key={ep.path + ep.method}
                        onClick={() => setSelected(ep)}
                        className={`w-full flex items-center gap-2 px-2 py-1 text-xs rounded ${
                          selected?.path === ep.path && selected?.method === ep.method
                            ? "bg-blue-50 text-blue-700"
                            : "text-gray-600 hover:bg-gray-50"
                        }`}
                      >
                        <span
                          className={`inline-block px-1.5 py-0.5 rounded text-[10px] font-bold leading-none ${methodBadge(
                            ep.method
                          )}`}
                        >
                          {ep.method}
                        </span>
                        <span className="truncate font-mono">{ep.path}</span>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </nav>
        </div>
      </div>

      {/* Main panel */}
      <div className="flex-1 overflow-y-auto p-6">
        {selected ? (
          <div>
            <div className="flex items-center gap-3 mb-2">
              <span
                className={`px-2 py-1 rounded text-xs font-bold ${methodBadge(selected.method)}`}
              >
                {selected.method}
              </span>
              <code className="text-sm font-mono text-gray-800">{selected.path}</code>
            </div>
            <p className="text-sm text-gray-500 mb-6">{selected.description}</p>
            <EndpointTester endpoint={selected} />
          </div>
        ) : (
          <div className="flex items-center justify-center h-full text-gray-400 text-sm">
            Select an endpoint from the sidebar to get started.
          </div>
        )}
      </div>
    </div>
  );
}
