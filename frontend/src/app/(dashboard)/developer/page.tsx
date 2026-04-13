"use client";

import React from "react";
import APIPlayground from "@/components/developer/APIPlayground";

export default function DeveloperPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">API Playground</h1>
        <p className="mt-1 text-sm text-gray-500">
          Explore and test API endpoints interactively. Select an endpoint, send
          requests, and view code snippets.
        </p>
      </div>

      <div className="bg-white rounded-lg shadow border border-gray-200 overflow-hidden" style={{ minHeight: "70vh" }}>
        <APIPlayground />
      </div>
    </div>
  );
}
