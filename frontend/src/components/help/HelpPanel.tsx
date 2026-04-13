"use client";

import React, { useState } from "react";

const quickLinks = [
  { label: "Getting Started", href: "/docs/getting-started" },
  { label: "Pipeline Builder", href: "/docs/pipeline" },
  { label: "Audio Analysis", href: "/docs/audio" },
  { label: "API Reference", href: "/docs/api" },
  { label: "Keyboard Shortcuts", href: "/docs/shortcuts" },
];

export default function HelpPanel() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");

  return (
    <>
      {/* Floating trigger button */}
      <button
        onClick={() => setOpen(true)}
        className="fixed bottom-6 right-6 z-[60] flex h-10 w-10 items-center justify-center rounded-full bg-gray-800 text-white shadow-lg hover:bg-gray-700 transition-colors"
        aria-label="Open help"
      >
        ?
      </button>

      {/* Slide-over panel */}
      {open && (
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 z-[65] bg-black/20"
            onClick={() => setOpen(false)}
          />

          <div className="fixed right-0 top-0 z-[70] flex h-full w-80 flex-col bg-white shadow-2xl">
            {/* Header */}
            <div className="flex items-center justify-between border-b px-4 py-3">
              <h2 className="text-lg font-semibold text-gray-900">Help</h2>
              <button
                onClick={() => setOpen(false)}
                className="text-gray-400 hover:text-gray-600 transition-colors"
                aria-label="Close help panel"
              >
                <svg
                  className="h-5 w-5"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M6 18L18 6M6 6l12 12"
                  />
                </svg>
              </button>
            </div>

            {/* Search */}
            <div className="px-4 py-3">
              <input
                type="text"
                placeholder="Search help articles..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-200 outline-none"
              />
            </div>

            {/* Quick links */}
            <div className="flex-1 overflow-y-auto px-4">
              <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-gray-500">
                Quick Links
              </h3>
              <ul className="space-y-1">
                {quickLinks.map((link) => (
                  <li key={link.href}>
                    <a
                      href={link.href}
                      className="block rounded-lg px-3 py-2 text-sm text-gray-700 hover:bg-gray-100 transition-colors"
                    >
                      {link.label}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </>
      )}
    </>
  );
}
